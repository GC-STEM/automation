"""Provide synthetic authored data and clocks for provider-independent tests."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import get_args

from gc_stem.d2l.client import CapabilitySet, ClientInfo, ToolCapability
from gc_stem.d2l.config import load_settings
from gc_stem.d2l.courses import load_courses
from gc_stem.d2l.coverage import CourseResult, ToolCoverage
from gc_stem.d2l.models import (
    AuthoredField,
    CourseRef,
    DiscoveryEnd,
    ObjectRef,
    ReadResult,
    RepresentationOutcome,
    ToolKey,
)
from gc_stem.d2l.reports import ReportWriter

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class Clock:
    """Advance simulated time instead of sleeping in recovery tests."""

    def __init__(self) -> None:
        """Start with a deterministic monotonic and wall-clock origin."""
        self.seconds = 0.0
        self.waits: list[float] = []

    def sleep(self, seconds: float) -> None:
        """Record a wait and advance monotonically."""
        self.waits.append(seconds)
        self.seconds += seconds

    def monotonic(self) -> float:
        """Return simulated elapsed time."""
        return self.seconds

    def now(self) -> datetime:
        """Return the corresponding aware UTC time."""
        return NOW + timedelta(seconds=self.seconds)


class Harness:
    """Create a local inventory, immutable settings, and report writer."""

    def __init__(self, root: Path) -> None:
        """Write two synthetic course rows and nonsecret test configuration."""
        self.root = root
        self.config = root / "d2l.toml"
        self.source = root / "courses.csv"
        with self.source.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["org_unit_id", "course_name"])
            writer.writerows(
                [("123", "First course"), ("456", "Second course")]
            )
        self.config.write_text(
            "schema_version = 1\n[instance]\n"
            'base_url = "https://tenant.example/"\n'
            '[courses]\nfile = "courses.csv"\n[search]\n'
            'terms = ["needle"]\nmode = "text"\n'
            '[crawl]\ntools = ["content"]\ndelay_seconds = 0\n'
            '[output]\ndirectory = "reports"\n',
            encoding="utf-8",
        )
        self.clock = Clock()
        self.configure()

    def configure(self, **overrides: object) -> None:
        """Reload settings/inventory using supported dotted override names."""
        self.settings = load_settings(self.config, overrides, {}, cwd=self.root)
        self.inventory = load_courses(self.settings)

    def ref(
        self,
        object_key: str = "item-1",
        *,
        tool: ToolKey = "content",
        course: CourseRef | None = None,
        paths: tuple[str, ...] = ("Module 1",),
    ) -> ObjectRef:
        """Build one explicitly scoped authored object."""
        owner = course or self.inventory.courses[0]
        return ObjectRef(
            owner,
            tool,
            object_key,
            "page",
            "Authored page",
            paths,
            owner.course_url,
            "container",
            "synthetic_platform_id",
        )

    def text(
        self, ref: ObjectRef, value: str = "needle", path: str = "body"
    ) -> AuthoredField:
        """Build a successful plain authored-text field."""
        return AuthoredField(
            ref,
            path,
            "text",
            (RepresentationOutcome("text", "AVAILABLE", value),),
            "synthetic_authored_text",
        )

    def writer(self, run_id: str = "test-run") -> ReportWriter:
        """Create a real spool identifying the provider as synthetic."""
        return ReportWriter(
            self.settings,
            self.inventory,
            client_info=ClientInfo("synthetic-fixture"),
            run_id=run_id,
            started_at=NOW,
        )

    def complete_results(
        self, writer: ReportWriter
    ) -> tuple[CourseResult, ...]:
        """Record complete text-field or empty evidence for report tests."""
        courses = []
        for course in self.inventory.courses:
            count, locations = writer.course_counts(course.org_unit_id)
            tools = []
            for tool in get_args(ToolKey):
                selected = tool in self.settings.crawl.tools
                scanned = count if tool == "content" else 0
                coverage = ToolCoverage(
                    course,
                    tool,
                    selected,
                    selected,
                    scanned,
                    scanned,
                    0,
                    0,
                    locations if scanned else 0,
                    0,
                    scanned if selected else None,
                    (),
                    () if selected else ("NOT_SELECTED",),
                    NOW,
                    NOW,
                )
                tools.append(coverage)
                writer.record_coverage(coverage)
            courses.append(CourseResult(course, tuple(tools), count, locations))
        return tuple(courses)


class FixtureClient:
    """Replay explicit synthetic data; never make browser/network requests."""

    info = ClientInfo("synthetic-fixture")

    def __init__(self, harness: Harness) -> None:
        """Start with verified-empty synthetic tools and configurable faults."""
        self.harness = harness
        self.discovery: dict[tuple[str, ToolKey], list[list[object]]] = {}
        self.reads: dict[tuple[str, str, ToolKey, str], object] = {}
        self.capability_overrides: dict[ToolKey, ToolCapability] = {}
        self.read_calls: list[tuple[str, str, ToolKey, str]] = []
        self.discovery_calls = 0
        self.auth_calls = 0
        self.auth_failures: list[BaseException | None] = []
        self.close_error: BaseException | None = None
        self.closed = False

    def authenticate(self) -> None:
        """Simulate normal login and injected authentication faults."""
        self.auth_calls += 1
        if self.auth_failures:
            failure = self.auth_failures.pop(0)
            if failure is not None:
                raise failure

    def capabilities(
        self, course: CourseRef, tools: tuple[ToolKey, ...]
    ) -> CapabilitySet:
        """Describe every requested synthetic adapter explicitly."""
        return CapabilitySet(
            tuple(
                self.capability_overrides.get(
                    tool, ToolCapability(tool, "SUPPORTED")
                )
                for tool in tools
            )
        )

    def discover(
        self, course: CourseRef, tool: ToolKey
    ) -> Iterator[ObjectRef | DiscoveryEnd]:
        """Replay discovery attempts with explicit terminal and fault events."""
        self.discovery_calls += 1
        attempts = self.discovery.get((course.org_unit_id, tool))
        if attempts:
            events = attempts.pop(0) if len(attempts) > 1 else attempts[0]
        else:
            events = [DiscoveryEnd(True, 0)]
        for event in events:
            if isinstance(event, BaseException):
                raise event
            yield event

    def read_object(self, ref: ObjectRef) -> ReadResult:
        """Return authored values or a deterministic scoped failure."""
        self.read_calls.append(ref.identity)
        result = self.reads.get(ref.identity)
        if isinstance(result, list):
            result = result.pop(0)
        if isinstance(result, BaseException):
            raise result
        return (
            result
            if result is not None
            else ReadResult(ref, (self.harness.text(ref),))
        )

    def close(self) -> None:
        """Record cleanup and optionally inject a cleanup failure."""
        self.closed = True
        if self.close_error is not None:
            raise self.close_error

    def __enter__(self) -> FixtureClient:
        """Enter the synthetic provider's lifetime."""
        return self

    def __exit__(self, *exception: object) -> None:
        """Close without swallowing errors."""
        self.close()
