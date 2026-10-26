"""AsyncPermio (grpc.aio) against the same in-process gRPC server."""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, List

import grpc
import pytest
from google.protobuf import empty_pb2

from permio import (
    AsyncPermio,
    MissingPermission,
    PermioAuthError,
    PermioDeniedError,
    PermioRateLimitError,
    PermioTimeoutError,
    PermioUnavailableError,
    RetryOptions,
    raw,
)
from permio.permissions.v1 import permissions_pb2 as pb

from .conftest import FAST_RETRIES, VALID_KEY, Abort, FakeServer, Recorder, retry_info_trailer


@pytest.fixture
async def aclient(server: FakeServer) -> AsyncIterator[AsyncPermio]:
    async with AsyncPermio(
        VALID_KEY, base_url=server.base_url, project="my-app", retries=FAST_RETRIES
    ) as client:
        yield client


async def test_check_family(aclient: AsyncPermio, rec: Recorder) -> None:
    missing = [pb.MissingPermissions(resource_uri="/d", missing_permissions=["w"])]
    rec.on("Check", lambda req, ctx: pb.CheckPermissionResponse(missing_permissions=missing))
    assert await aclient.check("alice", ["r", "w"], "/d") is False
    assert await aclient.check_all("alice", ["r", "w"], "/d") is False
    assert await aclient.check_any("alice", ["r", "w"], "/d") is True
    result = await aclient.check_detailed("alice", ["r", "w"], "/d")
    assert result.missing == [MissingPermission("/d", ["w"])]
    with pytest.raises(PermioDeniedError):
        await aclient.assert_allowed("alice", ["r", "w"], "/d")
    assert rec.calls[0][2]["authorization"] == f"Bearer {VALID_KEY}"


async def test_batch_check_chunks_in_parallel(aclient: AsyncPermio, rec: Recorder) -> None:
    rec.on(
        "BatchCheck",
        lambda req, ctx: pb.BatchCheckResponse(
            results=[pb.BatchCheckResult(resource_uri=u, allowed=True) for u in req.resource_uris]
        ),
    )
    uris = [f"/d/{i}" for i in range(150)]
    result = await aclient.batch_check("alice", "p", uris)
    assert list(result) == uris
    assert sorted(len(r.resource_uris) for r in rec.requests("BatchCheck")) == [50, 100]


async def test_async_iterators(aclient: AsyncPermio, rec: Recorder) -> None:
    def perms(req: Any, ctx: Any) -> Any:
        if not req.pagination.cursor:
            res = pb.ListPermissionsResponse(permissions=[pb.Permission(name="a")])
            res.pagination.next_cursor = "1"
            return res
        return pb.ListPermissionsResponse(permissions=[pb.Permission(name="b")])

    rec.on("ListPermissions", perms)
    rec.on("ListGroups", lambda req, ctx: pb.ListGroupsResponse(groups=[pb.Group(name="eds")]))
    assert [p.name async for p in aclient.list_permissions()] == ["a", "b"]
    assert [g.name async for g in aclient.groups.list()] == ["eds"]


async def test_access_queries(aclient: AsyncPermio, rec: Recorder) -> None:
    rec.on(
        "ListAccess",
        lambda req, ctx: pb.ListAccessResponse(
            covers_all=True,
            scopes=[pb.AccessScope(uri=req.under_uri, scope=pb.ACCESS_SCOPE_KIND_SUBTREE)],
        ),
    )
    rec.on(
        "ListPrincipalsWithAccess",
        lambda req, ctx: pb.ListPrincipalsWithAccessResponse(
            principals=[pb.PrincipalAccess(principal_id="alice")]
        ),
    )
    access = await aclient.list_access("alice", "p", "/docs")
    assert access.covers_all and access.allows("/docs/x")
    assert [e.principal for e in await aclient.who_has_access("/docs")] == ["alice"]


async def test_grant_revoke_groups_whoami(aclient: AsyncPermio, rec: Recorder) -> None:
    rec.on("GrantUserPermissionsAndRolesOnResource", lambda req, ctx: empty_pb2.Empty())
    rec.on("RevokeUserPermissionsAndRolesOnResource", lambda req, ctx: empty_pb2.Empty())
    rec.on("CreateGroup", lambda req, ctx: pb.Group(name=req.name))
    rec.on(
        "AddGroupMembers",
        lambda req, ctx: pb.AddGroupMembersResponse(added_principal_ids=list(req.principal_ids)),
    )
    rec.on("DeleteGroup", lambda req, ctx: empty_pb2.Empty())
    rec.on(
        "WhoAmI",
        lambda req, ctx: pb.WhoAmIResponse(
            principal_type=pb.PRINCIPAL_TYPE_API_KEY,
            project_name="my-app",
            api_key_access=pb.API_KEY_ACCESS_CHECK,
        ),
    )
    await aclient.grant("alice", "/d", permissions="p")
    await aclient.revoke("alice", "/d", roles="r1")
    assert (await aclient.groups.create("eds")).name == "eds"
    assert (await aclient.groups.add_members("eds", ["bob"])).added == ["bob"]
    await aclient.groups.delete("eds")
    me = await aclient.who_am_i()
    assert (me.kind, me.project, me.api_key_access) == ("api_key", "my-app", "check")


async def test_retries_reads_not_writes(aclient: AsyncPermio, rec: Recorder) -> None:
    def down(req: Any, ctx: Any) -> Any:
        raise Abort(grpc.StatusCode.UNAVAILABLE, "down")

    rec.on("WhoAmI", down)
    rec.on("GrantUserPermissionsAndRolesOnResource", down)
    with pytest.raises(PermioUnavailableError):
        await aclient.who_am_i()
    with pytest.raises(PermioUnavailableError):
        await aclient.grant("a", "/x", permissions="p")
    assert rec.count("WhoAmI") == 3
    assert rec.count("GrantUserPermissionsAndRolesOnResource") == 1


async def test_error_mapping_and_raw(aclient: AsyncPermio, rec: Recorder) -> None:
    def unauth(req: Any, ctx: Any) -> Any:
        raise Abort(grpc.StatusCode.UNAUTHENTICATED, "bad key")

    rec.on("CreatePermission", unauth)
    with pytest.raises(PermioAuthError) as err:
        await aclient.permissions.CreatePermission(
            raw.permissions_pb2.CreatePermissionRequest(name="x")
        )
    assert err.value.code == grpc.StatusCode.UNAUTHENTICATED


async def test_rate_limit_retry(server: FakeServer, rec: Recorder) -> None:
    at: List[float] = []

    def limited(req: Any, ctx: Any) -> Any:
        at.append(time.monotonic())
        if len(at) == 1:
            raise Abort(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                "limited",
                [retry_info_trailer(grpc.StatusCode.RESOURCE_EXHAUSTED, "limited", 0.2)],
            )
        return pb.CheckPermissionResponse(passed=True)

    rec.on("Check", limited)
    async with AsyncPermio(VALID_KEY, base_url=server.base_url, project="p") as c:
        assert await c.check("a", "p", "/x") is True
    assert at[1] - at[0] >= 0.19

    at.clear()
    async with AsyncPermio(
        VALID_KEY,
        base_url=server.base_url,
        project="p",
        retries=RetryOptions(max_retries=2, max_delay=0.05),
    ) as c:
        with pytest.raises(PermioRateLimitError) as err:
            await c.check("a", "p", "/x")
        assert err.value.retry_after == pytest.approx(0.2)


async def test_timeouts_and_cancellation(server: FakeServer, rec: Recorder) -> None:
    def slow(req: Any, ctx: Any) -> Any:
        time.sleep(0.5)
        return pb.CheckPermissionResponse(passed=True)

    rec.on("Check", slow)
    async with AsyncPermio(VALID_KEY, base_url=server.base_url, project="p", retries=0) as c:
        with pytest.raises(PermioTimeoutError):
            await c.check("a", "p", "/x", timeout=0.1)
        task = asyncio.ensure_future(c.check("a", "p", "/x"))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
