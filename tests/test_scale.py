"""Scale guardrails: streaming access listings, result caps, batch bounds, list timeouts."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, AsyncIterator, Callable, Iterator, List

import grpc
import pytest

from permio import (
    DEFAULT_MAX_BATCH_RESOURCES,
    DEFAULT_MAX_RESULTS,
    AsyncPermio,
    Permio,
    PermioError,
    PermioTooManyResultsError,
    PermioUnavailableError,
    PermioValidationError,
    RetryOptions,
)
from permio.permissions.v1 import permissions_pb2 as pb

from .conftest import FAST_RETRIES, VALID_KEY, Abort, FakeServer, Recorder

MakeClient = Callable[..., Permio]


def serve_principals(rec: Recorder, total: int) -> None:
    """ListPrincipalsWithAccess over ``total`` principals, honouring limit; cursor = offset."""

    def handler(req: Any, ctx: Any) -> Any:
        start = int(req.pagination.cursor or 0)
        end = min(total, start + req.pagination.limit)
        res = pb.ListPrincipalsWithAccessResponse(
            principals=[pb.PrincipalAccess(principal_id=f"u{i:07d}") for i in range(start, end)]
        )
        if end < total:
            res.pagination.next_cursor = str(end)
        return res

    rec.on("ListPrincipalsWithAccess", handler)


def serve_scopes(rec: Recorder, total: int) -> None:
    def handler(req: Any, ctx: Any) -> Any:
        start = int(req.pagination.cursor or 0)
        end = min(total, start + req.pagination.limit)
        res = pb.ListAccessResponse(
            scopes=[
                pb.AccessScope(uri=f"/d/{i}", scope=pb.ACCESS_SCOPE_KIND_EXACT)
                for i in range(start, end)
            ]
        )
        if end < total:
            res.pagination.next_cursor = str(end)
        return res

    rec.on("ListAccess", handler)


def fetched(rec: Recorder, method: str) -> int:
    """Items the fake server was asked for in total."""
    return sum(r.pagination.limit for r in rec.requests(method))


def test_defaults() -> None:
    assert DEFAULT_MAX_RESULTS == 10_000
    assert DEFAULT_MAX_BATCH_RESOURCES == 10_000


class TestStreaming:
    def test_iter_who_has_access_streams_many_pages_lazily(
        self, client: Permio, rec: Recorder
    ) -> None:
        serve_principals(rec, 2_550)
        it = client.iter_who_has_access("/docs/1")
        assert rec.count("ListPrincipalsWithAccess") == 0
        first = next(it)
        assert first.principal == "u0000000"
        assert rec.count("ListPrincipalsWithAccess") == 1
        rest = list(it)
        assert len(rest) == 2_549
        assert rest[-1].principal == "u0002549"
        assert rec.count("ListPrincipalsWithAccess") == 26
        assert all(r.pagination.limit == 100 for r in rec.requests("ListPrincipalsWithAccess"))

    def test_streams_are_not_capped(self, client: Permio, rec: Recorder) -> None:
        serve_principals(rec, 12_000)
        assert sum(1 for _ in client.iter_who_has_access("/docs/1")) == 12_000

    def test_iter_validates_eagerly(self, client: Permio, rec: Recorder) -> None:
        with pytest.raises(PermioValidationError):
            client.iter_who_has_access("no-slash")
        with pytest.raises(PermioValidationError):
            client.iter_list_access("", "p", "/d")
        assert rec.calls == []

    def test_iter_list_access(self, client: Permio, rec: Recorder) -> None:
        serve_scopes(rec, 250)
        scopes = list(client.iter_list_access("alice", "docs.read", "/d", page_size=50))
        assert [s.uri for s in scopes[:2]] == ["/d/0", "/d/1"]
        assert len(scopes) == 250
        assert rec.count("ListAccess") == 5

    def test_iter_list_access_covers_all(self, client: Permio, rec: Recorder) -> None:
        rec.on(
            "ListAccess",
            lambda req, ctx: pb.ListAccessResponse(
                covers_all=True,
                scopes=[pb.AccessScope(uri="/d", scope=pb.ACCESS_SCOPE_KIND_SUBTREE)],
            ),
        )
        [scope] = list(client.iter_list_access("alice", "docs.read", "/d"))
        assert (scope.uri, scope.kind) == ("/d", "subtree")
        assert client.list_access("alice", "docs.read", "/d").covers_all is True


class TestCaps:
    def test_who_has_access_stops_at_cap_plus_one(self, client: Permio, rec: Recorder) -> None:
        serve_principals(rec, 100_000)
        with pytest.raises(PermioTooManyResultsError) as exc:
            client.who_has_access("/docs/1", max_results=250)
        assert exc.value.max_results == 250
        assert "iter_who_has_access" in str(exc.value)
        assert exc.value.code is None
        assert isinstance(exc.value, PermioError)
        # Pages of 100, 100, then just the 51 still wanted.
        assert [r.pagination.limit for r in rec.requests("ListPrincipalsWithAccess")] == [
            100,
            100,
            51,
        ]
        assert fetched(rec, "ListPrincipalsWithAccess") == 251

    def test_exactly_cap_succeeds(self, client: Permio, rec: Recorder) -> None:
        serve_principals(rec, 250)
        assert len(client.who_has_access("/docs/1", max_results=250)) == 250

    def test_default_cap_is_10000(self, client: Permio, rec: Recorder) -> None:
        serve_principals(rec, 10_000)
        assert len(client.who_has_access("/docs/1")) == 10_000
        rec.calls.clear()
        serve_principals(rec, 10_500)
        with pytest.raises(PermioTooManyResultsError):
            client.who_has_access("/docs/1")
        assert fetched(rec, "ListPrincipalsWithAccess") == 10_001

    def test_list_access_cap(self, client: Permio, rec: Recorder) -> None:
        serve_scopes(rec, 1_000)
        with pytest.raises(PermioTooManyResultsError) as exc:
            client.list_access("alice", "p", "/d", max_results=120)
        assert "iter_list_access" in str(exc.value)
        assert fetched(rec, "ListAccess") == 121
        rec.calls.clear()
        assert len(client.list_access("alice", "p", "/d", max_results=1_000).scopes) == 1_000

    @pytest.mark.parametrize("bad", [0, -1, True, 1.5, "10"])
    def test_bad_cap_is_validation_error(self, client: Permio, rec: Recorder, bad: Any) -> None:
        with pytest.raises(PermioValidationError):
            client.who_has_access("/d", max_results=bad)
        with pytest.raises(PermioValidationError):
            client.list_access("a", "p", "/d", max_results=bad)
        assert rec.calls == []


def ok_batch(req: Any, ctx: Any) -> Any:
    return pb.BatchCheckResponse(
        results=[pb.BatchCheckResult(resource_uri=u, allowed=True) for u in req.resource_uris]
    )


class TestBatchBound:
    def test_default_bound(self, client: Permio, rec: Recorder) -> None:
        rec.on("BatchCheck", ok_batch)
        with pytest.raises(PermioValidationError, match="max_resources=10000"):
            client.batch_check("alice", "p", [f"/d/{i}" for i in range(10_001)])
        assert rec.calls == []
        assert len(client.batch_check("alice", "p", [f"/d/{i}" for i in range(10_000)])) == 10_000
        assert rec.count("BatchCheck") == 100

    def test_counts_before_dedup_and_stops_reading(self, client: Permio, rec: Recorder) -> None:
        with pytest.raises(PermioValidationError):
            client.batch_check("alice", "p", ["/d"] * 6, max_resources=5)
        consumed: List[int] = []

        def gen() -> Iterator[str]:
            for i in range(1_000_000):
                consumed.append(i)
                yield f"/d/{i}"

        with pytest.raises(PermioValidationError):
            client.batch_check("alice", "p", gen(), max_resources=10)
        assert len(consumed) == 11
        with pytest.raises(PermioValidationError):
            client.batch_check("alice", "p", ["/d"], max_resources=0)
        assert rec.calls == []

    def test_sync_sends_chunks_in_order_and_stops_on_error(
        self, client: Permio, rec: Recorder
    ) -> None:
        def handler(req: Any, ctx: Any) -> Any:
            if rec.count("BatchCheck") == 3:
                raise Abort(grpc.StatusCode.INTERNAL, "boom")
            return ok_batch(req, ctx)

        rec.on("BatchCheck", handler)
        with pytest.raises(PermioError):
            client.batch_check("alice", "p", [f"/d/{i}" for i in range(1_000)])
        assert rec.count("BatchCheck") == 3


class TestListTimeoutAndRetries:
    def test_list_timeout_applies_to_pages_only(
        self, make_client: MakeClient, rec: Recorder
    ) -> None:
        attempts: List[int] = []

        def slow_once(req: Any, ctx: Any) -> Any:
            attempts.append(1)
            if len(attempts) == 1:
                time.sleep(0.4)
            return pb.ListPrincipalsWithAccessResponse()

        def slow_check(req: Any, ctx: Any) -> Any:
            time.sleep(0.2)
            return pb.CheckPermissionResponse(passed=True)

        rec.on("ListPrincipalsWithAccess", slow_once)
        rec.on("Check", slow_check)
        client = make_client(timeout=5, list_timeout=0.1)
        assert client.who_has_access("/d") == []
        assert len(attempts) == 2  # first page attempt timed out, then retried
        assert client.check("a", "p", "/d") is True  # 0.2s is fine under timeout=5

    def test_list_timeout_defaults_to_timeout(self, make_client: MakeClient) -> None:
        assert make_client(timeout=3)._config.list_timeout == 3.0
        assert make_client(timeout=3, list_timeout=30)._config.list_timeout == 30.0

    def test_deadline_exceeded_page_is_retried_with_backoff(
        self, make_client: MakeClient, rec: Recorder
    ) -> None:
        def flaky(req: Any, ctx: Any) -> Any:
            if rec.count("ListPrincipalsWithAccess") <= 2:
                raise Abort(grpc.StatusCode.DEADLINE_EXCEEDED, "slow")
            return pb.ListPrincipalsWithAccessResponse()

        rec.on("ListPrincipalsWithAccess", flaky)
        client = make_client(retries=RetryOptions(max_retries=2, base_delay=0.05, max_delay=1))
        delays: List[float] = []
        client._invoker.sleep = delays.append  # type: ignore[method-assign,assignment]
        assert list(client.iter_who_has_access("/d")) == []
        assert len(delays) == 2
        assert delays[0] >= 0.025 and delays[1] >= 0.05  # jittered exponential, never 0

    def test_rate_limited_page_honours_retry_after(
        self, make_client: MakeClient, rec: Recorder
    ) -> None:
        at: List[float] = []

        def limited(req: Any, ctx: Any) -> Any:
            at.append(time.monotonic())
            if len(at) == 1:
                raise Abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "slow down", [("retry-after", "1")])
            return pb.ListAccessResponse()

        rec.on("ListAccess", limited)
        client = make_client(retries=RetryOptions(max_retries=1, base_delay=0.001, max_delay=2))
        assert list(client.iter_list_access("a", "p", "/d")) == []
        assert at[1] - at[0] >= 0.95


# -- asyncio -----------------------------------------------------------------


@pytest.fixture
async def aclient(server: FakeServer) -> AsyncIterator[AsyncPermio]:
    async with AsyncPermio(
        VALID_KEY, base_url=server.base_url, project="my-app", retries=FAST_RETRIES
    ) as client:
        yield client


class TestAsync:
    async def test_iter_who_has_access_streams(self, aclient: AsyncPermio, rec: Recorder) -> None:
        serve_principals(rec, 2_550)
        it = aclient.iter_who_has_access("/docs/1")
        first = await it.__anext__()
        assert first.principal == "u0000000"
        assert rec.count("ListPrincipalsWithAccess") == 1
        n = 1 + len([e async for e in it])
        assert n == 2_550
        assert rec.count("ListPrincipalsWithAccess") == 26

    async def test_iter_list_access(self, aclient: AsyncPermio, rec: Recorder) -> None:
        serve_scopes(rec, 230)
        scopes = [s async for s in aclient.iter_list_access("a", "p", "/d")]
        assert len(scopes) == 230 and scopes[0].kind == "exact"

    async def test_caps(self, aclient: AsyncPermio, rec: Recorder) -> None:
        serve_principals(rec, 5_000)
        with pytest.raises(PermioTooManyResultsError):
            await aclient.who_has_access("/d", max_results=150)
        assert fetched(rec, "ListPrincipalsWithAccess") == 151
        serve_scopes(rec, 5_000)
        with pytest.raises(PermioTooManyResultsError):
            await aclient.list_access("a", "p", "/d", max_results=99)
        assert fetched(rec, "ListAccess") == 100
        assert len(await aclient.who_has_access("/d", max_results=5_000)) == 5_000
        with pytest.raises(PermioValidationError):
            await aclient.who_has_access("/d", max_results=0)

    async def test_batch_bound(self, aclient: AsyncPermio, rec: Recorder) -> None:
        with pytest.raises(PermioValidationError):
            await aclient.batch_check("a", "p", [f"/d/{i}" for i in range(10_001)])
        with pytest.raises(PermioValidationError):
            await aclient.batch_check("a", "p", ["/x", "/y", "/z"], max_resources=2)
        assert rec.calls == []

    async def test_batch_concurrency_is_4_and_keeps_order(
        self, aclient: AsyncPermio, rec: Recorder
    ) -> None:
        lock = threading.Lock()
        in_flight = [0, 0]  # current, peak

        def slow(req: Any, ctx: Any) -> Any:
            with lock:
                in_flight[0] += 1
                in_flight[1] = max(in_flight[1], in_flight[0])
            # Later chunks answer faster, so completion order differs from request order.
            time.sleep(0.05 if req.resource_uris[0].endswith("/0") else 0.01)
            with lock:
                in_flight[0] -= 1
            return ok_batch(req, ctx)

        rec.on("BatchCheck", slow)
        uris = [f"/d/{i}" for i in range(1_250)]
        result = await aclient.batch_check("alice", "p", uris)
        assert list(result) == uris
        assert rec.count("BatchCheck") == 13
        assert in_flight[1] == 4

    async def test_batch_first_error_stops_new_chunks(
        self, aclient: AsyncPermio, rec: Recorder
    ) -> None:
        def handler(req: Any, ctx: Any) -> Any:
            if req.resource_uris[0] == "/d/0":
                raise Abort(grpc.StatusCode.UNAVAILABLE, "down")
            time.sleep(0.05)
            return ok_batch(req, ctx)

        rec.on("BatchCheck", handler)
        with pytest.raises(PermioUnavailableError):
            await aclient.batch_check("alice", "p", [f"/d/{i}" for i in range(5_000)])
        await asyncio.sleep(0.1)
        # Chunk 0 failed 3 times (retries); the other workers stopped soon after.
        assert rec.count("BatchCheck") < 20

    async def test_list_timeout(self, server: FakeServer, rec: Recorder) -> None:
        attempts: List[int] = []

        def slow_once(req: Any, ctx: Any) -> Any:
            attempts.append(1)
            if len(attempts) == 1:
                time.sleep(0.4)
            return pb.ListPrincipalsResponse(principals=["a"])

        rec.on("ListPrincipals", slow_once)
        async with AsyncPermio(
            VALID_KEY,
            base_url=server.base_url,
            project="my-app",
            retries=FAST_RETRIES,
            timeout=5,
            list_timeout=0.1,
        ) as client:
            assert [p async for p in client.list_principals()] == ["a"]
        assert len(attempts) == 2
