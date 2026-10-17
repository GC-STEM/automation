"""Test coverage truth tables separately from whether targets were found."""

from dataclasses import replace

import pytest
from d2l_test_helpers import NOW, Harness

from gc_stem.d2l.coverage import CourseResult, ToolCoverage


def base(harness: Harness, **changes: object) -> ToolCoverage:
    """Create a genuinely empty, completely enumerated selected tool."""
    result = ToolCoverage(
        harness.inventory.courses[0],
        "content",
        True,
        True,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        (),
        (),
        NOW,
        NOW,
    )
    return replace(result, **changes)


@pytest.mark.parametrize(
    "changes,status",
    [
        ({}, "COMPLETE"),
        ({"known_total": None}, "COMPLETE"),
        ({"enumeration_complete": False}, "ERROR"),
        ({"reason_codes": ("ACCESS_DENIED",)}, "ERROR"),
        ({"objects_discovered": 1, "objects_failed": 1}, "ERROR"),
        ({"fields_scanned": 1, "fields_unavailable": 1}, "PARTIAL"),
        (
            {"objects_discovered": 1, "objects_scanned": 1, "known_total": 1},
            "COMPLETE",
        ),
        ({"known_total": 1}, "ERROR"),
        ({"selected": False}, "NOT_SELECTED"),
        ({"not_applicable_reason": "VERIFIED_DISABLED"}, "NOT_APPLICABLE"),
    ],
)
def test_tool_coverage_classification(
    harness: Harness, changes: dict, status: str
) -> None:
    """Only trustworthy complete evidence can yield complete tool coverage."""
    assert base(harness, **changes).status == status


@pytest.mark.parametrize(
    "changes",
    [
        {"objects_discovered": 1},
        {"fields_scanned": True},
        {"fields_unavailable": -1},
        {"known_total": -1},
        {"selected": False, "fields_scanned": 1},
        {"not_applicable_reason": "VERIFIED_DISABLED", "fields_scanned": 1},
    ],
)
def test_contradictory_evidence_is_rejected(
    harness: Harness, changes: dict
) -> None:
    """Counts and selection/applicability invariants are checked locally."""
    with pytest.raises((ValueError, TypeError)):
        base(harness, **changes)


@pytest.mark.parametrize(
    "found,complete,match_status",
    [
        (False, True, "NOT_FOUND"),
        (False, False, "UNKNOWN"),
        (True, False, "FOUND"),
        (True, True, "FOUND"),
    ],
)
def test_match_and_coverage_are_independent(
    harness: Harness, found: bool, complete: bool, match_status: str
) -> None:
    """Finding a target never repairs a coverage gap."""
    writer = harness.writer()
    try:
        results = harness.complete_results(writer)
        first = results[0]
        tools = tuple(
            replace(item, enumeration_complete=complete)
            if item.selected
            else item
            for item in first.tools
        )
        result = CourseResult(first.course, tools, int(found), int(found))
        assert result.match_status == match_status
        assert result.coverage_status == ("COMPLETE" if complete else "ERROR")
    finally:
        writer.close()


def test_successfully_empty_selected_tool_can_make_course_partial(
    harness: Harness,
) -> None:
    """A verified empty tool counts as completed work beside another failure."""
    writer = harness.writer()
    try:
        first = harness.complete_results(writer)[0]
        tools = tuple(
            replace(
                item,
                selected=True,
                enumeration_complete=False,
                known_total=None,
                reason_codes=("ACCESS_DENIED",),
            )
            if item.tool == "files"
            else item
            for item in first.tools
        )
        result = CourseResult(first.course, tools, 0, 0)
        assert (
            result.coverage_status == "PARTIAL"
            and result.match_status == "UNKNOWN"
        )
    finally:
        writer.close()


def test_all_baseline_tools_are_required(harness: Harness) -> None:
    """Missing report rows cannot quietly shrink declared coverage."""
    with pytest.raises(ValueError):
        CourseResult(harness.inventory.courses[0], (base(harness),), 0, 0)
