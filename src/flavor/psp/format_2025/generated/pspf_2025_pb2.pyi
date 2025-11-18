from modules import operations_pb2 as _operations_pb2
from modules import slots_pb2 as _slots_pb2
from modules import index_pb2 as _index_pb2
from modules import metadata_pb2 as _metadata_pb2
from modules import crypto_pb2 as _crypto_pb2
from modules import jit_pb2 as _jit_pb2
from modules import spa_pb2 as _spa_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PSPFPackage(_message.Message):
    __slots__ = ("index", "metadata", "slots", "crypto", "operation_chains", "jit_config", "spa_config")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    CRYPTO_FIELD_NUMBER: _ClassVar[int]
    OPERATION_CHAINS_FIELD_NUMBER: _ClassVar[int]
    JIT_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SPA_CONFIG_FIELD_NUMBER: _ClassVar[int]
    index: _index_pb2.IndexBlock
    metadata: _metadata_pb2.PackageMetadata
    slots: _containers.RepeatedCompositeFieldContainer[_slots_pb2.SlotEntry]
    crypto: _crypto_pb2.CryptoInfo
    operation_chains: _containers.RepeatedCompositeFieldContainer[_operations_pb2.OperationChain]
    jit_config: _jit_pb2.JITSystemConfig
    spa_config: _spa_pb2.SPASystemConfig
    def __init__(self, index: _Optional[_Union[_index_pb2.IndexBlock, _Mapping]] = ..., metadata: _Optional[_Union[_metadata_pb2.PackageMetadata, _Mapping]] = ..., slots: _Optional[_Iterable[_Union[_slots_pb2.SlotEntry, _Mapping]]] = ..., crypto: _Optional[_Union[_crypto_pb2.CryptoInfo, _Mapping]] = ..., operation_chains: _Optional[_Iterable[_Union[_operations_pb2.OperationChain, _Mapping]]] = ..., jit_config: _Optional[_Union[_jit_pb2.JITSystemConfig, _Mapping]] = ..., spa_config: _Optional[_Union[_spa_pb2.SPASystemConfig, _Mapping]] = ...) -> None: ...
