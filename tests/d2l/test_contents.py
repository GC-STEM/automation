"""Exercise complete, partial, failed, and canceled synthetic scan pipelines."""

import csv
import json
from dataclasses import replace

import pytest
from d2l_test_helpers import FixtureClient, Harness

from gc_stem.d2l.client import (
    AccessDenied,
    AuthenticationFailed,
    AuthenticationRequired,
    CapabilitySet,
    ReadTimeout,
    ToolCapability,
    TransientReadError,
)
from gc_stem.d2l.content import RunResult, scan_courses
from gc_stem.d2l.models import (
    AuthoredField,
    DiscoveryEnd,
    FieldGap,
    ReadResult,
    RepresentationOutcome,
)


def run(
    harness: Harness, client: FixtureClient, **options: object
) -> RunResult:
    """Scan with actual reports and a deterministic clock."""
    return scan_courses(
        harness.settings,
        harness.inventory,
        client,
        harness.writer(),
        sleep=harness.clock.sleep,
        monotonic=harness.clock.monotonic,
        now=harness.clock.now,
        **options,
    )


def one_object(harness: Harness, client: FixtureClient) -> object:
    """Configure one complete authored object in the first course."""
    ref = harness.ref()
    client.discovery[("123", "content")] = [[ref, DiscoveryEnd(True, 1)]]
    return ref


def test_complete_pipeline_retains_matches_and_all_tool_rows(
    harness: Harness,
) -> None:
    """A synthetic read yields a finding with truthful complete scope."""
    client = FixtureClient(harness)
    ref = one_object(harness, client)
    result = run(harness, client)
    assert result.state == "COMPLETE" and result.exit_code == 0
    assert result.courses[0].match_status == "FOUND"
    assert result.courses[1].match_status == "NOT_FOUND"
    assert client.read_calls == [ref.identity] and client.closed
    assert all(len(course.tools) == 7 for course in result.courses)
    assert result.outputs.summary.is_file()


def test_verified_empty_tools_can_complete(harness: Harness) -> None:
    """A complete zero-item enumeration is distinct from an unknown total."""
    result = run(harness, FixtureClient(harness))
    assert result.state == "COMPLETE"
    assert all(item.match_status == "NOT_FOUND" for item in result.courses)
    assert result.courses[0].tools[0].known_total == 0


def test_denial_is_unknown_and_other_courses_continue(harness: Harness) -> None:
    """A denied tool is never converted to a clean negative."""
    client = FixtureClient(harness)
    client.discovery[("123", "content")] = [[AccessDenied()]]
    result = run(harness, client)
    assert result.exit_code == 3 and result.state == "PARTIAL"
    assert result.courses[0].match_status == "UNKNOWN"
    assert result.courses[1].coverage_status == "COMPLETE"


def test_found_and_partial_can_coexist(harness: Harness) -> None:
    """A successful representation does not hide an unavailable one."""
    harness.configure(**{"search.mode": "all"})
    client = FixtureClient(harness)
    ref = one_object(harness, client)
    field = AuthoredField(
        ref,
        "body",
        "html",
        (
            RepresentationOutcome(
                "source", "UNAVAILABLE", reason="AUTH_SECRET"
            ),
            RepresentationOutcome("dom", "AVAILABLE", "needle"),
            RepresentationOutcome("text", "AVAILABLE", "needle"),
        ),
        "synthetic_html",
    )
    client.reads[ref.identity] = ReadResult(ref, (field,))
    result = run(harness, client)
    course = result.courses[0]
    assert (
        course.match_status == "FOUND" and course.coverage_status == "PARTIAL"
    )
    assert course.tools[0].objects_failed == 1
    assert course.tools[0].fields_scanned == 2
    assert "AUTH_SECRET" not in result.outputs.summary.read_text(
        encoding="utf-8"
    )


def test_wholly_missing_field_is_explicit(harness: Harness) -> None:
    """A reader cannot lose an authored-field family without a coverage gap."""
    client = FixtureClient(harness)
    ref = one_object(harness, client)
    client.reads[ref.identity] = ReadResult(
        ref, missing_fields=(FieldGap("feedback", "AUTH_SECRET"),)
    )
    result = run(harness, client)
    assert result.courses[0].match_status == "UNKNOWN"
    assert result.courses[0].tools[0].fields_unavailable == 1


@pytest.mark.parametrize(
    "events,code",
    [
        ([], "ENUMERATION_INCOMPLETE"),
        (
            [DiscoveryEnd(False, reason_codes=("PAGINATION_UNKNOWN",))],
            "PAGINATION_UNKNOWN",
        ),
        ([DiscoveryEnd(True, 1)], "TOTAL_MISMATCH"),
        (
            [DiscoveryEnd(True, 0), DiscoveryEnd(True, 0)],
            "EVENT_AFTER_TERMINAL",
        ),
    ],
)
def test_untrustworthy_discovery_is_incomplete(
    harness: Harness, events: list, code: str
) -> None:
    """Untrustworthy discovery evidence creates explicit coverage gaps."""
    client = FixtureClient(harness)
    client.discovery[("123", "content")] = [events]
    result = run(harness, client)
    coverage = result.courses[0].tools[0]
    assert code in coverage.reason_codes
    assert (
        coverage.status == "ERROR"
        and result.courses[0].match_status == "UNKNOWN"
    )


def test_duplicate_objects_merge_locations_and_read_once(
    harness: Harness,
) -> None:
    """Discovery replay retains alternate paths without repeated work."""
    client = FixtureClient(harness)
    ref = harness.ref()
    duplicate = replace(ref, paths=("Module 2",))
    client.discovery[("123", "content")] = [
        [ref, duplicate, DiscoveryEnd(True, 1)]
    ]
    result = run(harness, client)
    assert client.read_calls == [ref.identity]
    with result.outputs.matches.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert json.loads(rows[0]["object_path"]) == ["Module 1", "Module 2"]


def test_transient_discovery_replays_without_duplicate_reads(
    harness: Harness,
) -> None:
    """Restarted enumeration preserves identities already completed."""
    client = FixtureClient(harness)
    ref = harness.ref()
    client.discovery[("123", "content")] = [
        [ref, ReadTimeout()],
        [ref, DiscoveryEnd(True, 1)],
    ]
    result = run(harness, client)
    assert result.state == "COMPLETE" and client.read_calls == [ref.identity]


def test_transient_object_read_retries(harness: Harness) -> None:
    """Retrying a safe object read does not count it as multiple objects."""
    client = FixtureClient(harness)
    ref = one_object(harness, client)
    client.reads[ref.identity] = [
        ReadTimeout(),
        ReadResult(ref, (harness.text(ref),)),
    ]
    result = run(harness, client)
    assert result.state == "COMPLETE"
    assert len(client.read_calls) == 2
    assert result.courses[0].tools[0].objects_discovered == 1


def test_reauthentication_resumes_unfinished_object(harness: Harness) -> None:
    """Session expiry preserves earlier work and retries the unfinished read."""
    client = FixtureClient(harness)
    ref = one_object(harness, client)
    client.reads[ref.identity] = [
        AuthenticationRequired(),
        ReadResult(ref, (harness.text(ref),)),
    ]
    result = run(harness, client)
    assert result.state == "COMPLETE" and client.auth_calls == 2


def test_failed_initial_authentication_marks_all_scope_unfinished(
    harness: Harness,
) -> None:
    """Authentication failure cannot become a successful empty run."""
    client = FixtureClient(harness)
    client.auth_failures = [AuthenticationFailed()]
    result = run(harness, client)
    assert result.state == "FAILED" and result.exit_code == 1
    assert all(course.match_status == "UNKNOWN" for course in result.courses)
    assert not client.read_calls and client.closed


def test_verified_not_applicable_is_different_from_denied(
    harness: Harness,
) -> None:
    """Verified disabled tools can complete the declared course scope."""
    client = FixtureClient(harness)
    client.capability_overrides["content"] = ToolCapability(
        "content", "NOT_APPLICABLE", "VERIFIED_DISABLED"
    )
    result = run(harness, client)
    assert result.state == "COMPLETE" and client.discovery_calls == 0
    assert result.courses[0].tools[0].status == "NOT_APPLICABLE"


def test_missing_capability_cannot_shrink_scope(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every selected tool must have explicit capability evidence."""
    client = FixtureClient(harness)
    monkeypatch.setattr(client, "capabilities", lambda *args: CapabilitySet(()))
    result = run(harness, client)
    assert result.state == "FAILED"
    assert result.diagnostics[0]["code"] == "CLIENT_CONTRACT_ERROR"


@pytest.mark.parametrize("kind", ["course", "tool", "url", "port"])
def test_cross_scope_reference_stops_the_session(
    harness: Harness, kind: str
) -> None:
    """Wrong identities and foreign review links are fatal provider faults."""
    client = FixtureClient(harness)
    ref = harness.ref()
    bad = {
        "course": replace(ref, course=harness.inventory.courses[1]),
        "tool": replace(ref, tool="files"),
        "url": replace(ref, page_url="https://foreign.invalid/"),
        "port": replace(ref, page_url="https://tenant.example:0/"),
    }[kind]
    client.discovery[("123", "content")] = [[bad]]
    result = run(harness, client)
    assert result.state == "FAILED" and not client.read_calls
    assert (
        client.closed
        and result.diagnostics[0]["code"] == "UNSAFE_ACTION_BLOCKED"
    )


def test_read_result_review_url_is_checked_again(harness: Harness) -> None:
    """Updated display metadata cannot smuggle an external review link."""
    client = FixtureClient(harness)
    ref = one_object(harness, client)
    bad = replace(ref, page_url="https://foreign.invalid/")
    client.reads[ref.identity] = ReadResult(bad, (harness.text(bad),))
    assert run(harness, client).state == "FAILED"


def test_object_limit_is_a_gap_not_a_clean_negative(harness: Harness) -> None:
    """Discovery truncation is visible even when some objects succeeded."""
    harness.configure(**{"crawl.max_objects_per_tool": 1})
    client = FixtureClient(harness)
    first, second = harness.ref("1"), harness.ref("2")
    client.discovery[("123", "content")] = [
        [first, second, DiscoveryEnd(True, 2)]
    ]
    result = run(harness, client)
    assert result.state == "PARTIAL"
    assert "OBJECT_LIMIT" in result.courses[0].tools[0].reason_codes
    assert client.read_calls == [first.identity]


def test_duplicate_only_discovery_is_bounded(harness: Harness) -> None:
    """An adapter looping through the same identity cannot hang the scan."""
    harness.configure(**{"crawl.max_objects_per_tool": 1})
    client = FixtureClient(harness)
    ref = harness.ref()
    client.discovery[("123", "content")] = [[ref] * 10]
    result = run(harness, client)
    assert "DISCOVERY_EVENT_LIMIT" in result.courses[0].tools[0].reason_codes
    assert len(client.read_calls) == 1


def test_size_limit_preserves_unknown_zero_match(harness: Harness) -> None:
    """A target beyond a configured field limit is not reported as absent."""
    harness.configure(**{"crawl.max_field_characters": 3})
    client = FixtureClient(harness)
    one_object(harness, client)
    result = run(harness, client)
    assert result.courses[0].match_status == "UNKNOWN"
    assert "FIELD_SIZE_LIMIT" in result.courses[0].tools[0].reason_codes


def test_cancellation_preserves_acquired_findings(harness: Harness) -> None:
    """Canceled work remains incomplete alongside acquired matches."""
    client = FixtureClient(harness)
    one_object(harness, client)
    result = run(harness, client, cancelled=lambda: client.discovery_calls > 1)
    assert result.state == "CANCELLED" and result.exit_code == 130
    assert result.courses[0].match_status == "FOUND"
    assert result.courses[1].match_status == "UNKNOWN"
    assert result.outputs.summary.is_file()
    assert client.closed


def test_keyboard_interrupt_finalizes_acquired_findings(
    harness: Harness,
) -> None:
    """Ctrl+C after one object saves that finding and canceled coverage."""
    client = FixtureClient(harness)
    ref = harness.ref()
    client.discovery[("123", "content")] = [[ref, KeyboardInterrupt()]]
    result = run(harness, client)
    assert (
        result.state == "CANCELLED"
        and result.courses[0].match_status == "FOUND"
    )
    assert (
        json.loads(result.outputs.summary.read_text(encoding="utf-8"))[
            "run_state"
        ]
        == "CANCELLED"
    )


def test_excessive_cooldown_defers_entire_run_without_more_reads(
    harness: Harness,
) -> None:
    """Switching objects/courses cannot bypass an advertised server cooldown."""
    client = FixtureClient(harness)
    ref = one_object(harness, client)
    client.reads[ref.identity] = TransientReadError(61)
    result = run(harness, client)
    assert result.state == "PARTIAL" and result.exit_code == 3
    assert client.read_calls == [ref.identity]
    assert client.discovery_calls == 1
    assert all(course.match_status == "UNKNOWN" for course in result.courses)


def test_client_cleanup_failure_is_not_reported_complete(
    harness: Harness,
) -> None:
    """Cleanup faults remain visible and do not skip manifest finalization."""
    client = FixtureClient(harness)
    client.close_error = RuntimeError("AUTH_SECRET")
    result = run(harness, client)
    assert result.state == "FAILED" and result.outputs.summary.is_file()
    assert "AUTH_SECRET" not in result.outputs.summary.read_text(
        encoding="utf-8"
    )


def test_unexpected_provider_exception_is_sanitized(harness: Harness) -> None:
    """A defect is fatal and identifiable without copying a response body."""
    client = FixtureClient(harness)
    ref = one_object(harness, client)
    client.reads[ref.identity] = RuntimeError("AUTH_SECRET")
    result = run(harness, client)
    assert result.state == "FAILED"
    assert result.diagnostics[0] == {
        "code": "UNEXPECTED_FAILURE",
        "type": "RuntimeError",
    }
    assert "AUTH_SECRET" not in result.outputs.summary.read_text(
        encoding="utf-8"
    )


def test_output_failure_overrides_scan_success(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed read is not a completed run when final reports fail."""
    client = FixtureClient(harness)
    one_object(harness, client)
    writer = harness.writer()
    monkeypatch.setattr(
        writer,
        "_publish",
        lambda *args: (_ for _ in ()).throw(OSError("AUTH_SECRET")),
    )
    result = scan_courses(
        harness.settings,
        harness.inventory,
        client,
        writer,
        now=harness.clock.now,
        sleep=harness.clock.sleep,
        monotonic=harness.clock.monotonic,
    )
    assert (
        result.state == "FAILED"
        and result.exit_code == 1
        and result.outputs is None
    )
    assert result.saved_paths and all(
        path.is_file() for path in result.saved_paths
    )
    assert not (writer.run_directory / "summary.json").exists()
