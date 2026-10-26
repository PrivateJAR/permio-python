"""The asyncio client, :class:`AsyncPermio`."""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Tuple, Type, Union

import grpc
import grpc.aio

from ._access import (
    AccessEntry,
    AccessScopeInfo,
    AccessScopes,
    BatchCheckEntry,
    CheckResult,
    WhoAmI,
    scope_kind_name,
    to_access_entry,
    to_who_am_i,
)
from ._core import (
    AddMembersResult,
    ClientConfig,
    Names,
    RemoveMembersResult,
    apaginate,
    require_principal,
)
from ._errors import PermioDeniedError, PermioValidationError
from ._transport import (
    ORGANISATION_SERVICE,
    PERMISSIONS_SERVICE,
    AsyncInvoker,
    MetadataArg,
    RawService,
    RetryOptions,
    channel_options,
    parse_target,
)
from .organisation.v1 import organisation_pb2_grpc
from .permissions.v1 import permissions_pb2 as pb
from .permissions.v1 import permissions_pb2_grpc


class AsyncPermio:
    """Asyncio client for the perms.io API (``grpc.aio``), with the same surface as :class:`Permio`.

    ::

        from permio import AsyncPermio, resource

        async with AsyncPermio(project="my-app") as permio:
            if await permio.check(user_id, "docs.read", resource("docs", doc_id)):
                ...

    List helpers return async iterators (``async for``). Cancel a call by
    cancelling its task.

    Args:
        api_key: API key from the dashboard (``perms_...``), or a legacy JWT key.
            Defaults to the ``PERMIO_API_KEY`` environment variable. Checked
            locally for typos (:class:`PermioConfigError`).
        base_url: API endpoint. Defaults to production, ``https://api.perms.io``
            (:data:`DEFAULT_BASE_URL`); use :data:`DEV_BASE_URL` for development.
            ``http://host:port`` connects without TLS; ``host:port`` uses TLS.
        project: Default project for helpers that take ``project``.
        timeout: Timeout per attempt in seconds. Default 10; 0 disables it.
        retries: Retries for idempotent reads on UNAVAILABLE / DEADLINE_EXCEEDED
            (and rate limiting with a server-given delay). An int sets
            ``max_retries``; default 2. Writes are never retried.
        channel: A ``grpc.aio.Channel`` to use instead of creating one (for tests,
            proxies or custom credentials). ``base_url`` is then ignored and the
            channel is not closed by :meth:`close`.
        channel_options: Extra gRPC channel options when the client creates the channel.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: Union[int, RetryOptions, None] = None,
        channel: Optional[grpc.aio.Channel] = None,
        channel_options: Optional[Sequence[Tuple[str, Any]]] = None,
    ) -> None:
        self._config = ClientConfig(api_key, base_url, project, timeout, retries)
        if channel is None:
            target, secure = parse_target(self._config.base_url)
            options = _channel_options(channel_options)
            channel = (
                grpc.aio.secure_channel(target, grpc.ssl_channel_credentials(), options=options)
                if secure
                else grpc.aio.insecure_channel(target, options=options)
            )
            self._owns_channel = True
        else:
            self._owns_channel = False
        self.channel: grpc.aio.Channel = channel
        """The underlying gRPC channel."""
        self._invoker = AsyncInvoker(self._config.api_key, self._config.timeout, self._config.retry)
        self.permissions = RawService(
            PERMISSIONS_SERVICE,
            _stub(permissions_pb2_grpc.PermissionsServiceStub, channel),
            self._invoker,
        )
        """Raw ``PermissionsService`` client with auth, timeouts, retries and typed errors applied."""
        self.organisations = RawService(
            ORGANISATION_SERVICE,
            _stub(organisation_pb2_grpc.OrganisationServiceStub, channel),
            self._invoker,
        )
        """Raw ``OrganisationService`` client with auth, timeouts, retries and typed errors applied."""
        self.groups = AsyncGroups(self)
        """Groups of principals: create them, manage members, list them."""

    @property
    def project(self) -> Optional[str]:
        """Default project for helpers, if configured."""
        return self._config.project

    @property
    def base_url(self) -> str:
        return self._config.base_url

    @property
    def api_key_kind(self) -> str:
        """``"opaque"`` for ``perms_...`` keys, ``"jwt"`` for legacy JWT keys."""
        return self._config.api_key_kind

    def __repr__(self) -> str:
        return f"AsyncPermio(base_url={self.base_url!r}, project={self.project!r})"

    # -- lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        """Closes the channel, if the client created it."""
        if self._owns_channel:
            await self.channel.close()

    async def __aenter__(self) -> AsyncPermio:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    # -- internals -----------------------------------------------------------

    async def _call(
        self,
        method: str,
        request: Any,
        timeout: Optional[float],
        metadata: MetadataArg,
    ) -> Any:
        return await getattr(self.permissions, method)(request, timeout=timeout, metadata=metadata)

    # -- checks --------------------------------------------------------------

    async def check_detailed(
        self,
        principal: str,
        permission: Names,
        resource: Names,
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> CheckResult:
        """Checks whether ``principal`` holds every permission on every resource, and what is missing.

        ``permission`` and ``resource`` each take one name / URI or a list of up
        to 100. A denial is a normal result, not an error.

        Raises:
            PermioPermissionError: if the API key lacks ``permission.check``.
            PermioValidationError: for malformed URIs or empty inputs.
        """
        req = self._config.check_request(principal, permission, resource, project)
        return self._config.check_result(await self._call("Check", req, timeout, metadata))

    async def check(
        self,
        principal: str,
        permission: Names,
        resource: Names,
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> bool:
        """True when ``principal`` holds every permission on every resource."""
        result = await self.check_detailed(
            principal, permission, resource, project=project, timeout=timeout, metadata=metadata
        )
        return result.allowed

    check_all = check
    """Alias of :meth:`check`: every permission on every resource."""

    async def check_any(
        self,
        principal: str,
        permission: Names,
        resource: Names,
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> bool:
        """True when, on every resource, ``principal`` holds at least one of the permissions.

        Uses a single ``Check`` call.
        """
        result = await self.check_detailed(
            principal, permission, resource, project=project, timeout=timeout, metadata=metadata
        )
        return self._config.any_allowed(result, permission)

    async def assert_allowed(
        self,
        principal: str,
        permission: Names,
        resource: Names,
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> None:
        """Returns when ``principal`` holds every permission on every resource.

        Raises:
            PermioDeniedError: when it does not, with ``missing`` filled in.
        """
        result = await self.check_detailed(
            principal, permission, resource, project=project, timeout=timeout, metadata=metadata
        )
        if not result.allowed:
            raise PermioDeniedError(principal, result.missing)

    async def batch_check(
        self,
        principal: str,
        permission: Names,
        resources: Sequence[str],
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> Dict[str, bool]:
        """Checks each resource separately; returns ``{uri: allowed}`` in request order.

        A resource is allowed only with every requested permission. More than
        100 resources are split into several ``BatchCheck`` calls. Use it to
        filter a list you already have::

            allowed = permio.batch_check(user_id, "docs.read", [resource("docs", d.id) for d in docs])
            visible = [d for d in docs if allowed[resource("docs", d.id)]]
        """
        entries = await self.batch_check_detailed(
            principal, permission, resources, project=project, timeout=timeout, metadata=metadata
        )
        return {e.resource: e.allowed for e in entries}

    async def batch_check_detailed(
        self,
        principal: str,
        permission: Names,
        resources: Sequence[str],
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> List[BatchCheckEntry]:
        """Like :meth:`batch_check`, but one entry per resource with the missing permissions."""
        uris, requests = self._config.batch_requests(principal, permission, resources, project)
        responses = await asyncio.gather(
            *(self._call("BatchCheck", r, timeout, metadata) for r in requests)
        )
        return self._config.batch_entries(uris, responses)

    # -- access queries ------------------------------------------------------

    async def list_access(
        self,
        principal: str,
        permission: str,
        under: str,
        *,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AccessScopes:
        """Answers "where may ``principal`` use ``permission`` at or below ``under``?".

        Follows every page. Use the result to filter lists in your database:
        ``covers_all`` means no filter is needed, ``to_prefixes()`` gives path
        prefixes, ``to_regex()`` a regex, and ``allows(uri)`` tests one URI.

        Raises:
            PermioPermissionError: unless the API key has ``permission.check`` on
                ``under`` and ``principal.assignment.get`` on the principal.
        """
        base = self._config.list_access_request(principal, permission, under, project)
        covers_all = False
        scopes: List[AccessScopeInfo] = []

        async def fetch(pagination: Any) -> Any:
            req = pb.ListAccessRequest()
            req.CopyFrom(base)
            req.pagination.CopyFrom(pagination)
            return await self._call("ListAccess", req, timeout, metadata)

        async for page in apaginate(fetch, lambda res: [res], page_size):
            covers_all = covers_all or page.covers_all
            scopes.extend(AccessScopeInfo(s.uri, scope_kind_name(s.scope)) for s in page.scopes)
        return AccessScopes(under, covers_all, scopes)

    async def who_has_access(
        self,
        resource: str,
        *,
        permission: Optional[str] = None,
        expand_groups: bool = False,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> List[AccessEntry]:
        """Answers "who has access to ``resource``?", following every page.

        Lists the principals (groups included, as ``group:<slug>``) with a grant
        on the resource, an ancestor of it, or a ``_`` wildcard URI matching it,
        ordered by principal ID, with the grants that give the access. With
        ``permission``, only grants that confer it count. ``expand_groups`` also
        lists every member of each listed group, with ``via_group`` set.

        Raises:
            PermioPermissionError: unless the API key has ``principal.list`` and
                ``principal.assignment.list`` on the project.
        """
        base = self._config.who_has_access_request(resource, permission, expand_groups, project)

        async def fetch(pagination: Any) -> Any:
            req = pb.ListPrincipalsWithAccessRequest()
            req.CopyFrom(base)
            req.pagination.CopyFrom(pagination)
            return await self._call("ListPrincipalsWithAccess", req, timeout, metadata)

        return [
            to_access_entry(p) async for p in apaginate(fetch, lambda r: r.principals, page_size)
        ]

    # -- lists ---------------------------------------------------------------

    def list_permissions(
        self,
        *,
        project: Optional[str] = None,
        search: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AsyncIterator[pb.Permission]:
        """Iterates every permission in a project, fetching pages as needed."""
        project_name = self._config.resolve_project(project)
        return apaginate(
            lambda p: self._call(
                "ListPermissions",
                pb.ListPermissionsRequest(
                    project_name=project_name, pagination=p, search=search or ""
                ),
                timeout,
                metadata,
            ),
            lambda r: r.permissions,
            page_size,
        )

    def list_roles(
        self,
        *,
        project: Optional[str] = None,
        search: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AsyncIterator[pb.Role]:
        """Iterates every role in a project."""
        project_name = self._config.resolve_project(project)
        return apaginate(
            lambda p: self._call(
                "ListRoles",
                pb.ListRolesRequest(project_name=project_name, pagination=p, search=search or ""),
                timeout,
                metadata,
            ),
            lambda r: r.roles,
            page_size,
        )

    def list_principals(
        self,
        *,
        project: Optional[str] = None,
        search: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AsyncIterator[str]:
        """Iterates the IDs of every principal with grants in a project."""
        project_name = self._config.resolve_project(project)
        return apaginate(
            lambda p: self._call(
                "ListPrincipals",
                pb.ListPrincipalsRequest(
                    project_name=project_name, pagination=p, search=search or ""
                ),
                timeout,
                metadata,
            ),
            lambda r: r.principals,
            page_size,
        )

    def list_assignments(
        self,
        principal: str,
        *,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AsyncIterator[pb.Assignment]:
        """Iterates every assignment (resource + permissions + roles) of a principal in a project."""
        require_principal(principal)
        project_name = self._config.resolve_project(project)
        return apaginate(
            lambda p: self._call(
                "GetAllAssignmentsForPrincipal",
                pb.GetAllAssignmentsForPrincipalRequest(
                    project_name=project_name, principal_id=principal, pagination=p
                ),
                timeout,
                metadata,
            ),
            lambda r: r.assignments,
            page_size,
        )

    # -- grant / revoke ------------------------------------------------------

    async def grant(
        self,
        principal: str,
        resource: str,
        *,
        permissions: Optional[Names] = None,
        roles: Optional[Names] = None,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> None:
        """Grants permissions and roles to ``principal`` on ``resource``, and so on everything below it.

        Additive: what the principal already holds there is kept. Pass
        ``group(slug)`` as ``principal`` to grant to every member of a group.
        ``permissions`` and ``roles`` (role IDs) each take one value or a list.
        Like every write, a grant is sent once and never retried automatically.

        Raises:
            PermioValidationError: if a permission or role does not exist in the
                project, or the input is malformed.
            PermioPermissionError: unless the API key has full access.
        """
        fields = self._config.grant_fields(principal, resource, permissions, roles, project)
        await self._call(
            "GrantUserPermissionsAndRolesOnResource",
            pb.GrantUserPermissionsAndRolesOnResourceRequest(**fields),
            timeout,
            metadata,
        )

    async def revoke(
        self,
        principal: str,
        resource: str,
        *,
        permissions: Optional[Names] = None,
        roles: Optional[Names] = None,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> None:
        """Removes permissions and roles from ``principal``'s grant on exactly ``resource``.

        Names the grant does not hold are ignored, so revoking twice is
        harmless. Grants on ancestor URIs are not touched, so the principal may
        still pass ``check()`` afterwards; ``who_has_access()`` shows where
        access comes from. Sent once, never retried automatically.

        Raises:
            PermioPermissionError: unless the API key has full access.
        """
        fields = self._config.grant_fields(principal, resource, permissions, roles, project)
        await self._call(
            "RevokeUserPermissionsAndRolesOnResource",
            pb.RevokeUserPermissionsAndRolesOnResourceRequest(**fields),
            timeout,
            metadata,
        )

    # -- whoami --------------------------------------------------------------

    async def who_am_i(
        self, *, timeout: Optional[float] = None, metadata: MetadataArg = None
    ) -> WhoAmI:
        """Describes the credential this client uses (ID, organisation, project, access level).

        Useful to verify a key at startup. Needs no project.

        Raises:
            PermioAuthError: if the key is unknown or invalidated.
        """
        return to_who_am_i(await self._call("WhoAmI", pb.WhoAmIRequest(), timeout, metadata))


class AsyncGroups:
    """Async groups of principals, available as ``permio.groups``. See :class:`Groups`.

    A group is referenced as the principal ``group:<slug>`` (see :func:`group`):
    grant to it and every member holds the grant. Groups cannot contain groups.
    Every method that takes a group accepts its slug (``"editors"``) or its
    principal ID (``"group:editors"``).
    """

    def __init__(self, client: AsyncPermio) -> None:
        self._client = client

    async def _call(
        self, method: str, request: Any, timeout: Optional[float], metadata: MetadataArg
    ) -> Any:
        return await self._client._call(method, request, timeout, metadata)

    def _project(self, project: Optional[str]) -> str:
        return self._client._config.resolve_project(project)

    async def create(
        self,
        name: str,
        *,
        description: str = "",
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> pb.Group:
        """Creates a group. Raises :class:`PermioError` with code ALREADY_EXISTS if the name is taken."""
        slug = ClientConfig.group_slug(name)
        req = pb.CreateGroupRequest(
            project_name=self._project(project), name=slug, description=description
        )
        res: pb.Group = await self._call("CreateGroup", req, timeout, metadata)
        return res

    async def get(
        self,
        name: str,
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> pb.Group:
        """Returns a group. Raises :class:`PermioNotFoundError` if it does not exist."""
        slug = ClientConfig.group_slug(name)
        req = pb.GetGroupRequest(project_name=self._project(project), name=slug)
        res: pb.Group = await self._call("GetGroup", req, timeout, metadata)
        return res

    async def update(
        self,
        name: str,
        *,
        description: str,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> pb.Group:
        """Replaces a group's description. A group's name cannot be changed."""
        slug = ClientConfig.group_slug(name)
        if not isinstance(description, str):
            raise PermioValidationError("permio: description is required")
        req = pb.UpdateGroupRequest(
            project_name=self._project(project), name=slug, description=description
        )
        res: pb.Group = await self._call("UpdateGroup", req, timeout, metadata)
        return res

    async def delete(
        self,
        name: str,
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> None:
        """Deletes a group, its memberships and every grant made to it, whether or not it existed."""
        slug = ClientConfig.group_slug(name)
        await self._call(
            "DeleteGroup",
            pb.DeleteGroupRequest(project_name=self._project(project), name=slug),
            timeout,
            metadata,
        )

    def list(
        self,
        *,
        project: Optional[str] = None,
        search: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AsyncIterator[pb.Group]:
        """Iterates every group in a project, ordered by name."""
        project_name = self._project(project)
        return apaginate(
            lambda p: self._call(
                "ListGroups",
                pb.ListGroupsRequest(project_name=project_name, pagination=p, search=search or ""),
                timeout,
                metadata,
            ),
            lambda r: r.groups,
            page_size,
        )

    async def add_members(
        self,
        name: str,
        principals: Sequence[str],
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AddMembersResult:
        """Adds up to 100 principals; ones already in the group are reported in ``existing``."""
        slug = ClientConfig.group_slug(name)
        ids = ClientConfig.member_ids(principals, adding=True)
        res = await self._call(
            "AddGroupMembers",
            pb.AddGroupMembersRequest(
                project_name=self._project(project), name=slug, principal_ids=ids
            ),
            timeout,
            metadata,
        )
        return AddMembersResult(list(res.added_principal_ids), list(res.existing_principal_ids))

    async def remove_members(
        self,
        name: str,
        principals: Sequence[str],
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> RemoveMembersResult:
        """Removes up to 100 principals; ones that were not members are reported in ``not_members``."""
        slug = ClientConfig.group_slug(name)
        ids = ClientConfig.member_ids(principals, adding=False)
        res = await self._call(
            "RemoveGroupMembers",
            pb.RemoveGroupMembersRequest(
                project_name=self._project(project), name=slug, principal_ids=ids
            ),
            timeout,
            metadata,
        )
        return RemoveMembersResult(
            list(res.removed_principal_ids), list(res.not_member_principal_ids)
        )

    def list_members(
        self,
        name: str,
        *,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AsyncIterator[pb.GroupMember]:
        """Iterates a group's members, ordered by principal ID."""
        slug = ClientConfig.group_slug(name)
        project_name = self._project(project)
        return apaginate(
            lambda p: self._call(
                "ListGroupMembers",
                pb.ListGroupMembersRequest(project_name=project_name, name=slug, pagination=p),
                timeout,
                metadata,
            ),
            lambda r: r.members,
            page_size,
        )

    def list_for_principal(
        self,
        principal: str,
        *,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AsyncIterator[pb.Group]:
        """Iterates the groups ``principal`` is a member of, ordered by name."""
        require_principal(principal)
        project_name = self._project(project)
        return apaginate(
            lambda p: self._call(
                "ListGroupsForPrincipal",
                pb.ListGroupsForPrincipalRequest(
                    project_name=project_name, principal_id=principal, pagination=p
                ),
                timeout,
                metadata,
            ),
            lambda r: r.groups,
            page_size,
        )


def _channel_options(extra: Optional[Sequence[Tuple[str, Any]]]) -> List[Tuple[str, Any]]:
    return channel_options(extra)


def _stub(cls: Any, channel: Any) -> Any:
    # The generated *_pb2_grpc stubs are untyped.
    return cls(channel)
