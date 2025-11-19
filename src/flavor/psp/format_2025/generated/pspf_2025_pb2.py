# 
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Generated protocol buffer code."""

from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    6,
    31,
    1,
    '',
    'pspf_2025.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from .modules import operations_pb2 as modules_dot_operations__pb2
from .modules import slots_pb2 as modules_dot_slots__pb2
from .modules import index_pb2 as modules_dot_index__pb2
from .modules import metadata_pb2 as modules_dot_metadata__pb2
from .modules import crypto_pb2 as modules_dot_crypto__pb2
from .modules import jit_pb2 as modules_dot_jit__pb2
from .modules import spa_pb2 as modules_dot_spa__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0fpspf_2025.proto\x12\tpspf_2025\x1a\x18modules/operations.proto\x1a\x13modules/slots.proto\x1a\x13modules/index.proto\x1a\x16modules/metadata.proto\x1a\x14modules/crypto.proto\x1a\x11modules/jit.proto\x1a\x11modules/spa.proto\"\xf1\x02\n\x0bPSPFPackage\x12*\n\x05index\x18\x01 \x01(\x0b\x32\x1b.pspf_2025.index.IndexBlock\x12\x35\n\x08metadata\x18\x02 \x01(\x0b\x32#.pspf_2025.metadata.PackageMetadata\x12)\n\x05slots\x18\x03 \x03(\x0b\x32\x1a.pspf_2025.slots.SlotEntry\x12,\n\x06\x63rypto\x18\x04 \x01(\x0b\x32\x1c.pspf_2025.crypto.CryptoInfo\x12>\n\x10operation_chains\x18\x05 \x03(\x0b\x32$.pspf_2025.operations.OperationChain\x12\x32\n\njit_config\x18\x06 \x01(\x0b\x32\x1e.pspf_2025.jit.JITSystemConfig\x12\x32\n\nspa_config\x18\x07 \x01(\x0b\x32\x1e.pspf_2025.spa.SPASystemConfigB[\n\x1eio.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pspf_2025_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\036io.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025'
  _globals['_PSPFPACKAGE']._serialized_start=183
  _globals['_PSPFPACKAGE']._serialized_end=552
# @@protoc_insertion_point(module_scope)

# 🌶️📦🔚
