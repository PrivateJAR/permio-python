from google.api import annotations_pb2 as _annotations_pb2
from permio.validate import validate_pb2 as _validate_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class PaginationRequest(_message.Message):
    __slots__ = ("limit", "cursor")
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    limit: int
    cursor: str
    def __init__(self, limit: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class PaginationResponse(_message.Message):
    __slots__ = ("next_cursor",)
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    next_cursor: str
    def __init__(self, next_cursor: _Optional[str] = ...) -> None: ...
