# Permio Python

Generated Protocol Buffer and gRPC client code for the [perms.io](https://perms.io) API.

This repository is generated from `PrivateJAR/proto` on every release. Do not edit it by hand.

## Installation

```bash
pip install "git+https://github.com/PrivateJAR/permio-python@v0.0.16"
```

## Usage

```python
import grpc

from permio.permissions.v1 import permissions_pb2, permissions_pb2_grpc

channel = grpc.secure_channel("api.perms.io:443", grpc.ssl_channel_credentials())
client = permissions_pb2_grpc.PermissionsServiceStub(channel)

res = client.Check(
    permissions_pb2.CheckPermissionRequest(
        project_name="my-project",
        principal_id="user-123",
        resource_uris=["/documents/42"],
        permissions=["document.read"],
    ),
    metadata=[("authorization", "Bearer <your perms.io API key>")],
)
print(res.passed)
```

Modules: `permio.permissions.v1`, `permio.organisation.v1`, `permio.pagination.v1`.

## Version

v0.0.16
