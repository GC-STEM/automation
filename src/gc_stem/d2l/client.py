"""Define provider-independent reads and bounded recovery for safe operations.

Concrete providers must guard routes, enforce navigation/page limits, and
return only course-authored scope. This module does not implement a browser
provider or verify that a provider's underlying requests are read-only.
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from types import TracebackType
from typing import Literal, Protocol, TypeVar

from .config import CrawlSettings, Settings
from .models import CourseRef, DiscoveryEnd, ObjectRef, ReadResult, ToolKey

_Result = TypeVar("_Result")
_REASON_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


class ClientError(Exception):
    """Carry a stable sanitized failure code rather than exception contents."""

    code = "CLIENT_FAILURE"

    def __init__(self) -> None:
        """Expose only this error class's predefined diagnostic code."""
        super().__init__(self.code)


class AuthenticationRequired(ClientError):
    """Suspend an unfinished safe read until reauthentication succeeds."""

    code = "AUTHENTICATION_REQUIRED"


class AuthenticationFailed(ClientError):
    """Indicate failed, canceled, or exhausted authentication."""

    code = "AUTHENTICATION_FAILED"


class AccessDenied(ClientError):
    """Indicate a scoped permission denial that must not be retried."""

    code = "ACCESS_DENIED"


class UnsupportedView(ClientError):
    """Indicate an unrecognized view or unsupported authored-field family."""

    code = "UNSUPPORTED_VIEW"


class UnsafeActionBlocked(ClientError):
    """Require the entire session to stop after an unsafe-action signal."""

    code = "UNSAFE_ACTION_BLOCKED"


class ClientContractError(ClientError):
    """Indicate provider output that violates a normalized read contract."""

    code = "CLIENT_CONTRACT_ERROR"


class OperatorCancelled(ClientError):
    """Request orderly cancellation with acquired findings preserved."""

    code = "CANCELLED"


class CooldownExceeded(ClientError):
    """Indicate a server wait exceeding the configured retry-wait budget."""

    code = "COOLDOWN_EXCEEDED"


class ProviderUnavailable(ClientError):
    """Indicate an unimplemented or unverified live provider."""

    code = "PROVIDER_UNAVAILABLE"


class TransientReadError(ClientError):
    """Allow bounded retries of an operation already verified to be safe."""

    code = "TRANSIENT_READ_ERROR"

    def __init__(self, retry_after_seconds: float | None = None) -> None:
        """Optionally require a finite nonnegative server cooldown."""
        if retry_after_seconds is not None and (
            isinstance(retry_after_seconds, bool)
            or not isinstance(retry_after_seconds, (int, float))
            or not math.isfinite(retry_after_seconds)
            or retry_after_seconds < 0
        ):
            raise ValueError("Retry delay must be finite and nonnegative.")
        super().__init__()
        self.retry_after_seconds = retry_after_seconds


class ReadTimeout(TransientReadError):
    """Describe a retryable timeout from a verified safe read."""

    code = "READ_TIMEOUT"


@dataclass(frozen=True, slots=True)
class ClientInfo:
    """Describe the actual provider and browser version when applicable."""

    provider: str
    browser_version: str | None = None


@dataclass(frozen=True, slots=True)
class ToolCapability:
    """Describe one tool's verified capability, denial, or applicability."""

    tool: ToolKey
    state: Literal["SUPPORTED", "NOT_APPLICABLE", "DENIED", "UNSUPPORTED"]
    reason_code: str | None = None

    def __post_init__(self) -> None:
        """Require explicit safe evidence codes for unsupported/absent scope."""
        if self.state not in (
            "SUPPORTED",
            "NOT_APPLICABLE",
            "DENIED",
            "UNSUPPORTED",
        ):
            raise ValueError("Unsupported capability state.")
        if self.state != "SUPPORTED" and self.reason_code is None:
            raise ValueError("Unavailable capability requires a reason code.")
        if (
            self.reason_code is not None
            and _REASON_CODE.fullmatch(self.reason_code) is None
        ):
            raise ValueError(
                "Capability reasons must use stable uppercase codes."
            )


@dataclass(frozen=True, slots=True)
class CapabilitySet:
    """Hold one capability record per requested tool."""

    tools: tuple[ToolCapability, ...]

    def __post_init__(self) -> None:
        """Reject duplicate tool capabilities."""
        if len({item.tool for item in self.tools}) != len(self.tools):
            raise ValueError("Capabilities must not repeat a tool.")


class BrightspaceReadClient(Protocol):
    """Expose safe authored reads without passing browser objects upstream."""

    info: ClientInfo

    def authenticate(self) -> None:
        """Obtain and verify a normal interactive session."""
        ...

    def capabilities(
        self, course: CourseRef, tools: tuple[ToolKey, ...]
    ) -> CapabilitySet:
        """Return verified capability evidence for every requested tool."""
        ...

    def discover(
        self, course: CourseRef, tool: ToolKey
    ) -> Iterator[ObjectRef | DiscoveryEnd]:
        """Yield scoped references followed by one terminal discovery event."""
        ...

    def read_object(self, ref: ObjectRef) -> ReadResult:
        """Read the declared authored-field inventory and explicit gaps."""
        ...

    def close(self) -> None:
        """Release all provider resources without persisting authentication."""
        ...

    def __enter__(self) -> BrightspaceReadClient:
        """Enter the concrete provider's managed lifetime."""
        ...

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release the concrete provider's managed lifetime."""
        ...


class ReadController:
    """Pace caller-verified safe operations using bounded recovery and a clock.

    Reauthentication is bounded across the entire controller/run. Read timeouts
    and actual navigation/page bounds remain provider responsibilities.
    """

    def __init__(
        self,
        settings: CrawlSettings,
        authenticate: Callable[[], None],
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> None:
        """Store immutable limits and injectable wait/cancellation functions."""
        self.settings = settings
        self.authenticate = authenticate
        self.sleep = sleep
        self.monotonic = monotonic
        self.cancelled = cancelled
        self.reauthentications = 0
        self._last_start: float | None = None
        self._not_before = 0.0

    def checkpoint(self) -> None:
        """Stop promptly when the operator requests cancellation."""
        if self.cancelled():
            raise OperatorCancelled

    def _wait(self, seconds: float) -> None:
        """Wait in short slices so cancellation remains responsive."""
        remaining = seconds
        while remaining > 0:
            self.checkpoint()
            interval = min(remaining, 0.1)
            self.sleep(interval)
            remaining = max(0.0, remaining - interval)
        self.checkpoint()

    def call(self, operation: Callable[[], _Result]) -> _Result:
        """Run one safe operation with pacing and bounded recovery.

        Permission, unsupported-view, and unsafe-action failures are never
        retried. A cooldown above the configured limit ends the scoped work
        rather than retrying early. Unexpected errors propagate unchanged.
        """
        retries = 0
        while True:
            self.checkpoint()
            if self._last_start is not None:
                elapsed = self.monotonic() - self._last_start
                self._wait(max(0.0, self.settings.delay_seconds - elapsed))
            self._wait(max(0.0, self._not_before - self.monotonic()))
            self._last_start = self.monotonic()
            try:
                return operation()
            except AuthenticationRequired:
                if (
                    self.reauthentications
                    >= self.settings.max_reauthentications
                ):
                    raise AuthenticationFailed from None
                self.reauthentications += 1
                self.authenticate()
            except TransientReadError as error:
                if error.retry_after_seconds is not None:
                    if (
                        error.retry_after_seconds
                        > self.settings.max_retry_wait_seconds
                    ):
                        raise CooldownExceeded from None
                    self._not_before = max(
                        self._not_before,
                        self.monotonic() + error.retry_after_seconds,
                    )
                if retries >= self.settings.max_retries:
                    raise
                delay = error.retry_after_seconds
                if delay is None:
                    delay = min(
                        2.0 ** min(retries, 20),
                        self.settings.max_retry_wait_seconds,
                    )
                if delay > self.settings.max_retry_wait_seconds:
                    raise CooldownExceeded from None
                retries += 1
                self._wait(delay)


def create_client(settings: Settings) -> BrightspaceReadClient:
    """Reject live scanning until a tenant-verified provider is implemented.

    Local validation and injected-client library scans are available. This
    factory never returns a synthetic client as a substitute for Brightspace.
    """
    raise ProviderUnavailable
