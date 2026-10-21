import datetime

from google.api import annotations_pb2 as _annotations_pb2
from permio.validate import validate_pb2 as _validate_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from permio.pagination.v1 import pagination_pb2 as _pagination_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AccessScopeKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCESS_SCOPE_KIND_UNSPECIFIED: _ClassVar[AccessScopeKind]
    ACCESS_SCOPE_KIND_EXACT: _ClassVar[AccessScopeKind]
    ACCESS_SCOPE_KIND_SUBTREE: _ClassVar[AccessScopeKind]
    ACCESS_SCOPE_KIND_PATTERN: _ClassVar[AccessScopeKind]

class AccessGrantMatch(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCESS_GRANT_MATCH_UNSPECIFIED: _ClassVar[AccessGrantMatch]
    ACCESS_GRANT_MATCH_EXACT: _ClassVar[AccessGrantMatch]
    ACCESS_GRANT_MATCH_ANCESTOR: _ClassVar[AccessGrantMatch]
    ACCESS_GRANT_MATCH_WILDCARD: _ClassVar[AccessGrantMatch]

class PrincipalType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PRINCIPAL_TYPE_UNSPECIFIED: _ClassVar[PrincipalType]
    PRINCIPAL_TYPE_USER: _ClassVar[PrincipalType]
    PRINCIPAL_TYPE_API_KEY: _ClassVar[PrincipalType]
    PRINCIPAL_TYPE_SERVICE_ACCOUNT: _ClassVar[PrincipalType]

class APIKeyAccess(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    API_KEY_ACCESS_UNSPECIFIED: _ClassVar[APIKeyAccess]
    API_KEY_ACCESS_CHECK: _ClassVar[APIKeyAccess]
    API_KEY_ACCESS_FULL: _ClassVar[APIKeyAccess]
ACCESS_SCOPE_KIND_UNSPECIFIED: AccessScopeKind
ACCESS_SCOPE_KIND_EXACT: AccessScopeKind
ACCESS_SCOPE_KIND_SUBTREE: AccessScopeKind
ACCESS_SCOPE_KIND_PATTERN: AccessScopeKind
ACCESS_GRANT_MATCH_UNSPECIFIED: AccessGrantMatch
ACCESS_GRANT_MATCH_EXACT: AccessGrantMatch
ACCESS_GRANT_MATCH_ANCESTOR: AccessGrantMatch
ACCESS_GRANT_MATCH_WILDCARD: AccessGrantMatch
PRINCIPAL_TYPE_UNSPECIFIED: PrincipalType
PRINCIPAL_TYPE_USER: PrincipalType
PRINCIPAL_TYPE_API_KEY: PrincipalType
PRINCIPAL_TYPE_SERVICE_ACCOUNT: PrincipalType
API_KEY_ACCESS_UNSPECIFIED: APIKeyAccess
API_KEY_ACCESS_CHECK: APIKeyAccess
API_KEY_ACCESS_FULL: APIKeyAccess

class GetTotalRolesAndPermissionsForOrganisationRequest(_message.Message):
    __slots__ = ("organisation_id",)
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    def __init__(self, organisation_id: _Optional[str] = ...) -> None: ...

class GetTotalRolesAndPermissionsForOrganisationResponse(_message.Message):
    __slots__ = ("total_roles", "total_permissions")
    TOTAL_ROLES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    total_roles: int
    total_permissions: int
    def __init__(self, total_roles: _Optional[int] = ..., total_permissions: _Optional[int] = ...) -> None: ...

class ListRolesRequest(_message.Message):
    __slots__ = ("project_name", "pagination", "search")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, project_name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class ListPermissionsRequest(_message.Message):
    __slots__ = ("project_name", "pagination", "search")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, project_name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class ListPrincipalsRequest(_message.Message):
    __slots__ = ("project_name", "pagination", "search")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, project_name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class CheckPermissionRequest(_message.Message):
    __slots__ = ("project_name", "principal_id", "resource_uris", "permissions")
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
    __slots__ = ("resource_uri", "missing_permissions")
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    MISSING_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    resource_uri: str
    missing_permissions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, resource_uri: _Optional[str] = ..., missing_permissions: _Optional[_Iterable[str]] = ...) -> None: ...

class CheckPermissionResponse(_message.Message):
    __slots__ = ("passed", "missing_permissions")
    PASSED_FIELD_NUMBER: _ClassVar[int]
    MISSING_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    passed: bool
    missing_permissions: _containers.RepeatedCompositeFieldContainer[MissingPermissions]
    def __init__(self, passed: _Optional[bool] = ..., missing_permissions: _Optional[_Iterable[_Union[MissingPermissions, _Mapping]]] = ...) -> None: ...

class ListPrincipalsResponse(_message.Message):
    __slots__ = ("principals", "pagination")
    PRINCIPALS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    principals: _containers.RepeatedScalarFieldContainer[str]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, principals: _Optional[_Iterable[str]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class GetAllAssignmentsForPrincipalRequest(_message.Message):
    __slots__ = ("project_name", "principal_id", "pagination")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    principal_id: str
    pagination: _pagination_pb2.PaginationRequest
    def __init__(self, project_name: _Optional[str] = ..., principal_id: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class GetAllAssignmentsForPrincipalResponse(_message.Message):
    __slots__ = ("assignments", "pagination")
    ASSIGNMENTS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    assignments: _containers.RepeatedCompositeFieldContainer[Assignment]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, assignments: _Optional[_Iterable[_Union[Assignment, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class InheritedRole(_message.Message):
    __slots__ = ("role", "inherited_from")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    INHERITED_FROM_FIELD_NUMBER: _ClassVar[int]
    role: Role
    inherited_from: str
    def __init__(self, role: _Optional[_Union[Role, _Mapping]] = ..., inherited_from: _Optional[str] = ...) -> None: ...

class InheritedPermission(_message.Message):
    __slots__ = ("permission", "inherited_from")
    PERMISSION_FIELD_NUMBER: _ClassVar[int]
    INHERITED_FROM_FIELD_NUMBER: _ClassVar[int]
    permission: Permission
    inherited_from: str
    def __init__(self, permission: _Optional[_Union[Permission, _Mapping]] = ..., inherited_from: _Optional[str] = ...) -> None: ...

class Assignment(_message.Message):
    __slots__ = ("resource_uri", "permissions", "roles")
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    resource_uri: str
    permissions: _containers.RepeatedCompositeFieldContainer[Permission]
    roles: _containers.RepeatedCompositeFieldContainer[Role]
    def __init__(self, resource_uri: _Optional[str] = ..., permissions: _Optional[_Iterable[_Union[Permission, _Mapping]]] = ..., roles: _Optional[_Iterable[_Union[Role, _Mapping]]] = ...) -> None: ...

class GetUserPermissionsAndRolesOnResourceResponse(_message.Message):
    __slots__ = ("project_name", "user_id", "resource_uri", "permissions", "roles")
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
    __slots__ = ("project_name", "user_id", "resource_uri")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    user_id: str
    resource_uri: str
    def __init__(self, project_name: _Optional[str] = ..., user_id: _Optional[str] = ..., resource_uri: _Optional[str] = ...) -> None: ...

class GrantUserPermissionsAndRolesOnResourceRequest(_message.Message):
    __slots__ = ("project_name", "user_id", "resource_uri", "permissions", "roles")
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
    __slots__ = ("project_name", "name", "description")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    description: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class Permission(_message.Message):
    __slots__ = ("id", "organisation_id", "name", "description", "project_name")
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
    __slots__ = ("project_name", "name")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class UpdatePermissionRequest(_message.Message):
    __slots__ = ("project_name", "name", "new_name", "description")
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
    __slots__ = ("project_name", "name")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class ListPermissionsResponse(_message.Message):
    __slots__ = ("permissions", "pagination")
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    permissions: _containers.RepeatedCompositeFieldContainer[Permission]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, permissions: _Optional[_Iterable[_Union[Permission, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class CreateRoleRequest(_message.Message):
    __slots__ = ("project_name", "name", "description", "permissions")
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
    __slots__ = ("id", "organisation_id", "name", "description", "permissions", "project_name")
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
    __slots__ = ("project_name", "id")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    id: str
    def __init__(self, project_name: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class UpdateRoleRequest(_message.Message):
    __slots__ = ("project_name", "id", "name", "description", "permissions")
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
    __slots__ = ("project_name", "id")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    id: str
    def __init__(self, project_name: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class ListRolesResponse(_message.Message):
    __slots__ = ("roles", "pagination")
    ROLES_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    roles: _containers.RepeatedCompositeFieldContainer[Role]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, roles: _Optional[_Iterable[_Union[Role, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class RevokeUserPermissionsAndRolesOnResourceRequest(_message.Message):
    __slots__ = ("project_name", "user_id", "resource_uri", "permissions", "roles")
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
    __slots__ = ("organisation_id", "unique_principal_count")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    UNIQUE_PRINCIPAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    unique_principal_count: int
    def __init__(self, organisation_id: _Optional[str] = ..., unique_principal_count: _Optional[int] = ...) -> None: ...

class BatchCheckRequest(_message.Message):
    __slots__ = ("project_name", "principal_id", "resource_uris", "permissions")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_URIS_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    principal_id: str
    resource_uris: _containers.RepeatedScalarFieldContainer[str]
    permissions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., principal_id: _Optional[str] = ..., resource_uris: _Optional[_Iterable[str]] = ..., permissions: _Optional[_Iterable[str]] = ...) -> None: ...

class BatchCheckResponse(_message.Message):
    __slots__ = ("results",)
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[BatchCheckResult]
    def __init__(self, results: _Optional[_Iterable[_Union[BatchCheckResult, _Mapping]]] = ...) -> None: ...

class BatchCheckResult(_message.Message):
    __slots__ = ("resource_uri", "allowed", "missing_permissions")
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_FIELD_NUMBER: _ClassVar[int]
    MISSING_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    resource_uri: str
    allowed: bool
    missing_permissions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, resource_uri: _Optional[str] = ..., allowed: _Optional[bool] = ..., missing_permissions: _Optional[_Iterable[str]] = ...) -> None: ...

class ListAccessRequest(_message.Message):
    __slots__ = ("project_name", "principal_id", "permission", "under_uri", "pagination")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    PERMISSION_FIELD_NUMBER: _ClassVar[int]
    UNDER_URI_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    principal_id: str
    permission: str
    under_uri: str
    pagination: _pagination_pb2.PaginationRequest
    def __init__(self, project_name: _Optional[str] = ..., principal_id: _Optional[str] = ..., permission: _Optional[str] = ..., under_uri: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListAccessResponse(_message.Message):
    __slots__ = ("covers_all", "scopes", "pagination")
    COVERS_ALL_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    covers_all: bool
    scopes: _containers.RepeatedCompositeFieldContainer[AccessScope]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, covers_all: _Optional[bool] = ..., scopes: _Optional[_Iterable[_Union[AccessScope, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class AccessScope(_message.Message):
    __slots__ = ("uri", "scope")
    URI_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    uri: str
    scope: AccessScopeKind
    def __init__(self, uri: _Optional[str] = ..., scope: _Optional[_Union[AccessScopeKind, str]] = ...) -> None: ...

class ListPrincipalsWithAccessRequest(_message.Message):
    __slots__ = ("project_name", "resource_uri", "permission", "expand_groups", "pagination")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    PERMISSION_FIELD_NUMBER: _ClassVar[int]
    EXPAND_GROUPS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    resource_uri: str
    permission: str
    expand_groups: bool
    pagination: _pagination_pb2.PaginationRequest
    def __init__(self, project_name: _Optional[str] = ..., resource_uri: _Optional[str] = ..., permission: _Optional[str] = ..., expand_groups: _Optional[bool] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListPrincipalsWithAccessResponse(_message.Message):
    __slots__ = ("principals", "pagination")
    PRINCIPALS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    principals: _containers.RepeatedCompositeFieldContainer[PrincipalAccess]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, principals: _Optional[_Iterable[_Union[PrincipalAccess, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class PrincipalAccess(_message.Message):
    __slots__ = ("principal_id", "is_group", "via_group", "via")
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    IS_GROUP_FIELD_NUMBER: _ClassVar[int]
    VIA_GROUP_FIELD_NUMBER: _ClassVar[int]
    VIA_FIELD_NUMBER: _ClassVar[int]
    principal_id: str
    is_group: bool
    via_group: str
    via: _containers.RepeatedCompositeFieldContainer[AccessGrant]
    def __init__(self, principal_id: _Optional[str] = ..., is_group: _Optional[bool] = ..., via_group: _Optional[str] = ..., via: _Optional[_Iterable[_Union[AccessGrant, _Mapping]]] = ...) -> None: ...

class AccessGrant(_message.Message):
    __slots__ = ("resource_uri", "inherited", "match", "role", "direct")
    RESOURCE_URI_FIELD_NUMBER: _ClassVar[int]
    INHERITED_FIELD_NUMBER: _ClassVar[int]
    MATCH_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    DIRECT_FIELD_NUMBER: _ClassVar[int]
    resource_uri: str
    inherited: bool
    match: AccessGrantMatch
    role: AccessGrantRole
    direct: AccessGrantDirect
    def __init__(self, resource_uri: _Optional[str] = ..., inherited: _Optional[bool] = ..., match: _Optional[_Union[AccessGrantMatch, str]] = ..., role: _Optional[_Union[AccessGrantRole, _Mapping]] = ..., direct: _Optional[_Union[AccessGrantDirect, _Mapping]] = ...) -> None: ...

class AccessGrantRole(_message.Message):
    __slots__ = ("id", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class AccessGrantDirect(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Group(_message.Message):
    __slots__ = ("id", "organisation_id", "project_name", "name", "description", "principal_id", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    organisation_id: str
    project_name: str
    name: str
    description: str
    principal_id: str
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., organisation_id: _Optional[str] = ..., project_name: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., principal_id: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CreateGroupRequest(_message.Message):
    __slots__ = ("project_name", "name", "description")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    description: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class GetGroupRequest(_message.Message):
    __slots__ = ("project_name", "name")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class UpdateGroupRequest(_message.Message):
    __slots__ = ("project_name", "name", "description")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    description: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class DeleteGroupRequest(_message.Message):
    __slots__ = ("project_name", "name")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class ListGroupsRequest(_message.Message):
    __slots__ = ("project_name", "pagination", "search")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, project_name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class ListGroupsResponse(_message.Message):
    __slots__ = ("groups", "pagination")
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    groups: _containers.RepeatedCompositeFieldContainer[Group]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, groups: _Optional[_Iterable[_Union[Group, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class AddGroupMembersRequest(_message.Message):
    __slots__ = ("project_name", "name", "principal_ids")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_IDS_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    principal_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., principal_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class AddGroupMembersResponse(_message.Message):
    __slots__ = ("added_principal_ids", "existing_principal_ids")
    ADDED_PRINCIPAL_IDS_FIELD_NUMBER: _ClassVar[int]
    EXISTING_PRINCIPAL_IDS_FIELD_NUMBER: _ClassVar[int]
    added_principal_ids: _containers.RepeatedScalarFieldContainer[str]
    existing_principal_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, added_principal_ids: _Optional[_Iterable[str]] = ..., existing_principal_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class RemoveGroupMembersRequest(_message.Message):
    __slots__ = ("project_name", "name", "principal_ids")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_IDS_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    principal_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., principal_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class RemoveGroupMembersResponse(_message.Message):
    __slots__ = ("removed_principal_ids", "not_member_principal_ids")
    REMOVED_PRINCIPAL_IDS_FIELD_NUMBER: _ClassVar[int]
    NOT_MEMBER_PRINCIPAL_IDS_FIELD_NUMBER: _ClassVar[int]
    removed_principal_ids: _containers.RepeatedScalarFieldContainer[str]
    not_member_principal_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, removed_principal_ids: _Optional[_Iterable[str]] = ..., not_member_principal_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class ListGroupMembersRequest(_message.Message):
    __slots__ = ("project_name", "name", "pagination")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    name: str
    pagination: _pagination_pb2.PaginationRequest
    def __init__(self, project_name: _Optional[str] = ..., name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class GroupMember(_message.Message):
    __slots__ = ("principal_id", "created_at")
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    principal_id: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, principal_id: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ListGroupMembersResponse(_message.Message):
    __slots__ = ("members", "pagination")
    MEMBERS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    members: _containers.RepeatedCompositeFieldContainer[GroupMember]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, members: _Optional[_Iterable[_Union[GroupMember, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class ListGroupsForPrincipalRequest(_message.Message):
    __slots__ = ("project_name", "principal_id", "pagination")
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    project_name: str
    principal_id: str
    pagination: _pagination_pb2.PaginationRequest
    def __init__(self, project_name: _Optional[str] = ..., principal_id: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListGroupsForPrincipalResponse(_message.Message):
    __slots__ = ("groups", "pagination")
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    groups: _containers.RepeatedCompositeFieldContainer[Group]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, groups: _Optional[_Iterable[_Union[Group, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class WhoAmIRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class WhoAmIResponse(_message.Message):
    __slots__ = ("principal_id", "organisation_id", "principal_type", "project_name", "api_key_access", "email")
    PRINCIPAL_ID_FIELD_NUMBER: _ClassVar[int]
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    API_KEY_ACCESS_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    principal_id: str
    organisation_id: str
    principal_type: PrincipalType
    project_name: str
    api_key_access: APIKeyAccess
    email: str
    def __init__(self, principal_id: _Optional[str] = ..., organisation_id: _Optional[str] = ..., principal_type: _Optional[_Union[PrincipalType, str]] = ..., project_name: _Optional[str] = ..., api_key_access: _Optional[_Union[APIKeyAccess, str]] = ..., email: _Optional[str] = ...) -> None: ...
