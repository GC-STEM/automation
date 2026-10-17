"""Spool bounded results and publish deterministic CSV files and a manifest.

Each writer owns a new directory. A SQLite spool stores report records, never
raw authored fields or authentication. CSV publication never replaces files;
summary.json is published last. Filesystems must support local hard links.
"""

from __future__ import annotations

import csv
import json
import os
import platform
import re
import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, get_args
from unicodedata import category
from uuid import uuid4

from .client import ClientInfo
from .config import Settings
from .courses import Inventory
from .coverage import CourseResult, ToolCoverage
from .models import Match, ObjectRef, RunState, ToolKey
from .search import SearchPlan, compile_targets

MATCH_COLUMNS = (
    "run_id",
    "org_unit_id",
    "course_name",
    "course_url",
    "tool",
    "object_type",
    "object_id",
    "object_title",
    "object_path",
    "page_url",
    "location_kind",
    "field_path",
    "representation",
    "target_id",
    "target",
    "occurrence_count",
    "first_offset",
    "context",
    "extraction_method",
)
COVERAGE_COLUMNS = (
    "run_id",
    "org_unit_id",
    "course_name",
    "tool",
    "selected",
    "status",
    "enumeration_complete",
    "objects_discovered",
    "objects_scanned",
    "objects_failed",
    "objects_excluded",
    "fields_scanned",
    "fields_unavailable",
    "known_total",
    "reason_codes",
    "exclusions",
    "started_at",
    "finished_at",
)


class ReportError(OSError):
    """Indicate an output/contract failure using a sanitized diagnostic code."""


@dataclass(frozen=True, slots=True)
class OutputPaths:
    """Name only the three successfully finalized reports."""

    run_directory: Path
    matches: Path
    coverage: Path
    summary: Path


def utc_text(value: datetime) -> str:
    """Serialize an aware timestamp as an unambiguous UTC ISO string."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Report timestamps must include a time zone.")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def csv_safe(value: object) -> object:
    """Prefix untrusted formula/control-leading strings with an apostrophe.

    Whitespace before =, +, -, or @ does not bypass escaping. Quoting is
    handled separately by csv.writer. Nonstring trusted counts are unchanged.
    """
    if not isinstance(value, str):
        return value
    index = 0
    controls = False
    while index < len(value) and (
        value[index].isspace() or category(value[index]) in ("Cc", "Cf")
    ):
        controls = controls or category(value[index]) in ("Cc", "Cf")
        index += 1
    if controls or index < len(value) and value[index] in "=+-@":
        return "'" + value
    return value


def _json_default(value: object) -> str:
    """Convert only the path/time types included in known settings records."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return utc_text(value)
    raise TypeError("Unsupported report metadata type.")


def _coverage_row(item: ToolCoverage, run_id: str) -> dict[str, object]:
    """Convert coverage evidence to the fixed report schema."""
    return {
        "run_id": run_id,
        "org_unit_id": item.course.org_unit_id,
        "course_name": item.course.name,
        "tool": item.tool,
        "selected": item.selected,
        "status": item.status,
        "enumeration_complete": item.enumeration_complete,
        "objects_discovered": item.objects_discovered,
        "objects_scanned": item.objects_scanned,
        "objects_failed": item.objects_failed,
        "objects_excluded": item.objects_excluded,
        "fields_scanned": item.fields_scanned,
        "fields_unavailable": item.fields_unavailable,
        "known_total": item.known_total,
        "reason_codes": list(item.reason_codes),
        "exclusions": list(item.exclusions),
        "started_at": utc_text(item.started_at),
        "finished_at": utc_text(item.finished_at),
    }


class ReportWriter:
    """Own a unique report run with a disk spool and bounded row payloads."""

    def __init__(
        self,
        settings: Settings,
        inventory: Inventory,
        *,
        client_info: ClientInfo,
        plan: SearchPlan | None = None,
        run_id: str | None = None,
        started_at: datetime | None = None,
        source_commit: str | None = None,
    ) -> None:
        """Create a unique run directory after local preflight has succeeded.

        Args:
            settings: Validated nonsecret effective settings.
            inventory: Validated source metadata and unique course identities.
            client_info: Actual provider/browser identity; synthetic clients
                must identify themselves as synthetic.
            plan: Compiled settings targets, otherwise compiled here.
            run_id: Optional safe unique identifier for reproducible fixtures.
            started_at: Aware start time, otherwise the current UTC time.
            source_commit: Explicit verified source commit, otherwise null.

        Raises:
            FileExistsError: If a supplied run ID already exists.
            OSError: If output creation fails.
            ValueError: If identity/metadata arguments are inconsistent.
        """
        self.settings, self.inventory = settings, inventory
        self.plan = plan or compile_targets(
            settings.search.terms, settings.search.ignore_case
        )
        expected = compile_targets(
            settings.search.terms, settings.search.ignore_case
        )
        if self.plan.targets != expected.targets:
            raise ValueError("Report targets do not match effective settings.")
        self.started_at = (
            datetime.now(UTC) if started_at is None else started_at
        )
        utc_text(self.started_at)
        self.run_id = (
            run_id
            if run_id is not None
            else (
                self.started_at.strftime("%Y%m%dT%H%M%S%fZ")
                + "-"
                + uuid4().hex[:8]
            )
        )
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", self.run_id) is None:
            raise ValueError("run_id must be a safe directory identifier.")
        if (
            source_commit is not None
            and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source_commit)
            is None
        ):
            raise ValueError(
                "source_commit must be an explicit full commit hash."
            )
        self.client_info, self.source_commit = client_info, source_commit
        self._courses = {
            item.org_unit_id: index
            for index, item in enumerate(inventory.courses)
        }
        if not self._courses or len(self._courses) != len(inventory.courses):
            raise ValueError("Report inventory must contain unique courses.")
        if any(
            item.tenant_origin != settings.instance.tenant_origin
            for item in inventory.courses
        ):
            raise ValueError(
                "Report inventory is outside the configured tenant."
            )
        self._targets = {item.target_id: item for item in self.plan.targets}
        self._target_order = {
            item.target_id: index
            for index, item in enumerate(self.plan.targets)
        }
        self._tools = {
            tool: index for index, tool in enumerate(get_args(ToolKey))
        }
        self._connection: sqlite3.Connection | None = None
        self._attempted = self._finalized = False
        settings.output.directory.mkdir(parents=True, exist_ok=True)
        self.run_directory = settings.output.directory / self.run_id
        self.run_directory.mkdir(mode=0o700)
        self._spool = self.run_directory / "spool.sqlite3"
        descriptor = os.open(
            self._spool, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600
        )
        os.close(descriptor)
        try:
            self._connection = sqlite3.connect(
                self._spool, isolation_level=None
            )
            self._connection.executescript(
                "CREATE TABLE objects (course TEXT, tool TEXT, "
                "object TEXT, paths TEXT, "
                "PRIMARY KEY(course,tool,object));"
                "CREATE TABLE matches (course TEXT, course_order INTEGER, "
                "tool TEXT, tool_order INTEGER, object TEXT, field TEXT, "
                "representation TEXT, representation_order INTEGER, "
                "target TEXT, target_order INTEGER, payload TEXT, "
                "PRIMARY KEY(course,tool,object,field,representation,target));"
                "CREATE TABLE coverage (course TEXT, course_order INTEGER, "
                "tool TEXT, "
                "tool_order INTEGER, payload TEXT, PRIMARY KEY(course,tool));"
            )
        except sqlite3.Error:
            self.close()
            raise ReportError("REPORT_INITIALIZATION_FAILED") from None

    def _database(self) -> sqlite3.Connection:
        """Require a live writer that has not begun final publication."""
        if self._connection is None or self._attempted:
            raise ReportError("REPORT_WRITER_CLOSED")
        return self._connection

    def merge_object_paths(self, ref: ObjectRef) -> None:
        """Retain additional containing paths without duplicating findings."""
        connection = self._database()
        course = ref.course.org_unit_id
        if (
            course not in self._courses
            or ref.course.tenant_origin != self.settings.instance.tenant_origin
        ):
            raise ReportError("MATCH_SCOPE_MISMATCH")
        try:
            existing = connection.execute(
                "SELECT paths FROM objects WHERE "
                "course=? AND tool=? AND object=?",
                (course, ref.tool, ref.object_key),
            ).fetchone()
            paths = [] if existing is None else json.loads(existing[0])
            paths = list(dict.fromkeys([*paths, *ref.paths]))
            connection.execute(
                "INSERT INTO objects VALUES(?,?,?,?) "
                "ON CONFLICT(course,tool,object) "
                "DO UPDATE SET paths=excluded.paths",
                (
                    course,
                    ref.tool,
                    ref.object_key,
                    json.dumps(paths, ensure_ascii=False),
                ),
            )
        except sqlite3.Error:
            raise ReportError("REPORT_SPOOL_FAILED") from None

    def record_match(self, match: Match) -> None:
        """Spool one unique bounded match, rejecting scope/target conflicts."""
        connection = self._database()
        ref = match.owner
        course = ref.course.org_unit_id
        if (
            ref.tool not in self.settings.crawl.tools
            or self._targets.get(match.target.target_id) != match.target
        ):
            raise ReportError("MATCH_SCOPE_MISMATCH")
        self.merge_object_paths(ref)
        payload = {
            "run_id": self.run_id,
            "org_unit_id": course,
            "course_name": ref.course.name,
            "course_url": ref.course.course_url,
            "tool": ref.tool,
            "object_type": ref.object_type,
            "object_id": ref.object_key,
            "object_title": ref.title,
            "page_url": ref.page_url,
            "location_kind": ref.location_kind,
            "field_path": match.field_path,
            "representation": match.representation,
            "target_id": match.target.target_id,
            "target": match.target.text,
            "occurrence_count": match.occurrence_count,
            "first_offset": match.first_offset,
            "context": match.context,
            "extraction_method": match.extraction_method,
        }
        try:
            connection.execute(
                "INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    course,
                    self._courses[course],
                    ref.tool,
                    self._tools[ref.tool],
                    ref.object_key,
                    match.field_path,
                    match.representation,
                    ("source", "dom", "text", "url").index(
                        match.representation
                    ),
                    match.target.target_id,
                    self._target_order[match.target.target_id],
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
        except sqlite3.IntegrityError:
            raise ReportError("DUPLICATE_MATCH") from None
        except sqlite3.Error:
            raise ReportError("REPORT_SPOOL_FAILED") from None

    def course_counts(self, course_id: str) -> tuple[int, int]:
        """Count rows and unique tool/object/field locations from the spool."""
        connection = self._database()
        try:
            rows = connection.execute(
                "SELECT count(*) FROM matches WHERE course=?", (course_id,)
            ).fetchone()[0]
            locations = connection.execute(
                "SELECT count(*) FROM (SELECT DISTINCT tool,object,field "
                "FROM matches WHERE course=?)",
                (course_id,),
            ).fetchone()[0]
            return rows, locations
        except sqlite3.Error:
            raise ReportError("REPORT_SPOOL_FAILED") from None

    def record_coverage(self, coverage: ToolCoverage) -> None:
        """Spool one final baseline tool row for a validated course."""
        connection = self._database()
        course = coverage.course.org_unit_id
        if (
            course not in self._courses
            or coverage.course.tenant_origin
            != self.settings.instance.tenant_origin
            or coverage.selected != (coverage.tool in self.settings.crawl.tools)
        ):
            raise ReportError("COVERAGE_SCOPE_MISMATCH")
        try:
            connection.execute(
                "INSERT INTO coverage VALUES(?,?,?,?,?)",
                (
                    course,
                    self._courses[course],
                    coverage.tool,
                    self._tools[coverage.tool],
                    json.dumps(
                        _coverage_row(coverage, self.run_id), ensure_ascii=False
                    ),
                ),
            )
        except sqlite3.Error:
            raise ReportError("COVERAGE_SPOOL_FAILED") from None

    def _match_rows(self) -> Iterator[dict[str, object]]:
        """Yield stable rows, joining the final retained object paths."""
        if self._connection is None:
            raise ReportError("REPORT_WRITER_CLOSED")
        cursor = self._connection.execute(
            "SELECT m.payload,o.paths FROM matches m JOIN objects o "
            "ON m.course=o.course AND m.tool=o.tool AND m.object=o.object "
            "ORDER BY m.course_order,m.tool_order,m.object,m.field,"
            "m.representation_order,m.target_order"
        )
        for payload, paths in cursor:
            item = json.loads(payload)
            item["object_path"] = json.loads(paths)
            yield item

    def _coverage_rows(self) -> Iterator[dict[str, object]]:
        """Yield coverage in inventory order and baseline tool order."""
        if self._connection is None:
            raise ReportError("REPORT_WRITER_CLOSED")
        cursor = self._connection.execute(
            "SELECT payload FROM coverage ORDER BY course_order,tool_order"
        )
        for (payload,) in cursor:
            yield json.loads(payload)

    def _publish(self, filename: str, write: Callable[[IO[str]], None]) -> Path:
        """Publish complete UTF-8 output with atomic no-replacement linking."""
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=self.run_directory,
                prefix="temporary-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                write(temporary)
                temporary.flush()
                os.fsync(temporary.fileno())
            destination = self.run_directory / filename
            os.link(temporary_path, destination)
            return destination
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _csv(
        self,
        filename: str,
        columns: tuple[str, ...],
        rows: Iterator[dict[str, object]],
    ) -> Path:
        """Serialize fixed-schema CSV with explicit list and boolean formats."""

        def write(stream: IO[str]) -> None:
            """Write rows sequentially without materializing all matches."""
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(columns)
            for row in rows:
                values: list[object] = []
                for key in columns:
                    value = row[key]
                    if isinstance(value, list):
                        value = json.dumps(value, ensure_ascii=False)
                    elif isinstance(value, bool):
                        value = str(value).lower()
                    values.append(csv_safe(value))
                writer.writerow(values)

        return self._publish(filename, write)

    def finalize(
        self,
        state: RunState,
        courses: tuple[CourseResult, ...],
        *,
        finished_at: datetime | None = None,
        diagnostics: tuple[dict[str, str], ...] = (),
    ) -> OutputPaths:
        """Publish CSVs, dispose the spool, and publish summary.json last.

        Reject false COMPLETE states, missing tool rows, inconsistent counts,
        and repeat finalization. On failure, existing CSVs/spool remain as
        recoverable artifacts and no completion manifest is fabricated.
        """
        connection = self._database()
        if state not in get_args(RunState):
            raise ValueError("Unsupported run state.")
        if tuple(item.course for item in courses) != self.inventory.courses:
            raise ReportError("COURSE_RESULTS_MISMATCH")
        if state == "COMPLETE" and any(
            item.coverage_status != "COMPLETE" for item in courses
        ):
            raise ReportError("INCOMPLETE_COVERAGE")
        expected_coverage = len(courses) * len(get_args(ToolKey))
        if (
            connection.execute("SELECT count(*) FROM coverage").fetchone()[0]
            != expected_coverage
        ):
            raise ReportError("MISSING_COVERAGE_ROWS")
        for item in courses:
            if self.course_counts(item.course.org_unit_id) != (
                item.match_count,
                item.matched_locations,
            ):
                raise ReportError("MATCH_COUNTS_MISMATCH")
            for tool in item.tools:
                matched_objects = connection.execute(
                    "SELECT count(DISTINCT object) FROM matches "
                    "WHERE course=? AND tool=?",
                    (item.course.org_unit_id, tool.tool),
                ).fetchone()[0]
                matched_pairs = connection.execute(
                    "SELECT count(*) FROM (SELECT DISTINCT "
                    "object,field,representation "
                    "FROM matches WHERE course=? AND tool=?)",
                    (item.course.org_unit_id, tool.tool),
                ).fetchone()[0]
                if (
                    matched_objects > tool.objects_discovered
                    or matched_pairs > tool.fields_scanned
                ):
                    raise ReportError("COVERAGE_COUNTS_MISMATCH")
                row = connection.execute(
                    "SELECT payload FROM coverage WHERE course=? AND tool=?",
                    (item.course.org_unit_id, tool.tool),
                ).fetchone()
                if row is None or json.loads(row[0]) != _coverage_row(
                    tool, self.run_id
                ):
                    raise ReportError("COVERAGE_RESULTS_MISMATCH")
        ended = finished_at or datetime.now(UTC)
        if ended < self.started_at:
            raise ValueError("Report end time precedes start time.")
        for diagnostic in diagnostics:
            if (
                set(diagnostic) - {"code", "type"}
                or re.fullmatch(
                    r"[A-Z][A-Z0-9_]{0,63}", diagnostic.get("code", "")
                )
                is None
                or (
                    "type" in diagnostic
                    and not diagnostic["type"].isidentifier()
                )
            ):
                raise ValueError(
                    "Diagnostics require stable codes and exception types."
                )
        try:
            distribution_version = version("gc-stem-automation")
        except PackageNotFoundError:
            distribution_version = None
        summary = {
            "schema_version": 1,
            "run_id": self.run_id,
            "run_state": state,
            "started_at": utc_text(self.started_at),
            "finished_at": utc_text(ended),
            "software": {
                "distribution": "gc-stem-automation",
                "version": distribution_version,
                "version_reason": None
                if distribution_version
                else "not_installed",
                "commit": self.source_commit,
                "commit_reason": None if self.source_commit else "not_supplied",
                "python": platform.python_version(),
                "provider": self.client_info.provider,
                "browser": self.client_info.browser_version,
            },
            "inventory": {
                "file": str(self.inventory.source_path),
                "sha256": self.inventory.sha256,
                "format": self.inventory.source_format,
                "sheet": self.inventory.sheet_name,
                "row_count": self.inventory.row_count,
                "duplicate_count": self.inventory.duplicate_count,
                "diagnostics": [
                    asdict(item) for item in self.inventory.diagnostics
                ],
            },
            "settings": asdict(self.settings),
            "scope": {
                "tools": list(self.settings.crawl.tools),
                "excluded_tools": [
                    key
                    for key in get_args(ToolKey)
                    if key not in self.settings.crawl.tools
                ],
                "include_hidden": self.settings.crawl.include_hidden,
                "mode": self.settings.search.mode,
                "exclusions": [
                    "learner_data",
                    "binary_files",
                    "external_destinations",
                ],
                "navigation_limits_enforced_by": "provider",
            },
            "counts": {
                "courses": len(courses),
                "match_rows": sum(item.match_count for item in courses),
                "matched_locations": sum(
                    item.matched_locations for item in courses
                ),
                "location_key": "course/tool/object/field",
            },
            "courses": [
                {
                    "org_unit_id": item.course.org_unit_id,
                    "course_name": item.course.name,
                    "course_url": item.course.course_url,
                    "source_rows": list(item.course.source_rows),
                    "match_status": item.match_status,
                    "coverage_status": item.coverage_status,
                    "match_count": item.match_count,
                    "matched_locations": item.matched_locations,
                    "tools": [
                        _coverage_row(tool, self.run_id) for tool in item.tools
                    ],
                }
                for item in courses
            ],
            "diagnostics": list(diagnostics),
            "outputs": {
                "matches": "matches.csv",
                "coverage": "coverage.csv",
                "summary": "summary.json",
            },
            "csv_formula_policy": (
                "apostrophe_prefix_for_formula_or_control_leading_strings"
            ),
            "json_policy": (
                "settings_and_course_metadata_keep_original_values; "
                "no_raw_authored_fields"
            ),
        }
        self._attempted = True
        try:
            matches = self._csv(
                "matches.csv", MATCH_COLUMNS, self._match_rows()
            )
            coverage = self._csv(
                "coverage.csv", COVERAGE_COLUMNS, self._coverage_rows()
            )
            connection.close()
            self._connection = None
            self._spool.unlink()
            manifest = self._publish(
                "summary.json",
                lambda stream: json.dump(
                    summary,
                    stream,
                    ensure_ascii=False,
                    indent=2,
                    default=_json_default,
                ),
            )
        except (OSError, sqlite3.Error, TypeError, ValueError):
            raise ReportError("REPORT_FINALIZATION_FAILED") from None
        self._finalized = True
        return OutputPaths(self.run_directory, matches, coverage, manifest)

    @property
    def saved_paths(self) -> tuple[Path, ...]:
        """List only actual finalized or recoverable files in this run."""
        return tuple(
            path
            for path in (
                self.run_directory / "matches.csv",
                self.run_directory / "coverage.csv",
                self.run_directory / "summary.json",
                self._spool,
            )
            if path.is_file()
        )

    def close(self) -> None:
        """Close the spool; preserve it when finalization did not dispose it."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> ReportWriter:
        """Enter a managed writer lifetime."""
        return self

    def __exit__(self, *exception: object) -> None:
        """Close without suppressing errors or manufacturing completion."""
        self.close()
