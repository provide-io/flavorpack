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
    'modules/metadata.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x16modules/metadata.proto\x12\x12pspf_2025.metadata\"\xaa\x05\n\x0fPackageMetadata\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0f\n\x07version\x18\x02 \x01(\t\x12\x16\n\x0e\x66ormat_version\x18\x03 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x04 \x01(\t\x12\x0e\n\x06\x61uthor\x18\x05 \x01(\t\x12\x0f\n\x07license\x18\x06 \x01(\t\x12/\n\x05slots\x18\x07 \x03(\x0b\x32 .pspf_2025.metadata.SlotMetadata\x12\x36\n\texecution\x18\x08 \x01(\x0b\x32#.pspf_2025.metadata.ExecutionConfig\x12,\n\x05\x62uild\x18\t \x01(\x0b\x32\x1d.pspf_2025.metadata.BuildInfo\x12\x34\n\x0c\x64\x65pendencies\x18\n \x03(\x0b\x32\x1e.pspf_2025.metadata.Dependency\x12\x36\n\x0crequirements\x18\x0b \x01(\x0b\x32 .pspf_2025.metadata.Requirements\x12*\n\x03spa\x18\x10 \x01(\x0b\x32\x1d.pspf_2025.metadata.SpaConfig\x12*\n\x03jit\x18\x11 \x01(\x0b\x32\x1d.pspf_2025.metadata.JitConfig\x12\x34\n\x08security\x18\x12 \x01(\x0b\x32\".pspf_2025.metadata.SecurityConfig\x12?\n\x06\x63ustom\x18\x14 \x03(\x0b\x32/.pspf_2025.metadata.PackageMetadata.CustomEntry\x12\x12\n\ncreated_at\x18\x15 \x01(\x04\x12\x13\n\x0bmodified_at\x18\x16 \x01(\x04\x1a-\n\x0b\x43ustomEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\xef\x01\n\x0f\x45xecutionConfig\x12\x0f\n\x07\x63ommand\x18\x01 \x01(\t\x12\x0c\n\x04\x61rgs\x18\x02 \x03(\t\x12\x39\n\x03\x65nv\x18\x03 \x03(\x0b\x32,.pspf_2025.metadata.ExecutionConfig.EnvEntry\x12\x13\n\x0bworking_dir\x18\x04 \x01(\t\x12\x13\n\x0binterpreter\x18\x05 \x01(\t\x12\x13\n\x0bpython_path\x18\x06 \x03(\t\x12\x17\n\x0ftimeout_seconds\x18\x07 \x01(\r\x1a*\n\x08\x45nvEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\xfd\x01\n\tBuildInfo\x12\x11\n\ttimestamp\x18\x01 \x01(\x04\x12\x0f\n\x07machine\x18\x02 \x01(\t\x12\x0c\n\x04user\x18\x03 \x01(\t\x12\x0e\n\x06\x63ommit\x18\x04 \x01(\t\x12\x0e\n\x06\x62ranch\x18\x05 \x01(\t\x12\x0c\n\x04tags\x18\x06 \x03(\t\x12\x17\n\x0f\x62uilder_version\x18\x07 \x01(\t\x12\x43\n\x0b\x65nvironment\x18\x08 \x03(\x0b\x32..pspf_2025.metadata.BuildInfo.EnvironmentEntry\x1a\x32\n\x10\x45nvironmentEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"b\n\nDependency\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x14\n\x0cversion_spec\x18\x02 \x01(\t\x12\x0e\n\x06source\x18\x03 \x01(\t\x12\x10\n\x08optional\x18\x04 \x01(\x08\x12\x0e\n\x06\x65xtras\x18\x05 \x03(\t\"\x8b\x01\n\x0cRequirements\x12\x16\n\x0epython_version\x18\x01 \x01(\t\x12\x10\n\x08platform\x18\x02 \x01(\t\x12\x14\n\x0c\x61rchitecture\x18\x03 \x01(\t\x12\x11\n\tmemory_mb\x18\x04 \x01(\x04\x12\x0f\n\x07\x64isk_mb\x18\x05 \x01(\x04\x12\x17\n\x0fsystem_packages\x18\x06 \x03(\t\"\xac\x01\n\tSpaConfig\x12\x0f\n\x07\x65nabled\x18\x01 \x01(\x08\x12\x10\n\x08pvp_slot\x18\x02 \x01(\r\x12\x16\n\x0epvp_timeout_ms\x18\x03 \x01(\r\x12\x16\n\x0epvp_max_memory\x18\x04 \x01(\x04\x12\x18\n\x10pvp_capabilities\x18\x05 \x03(\t\x12\x15\n\rboundary_type\x18\x06 \x01(\t\x12\x1b\n\x13\x62oundary_timeout_ms\x18\x07 \x01(\r\"\x8f\x01\n\tJitConfig\x12\x0f\n\x07\x65nabled\x18\x01 \x01(\x08\x12\x10\n\x08strategy\x18\x02 \x01(\t\x12\x11\n\tcache_dir\x18\x03 \x01(\t\x12\x16\n\x0emax_cache_size\x18\x04 \x01(\x04\x12\x1a\n\x12network_timeout_ms\x18\x05 \x01(\r\x12\x18\n\x10\x62\x61\x63kground_slots\x18\x06 \x03(\r\"\xa8\x02\n\x0cSlotMetadata\x12\x0c\n\x04slot\x18\x01 \x01(\r\x12\n\n\x02id\x18\x02 \x01(\t\x12\x0e\n\x06source\x18\x03 \x01(\t\x12\x0e\n\x06target\x18\x04 \x01(\t\x12\x0c\n\x04size\x18\x05 \x01(\x04\x12\x10\n\x08\x63hecksum\x18\x06 \x01(\t\x12\x12\n\noperations\x18\x07 \x01(\t\x12\x0f\n\x07purpose\x18\x08 \x01(\t\x12\x11\n\tlifecycle\x18\t \x01(\t\x12\x13\n\x0bpermissions\x18\n \x01(\t\x12@\n\x08metadata\x18\x0b \x03(\x0b\x32..pspf_2025.metadata.SlotMetadata.MetadataEntry\x1a/\n\rMetadataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\xd3\x01\n\x0eSecurityConfig\x12\x19\n\x11require_signature\x18\x01 \x01(\x08\x12\x16\n\x0e\x61llow_unsigned\x18\x02 \x01(\x08\x12\x12\n\nkey_source\x18\x03 \x01(\t\x12\x14\n\x0ctrusted_keys\x18\x04 \x03(\t\x12\x1b\n\x13signature_algorithm\x18\x05 \x01(\t\x12\x18\n\x10verify_checksums\x18\x06 \x01(\x08\x12\x17\n\x0fsandbox_enabled\x18\x07 \x01(\x08\x12\x14\n\x0c\x63\x61pabilities\x18\x08 \x03(\tB[\n\x1eio.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'modules.metadata_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\036io.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025'
  _globals['_PACKAGEMETADATA_CUSTOMENTRY']._loaded_options = None
  _globals['_PACKAGEMETADATA_CUSTOMENTRY']._serialized_options = b'8\001'
  _globals['_EXECUTIONCONFIG_ENVENTRY']._loaded_options = None
  _globals['_EXECUTIONCONFIG_ENVENTRY']._serialized_options = b'8\001'
  _globals['_BUILDINFO_ENVIRONMENTENTRY']._loaded_options = None
  _globals['_BUILDINFO_ENVIRONMENTENTRY']._serialized_options = b'8\001'
  _globals['_SLOTMETADATA_METADATAENTRY']._loaded_options = None
  _globals['_SLOTMETADATA_METADATAENTRY']._serialized_options = b'8\001'
  _globals['_PACKAGEMETADATA']._serialized_start=47
  _globals['_PACKAGEMETADATA']._serialized_end=729
  _globals['_PACKAGEMETADATA_CUSTOMENTRY']._serialized_start=684
  _globals['_PACKAGEMETADATA_CUSTOMENTRY']._serialized_end=729
  _globals['_EXECUTIONCONFIG']._serialized_start=732
  _globals['_EXECUTIONCONFIG']._serialized_end=971
  _globals['_EXECUTIONCONFIG_ENVENTRY']._serialized_start=929
  _globals['_EXECUTIONCONFIG_ENVENTRY']._serialized_end=971
  _globals['_BUILDINFO']._serialized_start=974
  _globals['_BUILDINFO']._serialized_end=1227
  _globals['_BUILDINFO_ENVIRONMENTENTRY']._serialized_start=1177
  _globals['_BUILDINFO_ENVIRONMENTENTRY']._serialized_end=1227
  _globals['_DEPENDENCY']._serialized_start=1229
  _globals['_DEPENDENCY']._serialized_end=1327
  _globals['_REQUIREMENTS']._serialized_start=1330
  _globals['_REQUIREMENTS']._serialized_end=1469
  _globals['_SPACONFIG']._serialized_start=1472
  _globals['_SPACONFIG']._serialized_end=1644
  _globals['_JITCONFIG']._serialized_start=1647
  _globals['_JITCONFIG']._serialized_end=1790
  _globals['_SLOTMETADATA']._serialized_start=1793
  _globals['_SLOTMETADATA']._serialized_end=2089
  _globals['_SLOTMETADATA_METADATAENTRY']._serialized_start=2042
  _globals['_SLOTMETADATA_METADATAENTRY']._serialized_end=2089
  _globals['_SECURITYCONFIG']._serialized_start=2092
  _globals['_SECURITYCONFIG']._serialized_end=2303
# @@protoc_insertion_point(module_scope)

# 🌶️📦🔚
