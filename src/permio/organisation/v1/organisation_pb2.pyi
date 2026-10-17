import datetime

from google.api import annotations_pb2 as _annotations_pb2
from permio.validate import validate_pb2 as _validate_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from permio.permissions.v1 import permissions_pb2 as _permissions_pb2
from permio.pagination.v1 import pagination_pb2 as _pagination_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class APIKeyAccess(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    API_KEY_ACCESS_UNSPECIFIED: _ClassVar[APIKeyAccess]
    API_KEY_ACCESS_CHECK: _ClassVar[APIKeyAccess]
    API_KEY_ACCESS_FULL: _ClassVar[APIKeyAccess]
API_KEY_ACCESS_UNSPECIFIED: APIKeyAccess
API_KEY_ACCESS_CHECK: APIKeyAccess
API_KEY_ACCESS_FULL: APIKeyAccess

class RemoveUserFromOrganisationRequest(_message.Message):
    __slots__ = ("organisation_id", "user_id")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    user_id: str
    def __init__(self, organisation_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class GetOrganisationDashboardRequest(_message.Message):
    __slots__ = ("organisation_id",)
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    def __init__(self, organisation_id: _Optional[str] = ...) -> None: ...

class GetOrganisationDashboardResponse(_message.Message):
    __slots__ = ("total_roles", "total_permissions", "total_principals", "total_users")
    TOTAL_ROLES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PRINCIPALS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_USERS_FIELD_NUMBER: _ClassVar[int]
    total_roles: int
    total_permissions: int
    total_principals: int
    total_users: int
    def __init__(self, total_roles: _Optional[int] = ..., total_permissions: _Optional[int] = ..., total_principals: _Optional[int] = ..., total_users: _Optional[int] = ...) -> None: ...

class GetPrincipalUsageStatsRequest(_message.Message):
    __slots__ = ("organisation_id",)
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    def __init__(self, organisation_id: _Optional[str] = ...) -> None: ...

class GetPrincipalUsageStatsResponse(_message.Message):
    __slots__ = ("current_count", "included_count", "usage_percentage", "overage", "overage_rate", "estimated_overage_cost", "current_billing_period", "days_left_in_billing_period")
    CURRENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    INCLUDED_COUNT_FIELD_NUMBER: _ClassVar[int]
    USAGE_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    OVERAGE_FIELD_NUMBER: _ClassVar[int]
    OVERAGE_RATE_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_OVERAGE_COST_FIELD_NUMBER: _ClassVar[int]
    CURRENT_BILLING_PERIOD_FIELD_NUMBER: _ClassVar[int]
    DAYS_LEFT_IN_BILLING_PERIOD_FIELD_NUMBER: _ClassVar[int]
    current_count: int
    included_count: int
    usage_percentage: int
    overage: int
    overage_rate: float
    estimated_overage_cost: float
    current_billing_period: str
    days_left_in_billing_period: int
    def __init__(self, current_count: _Optional[int] = ..., included_count: _Optional[int] = ..., usage_percentage: _Optional[int] = ..., overage: _Optional[int] = ..., overage_rate: _Optional[float] = ..., estimated_overage_cost: _Optional[float] = ..., current_billing_period: _Optional[str] = ..., days_left_in_billing_period: _Optional[int] = ...) -> None: ...

class GetUsageHistoryRequest(_message.Message):
    __slots__ = ("organisation_id", "days")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    DAYS_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    days: int
    def __init__(self, organisation_id: _Optional[str] = ..., days: _Optional[int] = ...) -> None: ...

class GetUsageHistoryResponse(_message.Message):
    __slots__ = ("history",)
    class UsageDataPoint(_message.Message):
        __slots__ = ("date", "count")
        DATE_FIELD_NUMBER: _ClassVar[int]
        COUNT_FIELD_NUMBER: _ClassVar[int]
        date: str
        count: int
        def __init__(self, date: _Optional[str] = ..., count: _Optional[int] = ...) -> None: ...
    HISTORY_FIELD_NUMBER: _ClassVar[int]
    history: _containers.RepeatedCompositeFieldContainer[GetUsageHistoryResponse.UsageDataPoint]
    def __init__(self, history: _Optional[_Iterable[_Union[GetUsageHistoryResponse.UsageDataPoint, _Mapping]]] = ...) -> None: ...

class Project(_message.Message):
    __slots__ = ("organisation_id", "name", "created_at")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    name: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, organisation_id: _Optional[str] = ..., name: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CreateProjectResponse(_message.Message):
    __slots__ = ("project",)
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    project: Project
    def __init__(self, project: _Optional[_Union[Project, _Mapping]] = ...) -> None: ...

class CreateProjectRequest(_message.Message):
    __slots__ = ("organisation_id", "name")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    name: str
    def __init__(self, organisation_id: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class GetProjectRequest(_message.Message):
    __slots__ = ("organisation_id", "project_name")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    project_name: str
    def __init__(self, organisation_id: _Optional[str] = ..., project_name: _Optional[str] = ...) -> None: ...

class GetProjectsForOrganisationRequest(_message.Message):
    __slots__ = ("organisation_id", "pagination", "search")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, organisation_id: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class GetProjectsForOrganisationResponse(_message.Message):
    __slots__ = ("projects", "pagination")
    PROJECTS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    projects: _containers.RepeatedCompositeFieldContainer[Project]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, projects: _Optional[_Iterable[_Union[Project, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class GetProjectResponse(_message.Message):
    __slots__ = ("project",)
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    project: Project
    def __init__(self, project: _Optional[_Union[Project, _Mapping]] = ...) -> None: ...

class DeleteProjectRequest(_message.Message):
    __slots__ = ("organisation_id", "project_name")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    project_name: str
    def __init__(self, organisation_id: _Optional[str] = ..., project_name: _Optional[str] = ...) -> None: ...

class User(_message.Message):
    __slots__ = ("id", "email")
    ID_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    id: str
    email: str
    def __init__(self, id: _Optional[str] = ..., email: _Optional[str] = ...) -> None: ...

class Organisation(_message.Message):
    __slots__ = ("id", "name", "users", "created_at", "updated_at", "billing_customer")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    USERS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    BILLING_CUSTOMER_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    users: _containers.RepeatedCompositeFieldContainer[User]
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    billing_customer: BillingCustomer
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., users: _Optional[_Iterable[_Union[User, _Mapping]]] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., billing_customer: _Optional[_Union[BillingCustomer, _Mapping]] = ...) -> None: ...

class BillingCustomer(_message.Message):
    __slots__ = ("id", "organisation_id", "name", "email")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    id: str
    organisation_id: str
    name: str
    email: str
    def __init__(self, id: _Optional[str] = ..., organisation_id: _Optional[str] = ..., name: _Optional[str] = ..., email: _Optional[str] = ...) -> None: ...

class CreateOrganisationRequest(_message.Message):
    __slots__ = ("name", "user_id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    user_id: str
    def __init__(self, name: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class CreateOrganisationResponse(_message.Message):
    __slots__ = ("organisation",)
    ORGANISATION_FIELD_NUMBER: _ClassVar[int]
    organisation: Organisation
    def __init__(self, organisation: _Optional[_Union[Organisation, _Mapping]] = ...) -> None: ...

class GetOrganisationRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class GetOrganisationResponse(_message.Message):
    __slots__ = ("organisation",)
    ORGANISATION_FIELD_NUMBER: _ClassVar[int]
    organisation: Organisation
    def __init__(self, organisation: _Optional[_Union[Organisation, _Mapping]] = ...) -> None: ...

class UpdateOrganisationRequest(_message.Message):
    __slots__ = ("id", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class UpdateOrganisationResponse(_message.Message):
    __slots__ = ("organisation",)
    ORGANISATION_FIELD_NUMBER: _ClassVar[int]
    organisation: Organisation
    def __init__(self, organisation: _Optional[_Union[Organisation, _Mapping]] = ...) -> None: ...

class SetUsersOrganisationRequest(_message.Message):
    __slots__ = ("id", "user_id", "email")
    ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    id: str
    user_id: str
    email: str
    def __init__(self, id: _Optional[str] = ..., user_id: _Optional[str] = ..., email: _Optional[str] = ...) -> None: ...

class InviteUserToOrganisationRequest(_message.Message):
    __slots__ = ("organisation_id", "email")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    email: str
    def __init__(self, organisation_id: _Optional[str] = ..., email: _Optional[str] = ...) -> None: ...

class GetUsersOrganisationRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class CreateAPIKeyRequest(_message.Message):
    __slots__ = ("organisation_id", "project_name", "name", "access")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    project_name: str
    name: str
    access: APIKeyAccess
    def __init__(self, organisation_id: _Optional[str] = ..., project_name: _Optional[str] = ..., name: _Optional[str] = ..., access: _Optional[_Union[APIKeyAccess, str]] = ...) -> None: ...

class APIKey(_message.Message):
    __slots__ = ("id", "name", "key", "created_at", "invalidated", "access")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    INVALIDATED_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    key: str
    created_at: _timestamp_pb2.Timestamp
    invalidated: bool
    access: APIKeyAccess
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., key: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., invalidated: _Optional[bool] = ..., access: _Optional[_Union[APIKeyAccess, str]] = ...) -> None: ...

class CreateAPIKeyResponse(_message.Message):
    __slots__ = ("api_key",)
    API_KEY_FIELD_NUMBER: _ClassVar[int]
    api_key: APIKey
    def __init__(self, api_key: _Optional[_Union[APIKey, _Mapping]] = ...) -> None: ...

class ListAPIKeysRequest(_message.Message):
    __slots__ = ("organisation_id", "project_name", "pagination", "search")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    project_name: str
    pagination: _pagination_pb2.PaginationRequest
    search: str
    def __init__(self, organisation_id: _Optional[str] = ..., project_name: _Optional[str] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationRequest, _Mapping]] = ..., search: _Optional[str] = ...) -> None: ...

class ListAPIKeysResponse(_message.Message):
    __slots__ = ("api_keys", "pagination")
    API_KEYS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    api_keys: _containers.RepeatedCompositeFieldContainer[APIKey]
    pagination: _pagination_pb2.PaginationResponse
    def __init__(self, api_keys: _Optional[_Iterable[_Union[APIKey, _Mapping]]] = ..., pagination: _Optional[_Union[_pagination_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class InvalidateAPIKeyRequest(_message.Message):
    __slots__ = ("organisation_id", "project_name", "id")
    ORGANISATION_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    organisation_id: str
    project_name: str
    id: str
    def __init__(self, organisation_id: _Optional[str] = ..., project_name: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...
