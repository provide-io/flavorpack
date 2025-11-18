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
    'modules/jit.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x11modules/jit.proto\x12\rpspf_2025.jit\"\xb9\x02\n\x0fJITSystemConfig\x12\x0f\n\x07\x65nabled\x18\x01 \x01(\x08\x12)\n\x08strategy\x18\x02 \x01(\x0e\x32\x17.pspf_2025.jit.Strategy\x12\x11\n\tcache_dir\x18\x03 \x01(\t\x12\x16\n\x0emax_cache_size\x18\x04 \x01(\x04\x12\x1a\n\x12network_timeout_ms\x18\x05 \x01(\r\x12\x18\n\x10\x62\x61\x63kground_slots\x18\x06 \x03(\r\x12/\n\x08prefetch\x18\x07 \x01(\x0b\x32\x1d.pspf_2025.jit.PrefetchConfig\x12-\n\x07network\x18\x08 \x01(\x0b\x32\x1c.pspf_2025.jit.NetworkConfig\x12)\n\x05\x63\x61\x63he\x18\t \x01(\x0b\x32\x1a.pspf_2025.jit.CacheConfig\"x\n\x0ePrefetchConfig\x12\x0f\n\x07\x65nabled\x18\x01 \x01(\x08\x12\x10\n\x08patterns\x18\x02 \x03(\t\x12\x16\n\x0emax_concurrent\x18\x03 \x01(\r\x12\x13\n\x0b\x62uffer_size\x18\x04 \x01(\r\x12\x16\n\x0epriority_slots\x18\x05 \x03(\r\"\xf2\x02\n\rNetworkConfig\x12\x35\n\x04type\x18\x01 \x01(\x0e\x32\'.pspf_2025.jit.NetworkConfig.SourceType\x12\x10\n\x08\x65ndpoint\x18\x02 \x01(\t\x12\x0f\n\x07use_tls\x18\x03 \x01(\x08\x12\x17\n\x0f\x63\x65rtificate_pin\x18\x04 \x01(\t\x12\'\n\x04\x61uth\x18\x05 \x01(\x0b\x32\x19.pspf_2025.jit.AuthConfig\x12)\n\x05retry\x18\x06 \x01(\x0b\x32\x1a.pspf_2025.jit.RetryConfig\x12\x35\n\x0b\x63ompression\x18\x07 \x01(\x0b\x32 .pspf_2025.jit.CompressionConfig\"c\n\nSourceType\x12\x0f\n\x0bSOURCE_HTTP\x10\x00\x12\x0f\n\x0bSOURCE_GRPC\x10\x01\x12\r\n\tSOURCE_S3\x10\x02\x12\x11\n\rSOURCE_WEBDAV\x10\x03\x12\x11\n\rSOURCE_CUSTOM\x10\x04\"\xf6\x01\n\nAuthConfig\x12\x30\n\x04type\x18\x01 \x01(\x0e\x32\".pspf_2025.jit.AuthConfig.AuthType\x12\r\n\x05token\x18\x02 \x01(\t\x12\x10\n\x08username\x18\x03 \x01(\t\x12\x10\n\x08password\x18\x04 \x01(\t\x12\x13\n\x0b\x63lient_cert\x18\x05 \x01(\x0c\x12\x12\n\nclient_key\x18\x06 \x01(\x0c\"Z\n\x08\x41uthType\x12\r\n\tAUTH_NONE\x10\x00\x12\x0f\n\x0b\x41UTH_BEARER\x10\x01\x12\x0e\n\nAUTH_BASIC\x10\x02\x12\x0f\n\x0b\x41UTH_CUSTOM\x10\x03\x12\r\n\tAUTH_MTLS\x10\x04\"l\n\x0bRetryConfig\x12\x14\n\x0cmax_attempts\x18\x01 \x01(\r\x12\x12\n\nbackoff_ms\x18\x02 \x03(\r\x12\x1b\n\x13\x65xponential_backoff\x18\x03 \x01(\x08\x12\x16\n\x0emax_backoff_ms\x18\x04 \x01(\r\"\xfd\x01\n\x11\x43ompressionConfig\x12>\n\x04type\x18\x01 \x01(\x0e\x32\x30.pspf_2025.jit.CompressionConfig.CompressionType\x12\r\n\x05level\x18\x02 \x01(\r\"\x98\x01\n\x0f\x43ompressionType\x12\x14\n\x10\x43OMPRESSION_NONE\x10\x00\x12\x14\n\x10\x43OMPRESSION_GZIP\x10\x01\x12\x16\n\x12\x43OMPRESSION_BROTLI\x10\x02\x12\x14\n\x10\x43OMPRESSION_ZSTD\x10\x03\x12\x16\n\x12\x43OMPRESSION_SNAPPY\x10\x04\x12\x13\n\x0f\x43OMPRESSION_LZ4\x10\x05\"\xbf\x02\n\x0b\x43\x61\x63heConfig\x12:\n\x08strategy\x18\x01 \x01(\x0e\x32(.pspf_2025.jit.CacheConfig.CacheStrategy\x12\x13\n\x0bttl_seconds\x18\x02 \x01(\r\x12\x10\n\x08max_size\x18\x03 \x01(\x04\x12\x18\n\x10verify_on_access\x18\x04 \x01(\x08\x12\x18\n\x10\x63leanup_interval\x18\x05 \x01(\r\x12\x33\n\nvalidation\x18\x06 \x01(\x0b\x32\x1f.pspf_2025.jit.ValidationConfig\"d\n\rCacheStrategy\x12\x14\n\x10\x43\x41\x43HE_PERSISTENT\x10\x00\x12\x12\n\x0e\x43\x41\x43HE_TEMPORAL\x10\x01\x12\x14\n\x10\x43\x41\x43HE_SIZE_BOUND\x10\x02\x12\x13\n\x0f\x43\x41\x43HE_VERSIONED\x10\x03\"\xf9\x01\n\x10ValidationConfig\x12<\n\x04mode\x18\x01 \x01(\x0e\x32..pspf_2025.jit.ValidationConfig.ValidationMode\x12\x18\n\x10interval_seconds\x18\x02 \x01(\r\x12\x1c\n\x14invalidate_on_update\x18\x03 \x01(\x08\"o\n\x0eValidationMode\x12\x14\n\x10VALIDATION_QUICK\x10\x00\x12\x17\n\x13VALIDATION_PERIODIC\x10\x01\x12\x17\n\x13VALIDATION_ON_ERROR\x10\x02\x12\x15\n\x11VALIDATION_ALWAYS\x10\x03\"o\n\x0bSlotRequest\x12\x12\n\npackage_id\x18\x01 \x01(\t\x12\x17\n\x0fpackage_version\x18\x02 \x01(\t\x12\x0f\n\x07slot_id\x18\x03 \x01(\r\x12\x12\n\nauth_token\x18\x04 \x01(\t\x12\x0e\n\x06offset\x18\x05 \x01(\x04\"r\n\x08SlotInfo\x12\x0f\n\x07slot_id\x18\x01 \x01(\r\x12\x0c\n\x04size\x18\x02 \x01(\x04\x12\x10\n\x08\x63hecksum\x18\x03 \x01(\r\x12\x0e\n\x06sha256\x18\x04 \x01(\x0c\x12\x11\n\tavailable\x18\x05 \x01(\x08\x12\x12\n\nexpires_at\x18\x06 \x01(\x04\"`\n\tSlotChunk\x12\x10\n\x08sequence\x18\x01 \x01(\r\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c\x12\x10\n\x08\x63hecksum\x18\x03 \x01(\r\x12\x10\n\x08progress\x18\x04 \x01(\x02\x12\x0f\n\x07is_last\x18\x05 \x01(\x08\"K\n\rUpdateRequest\x12\x12\n\npackage_id\x18\x01 \x01(\t\x12\x17\n\x0f\x63urrent_version\x18\x02 \x01(\t\x12\r\n\x05slots\x18\x03 \x03(\r\"y\n\nUpdateInfo\x12\x18\n\x10update_available\x18\x01 \x01(\x08\x12\x13\n\x0bnew_version\x18\x02 \x01(\t\x12\x15\n\rchanged_slots\x18\x03 \x03(\r\x12\x12\n\ntotal_size\x18\x04 \x01(\x04\x12\x11\n\tchangelog\x18\x05 \x01(\t*|\n\x08Strategy\x12\x11\n\rSTRATEGY_LAZY\x10\x00\x12\x17\n\x13STRATEGY_AGGRESSIVE\x10\x01\x12\x15\n\x11STRATEGY_BALANCED\x10\x02\x12\x14\n\x10STRATEGY_MINIMAL\x10\x03\x12\x17\n\x13STRATEGY_PREDICTIVE\x10\x04\x42[\n\x1eio.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'modules.jit_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\036io.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025'
  _globals['_STRATEGY']._serialized_start=2563
  _globals['_STRATEGY']._serialized_end=2687
  _globals['_JITSYSTEMCONFIG']._serialized_start=37
  _globals['_JITSYSTEMCONFIG']._serialized_end=350
  _globals['_PREFETCHCONFIG']._serialized_start=352
  _globals['_PREFETCHCONFIG']._serialized_end=472
  _globals['_NETWORKCONFIG']._serialized_start=475
  _globals['_NETWORKCONFIG']._serialized_end=845
  _globals['_NETWORKCONFIG_SOURCETYPE']._serialized_start=746
  _globals['_NETWORKCONFIG_SOURCETYPE']._serialized_end=845
  _globals['_AUTHCONFIG']._serialized_start=848
  _globals['_AUTHCONFIG']._serialized_end=1094
  _globals['_AUTHCONFIG_AUTHTYPE']._serialized_start=1004
  _globals['_AUTHCONFIG_AUTHTYPE']._serialized_end=1094
  _globals['_RETRYCONFIG']._serialized_start=1096
  _globals['_RETRYCONFIG']._serialized_end=1204
  _globals['_COMPRESSIONCONFIG']._serialized_start=1207
  _globals['_COMPRESSIONCONFIG']._serialized_end=1460
  _globals['_COMPRESSIONCONFIG_COMPRESSIONTYPE']._serialized_start=1308
  _globals['_COMPRESSIONCONFIG_COMPRESSIONTYPE']._serialized_end=1460
  _globals['_CACHECONFIG']._serialized_start=1463
  _globals['_CACHECONFIG']._serialized_end=1782
  _globals['_CACHECONFIG_CACHESTRATEGY']._serialized_start=1682
  _globals['_CACHECONFIG_CACHESTRATEGY']._serialized_end=1782
  _globals['_VALIDATIONCONFIG']._serialized_start=1785
  _globals['_VALIDATIONCONFIG']._serialized_end=2034
  _globals['_VALIDATIONCONFIG_VALIDATIONMODE']._serialized_start=1923
  _globals['_VALIDATIONCONFIG_VALIDATIONMODE']._serialized_end=2034
  _globals['_SLOTREQUEST']._serialized_start=2036
  _globals['_SLOTREQUEST']._serialized_end=2147
  _globals['_SLOTINFO']._serialized_start=2149
  _globals['_SLOTINFO']._serialized_end=2263
  _globals['_SLOTCHUNK']._serialized_start=2265
  _globals['_SLOTCHUNK']._serialized_end=2361
  _globals['_UPDATEREQUEST']._serialized_start=2363
  _globals['_UPDATEREQUEST']._serialized_end=2438
  _globals['_UPDATEINFO']._serialized_start=2440
  _globals['_UPDATEINFO']._serialized_end=2561
# @@protoc_insertion_point(module_scope)

# 🌶️📦🔚
