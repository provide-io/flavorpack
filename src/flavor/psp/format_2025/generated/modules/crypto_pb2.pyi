from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SignatureAlgorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SIGNATURE_NONE: _ClassVar[SignatureAlgorithm]
    SIGNATURE_ED25519: _ClassVar[SignatureAlgorithm]
    SIGNATURE_RSA4096: _ClassVar[SignatureAlgorithm]
    SIGNATURE_ECDSA_P256: _ClassVar[SignatureAlgorithm]

class KeyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    KEY_TYPE_SIGNING: _ClassVar[KeyType]
    KEY_TYPE_ENCRYPTION: _ClassVar[KeyType]
    KEY_TYPE_VERIFICATION: _ClassVar[KeyType]

class KeyUsage(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    KEY_USAGE_NONE: _ClassVar[KeyUsage]
    KEY_USAGE_SIGN: _ClassVar[KeyUsage]
    KEY_USAGE_VERIFY: _ClassVar[KeyUsage]
    KEY_USAGE_ENCRYPT: _ClassVar[KeyUsage]
    KEY_USAGE_DECRYPT: _ClassVar[KeyUsage]

class ChecksumAlgorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CHECKSUM_ADLER32: _ClassVar[ChecksumAlgorithm]
    CHECKSUM_CRC32: _ClassVar[ChecksumAlgorithm]
    CHECKSUM_SHA256: _ClassVar[ChecksumAlgorithm]
    CHECKSUM_XXHASH: _ClassVar[ChecksumAlgorithm]
    CHECKSUM_BLAKE3: _ClassVar[ChecksumAlgorithm]

class TrustLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRUST_NONE: _ClassVar[TrustLevel]
    TRUST_SELF_SIGNED: _ClassVar[TrustLevel]
    TRUST_ORGANIZATION: _ClassVar[TrustLevel]
    TRUST_CA: _ClassVar[TrustLevel]
    TRUST_ROOT: _ClassVar[TrustLevel]

class EncryptionAlgorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ENCRYPTION_NONE: _ClassVar[EncryptionAlgorithm]
    ENCRYPTION_AES256_GCM: _ClassVar[EncryptionAlgorithm]
    ENCRYPTION_CHACHA20_POLY1305: _ClassVar[EncryptionAlgorithm]
    ENCRYPTION_AES256_CBC: _ClassVar[EncryptionAlgorithm]
SIGNATURE_NONE: SignatureAlgorithm
SIGNATURE_ED25519: SignatureAlgorithm
SIGNATURE_RSA4096: SignatureAlgorithm
SIGNATURE_ECDSA_P256: SignatureAlgorithm
KEY_TYPE_SIGNING: KeyType
KEY_TYPE_ENCRYPTION: KeyType
KEY_TYPE_VERIFICATION: KeyType
KEY_USAGE_NONE: KeyUsage
KEY_USAGE_SIGN: KeyUsage
KEY_USAGE_VERIFY: KeyUsage
KEY_USAGE_ENCRYPT: KeyUsage
KEY_USAGE_DECRYPT: KeyUsage
CHECKSUM_ADLER32: ChecksumAlgorithm
CHECKSUM_CRC32: ChecksumAlgorithm
CHECKSUM_SHA256: ChecksumAlgorithm
CHECKSUM_XXHASH: ChecksumAlgorithm
CHECKSUM_BLAKE3: ChecksumAlgorithm
TRUST_NONE: TrustLevel
TRUST_SELF_SIGNED: TrustLevel
TRUST_ORGANIZATION: TrustLevel
TRUST_CA: TrustLevel
TRUST_ROOT: TrustLevel
ENCRYPTION_NONE: EncryptionAlgorithm
ENCRYPTION_AES256_GCM: EncryptionAlgorithm
ENCRYPTION_CHACHA20_POLY1305: EncryptionAlgorithm
ENCRYPTION_AES256_CBC: EncryptionAlgorithm

class CryptoInfo(_message.Message):
    __slots__ = ("signature", "keys", "integrity", "trust", "encryption")
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    KEYS_FIELD_NUMBER: _ClassVar[int]
    INTEGRITY_FIELD_NUMBER: _ClassVar[int]
    TRUST_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTION_FIELD_NUMBER: _ClassVar[int]
    signature: SignatureInfo
    keys: _containers.RepeatedCompositeFieldContainer[KeyInfo]
    integrity: _containers.RepeatedCompositeFieldContainer[IntegrityCheck]
    trust: TrustChain
    encryption: EncryptionSettings
    def __init__(self, signature: _Optional[_Union[SignatureInfo, _Mapping]] = ..., keys: _Optional[_Iterable[_Union[KeyInfo, _Mapping]]] = ..., integrity: _Optional[_Iterable[_Union[IntegrityCheck, _Mapping]]] = ..., trust: _Optional[_Union[TrustChain, _Mapping]] = ..., encryption: _Optional[_Union[EncryptionSettings, _Mapping]] = ...) -> None: ...

class SignatureInfo(_message.Message):
    __slots__ = ("algorithm", "public_key", "signature", "timestamp", "key_id", "metadata_hash")
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    METADATA_HASH_FIELD_NUMBER: _ClassVar[int]
    algorithm: SignatureAlgorithm
    public_key: bytes
    signature: bytes
    timestamp: int
    key_id: str
    metadata_hash: bytes
    def __init__(self, algorithm: _Optional[_Union[SignatureAlgorithm, str]] = ..., public_key: _Optional[bytes] = ..., signature: _Optional[bytes] = ..., timestamp: _Optional[int] = ..., key_id: _Optional[str] = ..., metadata_hash: _Optional[bytes] = ...) -> None: ...

class KeyInfo(_message.Message):
    __slots__ = ("key_id", "key_type", "usage", "public_key", "created_at", "expires_at", "algorithm", "key_size")
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    KEY_SIZE_FIELD_NUMBER: _ClassVar[int]
    key_id: str
    key_type: KeyType
    usage: KeyUsage
    public_key: bytes
    created_at: int
    expires_at: int
    algorithm: str
    key_size: int
    def __init__(self, key_id: _Optional[str] = ..., key_type: _Optional[_Union[KeyType, str]] = ..., usage: _Optional[_Union[KeyUsage, str]] = ..., public_key: _Optional[bytes] = ..., created_at: _Optional[int] = ..., expires_at: _Optional[int] = ..., algorithm: _Optional[str] = ..., key_size: _Optional[int] = ...) -> None: ...

class IntegrityCheck(_message.Message):
    __slots__ = ("algorithm", "checksum", "data_size", "scope", "slot_id")
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    DATA_SIZE_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    SLOT_ID_FIELD_NUMBER: _ClassVar[int]
    algorithm: ChecksumAlgorithm
    checksum: bytes
    data_size: int
    scope: str
    slot_id: int
    def __init__(self, algorithm: _Optional[_Union[ChecksumAlgorithm, str]] = ..., checksum: _Optional[bytes] = ..., data_size: _Optional[int] = ..., scope: _Optional[str] = ..., slot_id: _Optional[int] = ...) -> None: ...

class TrustChain(_message.Message):
    __slots__ = ("certificates", "anchors", "validation_time", "level")
    CERTIFICATES_FIELD_NUMBER: _ClassVar[int]
    ANCHORS_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_TIME_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    certificates: _containers.RepeatedCompositeFieldContainer[Certificate]
    anchors: _containers.RepeatedCompositeFieldContainer[TrustAnchor]
    validation_time: str
    level: TrustLevel
    def __init__(self, certificates: _Optional[_Iterable[_Union[Certificate, _Mapping]]] = ..., anchors: _Optional[_Iterable[_Union[TrustAnchor, _Mapping]]] = ..., validation_time: _Optional[str] = ..., level: _Optional[_Union[TrustLevel, str]] = ...) -> None: ...

class Certificate(_message.Message):
    __slots__ = ("certificate", "issuer", "subject", "not_before", "not_after", "serial_number", "fingerprint")
    CERTIFICATE_FIELD_NUMBER: _ClassVar[int]
    ISSUER_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    NOT_BEFORE_FIELD_NUMBER: _ClassVar[int]
    NOT_AFTER_FIELD_NUMBER: _ClassVar[int]
    SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    FINGERPRINT_FIELD_NUMBER: _ClassVar[int]
    certificate: bytes
    issuer: str
    subject: str
    not_before: int
    not_after: int
    serial_number: str
    fingerprint: bytes
    def __init__(self, certificate: _Optional[bytes] = ..., issuer: _Optional[str] = ..., subject: _Optional[str] = ..., not_before: _Optional[int] = ..., not_after: _Optional[int] = ..., serial_number: _Optional[str] = ..., fingerprint: _Optional[bytes] = ...) -> None: ...

class TrustAnchor(_message.Message):
    __slots__ = ("name", "public_key", "algorithm", "created_at")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    name: str
    public_key: bytes
    algorithm: str
    created_at: int
    def __init__(self, name: _Optional[str] = ..., public_key: _Optional[bytes] = ..., algorithm: _Optional[str] = ..., created_at: _Optional[int] = ...) -> None: ...

class EncryptionSettings(_message.Message):
    __slots__ = ("encrypted", "algorithm", "key_id", "salt", "iteration_count", "encrypted_slots")
    ENCRYPTED_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SALT_FIELD_NUMBER: _ClassVar[int]
    ITERATION_COUNT_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTED_SLOTS_FIELD_NUMBER: _ClassVar[int]
    encrypted: bool
    algorithm: EncryptionAlgorithm
    key_id: bytes
    salt: bytes
    iteration_count: int
    encrypted_slots: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, encrypted: bool = ..., algorithm: _Optional[_Union[EncryptionAlgorithm, str]] = ..., key_id: _Optional[bytes] = ..., salt: _Optional[bytes] = ..., iteration_count: _Optional[int] = ..., encrypted_slots: _Optional[_Iterable[int]] = ...) -> None: ...
