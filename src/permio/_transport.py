"""Auth, per-attempt timeouts, retries and error mapping around the generated stubs."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Sequence, Tuple, Union
from urllib.parse import urlsplit

import grpc
import grpc.aio

from ._errors import (
    PermioConfigError,
    PermioError,
    PermioRateLimitError,
    PermioTimeoutError,
    server_retry_delay,
    to_permio_error,
)
from ._version import __version__

DEFAULT_BASE_URL = "https://api.perms.io"
"""Production API."""
DEV_BASE_URL = "https://dev-api.perms.io"
"""Development API."""

PERMISSIONS_SERVICE = "permio.permissions.v1.PermissionsService"
ORGANISATION_SERVICE = "permio.organisation.v1.OrganisationService"

MetadataArg = Optional[Sequence[Tuple[str, Union[str, bytes]]]]


@dataclass(frozen=True)
class RetryOptions:
    """Retries for idempotent reads (Check, BatchCheck, WhoAmI, Get*, List*).

    Retried on UNAVAILABLE or DEADLINE_EXCEEDED with jittered exponential
    backoff, and on RESOURCE_EXHAUSTED when the server says how long to wait
    and that is within ``max_delay``. Writes are never retried.
    """

    max_retries: int = 2
    """Retries after the first attempt."""
    base_delay: float = 0.1
    """Delay before the first retry in seconds; doubles each time, with jitter."""
    max_delay: float = 2.0
    """Upper bound for a single delay in seconds. A rate-limited read is only retried
    when the server's requested delay is within this bound."""


# Read-only RPCs that are safe to repeat. Anything not listed (every Create,
# Update, Delete, Grant, Revoke, Invite, Set, Invalidate, Remove...) is sent
# exactly once.
#
# Grant and Revoke converge on the server (a grant is additive, a revoke
# ignores names the grant lacks), but they stay off this list: after a timeout
# the first attempt may still land, and repeating it could undo another
# caller's revoke or grant made in between. The caller decides instead.
_IDEMPOTENT_METHODS = frozenset(
    [
        f"{PERMISSIONS_SERVICE}.{m}"
        for m in (
            "Check",
            "GetPermission",
            "ListPermissions",
            "GetRole",
            "ListRoles",
            "GetUserPermissionsAndRolesOnResource",
            "ListPrincipals",
            "GetAllAssignmentsForPrincipal",
            "GetTotalRolesAndPermissionsForOrganisation",
            "BatchCheck",
            "ListAccess",
            "ListPrincipalsWithAccess",
            "GetGroup",
            "ListGroups",
            "ListGroupMembers",
            "ListGroupsForPrincipal",
            "WhoAmI",
        )
    ]
    + [
        f"{ORGANISATION_SERVICE}.{m}"
        for m in (
            "GetOrganisation",
            "GetUsersOrganisation",
            "ListAPIKeys",
            "GetProject",
            "GetProjectsForOrganisation",
            "GetPrincipalUsageStats",
            "GetUsageHistory",
            "GetOrganisationDashboard",
        )
    ]
)

_RETRYABLE_CODES = (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)


def is_idempotent_method(name: str) -> bool:
    """Whether the SDK retries this RPC, by fully qualified ``package.Service.Method`` name."""
    return name in _IDEMPOTENT_METHODS


def normalize_retries(retries: Union[int, RetryOptions, None]) -> RetryOptions:
    if retries is None:
        return RetryOptions()
    if isinstance(retries, bool) or not isinstance(retries, (int, RetryOptions)):
        raise PermioConfigError("permio: retries must be an int or RetryOptions")
    if isinstance(retries, int):
        return RetryOptions(max_retries=max(0, retries))
    return RetryOptions(
        max_retries=max(0, int(retries.max_retries)),
        base_delay=max(0.0, float(retries.base_delay)),
        max_delay=max(0.0, float(retries.max_delay)),
    )


def parse_target(base_url: str) -> Tuple[str, bool]:
    """Turns ``https://host[:port]``, ``http://host[:port]`` or ``host:port`` into a gRPC target.

    Returns ``(target, secure)``. ``http://`` means plaintext (e.g. a local
    server); anything else uses TLS.
    """
    if not isinstance(base_url, str) or base_url.strip() == "":
        raise PermioConfigError("permio: base_url must be a non-empty string")
    text = base_url.strip().rstrip("/")
    if "://" not in text:
        if "/" in text:
            raise PermioConfigError(f"permio: base_url must not have a path, got {base_url!r}")
        return (text if ":" in text.rsplit("]", 1)[-1] else text + ":443"), True
    parts = urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise PermioConfigError(
            f"permio: base_url must be an http(s) URL or host:port, got {base_url!r}"
        )
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise PermioConfigError(f"permio: base_url must not have a path, got {base_url!r}")
    secure = parts.scheme == "https"
    host = parts.hostname
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    port = parts.port or (443 if secure else 80)
    return f"{host}:{port}", secure


def channel_options(extra: Optional[Sequence[Tuple[str, Any]]]) -> list[Tuple[str, Any]]:
    return [("grpc.primary_user_agent", f"permio-python/{__version__}"), *(extra or [])]


class _Unset:
    """Sentinel type: "use the client's per-attempt timeout"."""


UNSET: Any = _Unset()


def _positive(value: Any) -> Optional[float]:
    return float(value) if value is not None and value > 0 else None


class _Policy:
    """What both invokers share: auth metadata, timeouts and the retry decision."""

    def __init__(self, api_key: str, timeout: Optional[float], retry: RetryOptions) -> None:
        self.authorization = ("authorization", f"Bearer {api_key}")
        self.timeout = _positive(timeout)
        self.retry = retry
        self.random: Callable[[], float] = random.random

    def metadata(self, extra: MetadataArg) -> Tuple[Tuple[str, Union[str, bytes]], ...]:
        md = [(k, v) for k, v in (extra or ()) if k.lower() != "authorization"]
        return (self.authorization, *md)

    def deadline(self, overall: Optional[float]) -> Optional[float]:
        return None if overall is None or overall <= 0 else time.monotonic() + overall

    def attempt_timeout(
        self,
        deadline: Optional[float],
        overall: Optional[float],
        per_attempt: Any = UNSET,
    ) -> Optional[float]:
        """Timeout for the next attempt, or raises if the overall deadline has passed.

        ``per_attempt`` replaces the client's per-attempt timeout (``<= 0``
        disables it); by default the client's applies.
        """
        attempt = self.timeout if per_attempt is UNSET else _positive(per_attempt)
        if deadline is None:
            return attempt
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PermioTimeoutError(
                f"deadline of {overall}s exceeded", code=grpc.StatusCode.DEADLINE_EXCEEDED
            )
        return remaining if attempt is None else min(attempt, remaining)

    def retry_delay(
        self, err: PermioError, attempt: int, retries: int, deadline: Optional[float]
    ) -> Optional[float]:
        """Seconds to wait before retrying ``err``, or None to raise it."""
        if attempt >= retries:
            return None
        # The server's RetryInfo detail / Retry-After header, if any. A rate
        # limited (RESOURCE_EXHAUSTED) read is only retried when the server
        # says when, and only if that is within max_delay.
        if isinstance(err, PermioRateLimitError):
            server_delay = err.retry_after
            if server_delay is None:
                return None
        elif err.code in _RETRYABLE_CODES:
            server_delay = server_retry_delay(err.metadata)
        else:
            return None
        if server_delay is not None and server_delay > self.retry.max_delay:
            return None
        ceiling = min(self.retry.max_delay, self.retry.base_delay * (2.0**attempt))
        backoff = ceiling / 2 + self.random() * (ceiling / 2)
        if server_delay is None:
            delay = backoff
        else:
            # Wait at least as long as the server asked, plus a little jitter so
            # clients limited in the same second don't all retry at once.
            delay = max(backoff, server_delay + self.random() * min(0.1, ceiling))
        if deadline is not None and time.monotonic() + delay >= deadline:
            return None
        return delay


class SyncInvoker(_Policy):
    """Sends unary calls on a ``grpc.Channel`` with auth, timeouts, retries and typed errors."""

    sleep: Callable[[float], None] = staticmethod(time.sleep)

    def call(
        self,
        method: str,
        fn: Callable[..., Any],
        request: Any,
        *,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
        per_attempt: Any = UNSET,
    ) -> Any:
        md = self.metadata(metadata)
        retries = self.retry.max_retries if is_idempotent_method(method) else 0
        deadline = self.deadline(timeout)
        attempt = 0
        while True:
            try:
                return fn(
                    request,
                    timeout=self.attempt_timeout(deadline, timeout, per_attempt),
                    metadata=md,
                )
            except grpc.RpcError as e:
                err = to_permio_error(e)
                delay = self.retry_delay(err, attempt, retries, deadline)
                if delay is None:
                    raise err from e
            self.sleep(delay)
            attempt += 1


class AsyncInvoker(_Policy):
    """Sends unary calls on a ``grpc.aio.Channel`` with auth, timeouts, retries and typed errors."""

    sleep: Callable[[float], Awaitable[None]] = staticmethod(asyncio.sleep)

    async def call(
        self,
        method: str,
        fn: Callable[..., Any],
        request: Any,
        *,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
        per_attempt: Any = UNSET,
    ) -> Any:
        md = self.metadata(metadata)
        retries = self.retry.max_retries if is_idempotent_method(method) else 0
        deadline = self.deadline(timeout)
        attempt = 0
        while True:
            try:
                return await fn(
                    request,
                    timeout=self.attempt_timeout(deadline, timeout, per_attempt),
                    metadata=md,
                )
            except grpc.RpcError as e:
                err = to_permio_error(e)
                delay = self.retry_delay(err, attempt, retries, deadline)
                if delay is None:
                    raise err from e
            await self.sleep(delay)
            attempt += 1


class RawService:
    """A generated service stub with auth, timeouts, retries and typed errors applied.

    Methods keep the generated names and request/response messages::

        permio.permissions.CreatePermission(
            raw.permissions_pb2.CreatePermissionRequest(project_name="my-app", name="docs.read")
        )

    Each method accepts ``timeout`` (overall deadline in seconds, across
    retries) and ``metadata`` (extra request headers). On ``AsyncPermio`` the
    methods are coroutines.
    """

    def __init__(self, service: str, stub: Any, invoker: Union[SyncInvoker, AsyncInvoker]) -> None:
        self._service = service
        self._stub = stub
        self._invoker = invoker

    def __getattr__(self, name: str) -> Callable[..., Any]:
        if name.startswith("_"):
            raise AttributeError(name)
        fn = getattr(self._stub, name)
        method = f"{self._service}.{name}"
        invoker = self._invoker

        def call(
            request: Any, *, timeout: Optional[float] = None, metadata: MetadataArg = None
        ) -> Any:
            return invoker.call(method, fn, request, timeout=timeout, metadata=metadata)

        call.__name__ = name
        call.__qualname__ = f"{type(self._stub).__name__}.{name}"
        return call

    def __repr__(self) -> str:
        return f"<RawService {self._service}>"
