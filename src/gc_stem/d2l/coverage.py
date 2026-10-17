"""Aggregate scan coverage independently from whether any target was found."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import get_args

from .models import CourseCoverage, CourseRef, MatchStatus, ToolKey, ToolStatus


@dataclass(frozen=True, slots=True)
class ToolCoverage:
    """Hold final tool evidence; status is derived from counts and gaps.

    fields_scanned counts successful field/representation pairs. Every
    discovered object must be scanned, failed (including partial), or excluded.
    A verified not-applicable reason is distinct from access/structure failure.
    """

    course: CourseRef
    tool: ToolKey
    selected: bool
    enumeration_complete: bool
    objects_discovered: int
    objects_scanned: int
    objects_failed: int
    objects_excluded: int
    fields_scanned: int
    fields_unavailable: int
    known_total: int | None
    reason_codes: tuple[str, ...]
    exclusions: tuple[str, ...]
    started_at: datetime
    finished_at: datetime
    not_applicable_reason: str | None = None

    def __post_init__(self) -> None:
        """Reject contradictory evidence before it reaches reporting."""
        if self.tool not in get_args(ToolKey):
            raise ValueError("Unsupported coverage tool.")
        if not isinstance(self.selected, bool) or not isinstance(
            self.enumeration_complete, bool
        ):
            raise TypeError(
                "Coverage selection and enumeration must be booleans."
            )
        counts = (
            self.objects_discovered,
            self.objects_scanned,
            self.objects_failed,
            self.objects_excluded,
            self.fields_scanned,
            self.fields_unavailable,
        )
        if any(type(value) is not int or value < 0 for value in counts):
            raise ValueError("Coverage counts must be nonnegative integers.")
        if sum(counts[1:4]) != self.objects_discovered:
            raise ValueError("Object coverage counts must reconcile.")
        if self.known_total is not None and (
            type(self.known_total) is not int or self.known_total < 0
        ):
            raise ValueError("known_total must be unknown or nonnegative.")
        if not self.selected and any(counts):
            raise ValueError("Unselected tools cannot include scanned work.")
        if self.not_applicable_reason is not None and (
            not self.selected or any(counts) or not self.not_applicable_reason
        ):
            raise ValueError(
                "Not-applicable evidence must describe an empty tool."
            )
        for instant in (self.started_at, self.finished_at):
            if instant.tzinfo is None or instant.utcoffset() is None:
                raise ValueError(
                    "Coverage timestamps must include a time zone."
                )
        if self.finished_at < self.started_at:
            raise ValueError("Coverage end time precedes start time.")

    @property
    def status(self) -> ToolStatus:
        """Classify completion, applicability, partial work, and failure."""
        if not self.selected:
            return "NOT_SELECTED"
        if self.not_applicable_reason is not None:
            return "NOT_APPLICABLE"
        if (
            self.enumeration_complete
            and not self.reason_codes
            and not self.objects_failed
            and not self.fields_unavailable
            and (
                self.known_total is None
                or self.known_total == self.objects_discovered
            )
        ):
            return "COMPLETE"
        if self.fields_scanned or self.objects_scanned:
            return "PARTIAL"
        return "ERROR"


@dataclass(frozen=True, slots=True)
class CourseResult:
    """Combine all baseline tools with field-level match/location counts."""

    course: CourseRef
    tools: tuple[ToolCoverage, ...]
    match_count: int
    matched_locations: int

    def __post_init__(self) -> None:
        """Require every tool once and internally consistent match counts."""
        keys = tuple(item.tool for item in self.tools)
        if len(keys) != len(set(keys)) or set(keys) != set(get_args(ToolKey)):
            raise ValueError("Course results require every baseline tool once.")
        identity = self.course.tenant_origin, self.course.org_unit_id
        if any(
            (item.course.tenant_origin, item.course.org_unit_id) != identity
            for item in self.tools
        ):
            raise ValueError("Coverage belongs to another course.")
        if not any(item.selected for item in self.tools):
            raise ValueError("At least one tool must be selected.")
        if (
            type(self.match_count) is not int
            or type(self.matched_locations) is not int
            or not 0 <= self.matched_locations <= self.match_count
            or bool(self.match_count) != bool(self.matched_locations)
        ):
            raise ValueError("Match and location counts must reconcile.")

    @property
    def coverage_status(self) -> CourseCoverage:
        """Evaluate declared scope while retaining explicit exclusions."""
        selected = tuple(item for item in self.tools if item.selected)
        if all(
            item.status in ("COMPLETE", "NOT_APPLICABLE") for item in selected
        ):
            return "COMPLETE"
        if any(
            item.status in ("COMPLETE", "NOT_APPLICABLE", "PARTIAL")
            for item in selected
        ):
            return "PARTIAL"
        return "ERROR"

    @property
    def match_status(self) -> MatchStatus:
        """Permit a negative result only when declared coverage is complete."""
        if self.match_count:
            return "FOUND"
        return "NOT_FOUND" if self.coverage_status == "COMPLETE" else "UNKNOWN"
