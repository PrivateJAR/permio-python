"""Configuration, request builders and response parsers shared by the sync and asyncio clients."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    TypeVar,
    Union,
)

from ._access import BatchCheckEntry, CheckResult, inconsistent_response
from ._apikey import validate_api_key
from ._errors import MissingPermission, PermioConfigError, PermioError, PermioValidationError
from ._resource import GROUP_PRINCIPAL_PREFIX, assert_resource_uri, slug_of
from ._transport import DEFAULT_BASE_URL, RetryOptions, normalize_retries
from .pagination.v1 import pagination_pb2
from .permissions.v1 import permissions_pb2 as pb

T = TypeVar("T")
R = TypeVar("R")

MAX_PAGE_SIZE = 100
"""Largest page the API accepts (``PaginationRequest.limit`` is 1..100)."""

DEFAULT_TIMEOUT = 10.0
"""Default per-attempt timeout in seconds."""

Names = Union[str, Sequence[str]]


@dataclass(frozen=True)
class AddMembersResult:
    added: List[str] = field(default_factory=list)
    """Principals that were added, in request order."""
    existing: List[str] = field(default_factory=list)
    """Principals that were already members, in request order."""


@dataclass(frozen=True)
class RemoveMembersResult:
    removed: List[str] = field(default_factory=list)
    """Principals that were removed, in request order."""
    not_members: List[str] = field(default_factory=list)
    """Principals that were not members, in request order."""


def _as_list(values: Optional[Names], what: str) -> List[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    elif not isinstance(values, (list, tuple, set, frozenset)) and not hasattr(values, "__iter__"):
        raise PermioValidationError(f"permio: {what}s must be a string or a list of strings")
    out = list(dict.fromkeys(values))
    for v in out:
        if not isinstance(v, str) or v == "":
            raise PermioValidationError(f"permio: {what}s must be non-empty strings")
    return out


def pick(values: Optional[Names], what: str) -> List[str]:
    """1..100 distinct non-empty strings, in order."""
    out = _as_list(values, what)
    if not out:
        raise PermioValidationError(f"permio: at least one {what} is required")
    if len(out) > 100:
        raise PermioValidationError(f"permio: at most 100 {what}s per check")
    return out


def require_principal(principal: object) -> str:
    if not isinstance(principal, str) or principal == "":
        raise PermioValidationError("permio: principal is required")
    return principal


def principal_list(principals: Sequence[str]) -> List[str]:
    if isinstance(principals, str) or not hasattr(principals, "__iter__"):
        raise PermioValidationError("permio: principals must be a list of principal IDs")
    values = list(dict.fromkeys(principals))
    if not values:
        raise PermioValidationError("permio: at least one principal is required")
    if len(values) > 100:
        raise PermioValidationError("permio: at most 100 principals per call")
    for p in values:
        if not isinstance(p, str) or p == "":
            raise PermioValidationError("permio: principal IDs must be non-empty strings")
    return values


def page_limit(page_size: Optional[int]) -> int:
    if page_size is None:
        return MAX_PAGE_SIZE
    return max(1, min(MAX_PAGE_SIZE, int(page_size)))


def check_cursor(cursor: str, seen: Set[str]) -> None:
    """Records ``cursor``, raising if the API already returned it in this listing."""
    if cursor in seen:
        raise PermioError(
            "permio: the API returned a pagination cursor it had already returned; "
            "stopping the listing instead of looping or returning partial results"
        )
    seen.add(cursor)


def paginate(
    fetch: Callable[[pagination_pb2.PaginationRequest], Any],
    items: Callable[[Any], Iterable[T]],
    page_size: Optional[int],
) -> Iterator[T]:
    """Follows ``next_cursor`` until the API returns an empty one.

    Raises:
        PermioError: if the API returns a cursor it already returned, which would
            otherwise loop forever (or silently cut the listing short).
    """
    limit = page_limit(page_size)
    cursor: Optional[str] = None
    seen: Set[str] = set()
    while True:
        req = pagination_pb2.PaginationRequest(limit=limit)
        if cursor is not None:
            req.cursor = cursor
        res = fetch(req)
        yield from items(res)
        nxt: str = res.pagination.next_cursor
        # An empty cursor ends the listing.
        if not nxt:
            return
        check_cursor(nxt, seen)
        cursor = nxt


async def apaginate(
    fetch: Callable[[pagination_pb2.PaginationRequest], Awaitable[Any]],
    items: Callable[[Any], Iterable[T]],
    page_size: Optional[int],
) -> AsyncIterator[T]:
    """Async version of :func:`paginate`."""
    limit = page_limit(page_size)
    cursor: Optional[str] = None
    seen: Set[str] = set()
    while True:
        req = pagination_pb2.PaginationRequest(limit=limit)
        if cursor is not None:
            req.cursor = cursor
        res = await fetch(req)
        for item in items(res):
            yield item
        nxt: str = res.pagination.next_cursor
        if not nxt:
            return
        check_cursor(nxt, seen)
        cursor = nxt


class ClientConfig:
    """Validated client settings plus the request builders and parsers both clients use."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        project: Optional[str],
        timeout: Optional[float],
        retries: Union[int, RetryOptions, None],
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("PERMIO_API_KEY")
        self.api_key_kind = validate_api_key(key)
        assert isinstance(key, str)
        self.api_key = key
        if project is not None and (not isinstance(project, str) or project == ""):
            raise PermioConfigError("permio: project must be a non-empty string")
        self.project = project
        self.base_url = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
        if timeout is not None and (
            isinstance(timeout, bool) or not isinstance(timeout, (int, float))
        ):
            raise PermioConfigError("permio: timeout must be a number of seconds or None")
        self.timeout = DEFAULT_TIMEOUT if timeout is None else max(0.0, float(timeout))
        self.retry = normalize_retries(retries)

    def resolve_project(self, project: Optional[str]) -> str:
        name = project if project is not None else self.project
        if not name:
            raise PermioConfigError(
                "permio: no project given; pass project= to this call or to the client"
            )
        return name

    # -- check ---------------------------------------------------------------

    def check_request(
        self, principal: str, permission: Names, resource: Names, project: Optional[str]
    ) -> pb.CheckPermissionRequest:
        require_principal(principal)
        uris = pick(resource, "resource")
        for uri in uris:
            assert_resource_uri(uri)
        perms = pick(permission, "permission")
        return pb.CheckPermissionRequest(
            project_name=self.resolve_project(project),
            principal_id=principal,
            resource_uris=uris,
            permissions=perms,
        )

    @staticmethod
    def check_result(res: pb.CheckPermissionResponse) -> CheckResult:
        missing = [
            MissingPermission(resource=m.resource_uri, permissions=list(m.missing_permissions))
            for m in res.missing_permissions
        ]
        return CheckResult(allowed=res.passed, missing=missing)

    @staticmethod
    def any_allowed(result: CheckResult, permission: Names) -> bool:
        if result.allowed:
            return True
        if not result.missing:
            # Denied without saying what is missing: fail closed.
            return False
        wanted = pick(permission, "permission")
        return all(any(p not in m.permissions for p in wanted) for m in result.missing)

    def batch_requests(
        self, principal: str, permission: Names, resources: Sequence[str], project: Optional[str]
    ) -> tuple[List[str], List[pb.BatchCheckRequest]]:
        require_principal(principal)
        if isinstance(resources, str) or not hasattr(resources, "__iter__"):
            raise PermioValidationError("permio: resources must be a list of resource URIs")
        uris = list(dict.fromkeys(resources))
        if not uris:
            raise PermioValidationError("permio: at least one resource is required")
        for uri in uris:
            assert_resource_uri(uri)
        perms = pick(permission, "permission")
        project_name = self.resolve_project(project)
        chunks = [uris[i : i + 100] for i in range(0, len(uris), 100)]
        return uris, [
            pb.BatchCheckRequest(
                project_name=project_name,
                principal_id=principal,
                resource_uris=chunk,
                permissions=perms,
            )
            for chunk in chunks
        ]

    @staticmethod
    def batch_entries(
        uris: List[str], responses: Iterable[pb.BatchCheckResponse]
    ) -> List[BatchCheckEntry]:
        by_uri: Dict[str, BatchCheckEntry] = {}
        for res in responses:
            for r in res.results:
                by_uri[r.resource_uri] = BatchCheckEntry(
                    resource=r.resource_uri,
                    allowed=r.allowed and len(r.missing_permissions) == 0,
                    missing=list(r.missing_permissions),
                )
        # Fail closed: every requested resource must have exactly its own answer.
        out = []
        for uri in uris:
            entry = by_uri.get(uri)
            if entry is None:
                raise inconsistent_response(f"no BatchCheck result for {uri!r}")
            out.append(entry)
        return out

    # -- access --------------------------------------------------------------

    def list_access_request(
        self, principal: str, permission: str, under: str, project: Optional[str]
    ) -> pb.ListAccessRequest:
        require_principal(principal)
        if not isinstance(permission, str) or permission == "":
            raise PermioValidationError("permio: permission is required")
        assert_resource_uri(under)
        return pb.ListAccessRequest(
            project_name=self.resolve_project(project),
            principal_id=principal,
            permission=permission,
            under_uri=under,
        )

    def who_has_access_request(
        self,
        resource: str,
        permission: Optional[str],
        expand_groups: bool,
        project: Optional[str],
    ) -> pb.ListPrincipalsWithAccessRequest:
        assert_resource_uri(resource)
        if permission is not None and (not isinstance(permission, str) or permission == ""):
            raise PermioValidationError("permio: permission must not be empty")
        req = pb.ListPrincipalsWithAccessRequest(
            project_name=self.resolve_project(project),
            resource_uri=resource,
            expand_groups=bool(expand_groups),
        )
        if permission is not None:
            req.permission = permission
        return req

    # -- grant / revoke ------------------------------------------------------

    def grant_fields(
        self,
        principal: str,
        resource: str,
        permissions: Optional[Names],
        roles: Optional[Names],
        project: Optional[str],
    ) -> Dict[str, Any]:
        require_principal(principal)
        assert_resource_uri(resource)
        perms = _as_list(permissions, "permission")
        role_ids = _as_list(roles, "role")
        if not perms and not role_ids:
            raise PermioValidationError("permio: at least one permission or role is required")
        return {
            "project_name": self.resolve_project(project),
            "user_id": principal,
            "resource_uri": resource,
            "permissions": perms,
            "roles": role_ids,
        }

    # -- groups --------------------------------------------------------------

    @staticmethod
    def group_slug(name: str) -> str:
        return slug_of(name)

    @staticmethod
    def member_ids(principals: Sequence[str], adding: bool) -> List[str]:
        ids = principal_list(principals)
        if adding and any(p.startswith(GROUP_PRINCIPAL_PREFIX) for p in ids):
            raise PermioValidationError("permio: groups cannot contain groups")
        return ids
