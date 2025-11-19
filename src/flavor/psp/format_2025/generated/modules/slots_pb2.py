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
    'modules/slots.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from . import operations_pb2 as modules_dot_operations__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13modules/slots.proto\x12\x0fpspf_2025.slots\x1a\x18modules/operations.proto\"\x8c\x04\n\tSlotEntry\x12\n\n\x02id\x18\x01 \x01(\r\x12\x11\n\tname_hash\x18\x02 \x01(\x04\x12\x0e\n\x06offset\x18\x03 \x01(\x04\x12\x0c\n\x04size\x18\x04 \x01(\x04\x12\x15\n\roriginal_size\x18\x05 \x01(\x04\x12\x12\n\noperations\x18\x06 \x01(\x04\x12\x10\n\x08\x63hecksum\x18\x07 \x01(\r\x12\x0c\n\x04hash\x18\x08 \x01(\x0c\x12)\n\x07purpose\x18\t \x01(\x0e\x32\x18.pspf_2025.slots.Purpose\x12-\n\tlifecycle\x18\n \x01(\x0e\x32\x1a.pspf_2025.slots.Lifecycle\x12+\n\x08platform\x18\x0b \x01(\x0e\x32\x19.pspf_2025.slots.Platform\x12\x13\n\x0bpermissions\x18\x0c \x01(\r\x12\r\n\x05\x66lags\x18\r \x01(\r\x12\'\n\x03jit\x18\x0e \x01(\x0b\x32\x1a.pspf_2025.slots.JITConfig\x12\x0c\n\x04name\x18\x14 \x01(\t\x12\x13\n\x0bsource_path\x18\x15 \x01(\t\x12\x13\n\x0btarget_path\x18\x16 \x01(\t\x12:\n\x08metadata\x18\x17 \x03(\x0b\x32(.pspf_2025.slots.SlotEntry.MetadataEntry\x1a/\n\rMetadataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\xac\x02\n\tJITConfig\x12\x31\n\x06source\x18\x01 \x01(\x0b\x32!.pspf_2025.slots.JITConfig.Source\x12/\n\x05\x63\x61\x63he\x18\x02 \x01(\x0b\x32 .pspf_2025.slots.JITConfig.Cache\x12\x10\n\x08priority\x18\x03 \x01(\r\x12\x12\n\ntimeout_ms\x18\x04 \x01(\r\x1aU\n\x06Source\x12\x0c\n\x04type\x18\x01 \x01(\t\x12\x10\n\x08\x65ndpoint\x18\x02 \x01(\t\x12\x0c\n\x04path\x18\x03 \x01(\t\x12\x0b\n\x03tls\x18\x04 \x01(\x08\x12\x10\n\x08\x63\x65rt_pin\x18\x05 \x01(\t\x1a>\n\x05\x43\x61\x63he\x12\x10\n\x08strategy\x18\x01 \x01(\t\x12\x0b\n\x03ttl\x18\x02 \x01(\r\x12\x16\n\x0everify_on_load\x18\x03 \x01(\x08\"\x88\x02\n\tSlotTable\x12)\n\x05slots\x18\x01 \x03(\x0b\x32\x1a.pspf_2025.slots.SlotEntry\x12\x12\n\nslot_count\x18\x02 \x01(\r\x12\x12\n\ntotal_size\x18\x03 \x01(\x04\x12\x16\n\x0etable_checksum\x18\x04 \x01(\r\x12\x0f\n\x07version\x18\x05 \x01(\r\x12\x12\n\ncreated_at\x18\x06 \x01(\x04\x12:\n\x08metadata\x18\x07 \x03(\x0b\x32(.pspf_2025.slots.SlotTable.MetadataEntry\x1a/\n\rMetadataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01*\x8c\x03\n\tLifecycle\x12\x12\n\x0eLIFECYCLE_INIT\x10\x00\x12\x13\n\x0fLIFECYCLE_EAGER\x10\x01\x12\x15\n\x11LIFECYCLE_STARTUP\x10\x02\x12\x15\n\x11LIFECYCLE_RUNTIME\x10\x03\x12\x14\n\x10LIFECYCLE_MANUAL\x10\x04\x12\x16\n\x12LIFECYCLE_VOLATILE\x10\x05\x12\x17\n\x13LIFECYCLE_EPHEMERAL\x10\x06\x12\x18\n\x14LIFECYCLE_PERSISTENT\x10\x07\x12\x14\n\x10LIFECYCLE_CACHED\x10\x08\x12\x12\n\x0eLIFECYCLE_LAZY\x10\t\x12\x15\n\x11LIFECYCLE_PRELOAD\x10\n\x12\x17\n\x13LIFECYCLE_JIT_LOCAL\x10\x0b\x12\x19\n\x15LIFECYCLE_JIT_NETWORK\x10\x0c\x12\x18\n\x14LIFECYCLE_JIT_HYBRID\x10\r\x12\x1a\n\x16LIFECYCLE_JIT_OPTIONAL\x10\x0e\x12\x1c\n\x18LIFECYCLE_JIT_BACKGROUND\x10\x0f*\xc0\x02\n\x07Purpose\x12\x10\n\x0cPURPOSE_CODE\x10\x00\x12\x10\n\x0cPURPOSE_DATA\x10\x01\x12\x12\n\x0ePURPOSE_CONFIG\x10\x02\x12\x12\n\x0ePURPOSE_ASSETS\x10\x03\x12\x13\n\x0fPURPOSE_RUNTIME\x10\x04\x12\x13\n\x0fPURPOSE_LIBRARY\x10\x05\x12\x14\n\x10PURPOSE_METADATA\x10\x06\x12\x10\n\x0cPURPOSE_DOCS\x10\x07\x12\x11\n\rPURPOSE_TESTS\x10\x08\x12\x11\n\rPURPOSE_TOOLS\x10\t\x12\x12\n\x0ePURPOSE_VENDOR\x10\n\x12\x11\n\rPURPOSE_CACHE\x10\x0b\x12\x10\n\x0cPURPOSE_TEMP\x10\x0c\x12\x10\n\x0cPURPOSE_LOGS\x10\r\x12\x11\n\rPURPOSE_STATE\x10\x0e\x12\x13\n\x0fPURPOSE_SECRETS\x10\x0f*\xa8\x01\n\x08Platform\x12\x10\n\x0cPLATFORM_ANY\x10\x00\x12\x12\n\x0ePLATFORM_LINUX\x10\x01\x12\x13\n\x0fPLATFORM_DARWIN\x10\x02\x12\x14\n\x10PLATFORM_WINDOWS\x10\x03\x12\x10\n\x0cPLATFORM_BSD\x10\x04\x12\x11\n\rPLATFORM_WASM\x10\x05\x12\x14\n\x10PLATFORM_ANDROID\x10\x06\x12\x10\n\x0cPLATFORM_IOS\x10\x07\x42[\n\x1eio.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'modules.slots_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\036io.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025'
  _globals['_SLOTENTRY_METADATAENTRY']._loaded_options = None
  _globals['_SLOTENTRY_METADATAENTRY']._serialized_options = b'8\001'
  _globals['_SLOTTABLE_METADATAENTRY']._loaded_options = None
  _globals['_SLOTTABLE_METADATAENTRY']._serialized_options = b'8\001'
  _globals['_LIFECYCLE']._serialized_start=1164
  _globals['_LIFECYCLE']._serialized_end=1560
  _globals['_PURPOSE']._serialized_start=1563
  _globals['_PURPOSE']._serialized_end=1883
  _globals['_PLATFORM']._serialized_start=1886
  _globals['_PLATFORM']._serialized_end=2054
  _globals['_SLOTENTRY']._serialized_start=67
  _globals['_SLOTENTRY']._serialized_end=591
  _globals['_SLOTENTRY_METADATAENTRY']._serialized_start=544
  _globals['_SLOTENTRY_METADATAENTRY']._serialized_end=591
  _globals['_JITCONFIG']._serialized_start=594
  _globals['_JITCONFIG']._serialized_end=894
  _globals['_JITCONFIG_SOURCE']._serialized_start=745
  _globals['_JITCONFIG_SOURCE']._serialized_end=830
  _globals['_JITCONFIG_CACHE']._serialized_start=832
  _globals['_JITCONFIG_CACHE']._serialized_end=894
  _globals['_SLOTTABLE']._serialized_start=897
  _globals['_SLOTTABLE']._serialized_end=1161
  _globals['_SLOTTABLE_METADATAENTRY']._serialized_start=544
  _globals['_SLOTTABLE_METADATAENTRY']._serialized_end=591
# @@protoc_insertion_point(module_scope)

# 🌶️📦🔚
