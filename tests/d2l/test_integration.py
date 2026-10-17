"""Verify scope, matching, recovery, and cancellation across modules."""

import re
from dataclasses import replace
from typing import get_args

import pytest
from d2l_test_helpers import FixtureClient, Harness

from gc_stem.cli import main
from gc_stem.d2l.client import (
    CooldownExceeded,
    ReadController,
    TransientReadError,
    UnsafeActionBlocked,
)
from gc_stem.d2l.content import RunResult, scan_courses
from gc_stem.d2l.models import (
    AuthoredField,
    DiscoveryEnd,
    RepresentationOutcome,
    Target,
    ToolKey,
)
from gc_stem.d2l.search import SearchPlan, compile_targets, match_field


def scan(
    harness: Harness, client: FixtureClient, **options: object
) -> RunResult:
    """Use the real spool/coordinator with deterministic time and no network."""
    return scan_courses(
        harness.settings,
        harness.inventory,
        client,
        harness.writer(),
        now=harness.clock.now,
        sleep=harness.clock.sleep,
        monotonic=harness.clock.monotonic,
        **options,
    )


def test_manually_supplied_regex_plan_is_rejected() -> None:
    """Calling the dataclass directly cannot enable arbitrary regex search."""
    with pytest.raises(ValueError, match="literal"):
        SearchPlan((Target("T001", "needle"),), (re.compile(".*"),))


@pytest.mark.parametrize("mode", ["dom", "all"])
def test_declared_html_url_outcome_participates(
    harness: Harness, mode: str
) -> None:
    """An explicitly supplied URL value is included in applicable modes."""
    field = AuthoredField(
        harness.ref(),
        "body",
        "html",
        (
            RepresentationOutcome("source", "AVAILABLE", "<a>title</a>"),
            RepresentationOutcome("dom", "AVAILABLE", "<a>title</a>"),
            RepresentationOutcome("text", "AVAILABLE", "title"),
            RepresentationOutcome(
                "url", "AVAILABLE", "https://example.org/needle"
            ),
        ),
        "synthetic_html",
    )
    batch = match_field(field, compile_targets(["needle"]), mode)
    assert batch.complete and batch.matches[0].representation == "url"


def test_cooldown_survives_exhausted_retries(harness: Harness) -> None:
    """A different object cannot bypass cooldown after retries end."""
    harness.configure(**{"crawl.max_retries": 0})
    recovery = ReadController(
        harness.settings.crawl,
        lambda: None,
        sleep=harness.clock.sleep,
        monotonic=harness.clock.monotonic,
    )
    with pytest.raises(TransientReadError):
        recovery.call(lambda: (_ for _ in ()).throw(TransientReadError(4)))
    recovery.call(lambda: "another safe read")
    assert harness.clock.seconds == pytest.approx(4)


def test_excessive_cooldown_stops_when_retries_disabled(
    harness: Harness,
) -> None:
    """Disabling retries cannot bypass an advertised server cooldown."""
    harness.configure(**{"crawl.max_retries": 0})
    recovery = ReadController(harness.settings.crawl, lambda: None)
    with pytest.raises(CooldownExceeded):
        recovery.call(lambda: (_ for _ in ()).throw(TransientReadError(61)))


def test_known_other_course_home_link_stops_session(harness: Harness) -> None:
    """Known course-home routes must agree with the owning course identity."""
    client = FixtureClient(harness)
    ref = replace(
        harness.ref(), page_url=harness.inventory.courses[1].course_url
    )
    client.discovery[("123", "content")] = [[ref]]
    result = scan(harness, client)
    assert result.state == "FAILED" and not client.read_calls


def test_all_seven_tools_are_enumerated_independently(harness: Harness) -> None:
    """Objects need no Content links to enter their own tool's scan."""
    harness.configure(**{"crawl.tools": list(get_args(ToolKey))})
    client = FixtureClient(harness)
    for tool in get_args(ToolKey):
        ref = harness.ref(f"{tool}-object", tool=tool)
        client.discovery[("123", tool)] = [[ref, DiscoveryEnd(True, 1)]]
    result = scan(harness, client)
    assert result.state == "COMPLETE"
    assert {identity[2] for identity in client.read_calls} == set(
        get_args(ToolKey)
    )
    assert result.courses[0].match_count == 7


def test_cancellation_before_login_accounts_for_all_courses(
    harness: Harness,
) -> None:
    """Pending cancellation prevents login and leaves scope unfinished."""
    client = FixtureClient(harness)
    result = scan(harness, client, cancelled=lambda: True)
    assert result.exit_code == 130 and client.auth_calls == 0 and client.closed
    assert all(item.match_status == "UNKNOWN" for item in result.courses)


def test_unsafe_signal_after_terminal_invalidates_completion(
    harness: Harness,
) -> None:
    """A later unsafe signal cannot leave an apparently complete empty tool."""
    client = FixtureClient(harness)
    client.discovery[("123", "content")] = [
        [DiscoveryEnd(True, 0), UnsafeActionBlocked()]
    ]
    result = scan(harness, client)
    assert (
        result.state == "FAILED" and result.courses[0].match_status == "UNKNOWN"
    )


def test_cli_cancellation_returns_130(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The common CLI preserves the coordinator's canceled process outcome."""
    client = FixtureClient(harness)
    client.auth_failures = [KeyboardInterrupt()]
    monkeypatch.setattr("gc_stem.cli.create_client", lambda settings: client)
    assert (
        main(["d2l", "search", "--config", str(harness.config)], environment={})
        == 130
    )


def test_limit_counts_discovered_but_unattempted_object(
    harness: Harness,
) -> None:
    """A boundary lookahead object remains visible as discovered failed work."""
    harness.configure(**{"crawl.max_objects_per_tool": 1})
    client = FixtureClient(harness)
    first, second = harness.ref("1"), harness.ref("2")
    client.discovery[("123", "content")] = [
        [first, second, DiscoveryEnd(True, 2)]
    ]
    result = scan(harness, client)
    coverage = result.courses[0].tools[0]
    assert coverage.objects_discovered == 2 and coverage.objects_failed == 1
    assert client.read_calls == [first.identity]
