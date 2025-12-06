from google.api import annotations_pb2 as _annotations_pb2
from validate import validate_pb2 as _validate_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from proto.pagination.v1 import pagination_pb2 as _pagination_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetTotalRolesAndPermissionsForOrganisationRequest(_message.Message):
    __slots__ = ()
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    def __init__(self, organisation_id: _Optional[str] = ...) -> None: ...

class GetTotalRolesAndPermissionsForOrganisationResponse(_message.Message):
    __slots__ = ()
    TOTAL_ROLES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    total_roles: int
    total_permissions: int
    def __init__(self, total_roles: _Optional[int] = ..., total_permissions: _Optional[int] = ...) -> None: ...

class ListRolesRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, project_name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class ListPermissionsRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, project_name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class ListPrincipalsRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, project_name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class CheckPermissionRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_URIS_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    principal_id: str
    resource_uris: _containers.RepeatedScalarFieldContainer[str]
    permissions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., principal_id: _Optional[str] = ..., resource_uris: _Optional[_Iterable[str]] = ..., permissions: _Optional[_Iterable[str]] = ...) -> None: ...

class MissingPermissions(_message.Message):
    __slots__ = ()
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    MISSING_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    resource_uri: str
    missing_permissions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, resource_uri: _Optional[str] = ..., missing_permissions: _Optional[_Iterable[str]] = ...) -> None: ...

class CheckPermissionResponse(_message.Message):
    __slots__ = ()
    PASSED_FIELD_NUMBER: _ClassVar[int]
    MISSING_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    passed: bool
    missing_permissions: _containers.RepeatedCompositeFieldContainer[MissingPermissions]
    def __init__(self, passed: _Optional[bool] = ..., missing_permissions: _Optional[_Iterable[_Union[MissingPermissions, _Mapping]]] = ...) -> None: ...

class ListPrincipalsResponse(_message.Message):
    __slots__ = ()
    PRINCIPALS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    principals: _containers.RepeatedScalarFieldContainer[str]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, principals: _Optional[_Iterable[str]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class GetAllAssignmentsForPrincipalRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    principal_id: str
    pagination: _pagination_pb2.PaginationRequest
    def __init__(self, project_name: _Optional[str] = ..., principal_id: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class GetAllAssignmentsForPrincipalResponse(_message.Message):
    __slots__ = ()
    ASSIGNMENTS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    assignments: _containers.RepeatedCompositeFieldContainer[Assignment]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, assignments: _Optional[_Iterable[_Union[Assignment, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class InheritedRole(_message.Message):
    __slots__ = ()
    ROLE_FIELD_NUMBER: _ClassVar[int]
    INHERITED_FROM_FIELD_NUMBER: _ClassVar[int]
    role: Role
    inherited_from: str
    def __init__(self, role: _Optional[_Union[Role, _Mapping]] = ..., inherited_from: _Optional[str] = ...) -> None: ...

class InheritedPermission(_message.Message):
    __slots__ = ()
    PERMISSION_FIELD_NUMBER: _ClassVar[int]
    INHERITED_FROM_FIELD_NUMBER: _ClassVar[int]
    permission: Permission
    inherited_from: str
    def __init__(self, permission: _Optional[_Union[Permission, _Mapping]] = ..., inherited_from: _Optional[str] = ...) -> None: ...

class Assignment(_message.Message):
    __slots__ = ()
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    resource_uri: str
    permissions: _containers.RepeatedCompositeFieldContainer[Permission]
    roles: _containers.RepeatedCompositeFieldContainer[Role]
    def __init__(self, resource_uri: _Optional[str] = ..., permissions: _Optional[_Iterable[_Union[Permission, _Mapping]]] = ..., roles: _Optional[_Iterable[_Union[Role, _Mapping]]] = ...) -> None: ...

class GetUserPermissionsAndRolesOnResourceResponse(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    user_id: str
    resource_uri: str
    permissions: _containers.RepeatedScalarFieldContainer[str]
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., user_id: _Optional[str] = ..., resource_uri: _Optional[str] = ..., permissions: _Optional[_Iterable[str]] = ..., roles: _Optional[_Iterable[str]] = ...) -> None: ...

class GetUserPermissionsAndRolesOnResourceRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    user_id: str
    resource_uri: str
    def __init__(self, project_name: _Optional[str] = ..., user_id: _Optional[str] = ..., resource_uri: _Optional[str] = ...) -> None: ...

class GrantUserPermissionsAndRolesOnResourceRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    user_id: str
    resource_uri: str
    permissions: _containers.RepeatedScalarFieldContainer[str]
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., user_id: _Optional[str] = ..., resource_uri: _Optional[str] = ..., permissions: _Optional[_Iterable[str]] = ..., roles: _Optional[_Iterable[str]] = ...) -> None: ...

class CreatePermissionRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    description: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class Permission(_message.Message):
    __slots__ = ()
    ID_FIELD_NUMBER: _ClassVar[int]
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    organisation_id: str
    name: str
    description: str
    project_name: str
    def __init__(self, id: _Optional[str] = ..., organisation_id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., project_name: _Optional[str] = ...) -> None: ...

class GetPermissionRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class UpdatePermissionRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    NEW_NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    new_name: str
    description: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., new_name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class DeletePermissionRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class ListPermissionsResponse(_message.Message):
    __slots__ = ()
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    permissions: _containers.RepeatedCompositeFieldContainer[Permission]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, permissions: _Optional[_Iterable[_Union[Permission, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class CreateRoleRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    description: str
    permissions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., permissions: _Optional[_Iterable[str]] = ...) -> None: ...

class Role(_message.Message):
    __slots__ = ()
    ID_FIELD_NUMBER: _ClassVar[int]
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    organisation_id: str
    name: str
    description: str
    permissions: _containers.RepeatedCompositeFieldContainer[Permission]
    project_name: str
    def __init__(self, id: _Optional[str] = ..., organisation_id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., permissions: _Optional[_Iterable[_Union[Permission, _Mapping]]] = ..., project_name: _Optional[str] = ...) -> None: ...

class GetRoleRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    id: str
    def __init__(self, project_name: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class UpdateRoleRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    id: str
    name: str
    description: str
    permissions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., permissions: _Optional[_Iterable[str]] = ...) -> None: ...

class DeleteRoleRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    id: str
    def __init__(self, project_name: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class ListRolesResponse(_message.Message):
    __slots__ = ()
    ROLES_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    roles: _containers.RepeatedCompositeFieldContainer[Role]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, roles: _Optional[_Iterable[_Union[Role, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class RevokeUserPermissionsAndRolesOnResourceRequest(_message.Message):
    __slots__ = ()
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    user_id: str
    resource_uri: str
    permissions: _containers.RepeatedScalarFieldContainer[str]
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., user_id: _Optional[str] = ..., resource_uri: _Optional[str] = ..., permissions: _Optional[_Iterable[str]] = ..., roles: _Optional[_Iterable[str]] = ...) -> None: ...

class PrincipalCountUpdatedEvent(_message.Message):
    __slots__ = ()
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    UNIQUE_PRINCIPAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    unique_principal_count: int
    def __init__(self, organisation_id: _Optional[str] = ..., unique_principal_count: _Optional[int] = ...) -> None: ...
