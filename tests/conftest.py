"""An in-process gRPC server implementing the generated servicers, for unit tests."""

from __future__ import annotations

from concurrent import futures
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import grpc
import pytest
from google.protobuf import duration_pb2
from google.rpc import error_details_pb2, status_pb2

from permio import Permio, RetryOptions
from permio.organisation.v1 import organisation_pb2_grpc
from permio.permissions.v1 import permissions_pb2_grpc

# Well-formed (correct checksum) but not a real key.
VALID_KEY = "perms_0123456789ABCDEFGHIJKLMNOPQRSTUV1ggZdL"

Handler = Callable[[Any, grpc.ServicerContext], Any]


class Abort(Exception):
    """Raise from a handler to fail the call with ``code``, ``details`` and trailers."""

    def __init__(
        self,
        code: grpc.StatusCode,
        details: str = "",
        trailers: Optional[List[Tuple[str, Any]]] = None,
    ) -> None:
        super().__init__(details)
        self.code = code
        self.details = details
        self.trailers = trailers or []


def retry_info_trailer(code: grpc.StatusCode, message: str, seconds: float) -> Tuple[str, bytes]:
    """A grpc-status-details-bin trailer carrying google.rpc.RetryInfo."""
    info = error_details_pb2.RetryInfo(
        retry_delay=duration_pb2.Duration(seconds=int(seconds), nanos=round((seconds % 1) * 1e9))
    )
    status = status_pb2.Status(code=code.value[0], message=message)
    status.details.add().Pack(info)
    return ("grpc-status-details-bin", status.SerializeToString())


class Recorder:
    """Per-method handlers plus a log of (method, request, metadata) calls."""

    def __init__(self) -> None:
        self.handlers: Dict[str, Handler] = {}
        self.calls: List[Tuple[str, Any, Dict[str, str]]] = []

    def on(self, method: str, handler: Handler) -> None:
        self.handlers[method] = handler

    def requests(self, method: str) -> List[Any]:
        return [req for name, req, _ in self.calls if name == method]

    def count(self, method: str) -> int:
        return len(self.requests(method))

    def dispatch(self, method: str, request: Any, context: grpc.ServicerContext) -> Any:
        md = {k: v for k, v in context.invocation_metadata() if isinstance(v, str)}
        self.calls.append((method, request, md))
        handler = self.handlers.get(method)
        if handler is None:
            context.abort(grpc.StatusCode.UNIMPLEMENTED, f"{method} not stubbed")
        try:
            return handler(request, context)
        except Abort as a:
            if a.trailers:
                context.set_trailing_metadata(a.trailers)
            context.abort(a.code, a.details)


def _servicer(base: type, recorder: Recorder) -> Any:
    """A servicer subclass whose every RPC goes through ``recorder``."""
    attrs: Dict[str, Any] = {}
    for name in dir(base):
        if name.startswith("_") or not callable(getattr(base, name)):
            continue

        def method(self: Any, request: Any, context: Any, _name: str = name) -> Any:
            return recorder.dispatch(_name, request, context)

        attrs[name] = method
    return type("Fake" + base.__name__, (base,), attrs)()


class FakeServer:
    def __init__(self) -> None:
        self.recorder = Recorder()
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
        permissions_pb2_grpc.add_PermissionsServiceServicer_to_server(
            _servicer(permissions_pb2_grpc.PermissionsServiceServicer, self.recorder), self.server
        )
        organisation_pb2_grpc.add_OrganisationServiceServicer_to_server(
            _servicer(organisation_pb2_grpc.OrganisationServiceServicer, self.recorder),
            self.server,
        )
        self.port = self.server.add_insecure_port("127.0.0.1:0")
        self.server.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        self.server.stop(None)


FAST_RETRIES = RetryOptions(max_retries=2, base_delay=0.001, max_delay=1.0)


@pytest.fixture
def server() -> Iterator[FakeServer]:
    s = FakeServer()
    yield s
    s.stop()


@pytest.fixture
def rec(server: FakeServer) -> Recorder:
    return server.recorder


@pytest.fixture
def make_client(server: FakeServer) -> Iterator[Callable[..., Permio]]:
    clients: List[Permio] = []

    def make(**kwargs: Any) -> Permio:
        kwargs.setdefault("api_key", VALID_KEY)
        kwargs.setdefault("project", "my-app")
        kwargs.setdefault("retries", FAST_RETRIES)
        client = Permio(base_url=server.base_url, **kwargs)
        clients.append(client)
        return client

    yield make
    for c in clients:
        c.close()


@pytest.fixture
def client(make_client: Callable[..., Permio]) -> Permio:
    return make_client()
