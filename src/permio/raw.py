"""The generated Protocol Buffer messages and gRPC stubs, as an escape hatch.

The hand-written client wraps the most common calls. Everything else in the
public API (permission and role CRUD, organisation and project calls, ...) is
reachable through these modules::

    from permio import Permio, raw

    permio = Permio(project="my-app")
    permio.permissions.CreatePermission(
        raw.permissions_pb2.CreatePermissionRequest(project_name="my-app", name="docs.read")
    )

``permio.permissions`` and ``permio.organisations`` add auth, timeouts,
retries and typed errors to the stubs. To use the stubs with your own channel
and no SDK behaviour, construct ``raw.permissions_pb2_grpc.PermissionsServiceStub``
directly.

The modules themselves live at ``permio.permissions.v1``,
``permio.organisation.v1`` and ``permio.pagination.v1``; they are generated
from the PrivateJAR/proto repository and must not be edited by hand.
"""

from .organisation.v1 import organisation_pb2, organisation_pb2_grpc
from .pagination.v1 import pagination_pb2
from .permissions.v1 import permissions_pb2, permissions_pb2_grpc

__all__ = [
    "organisation_pb2",
    "organisation_pb2_grpc",
    "pagination_pb2",
    "permissions_pb2",
    "permissions_pb2_grpc",
]
