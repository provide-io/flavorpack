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
    'modules/index.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13modules/index.proto\x12\x0fpspf_2025.index\"\xd4\x06\n\nIndexBlock\x12\x16\n\x0e\x66ormat_version\x18\x01 \x01(\x07\x12\x16\n\x0eindex_checksum\x18\x02 \x01(\x07\x12\x14\n\x0cpackage_size\x18\x03 \x01(\x06\x12\x15\n\rlauncher_size\x18\x04 \x01(\x06\x12\x17\n\x0fmetadata_offset\x18\x05 \x01(\x06\x12\x15\n\rmetadata_size\x18\x06 \x01(\x06\x12\x19\n\x11slot_table_offset\x18\x07 \x01(\x06\x12\x17\n\x0fslot_table_size\x18\x08 \x01(\x06\x12\x12\n\nslot_count\x18\t \x01(\x07\x12\r\n\x05\x66lags\x18\n \x01(\x07\x12\x12\n\npublic_key\x18\x0b \x01(\x0c\x12\x19\n\x11metadata_checksum\x18\x0c \x01(\x0c\x12\x1b\n\x13integrity_signature\x18\r \x01(\x0c\x12\x13\n\x0b\x61\x63\x63\x65ss_mode\x18\x10 \x01(\r\x12\x16\n\x0e\x63\x61\x63he_strategy\x18\x11 \x01(\r\x12\x12\n\ncodec_type\x18\x12 \x01(\r\x12\x17\n\x0f\x65ncryption_type\x18\x13 \x01(\r\x12\x11\n\tpage_size\x18\x14 \x01(\r\x12\x12\n\nmax_memory\x18\x15 \x01(\x04\x12\x12\n\nmin_memory\x18\x16 \x01(\x04\x12\x14\n\x0c\x63pu_features\x18\x17 \x01(\x04\x12\x18\n\x10gpu_requirements\x18\x18 \x01(\x04\x12\x12\n\nnuma_hints\x18\x19 \x01(\x04\x12\x19\n\x11stream_chunk_size\x18\x1a \x01(\r\x12\x17\n\x0f\x62uild_timestamp\x18\x1b \x01(\x04\x12\x15\n\rbuild_machine\x18\x1c \x01(\x0c\x12\x13\n\x0bsource_hash\x18\x1d \x01(\x0c\x12\x17\n\x0f\x64\x65pendency_hash\x18\x1e \x01(\x0c\x12\x12\n\nlicense_id\x18\x1f \x01(\x0c\x12\x16\n\x0eprovenance_uri\x18  \x01(\x0c\x12\x14\n\x0c\x63\x61pabilities\x18! \x01(\x04\x12\x14\n\x0crequirements\x18\" \x01(\x04\x12\x12\n\nextensions\x18# \x01(\x04\x12\x15\n\rcompatibility\x18$ \x01(\r\x12\x18\n\x10protocol_version\x18% \x01(\r\x12\x15\n\rfuture_crypto\x18& \x01(\x0c\x12\x10\n\x08reserved\x18\' \x01(\x0c*\xb0\x01\n\x0cPackageFlags\x12\r\n\tFLAG_NONE\x10\x00\x12\x0f\n\x0b\x46LAG_SIGNED\x10\x01\x12\x12\n\x0e\x46LAG_ENCRYPTED\x10\x02\x12\x13\n\x0f\x46LAG_COMPRESSED\x10\x04\x12\x17\n\x13\x46LAG_MMAP_OPTIMIZED\x10\x08\x12\x12\n\x0e\x46LAG_STREAMING\x10\x10\x12\x14\n\x10\x46LAG_SPA_ENABLED\x10 \x12\x14\n\x10\x46LAG_JIT_ENABLED\x10@*\xb8\x01\n\x0c\x43\x61pabilities\x12\x0c\n\x08\x43\x41P_NONE\x10\x00\x12\x0c\n\x08\x43\x41P_MMAP\x10\x01\x12\x14\n\x10\x43\x41P_PAGE_ALIGNED\x10\x02\x12\x18\n\x14\x43\x41P_COMPRESSED_INDEX\x10\x04\x12\x11\n\rCAP_STREAMING\x10\x08\x12\x10\n\x0c\x43\x41P_PREFETCH\x10\x10\x12\x13\n\x0f\x43\x41P_CACHE_AWARE\x10 \x12\x11\n\rCAP_ENCRYPTED\x10@\x12\x0f\n\nCAP_SIGNED\x10\x80\x01\x42[\n\x1eio.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'modules.index_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\036io.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025'
  _globals['_PACKAGEFLAGS']._serialized_start=896
  _globals['_PACKAGEFLAGS']._serialized_end=1072
  _globals['_CAPABILITIES']._serialized_start=1075
  _globals['_CAPABILITIES']._serialized_end=1259
  _globals['_INDEXBLOCK']._serialized_start=41
  _globals['_INDEXBLOCK']._serialized_end=893
# @@protoc_insertion_point(module_scope)

# 🌶️📦🔚
