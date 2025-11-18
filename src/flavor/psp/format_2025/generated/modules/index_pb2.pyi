from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class PackageFlags(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FLAG_NONE: _ClassVar[PackageFlags]
    FLAG_SIGNED: _ClassVar[PackageFlags]
    FLAG_ENCRYPTED: _ClassVar[PackageFlags]
    FLAG_COMPRESSED: _ClassVar[PackageFlags]
    FLAG_MMAP_OPTIMIZED: _ClassVar[PackageFlags]
    FLAG_STREAMING: _ClassVar[PackageFlags]
    FLAG_SPA_ENABLED: _ClassVar[PackageFlags]
    FLAG_JIT_ENABLED: _ClassVar[PackageFlags]

class Capabilities(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CAP_NONE: _ClassVar[Capabilities]
    CAP_MMAP: _ClassVar[Capabilities]
    CAP_PAGE_ALIGNED: _ClassVar[Capabilities]
    CAP_COMPRESSED_INDEX: _ClassVar[Capabilities]
    CAP_STREAMING: _ClassVar[Capabilities]
    CAP_PREFETCH: _ClassVar[Capabilities]
    CAP_CACHE_AWARE: _ClassVar[Capabilities]
    CAP_ENCRYPTED: _ClassVar[Capabilities]
    CAP_SIGNED: _ClassVar[Capabilities]
FLAG_NONE: PackageFlags
FLAG_SIGNED: PackageFlags
FLAG_ENCRYPTED: PackageFlags
FLAG_COMPRESSED: PackageFlags
FLAG_MMAP_OPTIMIZED: PackageFlags
FLAG_STREAMING: PackageFlags
FLAG_SPA_ENABLED: PackageFlags
FLAG_JIT_ENABLED: PackageFlags
CAP_NONE: Capabilities
CAP_MMAP: Capabilities
CAP_PAGE_ALIGNED: Capabilities
CAP_COMPRESSED_INDEX: Capabilities
CAP_STREAMING: Capabilities
CAP_PREFETCH: Capabilities
CAP_CACHE_AWARE: Capabilities
CAP_ENCRYPTED: Capabilities
CAP_SIGNED: Capabilities

class IndexBlock(_message.Message):
    __slots__ = ("format_version", "index_checksum", "package_size", "launcher_size", "metadata_offset", "metadata_size", "slot_table_offset", "slot_table_size", "slot_count", "flags", "public_key", "metadata_checksum", "integrity_signature", "access_mode", "cache_strategy", "reserved_hint1", "reserved_hint2", "page_size", "max_memory", "min_memory", "cpu_features", "gpu_requirements", "numa_hints", "stream_chunk_size", "build_timestamp", "build_machine", "source_hash", "dependency_hash", "license_id", "provenance_uri", "capabilities", "requirements", "extensions", "compatibility", "protocol_version", "future_crypto", "reserved")
    FORMAT_VERSION_FIELD_NUMBER: _ClassVar[int]
    INDEX_CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    PACKAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    LAUNCHER_SIZE_FIELD_NUMBER: _ClassVar[int]
    METADATA_OFFSET_FIELD_NUMBER: _ClassVar[int]
    METADATA_SIZE_FIELD_NUMBER: _ClassVar[int]
    SLOT_TABLE_OFFSET_FIELD_NUMBER: _ClassVar[int]
    SLOT_TABLE_SIZE_FIELD_NUMBER: _ClassVar[int]
    SLOT_COUNT_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    METADATA_CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    INTEGRITY_SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    ACCESS_MODE_FIELD_NUMBER: _ClassVar[int]
    CACHE_STRATEGY_FIELD_NUMBER: _ClassVar[int]
    CODEC_TYPE_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    MAX_MEMORY_FIELD_NUMBER: _ClassVar[int]
    MIN_MEMORY_FIELD_NUMBER: _ClassVar[int]
    CPU_FEATURES_FIELD_NUMBER: _ClassVar[int]
    GPU_REQUIREMENTS_FIELD_NUMBER: _ClassVar[int]
    NUMA_HINTS_FIELD_NUMBER: _ClassVar[int]
    STREAM_CHUNK_SIZE_FIELD_NUMBER: _ClassVar[int]
    BUILD_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    BUILD_MACHINE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_HASH_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCY_HASH_FIELD_NUMBER: _ClassVar[int]
    LICENSE_ID_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_URI_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    REQUIREMENTS_FIELD_NUMBER: _ClassVar[int]
    EXTENSIONS_FIELD_NUMBER: _ClassVar[int]
    COMPATIBILITY_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_VERSION_FIELD_NUMBER: _ClassVar[int]
    FUTURE_CRYPTO_FIELD_NUMBER: _ClassVar[int]
    RESERVED_FIELD_NUMBER: _ClassVar[int]
    format_version: int
    index_checksum: int
    package_size: int
    launcher_size: int
    metadata_offset: int
    metadata_size: int
    slot_table_offset: int
    slot_table_size: int
    slot_count: int
    flags: int
    public_key: bytes
    metadata_checksum: bytes
    integrity_signature: bytes
    access_mode: int
    cache_strategy: int
    reserved_hint1: int
    reserved_hint2: int
    page_size: int
    max_memory: int
    min_memory: int
    cpu_features: int
    gpu_requirements: int
    numa_hints: int
    stream_chunk_size: int
    build_timestamp: int
    build_machine: bytes
    source_hash: bytes
    dependency_hash: bytes
    license_id: bytes
    provenance_uri: bytes
    capabilities: int
    requirements: int
    extensions: int
    compatibility: int
    protocol_version: int
    future_crypto: bytes
    reserved: bytes
    def __init__(self, format_version: _Optional[int] = ..., index_checksum: _Optional[int] = ..., package_size: _Optional[int] = ..., launcher_size: _Optional[int] = ..., metadata_offset: _Optional[int] = ..., metadata_size: _Optional[int] = ..., slot_table_offset: _Optional[int] = ..., slot_table_size: _Optional[int] = ..., slot_count: _Optional[int] = ..., flags: _Optional[int] = ..., public_key: _Optional[bytes] = ..., metadata_checksum: _Optional[bytes] = ..., integrity_signature: _Optional[bytes] = ..., access_mode: _Optional[int] = ..., cache_strategy: _Optional[int] = ..., reserved_hint1: _Optional[int] = ..., reserved_hint2: _Optional[int] = ..., page_size: _Optional[int] = ..., max_memory: _Optional[int] = ..., min_memory: _Optional[int] = ..., cpu_features: _Optional[int] = ..., gpu_requirements: _Optional[int] = ..., numa_hints: _Optional[int] = ..., stream_chunk_size: _Optional[int] = ..., build_timestamp: _Optional[int] = ..., build_machine: _Optional[bytes] = ..., source_hash: _Optional[bytes] = ..., dependency_hash: _Optional[bytes] = ..., license_id: _Optional[bytes] = ..., provenance_uri: _Optional[bytes] = ..., capabilities: _Optional[int] = ..., requirements: _Optional[int] = ..., extensions: _Optional[int] = ..., compatibility: _Optional[int] = ..., protocol_version: _Optional[int] = ..., future_crypto: _Optional[bytes] = ..., reserved: _Optional[bytes] = ...) -> None: ...
