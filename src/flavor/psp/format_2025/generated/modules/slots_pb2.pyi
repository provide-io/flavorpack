from modules import operations_pb2 as _operations_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Lifecycle(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LIFECYCLE_INIT: _ClassVar[Lifecycle]
    LIFECYCLE_EAGER: _ClassVar[Lifecycle]
    LIFECYCLE_STARTUP: _ClassVar[Lifecycle]
    LIFECYCLE_RUNTIME: _ClassVar[Lifecycle]
    LIFECYCLE_MANUAL: _ClassVar[Lifecycle]
    LIFECYCLE_VOLATILE: _ClassVar[Lifecycle]
    LIFECYCLE_EPHEMERAL: _ClassVar[Lifecycle]
    LIFECYCLE_PERSISTENT: _ClassVar[Lifecycle]
    LIFECYCLE_CACHED: _ClassVar[Lifecycle]
    LIFECYCLE_LAZY: _ClassVar[Lifecycle]
    LIFECYCLE_PRELOAD: _ClassVar[Lifecycle]
    LIFECYCLE_JIT_LOCAL: _ClassVar[Lifecycle]
    LIFECYCLE_JIT_NETWORK: _ClassVar[Lifecycle]
    LIFECYCLE_JIT_HYBRID: _ClassVar[Lifecycle]
    LIFECYCLE_JIT_OPTIONAL: _ClassVar[Lifecycle]
    LIFECYCLE_JIT_BACKGROUND: _ClassVar[Lifecycle]

class Purpose(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PURPOSE_CODE: _ClassVar[Purpose]
    PURPOSE_DATA: _ClassVar[Purpose]
    PURPOSE_CONFIG: _ClassVar[Purpose]
    PURPOSE_ASSETS: _ClassVar[Purpose]
    PURPOSE_RUNTIME: _ClassVar[Purpose]
    PURPOSE_LIBRARY: _ClassVar[Purpose]
    PURPOSE_METADATA: _ClassVar[Purpose]
    PURPOSE_DOCS: _ClassVar[Purpose]
    PURPOSE_TESTS: _ClassVar[Purpose]
    PURPOSE_TOOLS: _ClassVar[Purpose]
    PURPOSE_VENDOR: _ClassVar[Purpose]
    PURPOSE_CACHE: _ClassVar[Purpose]
    PURPOSE_TEMP: _ClassVar[Purpose]
    PURPOSE_LOGS: _ClassVar[Purpose]
    PURPOSE_STATE: _ClassVar[Purpose]
    PURPOSE_SECRETS: _ClassVar[Purpose]

class Platform(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLATFORM_ANY: _ClassVar[Platform]
    PLATFORM_LINUX: _ClassVar[Platform]
    PLATFORM_DARWIN: _ClassVar[Platform]
    PLATFORM_WINDOWS: _ClassVar[Platform]
    PLATFORM_BSD: _ClassVar[Platform]
    PLATFORM_WASM: _ClassVar[Platform]
    PLATFORM_ANDROID: _ClassVar[Platform]
    PLATFORM_IOS: _ClassVar[Platform]
LIFECYCLE_INIT: Lifecycle
LIFECYCLE_EAGER: Lifecycle
LIFECYCLE_STARTUP: Lifecycle
LIFECYCLE_RUNTIME: Lifecycle
LIFECYCLE_MANUAL: Lifecycle
LIFECYCLE_VOLATILE: Lifecycle
LIFECYCLE_EPHEMERAL: Lifecycle
LIFECYCLE_PERSISTENT: Lifecycle
LIFECYCLE_CACHED: Lifecycle
LIFECYCLE_LAZY: Lifecycle
LIFECYCLE_PRELOAD: Lifecycle
LIFECYCLE_JIT_LOCAL: Lifecycle
LIFECYCLE_JIT_NETWORK: Lifecycle
LIFECYCLE_JIT_HYBRID: Lifecycle
LIFECYCLE_JIT_OPTIONAL: Lifecycle
LIFECYCLE_JIT_BACKGROUND: Lifecycle
PURPOSE_CODE: Purpose
PURPOSE_DATA: Purpose
PURPOSE_CONFIG: Purpose
PURPOSE_ASSETS: Purpose
PURPOSE_RUNTIME: Purpose
PURPOSE_LIBRARY: Purpose
PURPOSE_METADATA: Purpose
PURPOSE_DOCS: Purpose
PURPOSE_TESTS: Purpose
PURPOSE_TOOLS: Purpose
PURPOSE_VENDOR: Purpose
PURPOSE_CACHE: Purpose
PURPOSE_TEMP: Purpose
PURPOSE_LOGS: Purpose
PURPOSE_STATE: Purpose
PURPOSE_SECRETS: Purpose
PLATFORM_ANY: Platform
PLATFORM_LINUX: Platform
PLATFORM_DARWIN: Platform
PLATFORM_WINDOWS: Platform
PLATFORM_BSD: Platform
PLATFORM_WASM: Platform
PLATFORM_ANDROID: Platform
PLATFORM_IOS: Platform

class SlotEntry(_message.Message):
    __slots__ = ("id", "name_hash", "offset", "size", "original_size", "operations", "checksum", "hash", "purpose", "lifecycle", "platform", "permissions", "flags", "jit", "name", "source_path", "target_path", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_HASH_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    PURPOSE_FIELD_NUMBER: _ClassVar[int]
    LIFECYCLE_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    JIT_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_PATH_FIELD_NUMBER: _ClassVar[int]
    TARGET_PATH_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    id: int
    name_hash: int
    offset: int
    size: int
    original_size: int
    operations: int
    checksum: int
    hash: bytes
    purpose: Purpose
    lifecycle: Lifecycle
    platform: Platform
    permissions: int
    flags: int
    jit: JITConfig
    name: str
    source_path: str
    target_path: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, id: _Optional[int] = ..., name_hash: _Optional[int] = ..., offset: _Optional[int] = ..., size: _Optional[int] = ..., original_size: _Optional[int] = ..., operations: _Optional[int] = ..., checksum: _Optional[int] = ..., hash: _Optional[bytes] = ..., purpose: _Optional[_Union[Purpose, str]] = ..., lifecycle: _Optional[_Union[Lifecycle, str]] = ..., platform: _Optional[_Union[Platform, str]] = ..., permissions: _Optional[int] = ..., flags: _Optional[int] = ..., jit: _Optional[_Union[JITConfig, _Mapping]] = ..., name: _Optional[str] = ..., source_path: _Optional[str] = ..., target_path: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class JITConfig(_message.Message):
    __slots__ = ("source", "cache", "priority", "timeout_ms")
    class Source(_message.Message):
        __slots__ = ("type", "endpoint", "path", "tls", "cert_pin")
        TYPE_FIELD_NUMBER: _ClassVar[int]
        ENDPOINT_FIELD_NUMBER: _ClassVar[int]
        PATH_FIELD_NUMBER: _ClassVar[int]
        TLS_FIELD_NUMBER: _ClassVar[int]
        CERT_PIN_FIELD_NUMBER: _ClassVar[int]
        type: str
        endpoint: str
        path: str
        tls: bool
        cert_pin: str
        def __init__(self, type: _Optional[str] = ..., endpoint: _Optional[str] = ..., path: _Optional[str] = ..., tls: bool = ..., cert_pin: _Optional[str] = ...) -> None: ...
    class Cache(_message.Message):
        __slots__ = ("strategy", "ttl", "verify_on_load")
        STRATEGY_FIELD_NUMBER: _ClassVar[int]
        TTL_FIELD_NUMBER: _ClassVar[int]
        VERIFY_ON_LOAD_FIELD_NUMBER: _ClassVar[int]
        strategy: str
        ttl: int
        verify_on_load: bool
        def __init__(self, strategy: _Optional[str] = ..., ttl: _Optional[int] = ..., verify_on_load: bool = ...) -> None: ...
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    CACHE_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    source: JITConfig.Source
    cache: JITConfig.Cache
    priority: int
    timeout_ms: int
    def __init__(self, source: _Optional[_Union[JITConfig.Source, _Mapping]] = ..., cache: _Optional[_Union[JITConfig.Cache, _Mapping]] = ..., priority: _Optional[int] = ..., timeout_ms: _Optional[int] = ...) -> None: ...

class SlotTable(_message.Message):
    __slots__ = ("slots", "slot_count", "total_size", "table_checksum", "version", "created_at", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    SLOT_COUNT_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    TABLE_CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    slots: _containers.RepeatedCompositeFieldContainer[SlotEntry]
    slot_count: int
    total_size: int
    table_checksum: int
    version: int
    created_at: int
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, slots: _Optional[_Iterable[_Union[SlotEntry, _Mapping]]] = ..., slot_count: _Optional[int] = ..., total_size: _Optional[int] = ..., table_checksum: _Optional[int] = ..., version: _Optional[int] = ..., created_at: _Optional[int] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...
