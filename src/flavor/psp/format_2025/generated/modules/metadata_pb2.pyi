from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PackageMetadata(_message.Message):
    __slots__ = ("name", "version", "format_version", "description", "author", "license", "slots", "execution", "build", "dependencies", "requirements", "spa", "jit", "security", "custom", "created_at", "modified_at")
    class CustomEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    FORMAT_VERSION_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    LICENSE_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    BUILD_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
    REQUIREMENTS_FIELD_NUMBER: _ClassVar[int]
    SPA_FIELD_NUMBER: _ClassVar[int]
    JIT_FIELD_NUMBER: _ClassVar[int]
    SECURITY_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    MODIFIED_AT_FIELD_NUMBER: _ClassVar[int]
    name: str
    version: str
    format_version: str
    description: str
    author: str
    license: str
    slots: _containers.RepeatedCompositeFieldContainer[SlotMetadata]
    execution: ExecutionConfig
    build: BuildInfo
    dependencies: _containers.RepeatedCompositeFieldContainer[Dependency]
    requirements: Requirements
    spa: SpaConfig
    jit: JitConfig
    security: SecurityConfig
    custom: _containers.ScalarMap[str, str]
    created_at: int
    modified_at: int
    def __init__(self, name: _Optional[str] = ..., version: _Optional[str] = ..., format_version: _Optional[str] = ..., description: _Optional[str] = ..., author: _Optional[str] = ..., license: _Optional[str] = ..., slots: _Optional[_Iterable[_Union[SlotMetadata, _Mapping]]] = ..., execution: _Optional[_Union[ExecutionConfig, _Mapping]] = ..., build: _Optional[_Union[BuildInfo, _Mapping]] = ..., dependencies: _Optional[_Iterable[_Union[Dependency, _Mapping]]] = ..., requirements: _Optional[_Union[Requirements, _Mapping]] = ..., spa: _Optional[_Union[SpaConfig, _Mapping]] = ..., jit: _Optional[_Union[JitConfig, _Mapping]] = ..., security: _Optional[_Union[SecurityConfig, _Mapping]] = ..., custom: _Optional[_Mapping[str, str]] = ..., created_at: _Optional[int] = ..., modified_at: _Optional[int] = ...) -> None: ...

class ExecutionConfig(_message.Message):
    __slots__ = ("command", "args", "env", "working_dir", "interpreter", "python_path", "timeout_seconds")
    class EnvEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIR_FIELD_NUMBER: _ClassVar[int]
    INTERPRETER_FIELD_NUMBER: _ClassVar[int]
    PYTHON_PATH_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_SECONDS_FIELD_NUMBER: _ClassVar[int]
    command: str
    args: _containers.RepeatedScalarFieldContainer[str]
    env: _containers.ScalarMap[str, str]
    working_dir: str
    interpreter: str
    python_path: _containers.RepeatedScalarFieldContainer[str]
    timeout_seconds: int
    def __init__(self, command: _Optional[str] = ..., args: _Optional[_Iterable[str]] = ..., env: _Optional[_Mapping[str, str]] = ..., working_dir: _Optional[str] = ..., interpreter: _Optional[str] = ..., python_path: _Optional[_Iterable[str]] = ..., timeout_seconds: _Optional[int] = ...) -> None: ...

class BuildInfo(_message.Message):
    __slots__ = ("timestamp", "machine", "user", "commit", "branch", "tags", "builder_version", "environment")
    class EnvironmentEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    MACHINE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    COMMIT_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    BUILDER_VERSION_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    timestamp: int
    machine: str
    user: str
    commit: str
    branch: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    builder_version: str
    environment: _containers.ScalarMap[str, str]
    def __init__(self, timestamp: _Optional[int] = ..., machine: _Optional[str] = ..., user: _Optional[str] = ..., commit: _Optional[str] = ..., branch: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ..., builder_version: _Optional[str] = ..., environment: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Dependency(_message.Message):
    __slots__ = ("name", "version_spec", "source", "optional", "extras")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_SPEC_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    OPTIONAL_FIELD_NUMBER: _ClassVar[int]
    EXTRAS_FIELD_NUMBER: _ClassVar[int]
    name: str
    version_spec: str
    source: str
    optional: bool
    extras: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, name: _Optional[str] = ..., version_spec: _Optional[str] = ..., source: _Optional[str] = ..., optional: bool = ..., extras: _Optional[_Iterable[str]] = ...) -> None: ...

class Requirements(_message.Message):
    __slots__ = ("python_version", "platform", "architecture", "memory_mb", "disk_mb", "system_packages")
    PYTHON_VERSION_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    ARCHITECTURE_FIELD_NUMBER: _ClassVar[int]
    MEMORY_MB_FIELD_NUMBER: _ClassVar[int]
    DISK_MB_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PACKAGES_FIELD_NUMBER: _ClassVar[int]
    python_version: str
    platform: str
    architecture: str
    memory_mb: int
    disk_mb: int
    system_packages: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, python_version: _Optional[str] = ..., platform: _Optional[str] = ..., architecture: _Optional[str] = ..., memory_mb: _Optional[int] = ..., disk_mb: _Optional[int] = ..., system_packages: _Optional[_Iterable[str]] = ...) -> None: ...

class SpaConfig(_message.Message):
    __slots__ = ("enabled", "pvp_slot", "pvp_timeout_ms", "pvp_max_memory", "pvp_capabilities", "boundary_type", "boundary_timeout_ms")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    PVP_SLOT_FIELD_NUMBER: _ClassVar[int]
    PVP_TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    PVP_MAX_MEMORY_FIELD_NUMBER: _ClassVar[int]
    PVP_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_TYPE_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    pvp_slot: int
    pvp_timeout_ms: int
    pvp_max_memory: int
    pvp_capabilities: _containers.RepeatedScalarFieldContainer[str]
    boundary_type: str
    boundary_timeout_ms: int
    def __init__(self, enabled: bool = ..., pvp_slot: _Optional[int] = ..., pvp_timeout_ms: _Optional[int] = ..., pvp_max_memory: _Optional[int] = ..., pvp_capabilities: _Optional[_Iterable[str]] = ..., boundary_type: _Optional[str] = ..., boundary_timeout_ms: _Optional[int] = ...) -> None: ...

class JitConfig(_message.Message):
    __slots__ = ("enabled", "strategy", "cache_dir", "max_cache_size", "network_timeout_ms", "background_slots")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    CACHE_DIR_FIELD_NUMBER: _ClassVar[int]
    MAX_CACHE_SIZE_FIELD_NUMBER: _ClassVar[int]
    NETWORK_TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    BACKGROUND_SLOTS_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    strategy: str
    cache_dir: str
    max_cache_size: int
    network_timeout_ms: int
    background_slots: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, enabled: bool = ..., strategy: _Optional[str] = ..., cache_dir: _Optional[str] = ..., max_cache_size: _Optional[int] = ..., network_timeout_ms: _Optional[int] = ..., background_slots: _Optional[_Iterable[int]] = ...) -> None: ...

class SlotMetadata(_message.Message):
    __slots__ = ("slot", "id", "source", "target", "size", "checksum", "operations", "purpose", "lifecycle", "permissions", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SLOT_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    PURPOSE_FIELD_NUMBER: _ClassVar[int]
    LIFECYCLE_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    slot: int
    id: str
    source: str
    target: str
    size: int
    checksum: str
    operations: str
    purpose: str
    lifecycle: str
    permissions: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, slot: _Optional[int] = ..., id: _Optional[str] = ..., source: _Optional[str] = ..., target: _Optional[str] = ..., size: _Optional[int] = ..., checksum: _Optional[str] = ..., operations: _Optional[str] = ..., purpose: _Optional[str] = ..., lifecycle: _Optional[str] = ..., permissions: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class SecurityConfig(_message.Message):
    __slots__ = ("require_signature", "allow_unsigned", "key_source", "trusted_keys", "signature_algorithm", "verify_checksums", "sandbox_enabled", "capabilities")
    REQUIRE_SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    ALLOW_UNSIGNED_FIELD_NUMBER: _ClassVar[int]
    KEY_SOURCE_FIELD_NUMBER: _ClassVar[int]
    TRUSTED_KEYS_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    VERIFY_CHECKSUMS_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_ENABLED_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    require_signature: bool
    allow_unsigned: bool
    key_source: str
    trusted_keys: _containers.RepeatedScalarFieldContainer[str]
    signature_algorithm: str
    verify_checksums: bool
    sandbox_enabled: bool
    capabilities: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, require_signature: bool = ..., allow_unsigned: bool = ..., key_source: _Optional[str] = ..., trusted_keys: _Optional[_Iterable[str]] = ..., signature_algorithm: _Optional[str] = ..., verify_checksums: bool = ..., sandbox_enabled: bool = ..., capabilities: _Optional[_Iterable[str]] = ...) -> None: ...
