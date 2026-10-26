"""Result types: access scopes, access entries, check results, whoAmI."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

from ._errors import MissingPermission, PermioError
from .permissions.v1 import permissions_pb2 as pb

WILDCARD_SEGMENT = "_"
"""The ``_`` segment: in a ``pattern`` scope it matches exactly one segment."""


@dataclass(frozen=True)
class CheckResult:
    """Result of ``check_detailed()``."""

    allowed: bool
    """True when the principal holds every permission on every resource."""
    missing: List[MissingPermission] = field(default_factory=list)
    """What is missing, per resource, in request order. Empty when allowed."""

    def __bool__(self) -> bool:
        return self.allowed


@dataclass(frozen=True)
class BatchCheckEntry:
    """One resource's result from ``batch_check_detailed()``."""

    resource: str
    allowed: bool
    """True when the principal holds every requested permission on ``resource``."""
    missing: List[str] = field(default_factory=list)
    """The requested permissions the principal lacks on ``resource``, in request order."""


@dataclass(frozen=True)
class WhoAmI:
    """The caller, as returned by ``who_am_i()``."""

    principal_id: str
    """The caller's principal ID; for an API key, the key's ID."""
    organisation_id: str
    """The caller's organisation. Empty for a user who has not joined one yet."""
    kind: str
    """``"user"``, ``"api_key"``, ``"service_account"`` or ``"unknown"``."""
    project: Optional[str]
    """The project an API key belongs to; it can only be used there. None for users."""
    api_key_access: Optional[str]
    """For an API key: ``"check"`` (checks and reads), ``"full"`` (also writes, grant and
    revoke) or ``"unknown"`` (its rights were changed by hand). None for other credentials."""
    email: Optional[str]
    """The user's email address, when the caller is a user and has one."""


@dataclass(frozen=True)
class AccessScopeInfo:
    """One place where a principal holds a permission.

    ``kind`` is ``"subtree"`` (the URI and everything below it), ``"pattern"``
    (every URI whose leading segments match, where each ``_`` segment matches
    exactly one segment, and everything below those), ``"exact"`` (exactly the
    URI; reserved by the API, not returned today) or ``"unknown"`` (a kind this
    SDK version does not know; it never matches).
    """

    uri: str
    kind: str


@dataclass(frozen=True)
class AccessGrantSource:
    """Where a grant's access comes from: ``type`` is ``"role"``, ``"direct"`` or ``"unknown"``."""

    type: str
    id: Optional[str] = None
    """The role ID, for ``type == "role"``."""
    name: Optional[str] = None
    """The role name, for ``type == "role"``."""


@dataclass(frozen=True)
class AccessGrantInfo:
    """One grant (or one role within a grant) that gives a principal access."""

    resource: str
    """The URI the grant was made on: the resource, an ancestor, or a URI with ``_`` segments matching it."""
    inherited: bool
    """True unless the grant was made on exactly the resource."""
    match: str
    """``"exact"``, ``"ancestor"``, ``"wildcard"`` or ``"unknown"``."""
    source: AccessGrantSource


@dataclass(frozen=True)
class AccessEntry:
    """One principal with access to a resource, returned by ``who_has_access()``."""

    principal: str
    """The principal ID; ``group:<slug>`` for a group."""
    is_group: bool
    via_group: Optional[str]
    """The slug of the group through which ``principal`` has the grants in ``via``, for
    entries added by ``expand_groups``. None for grants made to ``principal`` itself."""
    via: List[AccessGrantInfo]
    """The grants that give the access, most specific first."""


_SCOPE_KINDS = {
    pb.ACCESS_SCOPE_KIND_SUBTREE: "subtree",
    pb.ACCESS_SCOPE_KIND_PATTERN: "pattern",
    pb.ACCESS_SCOPE_KIND_EXACT: "exact",
}

_MATCHES = {
    pb.ACCESS_GRANT_MATCH_EXACT: "exact",
    pb.ACCESS_GRANT_MATCH_ANCESTOR: "ancestor",
    pb.ACCESS_GRANT_MATCH_WILDCARD: "wildcard",
}


def scope_kind_name(kind: pb.AccessScopeKind) -> str:
    return _SCOPE_KINDS.get(kind, "unknown")


def _segments(uri: str) -> Optional[List[str]]:
    """Splits "/a/b" into ["a", "b"]; None for anything that is not a well-formed URI."""
    if not isinstance(uri, str) or not uri.startswith("/") or len(uri) < 2:
        return None
    parts = uri[1:].split("/")
    return None if "" in parts else parts


def _scope_matches(scope: AccessScopeInfo, target: List[str]) -> bool:
    own = _segments(scope.uri)
    if own is None:
        return False
    if scope.kind == "exact":
        return own == target
    if scope.kind == "subtree":
        # Segment by segment, so /a/b covers /a/b/c but not /a/bc. A "_" here is literal.
        return len(own) <= len(target) and own == target[: len(own)]
    if scope.kind == "pattern":
        return len(own) <= len(target) and all(
            s in (WILDCARD_SEGMENT, t) for s, t in zip(own, target)
        )
    return False


_REGEX_META = re.compile(r"[.*+?^${}()|\[\]\\/]")


def _escape(text: str) -> str:
    # The same escaping as the JavaScript SDK, so the pattern source also works
    # in PCRE (MongoDB $regex) and PostgreSQL regexes.
    return _REGEX_META.sub(lambda m: "\\" + m.group(0), text)


def _scope_regex_source(scope: AccessScopeInfo) -> Optional[str]:
    own = _segments(scope.uri)
    if own is None:
        return None
    body = "".join(
        "\\/" + ("[^/]+" if scope.kind == "pattern" and s == WILDCARD_SEGMENT else _escape(s))
        for s in own
    )
    if scope.kind == "exact":
        return body
    if scope.kind in ("subtree", "pattern"):
        return body + "(?:\\/.*)?"
    return None


class AccessScopes:
    """The answer to "where may this principal use this permission under ``under``?".

    Returned by ``list_access()``; every page has already been fetched::

        access = permio.list_access("alice", "docs.read", under="/docs")
        visible = [d for d in docs if access.allows(resource("docs", d.id))]

    The scopes describe resources at or below ``under``. A URI outside ``under``
    was not asked about, so ``allows()`` returning False for it means "unknown",
    not "denied". A pattern scope may also match some URIs outside ``under``
    (its ``_`` segments can sit in the part that matches ``under``); those really
    are allowed.
    """

    def __init__(self, under: str, covers_all: bool, scopes: Iterable[AccessScopeInfo]) -> None:
        self.under = under
        """The ``under`` URI that was asked about."""
        self.covers_all = covers_all
        """True when the principal holds the permission on ``under`` itself, and so on
        everything below it. Check this first: when it is true, a list needs no filter."""
        self.scopes: Tuple[AccessScopeInfo, ...] = tuple(scopes)
        """Every scope, ordered by URI as the API returned them."""

    def __repr__(self) -> str:
        return f"AccessScopes(under={self.under!r}, covers_all={self.covers_all!r}, scopes={list(self.scopes)!r})"

    @property
    def is_empty(self) -> bool:
        """True when the principal has no access anywhere under ``under``."""
        return not self.covers_all and not any(s.kind != "unknown" for s in self.scopes)

    def allows(self, uri: str) -> bool:
        """Whether the principal holds the permission on ``uri``, according to these scopes.

        Matching is per segment: a subtree scope ``/a/b`` allows ``/a/b`` and
        ``/a/b/c`` but not ``/a/bc``; a pattern scope ``/a/_/c`` allows
        ``/a/x/c`` and ``/a/x/c/d`` but not ``/a/x`` or ``/a/x/y``. Malformed
        URIs are never allowed.
        """
        target = _segments(uri)
        if target is None:
            return False
        return any(_scope_matches(s, target) for s in self.scopes)

    def to_prefixes(self) -> List[str]:
        """The subtree scopes' URIs, for filtering a database by path prefix.

        A URI ``p`` here stands for ``p`` itself and everything below it, so
        match ``path = p OR starts_with(path, p || '/')`` (a literal prefix
        test). Avoid ``LIKE p || '/%'``: ``_`` and ``%`` in ``p`` are ``LIKE``
        wildcards. A bare prefix match would also match ``/docs/12`` for
        ``/docs/1``. Prefixes already covered by a shorter
        one are dropped. Pattern scopes are not included: see ``patterns()``,
        ``to_regex()`` and ``has_patterns``.
        """
        subtrees = list(dict.fromkeys(s.uri for s in self.scopes if s.kind == "subtree"))
        return [p for p in subtrees if not any(p.startswith(q + "/") for q in subtrees)]

    def patterns(self) -> List[str]:
        """The pattern scopes' URIs (with ``_`` segments). Empty when every scope is a prefix."""
        return [s.uri for s in self.scopes if s.kind == "pattern"]

    def exact(self) -> List[str]:
        """The exact scopes' URIs. The API does not return exact scopes today."""
        return [s.uri for s in self.scopes if s.kind == "exact"]

    @property
    def has_patterns(self) -> bool:
        """True when some scope is a pattern, so ``to_prefixes()`` alone does not cover everything."""
        return any(s.kind == "pattern" for s in self.scopes)

    def to_regex(self) -> re.Pattern[str]:
        """One anchored regular expression matching exactly the URIs ``allows()`` accepts.

        Use ``.pattern`` for stores that filter by regex (MongoDB ``$regex``,
        PostgreSQL ``~``). With no scopes it matches nothing.
        """
        parts = [p for p in (_scope_regex_source(s) for s in self.scopes) if p is not None]
        # "$.^" can never match, and is valid in Python, PCRE (MongoDB) and PostgreSQL regexes.
        return re.compile("$.^" if not parts else "^(?:" + "|".join(parts) + ")$")


def to_access_entry(p: pb.PrincipalAccess) -> AccessEntry:
    via: List[AccessGrantInfo] = []
    for g in p.via:
        which = g.WhichOneof("source")
        if which == "role":
            source = AccessGrantSource("role", g.role.id, g.role.name)
        elif which == "direct":
            source = AccessGrantSource("direct")
        else:
            source = AccessGrantSource("unknown")
        via.append(
            AccessGrantInfo(
                resource=g.resource_uri,
                inherited=g.inherited,
                match=_MATCHES.get(g.match, "unknown"),
                source=source,
            )
        )
    return AccessEntry(
        principal=p.principal_id,
        is_group=p.is_group,
        via_group=p.via_group or None,
        via=via,
    )


def inconsistent_response(what: str) -> PermioError:
    """The API answered in a way the SDK cannot trust, e.g. a batch result for an unrequested resource."""
    return PermioError(f"permio: inconsistent response from the API: {what}")


_PRINCIPAL_KINDS = {
    pb.PRINCIPAL_TYPE_USER: "user",
    pb.PRINCIPAL_TYPE_API_KEY: "api_key",
    pb.PRINCIPAL_TYPE_SERVICE_ACCOUNT: "service_account",
}

_API_KEY_ACCESS = {
    pb.API_KEY_ACCESS_CHECK: "check",
    pb.API_KEY_ACCESS_FULL: "full",
}


def to_who_am_i(res: pb.WhoAmIResponse) -> WhoAmI:
    kind = _PRINCIPAL_KINDS.get(res.principal_type, "unknown")
    return WhoAmI(
        principal_id=res.principal_id,
        organisation_id=res.organisation_id,
        kind=kind,
        project=res.project_name or None,
        api_key_access=(
            _API_KEY_ACCESS.get(res.api_key_access, "unknown") if kind == "api_key" else None
        ),
        email=res.email or None,
    )
