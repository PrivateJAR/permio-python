"""The synchronous client, :class:`Permio`."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Type, Union

import grpc

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
    DEFAULT_MAX_BATCH_RESOURCES,
    DEFAULT_MAX_RESULTS,
    LIST_PAGE_METHODS,
    AddMembersResult,
    ClientConfig,
    Names,
    RemoveMembersResult,
    check_max,
    collect,
    paginate,
    require_principal,
)
from ._errors import PermioDeniedError, PermioValidationError
from ._transport import (
    ORGANISATION_SERVICE,
    PERMISSIONS_SERVICE,
    MetadataArg,
    RawService,
    RetryOptions,
    SyncInvoker,
    channel_options,
    parse_target,
)
from .organisation.v1 import organisation_pb2_grpc
from .permissions.v1 import permissions_pb2 as pb
from .permissions.v1 import permissions_pb2_grpc


class Permio:
    """Synchronous client for the perms.io API.

    ::

        from permio import Permio, resource

        with Permio(project="my-app") as permio:  # api_key defaults to $PERMIO_API_KEY
            if permio.check(user_id, "docs.read", resource("docs", doc_id)):
                ...

    Args:
        api_key: API key from the dashboard (``perms_...``), or a legacy JWT key.
            Defaults to the ``PERMIO_API_KEY`` environment variable. Checked
            locally for typos (:class:`PermioConfigError`).
        base_url: API endpoint. Defaults to production, ``https://api.perms.io``
            (:data:`DEFAULT_BASE_URL`); use :data:`DEV_BASE_URL` for development.
            ``http://host:port`` connects without TLS; ``host:port`` uses TLS.
        project: Default project for helpers that take ``project``.
        timeout: Timeout per attempt in seconds. Default 10; 0 disables it.
        list_timeout: Timeout per attempt for each page a list helper fetches
            (iterators, streams, ``who_has_access``, ``list_access``). Defaults to
            ``timeout``; 0 disables it. A per-call ``timeout`` still caps it.
        retries: Retries for idempotent reads on UNAVAILABLE / DEADLINE_EXCEEDED
            (and rate limiting with a server-given delay). An int sets
            ``max_retries``; default 2. Writes are never retried.
        channel: A ``grpc.Channel`` to use instead of creating one (for tests,
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
        list_timeout: Optional[float] = None,
        retries: Union[int, RetryOptions, None] = None,
        channel: Optional[grpc.Channel] = None,
        channel_options: Optional[Sequence[Tuple[str, Any]]] = None,
    ) -> None:
        self._config = ClientConfig(api_key, base_url, project, timeout, retries, list_timeout)
        if channel is None:
            target, secure = parse_target(self._config.base_url)
            options = _channel_options(channel_options)
            channel = (
                grpc.secure_channel(target, grpc.ssl_channel_credentials(), options=options)
                if secure
                else grpc.insecure_channel(target, options=options)
            )
            self._owns_channel = True
        else:
            self._owns_channel = False
        self.channel: grpc.Channel = channel
        """The underlying gRPC channel."""
        self._invoker = SyncInvoker(self._config.api_key, self._config.timeout, self._config.retry)
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
        self.groups = Groups(self)
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
        return f"Permio(base_url={self.base_url!r}, project={self.project!r})"

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Closes the channel, if the client created it."""
        if self._owns_channel:
            self.channel.close()

    def __enter__(self) -> Permio:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    # -- internals -----------------------------------------------------------

    def _call(
        self,
        method: str,
        request: Any,
        timeout: Optional[float],
        metadata: MetadataArg,
    ) -> Any:
        if method in LIST_PAGE_METHODS:
            # One page of a listing: per-attempt timeout is list_timeout.
            return self._invoker.call(
                f"{PERMISSIONS_SERVICE}.{method}",
                getattr(self.permissions._stub, method),
                request,
                timeout=timeout,
                metadata=metadata,
                per_attempt=self._config.list_timeout,
            )
        return getattr(self.permissions, method)(request, timeout=timeout, metadata=metadata)

    # -- checks --------------------------------------------------------------

    def check_detailed(
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
        return self._config.check_result(self._call("Check", req, timeout, metadata))

    def check(
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
        return self.check_detailed(
            principal, permission, resource, project=project, timeout=timeout, metadata=metadata
        ).allowed

    check_all = check
    """Alias of :meth:`check`: every permission on every resource."""

    def check_any(
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
        result = self.check_detailed(
            principal, permission, resource, project=project, timeout=timeout, metadata=metadata
        )
        return self._config.any_allowed(result, permission)

    def assert_allowed(
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
        result = self.check_detailed(
            principal, permission, resource, project=project, timeout=timeout, metadata=metadata
        )
        if not result.allowed:
            raise PermioDeniedError(principal, result.missing)

    def batch_check(
        self,
        principal: str,
        permission: Names,
        resources: Iterable[str],
        *,
        max_resources: int = DEFAULT_MAX_BATCH_RESOURCES,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> Dict[str, bool]:
        """Checks each resource separately; returns ``{uri: allowed}`` in request order.

        A resource is allowed only with every requested permission. More than
        100 resources are split into ``BatchCheck`` calls of 100. Use it to
        filter a list you already have::

            allowed = permio.batch_check(user_id, "docs.read", [resource("docs", d.id) for d in docs])
            visible = [d for d in docs if allowed[resource("docs", d.id)]]

        Raises:
            PermioValidationError: for more than ``max_resources`` resources
                (default 10,000, counted before de-duplication), or malformed input.
        """
        entries = self.batch_check_detailed(
            principal,
            permission,
            resources,
            max_resources=max_resources,
            project=project,
            timeout=timeout,
            metadata=metadata,
        )
        return {e.resource: e.allowed for e in entries}

    def batch_check_detailed(
        self,
        principal: str,
        permission: Names,
        resources: Iterable[str],
        *,
        max_resources: int = DEFAULT_MAX_BATCH_RESOURCES,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> List[BatchCheckEntry]:
        """Like :meth:`batch_check`, but one entry per resource with the missing permissions."""
        plan = self._config.batch_plan(principal, permission, resources, project, max_resources)
        # Sent one chunk at a time; each request is built only when it is sent.
        responses = (
            self._call("BatchCheck", plan.request(i), timeout, metadata)
            for i in range(plan.chunk_count())
        )
        return self._config.batch_entries(plan.uris, responses)

    # -- access queries ------------------------------------------------------

    def list_access(
        self,
        principal: str,
        permission: str,
        under: str,
        *,
        max_results: int = DEFAULT_MAX_RESULTS,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> AccessScopes:
        """Answers "where may ``principal`` use ``permission`` at or below ``under``?".

        Follows every page into memory, up to ``max_results`` scopes (default
        10,000). Use the result to filter lists in your database:
        ``covers_all`` means no filter is needed, ``to_prefixes()`` gives path
        prefixes, ``to_regex()`` a regex, and ``allows(uri)`` tests one URI.
        :meth:`iter_list_access` streams the scopes instead.

        Raises:
            PermioTooManyResultsError: past ``max_results`` scopes; at most
                ``max_results + 1`` are fetched.
            PermioPermissionError: unless the API key has ``permission.check`` on
                ``under`` and ``principal.assignment.get`` on the principal.
        """
        check_max(max_results, "max_results")
        found = collect(
            self._list_access_items(
                principal, permission, under, project, page_size, timeout, metadata, max_results + 1
            ),
            max_results,
            "list_access",
            "iter_list_access",
        )
        covers_all = any(c for c, _ in found)
        return AccessScopes(under, covers_all, [s for _, s in found])

    def iter_list_access(
        self,
        principal: str,
        permission: str,
        under: str,
        *,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> Iterator[AccessScopeInfo]:
        """Streams the scopes of :meth:`list_access`, fetching pages as needed.

        Nothing is buffered beyond one page. When ``principal`` holds
        ``permission`` on ``under`` itself, the only scope is a ``"subtree"``
        scope whose ``uri`` is ``under`` (that is ``covers_all``).
        """
        return (
            s
            for _, s in self._list_access_items(
                principal, permission, under, project, page_size, timeout, metadata, None
            )
        )

    def _list_access_items(
        self,
        principal: str,
        permission: str,
        under: str,
        project: Optional[str],
        page_size: Optional[int],
        timeout: Optional[float],
        metadata: MetadataArg,
        max_items: Optional[int],
    ) -> Iterator[Tuple[bool, AccessScopeInfo]]:
        base = self._config.list_access_request(principal, permission, under, project)

        def fetch(pagination: Any) -> Any:
            req = pb.ListAccessRequest()
            req.CopyFrom(base)
            req.pagination.CopyFrom(pagination)
            return self._call("ListAccess", req, timeout, metadata)

        return paginate(
            fetch,
            lambda res: [
                (res.covers_all, AccessScopeInfo(s.uri, scope_kind_name(s.scope)))
                for s in res.scopes
            ],
            page_size,
            max_items,
        )

    def who_has_access(
        self,
        resource: str,
        *,
        permission: Optional[str] = None,
        expand_groups: bool = False,
        max_results: int = DEFAULT_MAX_RESULTS,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> List[AccessEntry]:
        """Answers "who has access to ``resource``?", following every page into memory.

        Lists the principals (groups included, as ``group:<slug>``) with a grant
        on the resource, an ancestor of it, or a ``_`` wildcard URI matching it,
        ordered by principal ID, with the grants that give the access. With
        ``permission``, only grants that confer it count. ``expand_groups`` also
        lists every member of each listed group, with ``via_group`` set.

        Collects at most ``max_results`` entries (default 10,000); a resource
        can have millions of principals, so :meth:`iter_who_has_access` streams
        them instead.

        Raises:
            PermioTooManyResultsError: past ``max_results`` entries; at most
                ``max_results + 1`` are fetched.
            PermioPermissionError: unless the API key has ``principal.list`` and
                ``principal.assignment.list`` on the project.
        """
        check_max(max_results, "max_results")
        return collect(
            self._who_has_access_items(
                resource,
                permission,
                expand_groups,
                project,
                page_size,
                timeout,
                metadata,
                max_results + 1,
            ),
            max_results,
            "who_has_access",
            "iter_who_has_access",
        )

    def iter_who_has_access(
        self,
        resource: str,
        *,
        permission: Optional[str] = None,
        expand_groups: bool = False,
        project: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> Iterator[AccessEntry]:
        """Streams the entries of :meth:`who_has_access`, fetching pages as needed.

        Nothing is buffered beyond one page, so this suits resources with any
        number of principals. Arguments are validated when called; pages are
        fetched as you iterate.
        """
        return self._who_has_access_items(
            resource, permission, expand_groups, project, page_size, timeout, metadata, None
        )

    def _who_has_access_items(
        self,
        resource: str,
        permission: Optional[str],
        expand_groups: bool,
        project: Optional[str],
        page_size: Optional[int],
        timeout: Optional[float],
        metadata: MetadataArg,
        max_items: Optional[int],
    ) -> Iterator[AccessEntry]:
        base = self._config.who_has_access_request(resource, permission, expand_groups, project)

        def fetch(pagination: Any) -> Any:
            req = pb.ListPrincipalsWithAccessRequest()
            req.CopyFrom(base)
            req.pagination.CopyFrom(pagination)
            return self._call("ListPrincipalsWithAccess", req, timeout, metadata)

        return paginate(
            fetch, lambda r: [to_access_entry(p) for p in r.principals], page_size, max_items
        )

    # -- lists ---------------------------------------------------------------

    def list_permissions(
        self,
        *,
        project: Optional[str] = None,
        search: Optional[str] = None,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> Iterator[pb.Permission]:
        """Iterates every permission in a project, fetching pages as needed."""
        project_name = self._config.resolve_project(project)
        return paginate(
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
    ) -> Iterator[pb.Role]:
        """Iterates every role in a project."""
        project_name = self._config.resolve_project(project)
        return paginate(
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
    ) -> Iterator[str]:
        """Iterates the IDs of every principal with grants in a project."""
        project_name = self._config.resolve_project(project)
        return paginate(
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
    ) -> Iterator[pb.Assignment]:
        """Iterates every assignment (resource + permissions + roles) of a principal in a project."""
        require_principal(principal)
        project_name = self._config.resolve_project(project)
        return paginate(
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

    def grant(
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
        self._call(
            "GrantUserPermissionsAndRolesOnResource",
            pb.GrantUserPermissionsAndRolesOnResourceRequest(**fields),
            timeout,
            metadata,
        )

    def revoke(
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
        self._call(
            "RevokeUserPermissionsAndRolesOnResource",
            pb.RevokeUserPermissionsAndRolesOnResourceRequest(**fields),
            timeout,
            metadata,
        )

    # -- whoami --------------------------------------------------------------

    def who_am_i(self, *, timeout: Optional[float] = None, metadata: MetadataArg = None) -> WhoAmI:
        """Describes the credential this client uses (ID, organisation, project, access level).

        Useful to verify a key at startup. Needs no project.

        Raises:
            PermioAuthError: if the key is unknown or invalidated.
        """
        return to_who_am_i(self._call("WhoAmI", pb.WhoAmIRequest(), timeout, metadata))


class Groups:
    """Groups of principals, available as ``permio.groups``.

    A group is referenced as the principal ``group:<slug>`` (see :func:`group`):
    grant to it and every member holds the grant. Groups cannot contain groups.
    Every method that takes a group accepts its slug (``"editors"``) or its
    principal ID (``"group:editors"``).
    """

    def __init__(self, client: Permio) -> None:
        self._client = client

    def _call(
        self, method: str, request: Any, timeout: Optional[float], metadata: MetadataArg
    ) -> Any:
        return self._client._call(method, request, timeout, metadata)

    def _project(self, project: Optional[str]) -> str:
        return self._client._config.resolve_project(project)

    def create(
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
        res: pb.Group = self._call("CreateGroup", req, timeout, metadata)
        return res

    def get(
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
        res: pb.Group = self._call("GetGroup", req, timeout, metadata)
        return res

    def update(
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
        res: pb.Group = self._call("UpdateGroup", req, timeout, metadata)
        return res

    def delete(
        self,
        name: str,
        *,
        project: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: MetadataArg = None,
    ) -> None:
        """Deletes a group, its memberships and every grant made to it, whether or not it existed."""
        slug = ClientConfig.group_slug(name)
        self._call(
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
    ) -> Iterator[pb.Group]:
        """Iterates every group in a project, ordered by name."""
        project_name = self._project(project)
        return paginate(
            lambda p: self._call(
                "ListGroups",
                pb.ListGroupsRequest(project_name=project_name, pagination=p, search=search or ""),
                timeout,
                metadata,
            ),
            lambda r: r.groups,
            page_size,
        )

    def add_members(
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
        res = self._call(
            "AddGroupMembers",
            pb.AddGroupMembersRequest(
                project_name=self._project(project), name=slug, principal_ids=ids
            ),
            timeout,
            metadata,
        )
        return AddMembersResult(list(res.added_principal_ids), list(res.existing_principal_ids))

    def remove_members(
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
        res = self._call(
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
    ) -> Iterator[pb.GroupMember]:
        """Iterates a group's members, ordered by principal ID."""
        slug = ClientConfig.group_slug(name)
        project_name = self._project(project)
        return paginate(
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
    ) -> Iterator[pb.Group]:
        """Iterates the groups ``principal`` is a member of, ordered by name."""
        require_principal(principal)
        project_name = self._project(project)
        return paginate(
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
