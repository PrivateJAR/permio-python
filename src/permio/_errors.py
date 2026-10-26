"""Typed errors raised by the SDK."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Any, List, Optional, Sequence, Tuple, Union

import grpc

Metadata = Tuple[Tuple[str, Union[str, bytes]], ...]


@dataclass(frozen=True)
class MissingPermission:
    """Permissions missing on one resource."""

    resource: str
    """The resource URI the permissions are missing on."""
    permissions: List[str] = field(default_factory=list)
    """The permission names the principal does not hold on ``resource``."""


class PermioError(Exception):
    """Base class for every error raised by the SDK.

    ``code`` is the gRPC status code when the error came from the API (or maps
    to an API status), and ``metadata`` holds the response headers and trailers
    sent with it. The original ``grpc.RpcError`` is chained as ``__cause__``.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[grpc.StatusCode] = None,
        metadata: Metadata = (),
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.metadata = metadata

    @property
    def code_name(self) -> Optional[str]:
        """Lower-case gRPC code name, e.g. ``"permission_denied"``, or None."""
        return None if self.code is None else self.code.name.lower()


class PermioConfigError(PermioError):
    """The client was configured incorrectly, e.g. a malformed API key."""


class PermioAuthError(PermioError):
    """The API key was missing, unknown, invalidated or otherwise rejected (gRPC UNAUTHENTICATED)."""


class PermioPermissionError(PermioError):
    """The API key is valid but lacks the rights for this call (gRPC PERMISSION_DENIED).

    For ``Check``, the key needs ``permission.check`` on the checked resources
    and on the principal. When the API lists what is missing, it is parsed into
    ``missing``. Those resource URIs are the fully qualified internal ones
    (``/organisation/{org}/project/{project}/...``), not the URIs you sent.

    This is about the *caller's* rights. A principal failing a check is not an
    error: ``check()`` returns ``False`` and ``assert_allowed()`` raises
    :class:`PermioDeniedError`.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[grpc.StatusCode] = None,
        metadata: Metadata = (),
        missing: Optional[List[MissingPermission]] = None,
    ) -> None:
        super().__init__(message, code=code, metadata=metadata)
        self.missing: List[MissingPermission] = missing or []


class PermioValidationError(PermioError):
    """The request was rejected as malformed (gRPC INVALID_ARGUMENT), or failed the SDK's own checks."""


class PermioNotFoundError(PermioError):
    """The requested entity does not exist (gRPC NOT_FOUND)."""


class PermioUnavailableError(PermioError):
    """The API could not be reached or is temporarily unavailable (gRPC UNAVAILABLE)."""


class PermioTimeoutError(PermioError):
    """The call did not finish in time (gRPC DEADLINE_EXCEEDED)."""


class PermioRateLimitError(PermioError):
    """The organisation's rate limit is used up (gRPC RESOURCE_EXHAUSTED, HTTP 429).

    Idempotent reads are retried automatically after the server's requested
    delay when it is within ``RetryOptions.max_delay``; otherwise this is raised
    with ``retry_after`` (seconds) set to that delay, or None if the server gave
    none.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[grpc.StatusCode] = None,
        metadata: Metadata = (),
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, code=code, metadata=metadata)
        self.retry_after = retry_after


class PermioDeniedError(PermioError):
    """Raised by ``assert_allowed()`` when the principal lacks the requested permissions.

    This is a normal authorization outcome, not an API failure, so ``code`` is None.
    """

    def __init__(self, principal: str, missing: List[MissingPermission]) -> None:
        summary = "; ".join(f"{', '.join(m.permissions)} on {m.resource}" for m in missing)
        super().__init__(
            f"principal {principal!r} is missing {summary or 'the requested permissions'}"
        )
        self.principal = principal
        self.missing = missing


# The permissions service formats PermissionDenied as Go's %+v of its missing list:
#   missing permissions: [{ResourceURI:/organisation/o/project/p/doc MissingPermissions:[permission.check]} ...]
_MISSING_ENTRY = re.compile(r"\{ResourceURI:(\S*) MissingPermissions:\[([^\]]*)\]\}")


def parse_missing_permissions(message: str) -> List[MissingPermission]:
    """Extracts the missing-permission list from a PERMISSION_DENIED message, if it has one."""
    return [
        MissingPermission(resource=m.group(1), permissions=m.group(2).split())
        for m in _MISSING_ENTRY.finditer(message)
    ]


_RETRY_INFO_TYPE = "google.rpc.RetryInfo"


def _metadata_of(error: Any) -> Metadata:
    """Initial and trailing metadata of a sync or asyncio gRPC error, as one tuple."""
    out: List[Tuple[str, Union[str, bytes]]] = []
    for getter in ("initial_metadata", "trailing_metadata"):
        fn = getattr(error, getter, None)
        if fn is None:
            continue
        try:
            md = fn()
        except Exception:  # pragma: no cover - defensive: some error objects lack metadata
            md = None
        if md:
            out.extend((str(k), v) for k, v in md)
    return tuple(out)


def _header(metadata: Metadata, name: str) -> Optional[Union[str, bytes]]:
    for key, value in metadata:
        if key.lower() == name:
            return value
    return None


def server_retry_delay(metadata: Metadata) -> Optional[float]:
    """How long the server asked the client to wait before retrying, in seconds.

    Reads a ``google.rpc.RetryInfo`` detail from ``grpc-status-details-bin``,
    else a ``retry-after`` header (seconds or an HTTP date). None when the
    server gave no delay.
    """
    details = _header(metadata, "grpc-status-details-bin")
    if isinstance(details, bytes):
        delay = _decode_retry_info(details)
        if delay is not None:
            return delay
    header = _header(metadata, "retry-after")
    if header is None:
        return None
    text = (header.decode("latin-1") if isinstance(header, bytes) else header).strip()
    if not text:
        return None
    if text.isdigit():
        return float(int(text))
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if when is None:  # pragma: no cover - older Pythons return None instead of raising
        return None
    return max(0.0, when.timestamp() - time.time())


def _decode_retry_info(status_bytes: bytes) -> Optional[float]:
    from google.protobuf.message import DecodeError
    from google.rpc import error_details_pb2, status_pb2

    try:
        status = status_pb2.Status.FromString(status_bytes)
        for detail in status.details:
            if detail.type_url.rsplit("/", 1)[-1] == _RETRY_INFO_TYPE:
                info = error_details_pb2.RetryInfo.FromString(detail.value)
                delay = info.retry_delay
                return max(0.0, float(delay.seconds) + float(delay.nanos) / 1e9)
    except DecodeError:
        return None
    return None


def to_permio_error(error: BaseException) -> PermioError:
    """Converts a ``grpc.RpcError`` (sync or asyncio) into the matching :class:`PermioError` subclass."""
    if isinstance(error, PermioError):
        return error
    code_fn = getattr(error, "code", None)
    code: Optional[grpc.StatusCode] = code_fn() if callable(code_fn) else None
    details_fn = getattr(error, "details", None)
    message = (details_fn() if callable(details_fn) else None) or str(error)
    if code is None:
        return PermioError(message)
    metadata = _metadata_of(error)
    if code == grpc.StatusCode.UNAUTHENTICATED:
        return PermioAuthError(message, code=code, metadata=metadata)
    if code == grpc.StatusCode.PERMISSION_DENIED:
        return PermioPermissionError(
            message, code=code, metadata=metadata, missing=parse_missing_permissions(message)
        )
    if code == grpc.StatusCode.INVALID_ARGUMENT:
        return PermioValidationError(message, code=code, metadata=metadata)
    if code == grpc.StatusCode.NOT_FOUND:
        return PermioNotFoundError(message, code=code, metadata=metadata)
    if code == grpc.StatusCode.UNAVAILABLE:
        return PermioUnavailableError(message, code=code, metadata=metadata)
    if code == grpc.StatusCode.DEADLINE_EXCEEDED:
        return PermioTimeoutError(message, code=code, metadata=metadata)
    if code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        return PermioRateLimitError(
            message, code=code, metadata=metadata, retry_after=server_retry_delay(metadata)
        )
    return PermioError(message, code=code, metadata=metadata)


__all__: Sequence[str] = (
    "MissingPermission",
    "PermioError",
    "PermioConfigError",
    "PermioAuthError",
    "PermioPermissionError",
    "PermioValidationError",
    "PermioNotFoundError",
    "PermioUnavailableError",
    "PermioTimeoutError",
    "PermioRateLimitError",
    "PermioDeniedError",
    "parse_missing_permissions",
    "server_retry_delay",
    "to_permio_error",
)
