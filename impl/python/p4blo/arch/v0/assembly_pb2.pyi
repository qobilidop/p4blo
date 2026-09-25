from p4blo.v0 import p4blo_pb2 as _p4blo_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BlockBindings(_message.Message):
    __slots__ = ("headers", "metadata", "exports")
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    EXPORTS_FIELD_NUMBER: _ClassVar[int]
    headers: str
    metadata: str
    exports: _containers.RepeatedCompositeFieldContainer[Export]
    def __init__(self, headers: _Optional[str] = ..., metadata: _Optional[str] = ..., exports: _Optional[_Iterable[_Union[Export, _Mapping]]] = ...) -> None: ...

class Export(_message.Message):
    __slots__ = ("role", "block")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    role: str
    block: str
    def __init__(self, role: _Optional[str] = ..., block: _Optional[str] = ...) -> None: ...

class BlockAssembly(_message.Message):
    __slots__ = ("name", "errors", "header_types", "struct_types", "enum_types", "extern_types", "extern_instances", "blocks", "headers", "metadata", "exports")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    HEADER_TYPES_FIELD_NUMBER: _ClassVar[int]
    STRUCT_TYPES_FIELD_NUMBER: _ClassVar[int]
    ENUM_TYPES_FIELD_NUMBER: _ClassVar[int]
    EXTERN_TYPES_FIELD_NUMBER: _ClassVar[int]
    EXTERN_INSTANCES_FIELD_NUMBER: _ClassVar[int]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    EXPORTS_FIELD_NUMBER: _ClassVar[int]
    name: str
    errors: _containers.RepeatedScalarFieldContainer[str]
    header_types: _containers.RepeatedCompositeFieldContainer[_p4blo_pb2.HeaderType]
    struct_types: _containers.RepeatedCompositeFieldContainer[_p4blo_pb2.StructType]
    enum_types: _containers.RepeatedCompositeFieldContainer[_p4blo_pb2.EnumType]
    extern_types: _containers.RepeatedCompositeFieldContainer[_p4blo_pb2.ExternType]
    extern_instances: _containers.RepeatedCompositeFieldContainer[_p4blo_pb2.ExternInstance]
    blocks: _containers.RepeatedCompositeFieldContainer[_p4blo_pb2.Block]
    headers: str
    metadata: str
    exports: _containers.RepeatedCompositeFieldContainer[Export]
    def __init__(self, name: _Optional[str] = ..., errors: _Optional[_Iterable[str]] = ..., header_types: _Optional[_Iterable[_Union[_p4blo_pb2.HeaderType, _Mapping]]] = ..., struct_types: _Optional[_Iterable[_Union[_p4blo_pb2.StructType, _Mapping]]] = ..., enum_types: _Optional[_Iterable[_Union[_p4blo_pb2.EnumType, _Mapping]]] = ..., extern_types: _Optional[_Iterable[_Union[_p4blo_pb2.ExternType, _Mapping]]] = ..., extern_instances: _Optional[_Iterable[_Union[_p4blo_pb2.ExternInstance, _Mapping]]] = ..., blocks: _Optional[_Iterable[_Union[_p4blo_pb2.Block, _Mapping]]] = ..., headers: _Optional[str] = ..., metadata: _Optional[str] = ..., exports: _Optional[_Iterable[_Union[Export, _Mapping]]] = ...) -> None: ...
