from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Capability(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CAPABILITY_NONE: _ClassVar[Capability]
    CAPABILITY_UI_RENDER: _ClassVar[Capability]
    CAPABILITY_TEMP_FILES: _ClassVar[Capability]
    CAPABILITY_IPC_SETUP: _ClassVar[Capability]
    CAPABILITY_CACHE_INIT: _ClassVar[Capability]
    CAPABILITY_CONFIG_LOAD: _ClassVar[Capability]
    CAPABILITY_MEMORY_MAP: _ClassVar[Capability]
    CAPABILITY_THREAD_SPAWN: _ClassVar[Capability]
    CAPABILITY_SIGNAL_HANDLE: _ClassVar[Capability]
CAPABILITY_NONE: Capability
CAPABILITY_UI_RENDER: Capability
CAPABILITY_TEMP_FILES: Capability
CAPABILITY_IPC_SETUP: Capability
CAPABILITY_CACHE_INIT: Capability
CAPABILITY_CONFIG_LOAD: Capability
CAPABILITY_MEMORY_MAP: Capability
CAPABILITY_THREAD_SPAWN: Capability
CAPABILITY_SIGNAL_HANDLE: Capability

class SPASystemConfig(_message.Message):
    __slots__ = ("enabled", "pvp_slot", "pvp_timeout_ms", "pvp_max_memory", "pvp_capabilities", "boundary", "sandbox", "targets")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    PVP_SLOT_FIELD_NUMBER: _ClassVar[int]
    PVP_TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    PVP_MAX_MEMORY_FIELD_NUMBER: _ClassVar[int]
    PVP_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    pvp_slot: int
    pvp_timeout_ms: int
    pvp_max_memory: int
    pvp_capabilities: _containers.RepeatedScalarFieldContainer[Capability]
    boundary: BoundaryConfig
    sandbox: SandboxConfig
    targets: PerformanceTargets
    def __init__(self, enabled: bool = ..., pvp_slot: _Optional[int] = ..., pvp_timeout_ms: _Optional[int] = ..., pvp_max_memory: _Optional[int] = ..., pvp_capabilities: _Optional[_Iterable[_Union[Capability, str]]] = ..., boundary: _Optional[_Union[BoundaryConfig, _Mapping]] = ..., sandbox: _Optional[_Union[SandboxConfig, _Mapping]] = ..., targets: _Optional[_Union[PerformanceTargets, _Mapping]] = ...) -> None: ...

class BoundaryConfig(_message.Message):
    __slots__ = ("type", "timeout_ms", "ipc")
    class BoundaryType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        BOUNDARY_SYNCHRONOUS: _ClassVar[BoundaryConfig.BoundaryType]
        BOUNDARY_ASYNC: _ClassVar[BoundaryConfig.BoundaryType]
        BOUNDARY_POLLING: _ClassVar[BoundaryConfig.BoundaryType]
    BOUNDARY_SYNCHRONOUS: BoundaryConfig.BoundaryType
    BOUNDARY_ASYNC: BoundaryConfig.BoundaryType
    BOUNDARY_POLLING: BoundaryConfig.BoundaryType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    IPC_FIELD_NUMBER: _ClassVar[int]
    type: BoundaryConfig.BoundaryType
    timeout_ms: int
    ipc: IPCConfig
    def __init__(self, type: _Optional[_Union[BoundaryConfig.BoundaryType, str]] = ..., timeout_ms: _Optional[int] = ..., ipc: _Optional[_Union[IPCConfig, _Mapping]] = ...) -> None: ...

class IPCConfig(_message.Message):
    __slots__ = ("type", "path", "buffer_size", "bidirectional")
    class IPCType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        IPC_SHARED_MEMORY: _ClassVar[IPCConfig.IPCType]
        IPC_UNIX_SOCKET: _ClassVar[IPCConfig.IPCType]
        IPC_NAMED_PIPE: _ClassVar[IPCConfig.IPCType]
        IPC_SEMAPHORE: _ClassVar[IPCConfig.IPCType]
        IPC_EVENTFD: _ClassVar[IPCConfig.IPCType]
        IPC_MACH_PORT: _ClassVar[IPCConfig.IPCType]
    IPC_SHARED_MEMORY: IPCConfig.IPCType
    IPC_UNIX_SOCKET: IPCConfig.IPCType
    IPC_NAMED_PIPE: IPCConfig.IPCType
    IPC_SEMAPHORE: IPCConfig.IPCType
    IPC_EVENTFD: IPCConfig.IPCType
    IPC_MACH_PORT: IPCConfig.IPCType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    BUFFER_SIZE_FIELD_NUMBER: _ClassVar[int]
    BIDIRECTIONAL_FIELD_NUMBER: _ClassVar[int]
    type: IPCConfig.IPCType
    path: str
    buffer_size: int
    bidirectional: bool
    def __init__(self, type: _Optional[_Union[IPCConfig.IPCType, str]] = ..., path: _Optional[str] = ..., buffer_size: _Optional[int] = ..., bidirectional: bool = ...) -> None: ...

class SandboxConfig(_message.Message):
    __slots__ = ("type", "allowed_syscalls", "blocked_syscalls", "limits", "fs")
    class SandboxType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SANDBOX_NONE: _ClassVar[SandboxConfig.SandboxType]
        SANDBOX_SECCOMP: _ClassVar[SandboxConfig.SandboxType]
        SANDBOX_NAMESPACE: _ClassVar[SandboxConfig.SandboxType]
        SANDBOX_APPCONTAINER: _ClassVar[SandboxConfig.SandboxType]
        SANDBOX_MAC_SANDBOX: _ClassVar[SandboxConfig.SandboxType]
        SANDBOX_PLEDGE: _ClassVar[SandboxConfig.SandboxType]
        SANDBOX_CAPSICUM: _ClassVar[SandboxConfig.SandboxType]
    SANDBOX_NONE: SandboxConfig.SandboxType
    SANDBOX_SECCOMP: SandboxConfig.SandboxType
    SANDBOX_NAMESPACE: SandboxConfig.SandboxType
    SANDBOX_APPCONTAINER: SandboxConfig.SandboxType
    SANDBOX_MAC_SANDBOX: SandboxConfig.SandboxType
    SANDBOX_PLEDGE: SandboxConfig.SandboxType
    SANDBOX_CAPSICUM: SandboxConfig.SandboxType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_SYSCALLS_FIELD_NUMBER: _ClassVar[int]
    BLOCKED_SYSCALLS_FIELD_NUMBER: _ClassVar[int]
    LIMITS_FIELD_NUMBER: _ClassVar[int]
    FS_FIELD_NUMBER: _ClassVar[int]
    type: SandboxConfig.SandboxType
    allowed_syscalls: _containers.RepeatedScalarFieldContainer[str]
    blocked_syscalls: _containers.RepeatedScalarFieldContainer[str]
    limits: ResourceLimits
    fs: FilesystemRestrictions
    def __init__(self, type: _Optional[_Union[SandboxConfig.SandboxType, str]] = ..., allowed_syscalls: _Optional[_Iterable[str]] = ..., blocked_syscalls: _Optional[_Iterable[str]] = ..., limits: _Optional[_Union[ResourceLimits, _Mapping]] = ..., fs: _Optional[_Union[FilesystemRestrictions, _Mapping]] = ...) -> None: ...

class ResourceLimits(_message.Message):
    __slots__ = ("memory_bytes", "cpu_percent", "file_handles", "threads", "processes", "disk_bytes", "network_connections")
    MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    CPU_PERCENT_FIELD_NUMBER: _ClassVar[int]
    FILE_HANDLES_FIELD_NUMBER: _ClassVar[int]
    THREADS_FIELD_NUMBER: _ClassVar[int]
    PROCESSES_FIELD_NUMBER: _ClassVar[int]
    DISK_BYTES_FIELD_NUMBER: _ClassVar[int]
    NETWORK_CONNECTIONS_FIELD_NUMBER: _ClassVar[int]
    memory_bytes: int
    cpu_percent: int
    file_handles: int
    threads: int
    processes: int
    disk_bytes: int
    network_connections: int
    def __init__(self, memory_bytes: _Optional[int] = ..., cpu_percent: _Optional[int] = ..., file_handles: _Optional[int] = ..., threads: _Optional[int] = ..., processes: _Optional[int] = ..., disk_bytes: _Optional[int] = ..., network_connections: _Optional[int] = ...) -> None: ...

class FilesystemRestrictions(_message.Message):
    __slots__ = ("allowed_paths", "blocked_paths", "temp_only", "read_only", "temp_prefix")
    ALLOWED_PATHS_FIELD_NUMBER: _ClassVar[int]
    BLOCKED_PATHS_FIELD_NUMBER: _ClassVar[int]
    TEMP_ONLY_FIELD_NUMBER: _ClassVar[int]
    READ_ONLY_FIELD_NUMBER: _ClassVar[int]
    TEMP_PREFIX_FIELD_NUMBER: _ClassVar[int]
    allowed_paths: _containers.RepeatedScalarFieldContainer[str]
    blocked_paths: _containers.RepeatedScalarFieldContainer[str]
    temp_only: bool
    read_only: bool
    temp_prefix: str
    def __init__(self, allowed_paths: _Optional[_Iterable[str]] = ..., blocked_paths: _Optional[_Iterable[str]] = ..., temp_only: bool = ..., read_only: bool = ..., temp_prefix: _Optional[str] = ...) -> None: ...

class PerformanceTargets(_message.Message):
    __slots__ = ("time_to_first_pixel_ms", "verification_duration_ms", "boundary_wait_ms", "total_startup_ms")
    TIME_TO_FIRST_PIXEL_MS_FIELD_NUMBER: _ClassVar[int]
    VERIFICATION_DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    BOUNDARY_WAIT_MS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_STARTUP_MS_FIELD_NUMBER: _ClassVar[int]
    time_to_first_pixel_ms: int
    verification_duration_ms: int
    boundary_wait_ms: int
    total_startup_ms: int
    def __init__(self, time_to_first_pixel_ms: _Optional[int] = ..., verification_duration_ms: _Optional[int] = ..., boundary_wait_ms: _Optional[int] = ..., total_startup_ms: _Optional[int] = ...) -> None: ...

class VerificationState(_message.Message):
    __slots__ = ("magic", "version", "state", "error_code", "metadata_hash", "timestamp")
    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        STATE_PENDING: _ClassVar[VerificationState.State]
        STATE_VERIFIED: _ClassVar[VerificationState.State]
        STATE_FAILED: _ClassVar[VerificationState.State]
    STATE_PENDING: VerificationState.State
    STATE_VERIFIED: VerificationState.State
    STATE_FAILED: VerificationState.State
    MAGIC_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    METADATA_HASH_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    magic: int
    version: int
    state: VerificationState.State
    error_code: int
    metadata_hash: bytes
    timestamp: int
    def __init__(self, magic: _Optional[int] = ..., version: _Optional[int] = ..., state: _Optional[_Union[VerificationState.State, str]] = ..., error_code: _Optional[int] = ..., metadata_hash: _Optional[bytes] = ..., timestamp: _Optional[int] = ...) -> None: ...

class HandshakeMessage(_message.Message):
    __slots__ = ("type", "pid", "nonce", "hash", "error")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TYPE_READY: _ClassVar[HandshakeMessage.Type]
        TYPE_ACK: _ClassVar[HandshakeMessage.Type]
        TYPE_AT_BOUNDARY: _ClassVar[HandshakeMessage.Type]
        TYPE_VERIFIED: _ClassVar[HandshakeMessage.Type]
        TYPE_FAILED: _ClassVar[HandshakeMessage.Type]
        TYPE_PROCEEDING: _ClassVar[HandshakeMessage.Type]
        TYPE_TERMINATING: _ClassVar[HandshakeMessage.Type]
    TYPE_READY: HandshakeMessage.Type
    TYPE_ACK: HandshakeMessage.Type
    TYPE_AT_BOUNDARY: HandshakeMessage.Type
    TYPE_VERIFIED: HandshakeMessage.Type
    TYPE_FAILED: HandshakeMessage.Type
    TYPE_PROCEEDING: HandshakeMessage.Type
    TYPE_TERMINATING: HandshakeMessage.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PID_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    type: HandshakeMessage.Type
    pid: int
    nonce: int
    hash: bytes
    error: int
    def __init__(self, type: _Optional[_Union[HandshakeMessage.Type, str]] = ..., pid: _Optional[int] = ..., nonce: _Optional[int] = ..., hash: _Optional[bytes] = ..., error: _Optional[int] = ...) -> None: ...

class FailureHandling(_message.Message):
    __slots__ = ("actions", "graceful_degradation")
    class FailureMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        FAILURE_PVP_TIMEOUT: _ClassVar[FailureHandling.FailureMode]
        FAILURE_PVP_CRASH: _ClassVar[FailureHandling.FailureMode]
        FAILURE_VERIFY_FAIL: _ClassVar[FailureHandling.FailureMode]
        FAILURE_SANDBOX_BREACH: _ClassVar[FailureHandling.FailureMode]
        FAILURE_RESOURCE_EXCEED: _ClassVar[FailureHandling.FailureMode]
    FAILURE_PVP_TIMEOUT: FailureHandling.FailureMode
    FAILURE_PVP_CRASH: FailureHandling.FailureMode
    FAILURE_VERIFY_FAIL: FailureHandling.FailureMode
    FAILURE_SANDBOX_BREACH: FailureHandling.FailureMode
    FAILURE_RESOURCE_EXCEED: FailureHandling.FailureMode
    class FailureAction(_message.Message):
        __slots__ = ("mode", "action", "log_details", "cleanup_resources")
        class Action(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ACTION_KILL_PVP: _ClassVar[FailureHandling.FailureAction.Action]
            ACTION_CONTINUE: _ClassVar[FailureHandling.FailureAction.Action]
            ACTION_TERMINATE: _ClassVar[FailureHandling.FailureAction.Action]
            ACTION_RETRY: _ClassVar[FailureHandling.FailureAction.Action]
        ACTION_KILL_PVP: FailureHandling.FailureAction.Action
        ACTION_CONTINUE: FailureHandling.FailureAction.Action
        ACTION_TERMINATE: FailureHandling.FailureAction.Action
        ACTION_RETRY: FailureHandling.FailureAction.Action
        MODE_FIELD_NUMBER: _ClassVar[int]
        ACTION_FIELD_NUMBER: _ClassVar[int]
        LOG_DETAILS_FIELD_NUMBER: _ClassVar[int]
        CLEANUP_RESOURCES_FIELD_NUMBER: _ClassVar[int]
        mode: FailureHandling.FailureMode
        action: FailureHandling.FailureAction.Action
        log_details: bool
        cleanup_resources: bool
        def __init__(self, mode: _Optional[_Union[FailureHandling.FailureMode, str]] = ..., action: _Optional[_Union[FailureHandling.FailureAction.Action, str]] = ..., log_details: bool = ..., cleanup_resources: bool = ...) -> None: ...
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    GRACEFUL_DEGRADATION_FIELD_NUMBER: _ClassVar[int]
    actions: _containers.RepeatedCompositeFieldContainer[FailureHandling.FailureAction]
    graceful_degradation: bool
    def __init__(self, actions: _Optional[_Iterable[_Union[FailureHandling.FailureAction, _Mapping]]] = ..., graceful_degradation: bool = ...) -> None: ...

class PlatformImplementation(_message.Message):
    __slots__ = ("platform", "sandbox", "ipc", "required_features", "min_version")
    class Platform(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        PLATFORM_LINUX: _ClassVar[PlatformImplementation.Platform]
        PLATFORM_MACOS: _ClassVar[PlatformImplementation.Platform]
        PLATFORM_WINDOWS: _ClassVar[PlatformImplementation.Platform]
        PLATFORM_BSD: _ClassVar[PlatformImplementation.Platform]
    PLATFORM_LINUX: PlatformImplementation.Platform
    PLATFORM_MACOS: PlatformImplementation.Platform
    PLATFORM_WINDOWS: PlatformImplementation.Platform
    PLATFORM_BSD: PlatformImplementation.Platform
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    SANDBOX_FIELD_NUMBER: _ClassVar[int]
    IPC_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FEATURES_FIELD_NUMBER: _ClassVar[int]
    MIN_VERSION_FIELD_NUMBER: _ClassVar[int]
    platform: PlatformImplementation.Platform
    sandbox: SandboxConfig.SandboxType
    ipc: IPCConfig.IPCType
    required_features: _containers.RepeatedScalarFieldContainer[str]
    min_version: str
    def __init__(self, platform: _Optional[_Union[PlatformImplementation.Platform, str]] = ..., sandbox: _Optional[_Union[SandboxConfig.SandboxType, str]] = ..., ipc: _Optional[_Union[IPCConfig.IPCType, str]] = ..., required_features: _Optional[_Iterable[str]] = ..., min_version: _Optional[str] = ...) -> None: ...
