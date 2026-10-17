"""Coordinate authored-field reads, matching, coverage, and final reports.

The client owns verified read routes, authenticated identity, authored-field
scope, navigation/page limits, and browser-specific readiness. This module
owns sequential operations, bounded recovery, object/event/field limits,
coverage evidence, cancellation, and provider-independent report records.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args
from urllib.parse import urlsplit

from .client import (
    AccessDenied,
    AuthenticationRequired,
    BrightspaceReadClient,
    CapabilitySet,
    ClientContractError,
    ClientError,
    CooldownExceeded,
    OperatorCancelled,
    ReadController,
    ToolCapability,
    TransientReadError,
    UnsafeActionBlocked,
    UnsupportedView,
)
from .config import Settings
from .courses import Inventory
from .coverage import CourseResult, ToolCoverage
from .models import (
    CourseRef,
    DiscoveryEnd,
    ObjectRef,
    ReadResult,
    RunState,
    ToolKey,
)
from .reports import OutputPaths, ReportError, ReportWriter
from .search import SearchPlan, compile_targets, match_field

_SCOPED = (AccessDenied, UnsupportedView, TransientReadError)
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


@dataclass(frozen=True, slots=True)
class RunResult:
    """Describe actual completion and saved paths without raw reads."""

    state: RunState
    exit_code: int
    courses: tuple[CourseResult, ...]
    outputs: OutputPaths | None
    saved_paths: tuple[Path, ...]
    diagnostics: tuple[dict[str, str], ...]


@dataclass(slots=True)
class _ToolProgress:
    """Accumulate one tool's evidence, including unfinished discovered work."""

    course: CourseRef
    tool: ToolKey
    selected: bool
    started_at: datetime
    finished_at: datetime
    enumeration_complete: bool = False
    discovered: int = 0
    scanned: int = 0
    fields_scanned: int = 0
    fields_unavailable: int = 0
    known_total: int | None = None
    reasons: list[str] = field(default_factory=list)
    not_applicable: str | None = None

    def reason(self, code: str) -> None:
        """Retain each sanitized gap code once in first-occurrence order."""
        if not isinstance(code, str) or _CODE.fullmatch(code) is None:
            raise ClientContractError
        if code not in self.reasons:
            self.reasons.append(code)

    def snapshot(self) -> ToolCoverage:
        """Classify every discovered object, including interrupted reads."""
        return ToolCoverage(
            course=self.course,
            tool=self.tool,
            selected=self.selected,
            enumeration_complete=self.enumeration_complete,
            objects_discovered=self.discovered,
            objects_scanned=self.scanned,
            objects_failed=self.discovered - self.scanned,
            objects_excluded=0,
            fields_scanned=self.fields_scanned,
            fields_unavailable=self.fields_unavailable,
            known_total=self.known_total,
            reason_codes=tuple(self.reasons),
            exclusions=() if self.selected else ("NOT_SELECTED",),
            started_at=self.started_at,
            finished_at=self.finished_at,
            not_applicable_reason=self.not_applicable,
        )


def _verify_ref(ref: ObjectRef, course: CourseRef, tool: ToolKey) -> None:
    """Reject cross-course/tool references and foreign review-link origins."""
    if not isinstance(ref, ObjectRef):
        raise ClientContractError
    if (
        ref.course.tenant_origin != course.tenant_origin
        or ref.course.org_unit_id != course.org_unit_id
        or ref.tool != tool
    ):
        raise UnsafeActionBlocked
    raw = ref.page_url
    try:
        parts, origin = urlsplit(raw), urlsplit(course.tenant_origin)
        valid = (
            parts.scheme == "https"
            and parts.hostname == origin.hostname
            and (parts.port or 443) == (origin.port or 443)
            and parts.port != 0
            and parts.username is None
            and parts.password is None
            and not any(
                character.isspace() or ord(character) < 32 for character in raw
            )
            and "\\" not in raw
        )
    except ValueError:
        valid = False
    if not valid:
        raise UnsafeActionBlocked
    home = re.fullmatch(r"/d2l/(?:p/)?home/([0-9]+)/?", parts.path)
    if home is not None and home[1].lstrip("0") != course.org_unit_id:
        raise UnsafeActionBlocked


def _close_iterator(
    iterator: Iterator[ObjectRef | DiscoveryEnd] | None,
) -> None:
    """Close generator-backed discovery promptly when a scope ends early."""
    close = getattr(iterator, "close", None)
    if close is not None:
        close()


def _scan_tool(
    progress: _ToolProgress,
    capability: ToolCapability,
    settings: Settings,
    client: BrightspaceReadClient,
    controller: ReadController,
    writer: ReportWriter,
    plan: SearchPlan,
) -> None:
    """Process one tool while keeping failures distinct from empty results."""
    if capability.state != "SUPPORTED":
        if capability.reason_code is None:
            raise ClientContractError
        progress.reason(capability.reason_code)
        if capability.state == "NOT_APPLICABLE":
            progress.not_applicable = capability.reason_code
            progress.known_total = 0
        return
    course, tool = progress.course, progress.tool
    iterator: Iterator[ObjectRef | DiscoveryEnd] | None = None
    seen: set[tuple[str, str, ToolKey, str]] = set()
    terminal = False
    events = 0

    def next_event() -> ObjectRef | DiscoveryEnd:
        """Restart replayable discovery after session/transient failures."""
        nonlocal iterator
        if iterator is None:
            iterator = iter(client.discover(course, tool))
        try:
            return next(iterator)
        except (AuthenticationRequired, TransientReadError):
            _close_iterator(iterator)
            iterator = None
            raise

    try:
        while True:
            controller.checkpoint()
            try:
                event = controller.call(next_event)
            except StopIteration:
                break
            events += 1
            if events > 2 * settings.crawl.max_objects_per_tool + 1:
                progress.reason("DISCOVERY_EVENT_LIMIT")
                progress.enumeration_complete = False
                break
            if terminal:
                progress.reason("EVENT_AFTER_TERMINAL")
                progress.enumeration_complete = False
                break
            if isinstance(event, DiscoveryEnd):
                terminal = True
                progress.enumeration_complete = event.enumeration_complete
                progress.known_total = event.known_total
                for code in event.reason_codes:
                    progress.reason(code)
                continue
            _verify_ref(event, course, tool)
            if event.identity in seen:
                writer.merge_object_paths(event)
                continue
            if len(seen) >= settings.crawl.max_objects_per_tool:
                progress.discovered += 1
                progress.reason("OBJECT_LIMIT")
                progress.enumeration_complete = False
                break
            seen.add(event.identity)
            progress.discovered += 1
            writer.merge_object_paths(event)
            try:
                read = controller.call(lambda: client.read_object(event))
                if (
                    not isinstance(read, ReadResult)
                    or read.owner.identity != event.identity
                ):
                    raise ClientContractError
                _verify_ref(read.owner, course, tool)
                complete = not read.missing_fields
                if read.missing_fields:
                    progress.fields_unavailable += len(read.missing_fields)
                    progress.reason("FIELD_UNAVAILABLE")
                for authored in read.fields:
                    controller.checkpoint()
                    _verify_ref(authored.owner, course, tool)
                    batch = match_field(
                        authored,
                        plan,
                        settings.search.mode,
                        max_characters=settings.crawl.max_field_characters,
                    )
                    progress.fields_scanned += len(batch.searched)
                    for match in batch.matches:
                        writer.record_match(match)
                    progress.fields_unavailable += len(batch.gaps)
                    complete = complete and batch.complete
                    for gap in batch.gaps:
                        progress.reason(gap.reason_code)
                if complete:
                    progress.scanned += 1
            except _SCOPED as error:
                progress.reason(error.code)
    except _SCOPED as error:
        progress.reason(error.code)
        progress.enumeration_complete = False
    except BaseException:
        progress.enumeration_complete = False
        raise
    finally:
        _close_iterator(iterator)
    if not terminal:
        progress.reason("ENUMERATION_INCOMPLETE")
        progress.enumeration_complete = False
    if progress.known_total is not None and progress.enumeration_complete:
        if progress.known_total != progress.discovered:
            progress.reason("TOTAL_MISMATCH")
            progress.enumeration_complete = False


def scan_courses(
    settings: Settings,
    inventory: Inventory,
    client: BrightspaceReadClient,
    writer: ReportWriter,
    *,
    cancelled: Callable[[], bool] = lambda: False,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> RunResult:
    """Run a sequential scan using an explicitly supplied read client.

    Args:
        settings: Validated effective configuration.
        inventory: Validated inventory returned by load_courses().
        client: Provider obeying the read-only, scope, and navigation contracts.
        writer: New ReportWriter for the same settings/inventory.
        cancelled: Pollable cancellation request; Ctrl+C is also supported.
        sleep: Injectable wait implementation for recovery tests.
        monotonic: Injectable monotonic clock for pacing tests.
        now: Injectable aware wall clock for reproducible report fixtures.

    Returns:
        Actual run state, exit code, all obtainable coverage, and only saved
        report/artifact paths. This function closes both client and writer.

    Raises:
        ValueError: If the caller mixes writer/settings/inventory instances.

    Discovery can replay after a transient failure; identities are read once
    and additional paths are retained. Event count is bounded to twice the
    configured object limit plus one, preventing duplicate-only infinite
    discovery. Actual page/navigation bounds must be enforced by the provider.
    """
    if writer.settings != settings or writer.inventory != inventory:
        raise ValueError("Writer and scan inputs must describe the same run.")
    plan = compile_targets(settings.search.terms, settings.search.ignore_case)
    controller = ReadController(
        settings.crawl,
        client.authenticate,
        sleep=sleep,
        monotonic=monotonic,
        cancelled=cancelled,
    )
    ledgers: dict[str, dict[ToolKey, _ToolProgress]] = {}
    for course in inventory.courses:
        tools: dict[ToolKey, _ToolProgress] = {}
        for tool in get_args(ToolKey):
            selected = tool in settings.crawl.tools
            progress = _ToolProgress(
                course, tool, selected, writer.started_at, writer.started_at
            )
            if selected:
                progress.reason("NOT_STARTED")
            tools[tool] = progress
        ledgers[course.org_unit_id] = tools
    diagnostics: list[dict[str, str]] = []
    state: RunState = "FAILED"
    results: tuple[CourseResult, ...] = ()
    outputs: OutputPaths | None = None
    try:
        controller.checkpoint()
        client.authenticate()
        for course in inventory.courses:
            controller.checkpoint()
            try:
                capabilities = controller.call(
                    lambda: client.capabilities(course, settings.crawl.tools)
                )
            except _SCOPED as error:
                for tool in settings.crawl.tools:
                    progress = ledgers[course.org_unit_id][tool]
                    progress.reasons.clear()
                    progress.reason(error.code)
                    progress.finished_at = now()
                continue
            if not isinstance(capabilities, CapabilitySet) or {
                item.tool for item in capabilities.tools
            } != set(settings.crawl.tools):
                raise ClientContractError
            lookup = {item.tool: item for item in capabilities.tools}
            for tool in settings.crawl.tools:
                controller.checkpoint()
                progress = ledgers[course.org_unit_id][tool]
                progress.reasons.clear()
                progress.started_at = now()
                try:
                    _scan_tool(
                        progress,
                        lookup[tool],
                        settings,
                        client,
                        controller,
                        writer,
                        plan,
                    )
                finally:
                    progress.finished_at = now()
        state = "COMPLETE"
    except (OperatorCancelled, KeyboardInterrupt):
        state = "CANCELLED"
        diagnostics.append({"code": "CANCELLED"})
    except CooldownExceeded:
        state = "PARTIAL"
        diagnostics.append({"code": "COOLDOWN_EXCEEDED"})
    except ClientError as error:
        diagnostics.append({"code": error.code})
    except ReportError:
        diagnostics.append({"code": "REPORT_OUTPUT_FAILED"})
    except Exception as error:
        diagnostics.append(
            {"code": "UNEXPECTED_FAILURE", "type": type(error).__name__}
        )
    finally:
        try:
            client.close()
        except Exception:
            state = "FAILED"
            diagnostics.append({"code": "CLIENT_CLEANUP_FAILED"})
    stop_code = {"CANCELLED": "CANCELLED", "PARTIAL": "COOLDOWN_EXCEEDED"}.get(
        state, "RUN_FAILED"
    )
    ended = now()
    try:
        collected: list[CourseResult] = []
        for course in inventory.courses:
            for progress in ledgers[course.org_unit_id].values():
                if (
                    progress.selected
                    and (
                        "NOT_STARTED" in progress.reasons
                        or not progress.enumeration_complete
                    )
                    and progress.not_applicable is None
                    and state in ("FAILED", "CANCELLED", "PARTIAL")
                ):
                    if "NOT_STARTED" in progress.reasons:
                        progress.reasons.remove("NOT_STARTED")
                    progress.reason(stop_code)
                    progress.finished_at = ended
            snapshots = tuple(
                item.snapshot() for item in ledgers[course.org_unit_id].values()
            )
            counts = writer.course_counts(course.org_unit_id)
            collected.append(CourseResult(course, snapshots, *counts))
            for coverage in snapshots:
                writer.record_coverage(coverage)
        results = tuple(collected)
        if state == "COMPLETE" and any(
            item.coverage_status != "COMPLETE" for item in results
        ):
            state = "PARTIAL"
        outputs = writer.finalize(
            state, results, finished_at=ended, diagnostics=tuple(diagnostics)
        )
    except Exception:
        state = "FAILED"
        diagnostics.append({"code": "REPORT_FINALIZATION_FAILED"})
    finally:
        try:
            writer.close()
        except Exception:
            state = "FAILED"
            diagnostics.append({"code": "REPORT_CLEANUP_FAILED"})
    return RunResult(
        state,
        {"COMPLETE": 0, "PARTIAL": 3, "FAILED": 1, "CANCELLED": 130}[state],
        results,
        outputs,
        writer.saved_paths,
        tuple(diagnostics),
    )
