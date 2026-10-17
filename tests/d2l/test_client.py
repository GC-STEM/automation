"""Test bounded safe-read recovery using deterministic clocks."""

import pytest
from d2l_test_helpers import Harness

from gc_stem.d2l.client import (
    AccessDenied,
    AuthenticationFailed,
    AuthenticationRequired,
    CapabilitySet,
    CooldownExceeded,
    OperatorCancelled,
    ProviderUnavailable,
    ReadController,
    ReadTimeout,
    ToolCapability,
    TransientReadError,
    UnsafeActionBlocked,
    UnsupportedView,
    create_client,
)


def controller(
    harness: Harness, authenticate: object = lambda: None
) -> ReadController:
    """Use a simulated clock and no real waits."""
    return ReadController(
        harness.settings.crawl,
        authenticate,
        sleep=harness.clock.sleep,
        monotonic=harness.clock.monotonic,
    )


def test_transient_reads_retry_at_most_configured_count(
    harness: Harness,
) -> None:
    """Two retries mean three total safe-read attempts."""
    attempts = []

    def operation() -> None:
        """Fail every safe-read attempt predictably."""
        attempts.append(1)
        raise ReadTimeout

    with pytest.raises(ReadTimeout):
        controller(harness).call(operation)
    assert len(attempts) == 3
    assert harness.clock.seconds == pytest.approx(3)


def test_retry_can_succeed_without_repeating_completed_reads(
    harness: Harness,
) -> None:
    """The operation result is returned after a bounded transient failure."""
    attempts = []

    def operation() -> str:
        """Fail once, then return one result."""
        attempts.append(1)
        if len(attempts) == 1:
            raise TransientReadError
        return "ok"

    assert controller(harness).call(operation) == "ok"
    assert len(attempts) == 2


@pytest.mark.parametrize(
    "failure",
    [AccessDenied, UnsupportedView, UnsafeActionBlocked, RuntimeError],
)
def test_nontransient_failures_are_never_retried(
    harness: Harness, failure: type[Exception]
) -> None:
    """Denials, unsafe work, unknown views, and defects stop the operation."""
    attempts = []

    def operation() -> None:
        """Raise the selected nonretryable error."""
        attempts.append(1)
        raise failure

    with pytest.raises(failure):
        controller(harness).call(operation)
    assert len(attempts) == 1 and not harness.clock.waits


def test_advertised_cooldown_is_respected(harness: Harness) -> None:
    """A server cooldown is waited in full before the next safe attempt."""
    attempts = []

    def operation() -> str:
        """Require a cooldown once."""
        attempts.append(harness.clock.monotonic())
        if len(attempts) == 1:
            raise TransientReadError(4)
        return "ok"

    assert controller(harness).call(operation) == "ok"
    assert attempts[1] >= 4 - 1e-8


def test_excessive_cooldown_is_not_retried_early(harness: Harness) -> None:
    """An excessive advertised wait creates a gap rather than an early retry."""
    with pytest.raises(CooldownExceeded):
        controller(harness).call(
            lambda: (_ for _ in ()).throw(TransientReadError(61))
        )
    assert not harness.clock.waits


def test_pacing_applies_between_safe_operation_starts(harness: Harness) -> None:
    """Configured pacing is distinct from readiness and retry backoff."""
    harness.configure(**{"crawl.delay_seconds": 1})
    recovery = controller(harness)
    recovery.call(lambda: "first")
    recovery.call(lambda: "second")
    assert harness.clock.seconds == pytest.approx(1)


def test_reauthentication_budget_is_shared_across_operations(
    harness: Harness,
) -> None:
    """One reauthentication opportunity does not reset for every object."""
    logins = []
    recovery = controller(harness, lambda: logins.append(1))
    attempts = []

    def first() -> str:
        """Require one successful reauthentication."""
        attempts.append(1)
        if len(attempts) == 1:
            raise AuthenticationRequired
        return "ok"

    assert recovery.call(first) == "ok"
    with pytest.raises(AuthenticationFailed):
        recovery.call(lambda: (_ for _ in ()).throw(AuthenticationRequired()))
    assert len(logins) == 1


def test_cancellation_interrupts_cooldown_slices(harness: Harness) -> None:
    """Cancellation is checked during waits rather than after the full delay."""
    recovery = ReadController(
        harness.settings.crawl,
        lambda: None,
        sleep=harness.clock.sleep,
        monotonic=harness.clock.monotonic,
        cancelled=lambda: harness.clock.seconds >= 0.2,
    )
    with pytest.raises(OperatorCancelled):
        recovery.call(lambda: (_ for _ in ()).throw(TransientReadError(10)))
    assert harness.clock.seconds < 1


@pytest.mark.parametrize("delay", [-1, float("inf"), float("nan"), True, "1"])
def test_bad_server_cooldowns_are_rejected(delay: object) -> None:
    """Invalid provider wait data cannot disable recovery bounds."""
    with pytest.raises(ValueError):
        TransientReadError(delay)


@pytest.mark.parametrize("state", ["NOT_APPLICABLE", "DENIED", "UNSUPPORTED"])
def test_unavailable_capabilities_require_evidence(state: str) -> None:
    """Missing menus cannot silently imply verified tool absence."""
    with pytest.raises(ValueError):
        ToolCapability("content", state)


def test_capability_reason_rejects_arbitrary_exception_text() -> None:
    """Capability diagnostics use stable codes rather than response bodies."""
    with pytest.raises(ValueError, match="uppercase"):
        ToolCapability("content", "DENIED", "AUTH_SECRET with body")


def test_duplicate_capabilities_are_rejected() -> None:
    """Each requested tool has one authoritative capability record."""
    with pytest.raises(ValueError):
        CapabilitySet((ToolCapability("content", "SUPPORTED"),) * 2)


def test_live_factory_never_substitutes_a_fixture_client(
    harness: Harness,
) -> None:
    """A build without verified adapters cannot claim a live scan."""
    with pytest.raises(ProviderUnavailable):
        create_client(harness.settings)
