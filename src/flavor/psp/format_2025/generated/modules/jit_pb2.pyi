from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Strategy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STRATEGY_LAZY: _ClassVar[Strategy]
    STRATEGY_AGGRESSIVE: _ClassVar[Strategy]
    STRATEGY_BALANCED: _ClassVar[Strategy]
    STRATEGY_MINIMAL: _ClassVar[Strategy]
    STRATEGY_PREDICTIVE: _ClassVar[Strategy]
STRATEGY_LAZY: Strategy
STRATEGY_AGGRESSIVE: Strategy
STRATEGY_BALANCED: Strategy
STRATEGY_MINIMAL: Strategy
STRATEGY_PREDICTIVE: Strategy

class JITSystemConfig(_message.Message):
    __slots__ = ("enabled", "strategy", "cache_dir", "max_cache_size", "network_timeout_ms", "background_slots", "prefetch", "network", "cache")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    CACHE_DIR_FIELD_NUMBER: _ClassVar[int]
    MAX_CACHE_SIZE_FIELD_NUMBER: _ClassVar[int]
    NETWORK_TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    BACKGROUND_SLOTS_FIELD_NUMBER: _ClassVar[int]
    PREFETCH_FIELD_NUMBER: _ClassVar[int]
    NETWORK_FIELD_NUMBER: _ClassVar[int]
    CACHE_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    strategy: Strategy
    cache_dir: str
    max_cache_size: int
    network_timeout_ms: int
    background_slots: _containers.RepeatedScalarFieldContainer[int]
    prefetch: PrefetchConfig
    network: NetworkConfig
    cache: CacheConfig
    def __init__(self, enabled: bool = ..., strategy: _Optional[_Union[Strategy, str]] = ..., cache_dir: _Optional[str] = ..., max_cache_size: _Optional[int] = ..., network_timeout_ms: _Optional[int] = ..., background_slots: _Optional[_Iterable[int]] = ..., prefetch: _Optional[_Union[PrefetchConfig, _Mapping]] = ..., network: _Optional[_Union[NetworkConfig, _Mapping]] = ..., cache: _Optional[_Union[CacheConfig, _Mapping]] = ...) -> None: ...

class PrefetchConfig(_message.Message):
    __slots__ = ("enabled", "patterns", "max_concurrent", "buffer_size", "priority_slots")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    PATTERNS_FIELD_NUMBER: _ClassVar[int]
    MAX_CONCURRENT_FIELD_NUMBER: _ClassVar[int]
    BUFFER_SIZE_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_SLOTS_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    patterns: _containers.RepeatedScalarFieldContainer[str]
    max_concurrent: int
    buffer_size: int
    priority_slots: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, enabled: bool = ..., patterns: _Optional[_Iterable[str]] = ..., max_concurrent: _Optional[int] = ..., buffer_size: _Optional[int] = ..., priority_slots: _Optional[_Iterable[int]] = ...) -> None: ...

class NetworkConfig(_message.Message):
    __slots__ = ("type", "endpoint", "use_tls", "certificate_pin", "auth", "retry", "compression")
    class SourceType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SOURCE_HTTP: _ClassVar[NetworkConfig.SourceType]
        SOURCE_GRPC: _ClassVar[NetworkConfig.SourceType]
        SOURCE_S3: _ClassVar[NetworkConfig.SourceType]
        SOURCE_WEBDAV: _ClassVar[NetworkConfig.SourceType]
        SOURCE_CUSTOM: _ClassVar[NetworkConfig.SourceType]
    SOURCE_HTTP: NetworkConfig.SourceType
    SOURCE_GRPC: NetworkConfig.SourceType
    SOURCE_S3: NetworkConfig.SourceType
    SOURCE_WEBDAV: NetworkConfig.SourceType
    SOURCE_CUSTOM: NetworkConfig.SourceType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    USE_TLS_FIELD_NUMBER: _ClassVar[int]
    CERTIFICATE_PIN_FIELD_NUMBER: _ClassVar[int]
    AUTH_FIELD_NUMBER: _ClassVar[int]
    RETRY_FIELD_NUMBER: _ClassVar[int]
    COMPRESSION_FIELD_NUMBER: _ClassVar[int]
    type: NetworkConfig.SourceType
    endpoint: str
    use_tls: bool
    certificate_pin: str
    auth: AuthConfig
    retry: RetryConfig
    compression: CompressionConfig
    def __init__(self, type: _Optional[_Union[NetworkConfig.SourceType, str]] = ..., endpoint: _Optional[str] = ..., use_tls: bool = ..., certificate_pin: _Optional[str] = ..., auth: _Optional[_Union[AuthConfig, _Mapping]] = ..., retry: _Optional[_Union[RetryConfig, _Mapping]] = ..., compression: _Optional[_Union[CompressionConfig, _Mapping]] = ...) -> None: ...

class AuthConfig(_message.Message):
    __slots__ = ("type", "token", "username", "password", "client_cert", "client_key")
    class AuthType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        AUTH_NONE: _ClassVar[AuthConfig.AuthType]
        AUTH_BEARER: _ClassVar[AuthConfig.AuthType]
        AUTH_BASIC: _ClassVar[AuthConfig.AuthType]
        AUTH_CUSTOM: _ClassVar[AuthConfig.AuthType]
        AUTH_MTLS: _ClassVar[AuthConfig.AuthType]
    AUTH_NONE: AuthConfig.AuthType
    AUTH_BEARER: AuthConfig.AuthType
    AUTH_BASIC: AuthConfig.AuthType
    AUTH_CUSTOM: AuthConfig.AuthType
    AUTH_MTLS: AuthConfig.AuthType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    CLIENT_CERT_FIELD_NUMBER: _ClassVar[int]
    CLIENT_KEY_FIELD_NUMBER: _ClassVar[int]
    type: AuthConfig.AuthType
    token: str
    username: str
    password: str
    client_cert: bytes
    client_key: bytes
    def __init__(self, type: _Optional[_Union[AuthConfig.AuthType, str]] = ..., token: _Optional[str] = ..., username: _Optional[str] = ..., password: _Optional[str] = ..., client_cert: _Optional[bytes] = ..., client_key: _Optional[bytes] = ...) -> None: ...

class RetryConfig(_message.Message):
    __slots__ = ("max_attempts", "backoff_ms", "exponential_backoff", "max_backoff_ms")
    MAX_ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    BACKOFF_MS_FIELD_NUMBER: _ClassVar[int]
    EXPONENTIAL_BACKOFF_FIELD_NUMBER: _ClassVar[int]
    MAX_BACKOFF_MS_FIELD_NUMBER: _ClassVar[int]
    max_attempts: int
    backoff_ms: _containers.RepeatedScalarFieldContainer[int]
    exponential_backoff: bool
    max_backoff_ms: int
    def __init__(self, max_attempts: _Optional[int] = ..., backoff_ms: _Optional[_Iterable[int]] = ..., exponential_backoff: bool = ..., max_backoff_ms: _Optional[int] = ...) -> None: ...

class CompressionConfig(_message.Message):
    __slots__ = ("type", "level")
    class CompressionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        COMPRESSION_NONE: _ClassVar[CompressionConfig.CompressionType]
        COMPRESSION_GZIP: _ClassVar[CompressionConfig.CompressionType]
        COMPRESSION_BROTLI: _ClassVar[CompressionConfig.CompressionType]
        COMPRESSION_ZSTD: _ClassVar[CompressionConfig.CompressionType]
        COMPRESSION_SNAPPY: _ClassVar[CompressionConfig.CompressionType]
        COMPRESSION_LZ4: _ClassVar[CompressionConfig.CompressionType]
    COMPRESSION_NONE: CompressionConfig.CompressionType
    COMPRESSION_GZIP: CompressionConfig.CompressionType
    COMPRESSION_BROTLI: CompressionConfig.CompressionType
    COMPRESSION_ZSTD: CompressionConfig.CompressionType
    COMPRESSION_SNAPPY: CompressionConfig.CompressionType
    COMPRESSION_LZ4: CompressionConfig.CompressionType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    type: CompressionConfig.CompressionType
    level: int
    def __init__(self, type: _Optional[_Union[CompressionConfig.CompressionType, str]] = ..., level: _Optional[int] = ...) -> None: ...

class CacheConfig(_message.Message):
    __slots__ = ("strategy", "ttl_seconds", "max_size", "verify_on_access", "cleanup_interval", "validation")
    class CacheStrategy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CACHE_PERSISTENT: _ClassVar[CacheConfig.CacheStrategy]
        CACHE_TEMPORAL: _ClassVar[CacheConfig.CacheStrategy]
        CACHE_SIZE_BOUND: _ClassVar[CacheConfig.CacheStrategy]
        CACHE_VERSIONED: _ClassVar[CacheConfig.CacheStrategy]
    CACHE_PERSISTENT: CacheConfig.CacheStrategy
    CACHE_TEMPORAL: CacheConfig.CacheStrategy
    CACHE_SIZE_BOUND: CacheConfig.CacheStrategy
    CACHE_VERSIONED: CacheConfig.CacheStrategy
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    TTL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    MAX_SIZE_FIELD_NUMBER: _ClassVar[int]
    VERIFY_ON_ACCESS_FIELD_NUMBER: _ClassVar[int]
    CLEANUP_INTERVAL_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_FIELD_NUMBER: _ClassVar[int]
    strategy: CacheConfig.CacheStrategy
    ttl_seconds: int
    max_size: int
    verify_on_access: bool
    cleanup_interval: int
    validation: ValidationConfig
    def __init__(self, strategy: _Optional[_Union[CacheConfig.CacheStrategy, str]] = ..., ttl_seconds: _Optional[int] = ..., max_size: _Optional[int] = ..., verify_on_access: bool = ..., cleanup_interval: _Optional[int] = ..., validation: _Optional[_Union[ValidationConfig, _Mapping]] = ...) -> None: ...

class ValidationConfig(_message.Message):
    __slots__ = ("mode", "interval_seconds", "invalidate_on_update")
    class ValidationMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        VALIDATION_QUICK: _ClassVar[ValidationConfig.ValidationMode]
        VALIDATION_PERIODIC: _ClassVar[ValidationConfig.ValidationMode]
        VALIDATION_ON_ERROR: _ClassVar[ValidationConfig.ValidationMode]
        VALIDATION_ALWAYS: _ClassVar[ValidationConfig.ValidationMode]
    VALIDATION_QUICK: ValidationConfig.ValidationMode
    VALIDATION_PERIODIC: ValidationConfig.ValidationMode
    VALIDATION_ON_ERROR: ValidationConfig.ValidationMode
    VALIDATION_ALWAYS: ValidationConfig.ValidationMode
    MODE_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    INVALIDATE_ON_UPDATE_FIELD_NUMBER: _ClassVar[int]
    mode: ValidationConfig.ValidationMode
    interval_seconds: int
    invalidate_on_update: bool
    def __init__(self, mode: _Optional[_Union[ValidationConfig.ValidationMode, str]] = ..., interval_seconds: _Optional[int] = ..., invalidate_on_update: bool = ...) -> None: ...

class SlotRequest(_message.Message):
    __slots__ = ("package_id", "package_version", "slot_id", "auth_token", "offset")
    PACKAGE_ID_FIELD_NUMBER: _ClassVar[int]
    PACKAGE_VERSION_FIELD_NUMBER: _ClassVar[int]
    SLOT_ID_FIELD_NUMBER: _ClassVar[int]
    AUTH_TOKEN_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    package_id: str
    package_version: str
    slot_id: int
    auth_token: str
    offset: int
    def __init__(self, package_id: _Optional[str] = ..., package_version: _Optional[str] = ..., slot_id: _Optional[int] = ..., auth_token: _Optional[str] = ..., offset: _Optional[int] = ...) -> None: ...

class SlotInfo(_message.Message):
    __slots__ = ("slot_id", "size", "checksum", "sha256", "available", "expires_at")
    SLOT_ID_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    slot_id: int
    size: int
    checksum: int
    sha256: bytes
    available: bool
    expires_at: int
    def __init__(self, slot_id: _Optional[int] = ..., size: _Optional[int] = ..., checksum: _Optional[int] = ..., sha256: _Optional[bytes] = ..., available: bool = ..., expires_at: _Optional[int] = ...) -> None: ...

class SlotChunk(_message.Message):
    __slots__ = ("sequence", "data", "checksum", "progress", "is_last")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_FIELD_NUMBER: _ClassVar[int]
    IS_LAST_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    data: bytes
    checksum: int
    progress: float
    is_last: bool
    def __init__(self, sequence: _Optional[int] = ..., data: _Optional[bytes] = ..., checksum: _Optional[int] = ..., progress: _Optional[float] = ..., is_last: bool = ...) -> None: ...

class UpdateRequest(_message.Message):
    __slots__ = ("package_id", "current_version", "slots")
    PACKAGE_ID_FIELD_NUMBER: _ClassVar[int]
    CURRENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    package_id: str
    current_version: str
    slots: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, package_id: _Optional[str] = ..., current_version: _Optional[str] = ..., slots: _Optional[_Iterable[int]] = ...) -> None: ...

class UpdateInfo(_message.Message):
    __slots__ = ("update_available", "new_version", "changed_slots", "total_size", "changelog")
    UPDATE_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    NEW_VERSION_FIELD_NUMBER: _ClassVar[int]
    CHANGED_SLOTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    CHANGELOG_FIELD_NUMBER: _ClassVar[int]
    update_available: bool
    new_version: str
    changed_slots: _containers.RepeatedScalarFieldContainer[int]
    total_size: int
    changelog: str
    def __init__(self, update_available: bool = ..., new_version: _Optional[str] = ..., changed_slots: _Optional[_Iterable[int]] = ..., total_size: _Optional[int] = ..., changelog: _Optional[str] = ...) -> None: ...
