"""Python SDK for perms.io, permissions as a service with hierarchical resource-URI RBAC.

::

    from permio import Permio, resource

    permio = Permio(project="my-app")  # API key from $PERMIO_API_KEY
    if permio.check("alice", "docs.read", resource("docs", "42")):
        ...

See :class:`Permio` (sync) and :class:`AsyncPermio` (asyncio). The generated
stubs are available under :mod:`permio.raw`.
"""

from . import raw
from ._access import (
    WILDCARD_SEGMENT,
    AccessEntry,
    AccessGrantInfo,
    AccessGrantSource,
    AccessScopeInfo,
    AccessScopes,
    BatchCheckEntry,
    CheckResult,
    WhoAmI,
)
from ._apikey import API_KEY_LENGTH, is_valid_api_key, validate_api_key
from ._async_client import AsyncGroups, AsyncPermio
from ._client import Groups, Permio
from ._core import MAX_PAGE_SIZE, AddMembersResult, RemoveMembersResult
from ._errors import (
    MissingPermission,
    PermioAuthError,
    PermioConfigError,
    PermioDeniedError,
    PermioError,
    PermioNotFoundError,
    PermioPermissionError,
    PermioRateLimitError,
    PermioTimeoutError,
    PermioUnavailableError,
    PermioValidationError,
    parse_missing_permissions,
)
from ._resource import (
    GROUP_PRINCIPAL_PREFIX,
    MAX_RESOURCE_URI_LENGTH,
    assert_resource_uri,
    encode_segment,
    group,
    resource,
)
from ._transport import DEFAULT_BASE_URL, DEV_BASE_URL, RetryOptions, is_idempotent_method
from ._version import __version__

__all__ = [
    "API_KEY_LENGTH",
    "DEFAULT_BASE_URL",
    "DEV_BASE_URL",
    "GROUP_PRINCIPAL_PREFIX",
    "MAX_PAGE_SIZE",
    "MAX_RESOURCE_URI_LENGTH",
    "WILDCARD_SEGMENT",
    "AccessEntry",
    "AccessGrantInfo",
    "AccessGrantSource",
    "AccessScopeInfo",
    "AccessScopes",
    "AddMembersResult",
    "AsyncGroups",
    "AsyncPermio",
    "BatchCheckEntry",
    "CheckResult",
    "Groups",
    "MissingPermission",
    "Permio",
    "PermioAuthError",
    "PermioConfigError",
    "PermioDeniedError",
    "PermioError",
    "PermioNotFoundError",
    "PermioPermissionError",
    "PermioRateLimitError",
    "PermioTimeoutError",
    "PermioUnavailableError",
    "PermioValidationError",
    "RemoveMembersResult",
    "RetryOptions",
    "WhoAmI",
    "__version__",
    "assert_resource_uri",
    "encode_segment",
    "group",
    "is_idempotent_method",
    "is_valid_api_key",
    "parse_missing_permissions",
    "raw",
    "resource",
    "validate_api_key",
]
