"""The sync client against an in-process gRPC server."""

from __future__ import annotations

import time
from typing import Any, Callable, List

import grpc
import pytest

from permio import (
    BatchCheckEntry,
    MissingPermission,
    Permio,
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
    RetryOptions,
    WhoAmI,
    group,
    raw,
)
from permio.permissions.v1 import permissions_pb2 as pb

from .conftest import VALID_KEY, Abort, Recorder, retry_info_trailer

MakeClient = Callable[..., Permio]


def passed(ok: bool = True, missing: Any = ()) -> pb.CheckPermissionResponse:
    return pb.CheckPermissionResponse(passed=ok, missing_permissions=list(missing))


class TestCheck:
    def test_sends_auth_project_and_request(self, client: Permio, rec: Recorder) -> None:
        rec.on("Check", lambda req, ctx: passed())
        assert client.check("alice", "docs.read", "/docs/1") is True
        (name, req, md) = rec.calls[0]
        assert name == "Check"
        assert md["authorization"] == f"Bearer {VALID_KEY}"
        assert md["user-agent"].startswith("permio-python/")
        assert req == pb.CheckPermissionRequest(
            project_name="my-app",
            principal_id="alice",
            resource_uris=["/docs/1"],
            permissions=["docs.read"],
        )

    def test_lists_are_deduplicated_and_project_overrides(
        self, client: Permio, rec: Recorder
    ) -> None:
        rec.on("Check", lambda req, ctx: passed())
        client.check("a", ["p1", "p2", "p1"], ["/x", "/y", "/x"], project="other")
        req = rec.requests("Check")[0]
        assert list(req.permissions) == ["p1", "p2"]
        assert list(req.resource_uris) == ["/x", "/y"]
        assert req.project_name == "other"

    def test_denied_and_detailed(self, client: Permio, rec: Recorder) -> None:
        missing = [
            pb.MissingPermissions(resource_uri="/docs/1", missing_permissions=["docs.write"])
        ]
        rec.on("Check", lambda req, ctx: passed(False, missing))
        assert client.check("alice", ["docs.read", "docs.write"], "/docs/1") is False
        assert client.check_all("alice", ["docs.read", "docs.write"], "/docs/1") is False
        result = client.check_detailed("alice", ["docs.read", "docs.write"], "/docs/1")
        assert not result
        assert result.missing == [MissingPermission("/docs/1", ["docs.write"])]
        # Holds docs.read, so "any" passes.
        assert client.check_any("alice", ["docs.read", "docs.write"], "/docs/1") is True
        assert client.check_any("alice", ["docs.write"], "/docs/1") is False
        with pytest.raises(PermioDeniedError) as err:
            client.assert_allowed("alice", ["docs.read", "docs.write"], "/docs/1")
        assert err.value.principal == "alice"
        assert err.value.missing == [MissingPermission("/docs/1", ["docs.write"])]
        assert err.value.code is None
        assert "docs.write on /docs/1" in str(err.value)

    def test_assert_allowed_passes(self, client: Permio, rec: Recorder) -> None:
        rec.on("Check", lambda req, ctx: passed())
        client.assert_allowed("alice", "docs.read", "/docs/1")

    def test_validation_before_sending(self, make_client: MakeClient, rec: Recorder) -> None:
        client = make_client()
        with pytest.raises(PermioValidationError, match="principal"):
            client.check("", "p", "/x")
        with pytest.raises(PermioValidationError, match="at least one permission"):
            client.check("a", [], "/x")
        with pytest.raises(PermioValidationError, match="at most 100"):
            client.check("a", [f"p{i}" for i in range(101)], "/x")
        with pytest.raises(PermioValidationError, match="invalid resource URI"):
            client.check("a", "p", "docs/1")
        with pytest.raises(PermioConfigError, match="no project"):
            make_client(project=None).check("a", "p", "/x")
        assert rec.calls == []


class TestBatchCheck:
    def test_returns_map_in_request_order(self, client: Permio, rec: Recorder) -> None:
        def handler(req: pb.BatchCheckRequest, ctx: Any) -> pb.BatchCheckResponse:
            # Answer out of order: the SDK maps by URI.
            results = [
                pb.BatchCheckResult(
                    resource_uri=u,
                    allowed=u != "/b",
                    missing_permissions=[] if u != "/b" else list(req.permissions),
                )
                for u in reversed(req.resource_uris)
            ]
            return pb.BatchCheckResponse(results=results)

        rec.on("BatchCheck", handler)
        result = client.batch_check("alice", "docs.read", ["/a", "/b", "/c", "/a"])
        assert list(result.items()) == [("/a", True), ("/b", False), ("/c", True)]
        detailed = client.batch_check_detailed("alice", "docs.read", ["/b"])
        assert detailed == [BatchCheckEntry("/b", False, ["docs.read"])]

    def test_splits_into_chunks_of_100(self, client: Permio, rec: Recorder) -> None:
        rec.on(
            "BatchCheck",
            lambda req, ctx: pb.BatchCheckResponse(
                results=[
                    pb.BatchCheckResult(resource_uri=u, allowed=True) for u in req.resource_uris
                ]
            ),
        )
        uris = [f"/d/{i}" for i in range(250)]
        result = client.batch_check("alice", "p", uris)
        assert list(result) == uris
        assert [len(r.resource_uris) for r in rec.requests("BatchCheck")] == [100, 100, 50]

    def test_fails_closed_on_missing_result(self, client: Permio, rec: Recorder) -> None:
        rec.on("BatchCheck", lambda req, ctx: pb.BatchCheckResponse())
        with pytest.raises(PermioError, match="inconsistent response"):
            client.batch_check("alice", "p", ["/a"])

    def test_allowed_requires_no_missing(self, client: Permio, rec: Recorder) -> None:
        rec.on(
            "BatchCheck",
            lambda req, ctx: pb.BatchCheckResponse(
                results=[
                    pb.BatchCheckResult(resource_uri="/a", allowed=True, missing_permissions=["p"])
                ]
            ),
        )
        assert client.batch_check("alice", "p", ["/a"]) == {"/a": False}

    def test_rejects_string_resources(self, client: Permio) -> None:
        with pytest.raises(PermioValidationError):
            client.batch_check("alice", "p", "/a")


class TestPagination:
    def paged(self, rec: Recorder, pages: List[List[str]], cursors: List[str]) -> None:
        def handler(req: pb.ListPermissionsRequest, ctx: Any) -> pb.ListPermissionsResponse:
            i = 0 if not req.pagination.cursor else int(req.pagination.cursor.split("-")[1])
            res = pb.ListPermissionsResponse(permissions=[pb.Permission(name=n) for n in pages[i]])
            res.pagination.next_cursor = cursors[i]
            return res

        rec.on("ListPermissions", handler)

    def test_follows_cursors(self, client: Permio, rec: Recorder) -> None:
        self.paged(rec, [["a", "b"], ["c"], ["d"]], ["c-1", "c-2", ""])
        names = [p.name for p in client.list_permissions(page_size=2, search="x")]
        assert names == ["a", "b", "c", "d"]
        reqs = rec.requests("ListPermissions")
        assert [r.pagination.cursor for r in reqs] == ["", "c-1", "c-2"]
        assert all(r.pagination.limit == 2 and r.search == "x" for r in reqs)

    def test_stops_on_repeated_cursor(self, client: Permio, rec: Recorder) -> None:
        self.paged(rec, [["a"], ["b"]], ["c-1", "c-1"])
        assert [p.name for p in client.list_permissions()] == ["a", "b"]
        assert rec.count("ListPermissions") == 2

    def test_page_size_is_clamped_and_lazy(self, client: Permio, rec: Recorder) -> None:
        self.paged(rec, [["a"]], [""])
        it = client.list_permissions(page_size=1000)
        assert rec.calls == []
        assert [p.name for p in it] == ["a"]
        assert rec.requests("ListPermissions")[0].pagination.limit == 100

    def test_other_lists(self, client: Permio, rec: Recorder) -> None:
        rec.on("ListRoles", lambda req, ctx: pb.ListRolesResponse(roles=[pb.Role(id="r1")]))
        rec.on("ListPrincipals", lambda req, ctx: pb.ListPrincipalsResponse(principals=["alice"]))
        rec.on(
            "GetAllAssignmentsForPrincipal",
            lambda req, ctx: pb.GetAllAssignmentsForPrincipalResponse(
                assignments=[pb.Assignment(resource_uri="/x")]
            ),
        )
        assert [r.id for r in client.list_roles()] == ["r1"]
        assert list(client.list_principals()) == ["alice"]
        assert [a.resource_uri for a in client.list_assignments("alice")] == ["/x"]
        assert rec.requests("GetAllAssignmentsForPrincipal")[0].principal_id == "alice"

    def test_project_is_resolved_eagerly(self, make_client: MakeClient) -> None:
        with pytest.raises(PermioConfigError):
            make_client(project=None).list_roles()


class TestAccess:
    def test_list_access_collects_pages(self, client: Permio, rec: Recorder) -> None:
        def handler(req: pb.ListAccessRequest, ctx: Any) -> pb.ListAccessResponse:
            if not req.pagination.cursor:
                res = pb.ListAccessResponse(
                    scopes=[pb.AccessScope(uri="/docs/1", scope=pb.ACCESS_SCOPE_KIND_SUBTREE)]
                )
                res.pagination.next_cursor = "next"
                return res
            return pb.ListAccessResponse(
                scopes=[pb.AccessScope(uri="/docs/_/x", scope=pb.ACCESS_SCOPE_KIND_PATTERN)]
            )

        rec.on("ListAccess", handler)
        access = client.list_access("alice", "docs.read", "/docs")
        assert not access.covers_all
        assert access.to_prefixes() == ["/docs/1"]
        assert access.patterns() == ["/docs/_/x"]
        assert access.allows("/docs/1/2")
        req = rec.requests("ListAccess")[0]
        assert (req.principal_id, req.permission, req.under_uri) == ("alice", "docs.read", "/docs")

    def test_who_has_access(self, client: Permio, rec: Recorder) -> None:
        def handler(req: Any, ctx: Any) -> pb.ListPrincipalsWithAccessResponse:
            return pb.ListPrincipalsWithAccessResponse(
                principals=[
                    pb.PrincipalAccess(
                        principal_id="group:eds",
                        is_group=True,
                        via=[
                            pb.AccessGrant(
                                resource_uri="/docs",
                                inherited=True,
                                match=pb.ACCESS_GRANT_MATCH_ANCESTOR,
                                role=pb.AccessGrantRole(id="r1", name="Editor"),
                            )
                        ],
                    ),
                    pb.PrincipalAccess(
                        principal_id="bob",
                        via_group="eds",
                        via=[pb.AccessGrant(resource_uri="/docs/1", direct=pb.AccessGrantDirect())],
                    ),
                ]
            )

        rec.on("ListPrincipalsWithAccess", handler)
        entries = client.who_has_access("/docs/1", permission="docs.read", expand_groups=True)
        assert [e.principal for e in entries] == ["group:eds", "bob"]
        assert entries[0].is_group and entries[0].via_group is None
        assert entries[0].via[0].source.type == "role"
        assert entries[0].via[0].source.name == "Editor"
        assert entries[0].via[0].match == "ancestor"
        assert entries[1].via_group == "eds"
        assert entries[1].via[0].source.type == "direct"
        assert entries[1].via[0].match == "unknown"
        req = rec.requests("ListPrincipalsWithAccess")[0]
        assert req.permission == "docs.read" and req.expand_groups


class TestGrantRevoke:
    def test_grant_and_revoke_requests(self, client: Permio, rec: Recorder) -> None:
        rec.on("GrantUserPermissionsAndRolesOnResource", lambda req, ctx: _empty())
        rec.on("RevokeUserPermissionsAndRolesOnResource", lambda req, ctx: _empty())
        client.grant("alice", "/docs/42", permissions="docs.read", roles=["r1"])
        client.revoke(group("eds"), "/docs", permissions=["docs.write"])
        g = rec.requests("GrantUserPermissionsAndRolesOnResource")[0]
        assert (g.project_name, g.user_id, g.resource_uri) == ("my-app", "alice", "/docs/42")
        assert list(g.permissions) == ["docs.read"] and list(g.roles) == ["r1"]
        r = rec.requests("RevokeUserPermissionsAndRolesOnResource")[0]
        assert r.user_id == "group:eds" and list(r.permissions) == ["docs.write"]

    def test_validates(self, client: Permio, rec: Recorder) -> None:
        with pytest.raises(PermioValidationError, match="at least one permission or role"):
            client.grant("alice", "/docs")
        with pytest.raises(PermioValidationError, match="empty"):
            client.revoke("alice", "", permissions="p")
        with pytest.raises(PermioValidationError, match="non-empty"):
            client.grant("alice", "/docs", permissions=[""])
        assert rec.calls == []

    def test_writes_are_never_retried(self, client: Permio, rec: Recorder) -> None:
        def down(req: Any, ctx: Any) -> Any:
            raise Abort(grpc.StatusCode.UNAVAILABLE, "down")

        rec.on("GrantUserPermissionsAndRolesOnResource", down)
        rec.on("RevokeUserPermissionsAndRolesOnResource", down)
        rec.on("CreatePermission", down)
        with pytest.raises(PermioUnavailableError):
            client.grant("a", "/x", permissions="p")
        with pytest.raises(PermioUnavailableError):
            client.revoke("a", "/x", permissions="p")
        with pytest.raises(PermioUnavailableError):
            client.permissions.CreatePermission(
                raw.permissions_pb2.CreatePermissionRequest(name="p")
            )
        assert rec.count("GrantUserPermissionsAndRolesOnResource") == 1
        assert rec.count("RevokeUserPermissionsAndRolesOnResource") == 1
        assert rec.count("CreatePermission") == 1


def _empty() -> Any:
    from google.protobuf import empty_pb2

    return empty_pb2.Empty()


class TestWhoAmI:
    def test_describes_api_key(self, make_client: MakeClient, rec: Recorder) -> None:
        responses = [
            pb.WhoAmIResponse(
                principal_id="key-1",
                organisation_id="org-1",
                principal_type=pb.PRINCIPAL_TYPE_API_KEY,
                project_name="my-app",
                api_key_access=pb.API_KEY_ACCESS_FULL,
            ),
            pb.WhoAmIResponse(principal_type=pb.PRINCIPAL_TYPE_API_KEY, project_name="p"),
            pb.WhoAmIResponse(
                principal_type=pb.PRINCIPAL_TYPE_USER, principal_id="u1", email="u@example.com"
            ),
            pb.WhoAmIResponse(),
        ]
        rec.on("WhoAmI", lambda req, ctx: responses.pop(0))
        client = make_client(project=None)  # needs no project
        assert client.who_am_i() == WhoAmI("key-1", "org-1", "api_key", "my-app", "full", None)
        assert client.who_am_i().api_key_access == "unknown"
        user = client.who_am_i()
        assert (user.kind, user.api_key_access, user.project, user.email) == (
            "user",
            None,
            None,
            "u@example.com",
        )
        assert client.who_am_i().kind == "unknown"


class TestErrorsAndRetries:
    @pytest.mark.parametrize(
        ("code", "cls"),
        [
            (grpc.StatusCode.UNAUTHENTICATED, PermioAuthError),
            (grpc.StatusCode.PERMISSION_DENIED, PermioPermissionError),
            (grpc.StatusCode.INVALID_ARGUMENT, PermioValidationError),
            (grpc.StatusCode.NOT_FOUND, PermioNotFoundError),
            (grpc.StatusCode.UNAVAILABLE, PermioUnavailableError),
            (grpc.StatusCode.DEADLINE_EXCEEDED, PermioTimeoutError),
            (grpc.StatusCode.RESOURCE_EXHAUSTED, PermioRateLimitError),
            (grpc.StatusCode.ALREADY_EXISTS, PermioError),
            (grpc.StatusCode.INTERNAL, PermioError),
        ],
    )
    def test_maps_status_codes(
        self, make_client: MakeClient, rec: Recorder, code: grpc.StatusCode, cls: type
    ) -> None:
        def fail(req: Any, ctx: Any) -> Any:
            raise Abort(code, "nope")

        rec.on("GetGroup", fail)
        client = make_client(retries=0)
        with pytest.raises(cls) as err:
            client.groups.get("eds")
        assert type(err.value) is cls
        assert err.value.code == code
        assert err.value.code_name == code.name.lower()
        assert str(err.value) == "nope"
        assert isinstance(err.value.__cause__, grpc.RpcError)

    def test_permission_error_parses_missing(self, client: Permio, rec: Recorder) -> None:
        msg = "missing permissions: [{ResourceURI:/organisation/o/project/p/docs MissingPermissions:[principal.grant]}]"

        def fail(req: Any, ctx: Any) -> Any:
            raise Abort(grpc.StatusCode.PERMISSION_DENIED, msg)

        rec.on("GrantUserPermissionsAndRolesOnResource", fail)
        with pytest.raises(PermioPermissionError) as err:
            client.grant("a", "/docs", permissions="p")
        assert err.value.missing == [
            MissingPermission("/organisation/o/project/p/docs", ["principal.grant"])
        ]

    def test_retries_reads_on_unavailable(self, client: Permio, rec: Recorder) -> None:
        attempts = []

        def flaky(req: Any, ctx: Any) -> Any:
            attempts.append(1)
            if len(attempts) < 3:
                raise Abort(grpc.StatusCode.UNAVAILABLE, "down")
            return passed()

        rec.on("Check", flaky)
        assert client.check("a", "p", "/x") is True
        assert rec.count("Check") == 3

    def test_gives_up_after_max_retries(self, make_client: MakeClient, rec: Recorder) -> None:
        def down(req: Any, ctx: Any) -> Any:
            raise Abort(grpc.StatusCode.UNAVAILABLE, "down")

        rec.on("WhoAmI", down)
        client = make_client(retries=RetryOptions(max_retries=1, base_delay=0.001))
        with pytest.raises(PermioUnavailableError):
            client.who_am_i()
        assert rec.count("WhoAmI") == 2

    def test_does_not_retry_other_codes(self, client: Permio, rec: Recorder) -> None:
        def fail(req: Any, ctx: Any) -> Any:
            raise Abort(grpc.StatusCode.INTERNAL, "boom")

        rec.on("Check", fail)
        with pytest.raises(PermioError):
            client.check("a", "p", "/x")
        assert rec.count("Check") == 1

    def test_per_attempt_timeout_then_retry(self, make_client: MakeClient, rec: Recorder) -> None:
        calls = []

        def slow_once(req: Any, ctx: Any) -> Any:
            calls.append(1)
            if len(calls) == 1:
                time.sleep(0.5)
            return passed()

        rec.on("Check", slow_once)
        client = make_client(timeout=0.1)
        assert client.check("a", "p", "/x") is True
        assert len(calls) == 2

    def test_overall_timeout(self, make_client: MakeClient, rec: Recorder) -> None:
        def slow(req: Any, ctx: Any) -> Any:
            time.sleep(0.5)
            return passed()

        rec.on("Check", slow)
        client = make_client(timeout=10)
        started = time.monotonic()
        with pytest.raises(PermioTimeoutError):
            client.check("a", "p", "/x", timeout=0.15)
        assert time.monotonic() - started < 0.45

    def test_rate_limit_retry_info(self, make_client: MakeClient, rec: Recorder) -> None:
        at: List[float] = []

        def limited(req: Any, ctx: Any) -> Any:
            at.append(time.monotonic())
            if len(at) == 1:
                raise Abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    "rate limited",
                    [retry_info_trailer(grpc.StatusCode.RESOURCE_EXHAUSTED, "rate limited", 0.2)],
                )
            return passed()

        rec.on("Check", limited)
        client = make_client()
        assert client.check("a", "p", "/x") is True
        assert at[1] - at[0] >= 0.19

    def test_rate_limit_retry_after_header(self, make_client: MakeClient, rec: Recorder) -> None:
        at: List[float] = []

        def limited(req: Any, ctx: Any) -> Any:
            at.append(time.monotonic())
            if len(at) == 1:
                raise Abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "slow down", [("retry-after", "1")])
            return passed()

        rec.on("Check", limited)
        client = make_client(retries=RetryOptions(max_retries=1, base_delay=0.001, max_delay=2))
        assert client.check("a", "p", "/x") is True
        assert at[1] - at[0] >= 0.95

    def test_rate_limit_too_long_raises_with_delay(
        self, make_client: MakeClient, rec: Recorder
    ) -> None:
        def limited(req: Any, ctx: Any) -> Any:
            raise Abort(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                "rate limited",
                [retry_info_trailer(grpc.StatusCode.RESOURCE_EXHAUSTED, "rate limited", 0.9)],
            )

        rec.on("Check", limited)
        client = make_client(retries=RetryOptions(max_retries=2, base_delay=0.001, max_delay=0.1))
        with pytest.raises(PermioRateLimitError) as err:
            client.check("a", "p", "/x")
        assert err.value.retry_after == pytest.approx(0.9)
        assert err.value.code_name == "resource_exhausted"
        assert rec.count("Check") == 1

    def test_rate_limit_without_delay_not_retried(self, client: Permio, rec: Recorder) -> None:
        def limited(req: Any, ctx: Any) -> Any:
            raise Abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "rate limited")

        rec.on("Check", limited)
        with pytest.raises(PermioRateLimitError) as err:
            client.check("a", "p", "/x")
        assert err.value.retry_after is None
        assert rec.count("Check") == 1

    def test_unavailable_honours_retry_after(self, make_client: MakeClient, rec: Recorder) -> None:
        at: List[float] = []

        def proxy(req: Any, ctx: Any) -> Any:
            at.append(time.monotonic())
            if len(at) == 1:
                raise Abort(
                    grpc.StatusCode.UNAVAILABLE, "too many requests", [("retry-after", "1")]
                )
            return passed()

        rec.on("Check", proxy)
        client = make_client(retries=RetryOptions(max_retries=1, base_delay=0.001, max_delay=2))
        assert client.check("a", "p", "/x") is True
        assert at[1] - at[0] >= 0.95

    def test_unreachable_server_is_unavailable(self) -> None:
        with (
            Permio(
                VALID_KEY, base_url="http://127.0.0.1:9", project="p", retries=0, timeout=2
            ) as c,
            pytest.raises(PermioUnavailableError),
        ):
            c.check("a", "p", "/x")


class TestRawAndLifecycle:
    def test_raw_service_applies_auth_and_errors(self, client: Permio, rec: Recorder) -> None:
        rec.on(
            "CreatePermission",
            lambda req, ctx: pb.Permission(name=req.name, project_name=req.project_name),
        )
        p = client.permissions.CreatePermission(
            raw.permissions_pb2.CreatePermissionRequest(project_name="my-app", name="docs.read"),
            metadata=[("x-extra", "1"), ("authorization", "Bearer spoof")],
        )
        assert p.name == "docs.read"
        md = rec.calls[0][2]
        assert md["authorization"] == f"Bearer {VALID_KEY}"
        assert md["x-extra"] == "1"
        with pytest.raises(AttributeError):
            _ = client.permissions.NoSuchMethod

    def test_organisation_service(self, client: Permio, rec: Recorder) -> None:
        rec.on(
            "GetProject",
            lambda req, ctx: raw.organisation_pb2.GetProjectResponse(
                project=raw.organisation_pb2.Project(name=req.project_name)
            ),
        )
        res = client.organisations.GetProject(
            raw.organisation_pb2.GetProjectRequest(project_name="p")
        )
        assert res.project.name == "p"

    def test_injected_channel_is_not_closed(self, server: Any, rec: Recorder) -> None:
        rec.on("Check", lambda req, ctx: passed())
        channel = grpc.insecure_channel(f"127.0.0.1:{server.port}")
        with Permio(VALID_KEY, channel=channel, project="p") as c:
            assert c.check("a", "p", "/x")
        # Still usable after the client closed.
        with Permio(VALID_KEY, channel=channel, project="p") as c:
            assert c.check("a", "p", "/x")
        channel.close()

    def test_config_errors(self) -> None:
        with pytest.raises(PermioConfigError):
            Permio(VALID_KEY, base_url="ftp://x")
        with pytest.raises(PermioConfigError):
            Permio(VALID_KEY, project="")
        with pytest.raises(PermioConfigError):
            Permio(VALID_KEY, retries="3")  # type: ignore[arg-type]
