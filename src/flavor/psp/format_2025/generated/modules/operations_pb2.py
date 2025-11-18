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
    'modules/operations.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x18modules/operations.proto\x12\x14pspf_2025.operations\"I\n\x0eOperationChain\x12\x0e\n\x06packed\x18\x01 \x01(\x04\x12\x12\n\noperations\x18\x02 \x03(\r\x12\x13\n\x0b\x64\x65scription\x18\x03 \x01(\t\"\xe1\x01\n\x13OperationCapability\x12\x32\n\toperation\x18\x01 \x01(\x0e\x32\x1f.pspf_2025.operations.Operation\x12\x1d\n\x15required_capabilities\x18\x02 \x03(\t\x12\x14\n\x0cinput_format\x18\x03 \x01(\t\x12\x15\n\routput_format\x18\x04 \x01(\t\x12\x10\n\x08\x63pu_cost\x18\x05 \x01(\r\x12\x13\n\x0bmemory_cost\x18\x06 \x01(\r\x12\x11\n\tstreaming\x18\x07 \x01(\x08\x12\x10\n\x08seekable\x18\x08 \x01(\x08\"\x80\x02\n\x0fOperationConfig\x12\x32\n\toperation\x18\x01 \x01(\x0e\x32\x1f.pspf_2025.operations.Operation\x12I\n\nparameters\x18\x02 \x03(\x0b\x32\x35.pspf_2025.operations.OperationConfig.ParametersEntry\x12\x13\n\x0b\x62uffer_size\x18\x03 \x01(\r\x12\x12\n\nmax_memory\x18\x04 \x01(\r\x12\x12\n\ntimeout_ms\x18\x05 \x01(\r\x1a\x31\n\x0fParametersEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01*\xa3\r\n\tOperation\x12\x0b\n\x07OP_NONE\x10\x00\x12\n\n\x06OP_TAR\x10\x01\x12\x11\n\rOP_TAR_SORTED\x10\x02\x12\x11\n\rOP_TAR_STREAM\x10\x03\x12\x0b\n\x07OP_CPIO\x10\x04\x12\x10\n\x0cOP_CPIO_NEWC\x10\x05\x12\t\n\x05OP_AR\x10\x06\x12\r\n\tOP_AR_BSD\x10\x07\x12\x10\n\x0cOP_ZIP_STORE\x10\x08\x12\x11\n\rOP_ZIP_STREAM\x10\t\x12\t\n\x05OP_7Z\x10\n\x12\n\n\x06OP_RAR\x10\x0b\x12\n\n\x06OP_PAX\x10\x0c\x12\x0c\n\x08OP_USTAR\x10\r\x12\x18\n\x14OP_BUNDLE_RESERVED_E\x10\x0e\x12\x18\n\x14OP_BUNDLE_RESERVED_F\x10\x0f\x12\x0b\n\x07OP_GZIP\x10\x10\x12\x10\n\x0cOP_GZIP_FAST\x10\x11\x12\x10\n\x0cOP_GZIP_BEST\x10\x12\x12\x0c\n\x08OP_BZIP2\x10\x13\x12\x11\n\rOP_BZIP2_FAST\x10\x14\x12\x11\n\rOP_BZIP2_BEST\x10\x15\x12\t\n\x05OP_XZ\x10\x16\x12\x0e\n\nOP_XZ_FAST\x10\x17\x12\x0e\n\nOP_XZ_BEST\x10\x18\x12\x0b\n\x07OP_LZMA\x10\x19\x12\x0c\n\x08OP_LZMA2\x10\x1a\x12\x0b\n\x07OP_ZSTD\x10\x1b\x12\x10\n\x0cOP_ZSTD_FAST\x10\x1c\x12\x10\n\x0cOP_ZSTD_BEST\x10\x1d\x12\n\n\x06OP_LZ4\x10\x1e\x12\r\n\tOP_LZ4_HC\x10\x1f\x12\r\n\tOP_SNAPPY\x10 \x12\r\n\tOP_BROTLI\x10!\x12\x12\n\x0eOP_BROTLI_TEXT\x10\"\x12\x0e\n\nOP_DEFLATE\x10#\x12\x10\n\x0cOP_DEFLATE64\x10$\x12\n\n\x06OP_PPM\x10%\x12\x0b\n\x07OP_PPMD\x10&\x12\x11\n\rOP_AES128_GCM\x10\x30\x12\x11\n\rOP_AES256_GCM\x10\x31\x12\x11\n\rOP_AES128_CBC\x10\x32\x12\x11\n\rOP_AES256_CBC\x10\x33\x12\x11\n\rOP_AES128_CTR\x10\x34\x12\x11\n\rOP_AES256_CTR\x10\x35\x12\x18\n\x14OP_CHACHA20_POLY1305\x10\x36\x12\x19\n\x15OP_XCHACHA20_POLY1305\x10\x37\x12\x0e\n\nOP_SALSA20\x10\x38\x12\x18\n\x14OP_XSALSA20_POLY1305\x10\x39\x12\x0f\n\x0bOP_RSA_2048\x10:\x12\x0f\n\x0bOP_RSA_4096\x10;\x12\x0e\n\nOP_ED25519\x10<\x12\r\n\tOP_X25519\x10=\x12\x10\n\x0cOP_SECP256K1\x10>\x12\x10\n\x0cOP_SECP256R1\x10?\x12\x0f\n\x0bOP_NACL_BOX\x10@\x12\x15\n\x11OP_NACL_SECRETBOX\x10\x41\x12\n\n\x06OP_AGE\x10\x42\x12\n\n\x06OP_PGP\x10\x43\x12\r\n\tOP_BASE64\x10P\x12\x11\n\rOP_BASE64_URL\x10Q\x12\r\n\tOP_BASE32\x10R\x12\r\n\tOP_BASE16\x10S\x12\n\n\x06OP_HEX\x10T\x12\x0e\n\nOP_ASCII85\x10U\x12\x0f\n\x0bOP_UUENCODE\x10V\x12\x0f\n\x0bOP_XXENCODE\x10W\x12\x17\n\x13OP_QUOTED_PRINTABLE\x10X\x12\x0f\n\x0bOP_PUNYCODE\x10Y\x12\x0e\n\nOP_PERCENT\x10Z\x12\r\n\tOP_SHA256\x10p\x12\r\n\tOP_SHA512\x10q\x12\x0f\n\x0bOP_SHA3_256\x10r\x12\x0f\n\x0bOP_SHA3_512\x10s\x12\x0e\n\nOP_BLAKE2B\x10t\x12\x0e\n\nOP_BLAKE2S\x10u\x12\r\n\tOP_BLAKE3\x10v\x12\n\n\x06OP_MD5\x10w\x12\x0b\n\x07OP_SHA1\x10x\x12\r\n\tOP_XXHASH\x10y\x12\x0e\n\nOP_XXHASH3\x10z\x12\x0e\n\nOP_SIPHASH\x10{\x12\x12\n\x0eOP_HIGHWAYHASH\x10|\x12\x0e\n\nOP_ADLER32\x10}\x12\x0c\n\x08OP_CRC32\x10~\x12\x0c\n\x08OP_CRC64\x10\x7f\x12\x14\n\x0fOP_ED25519_SIGN\x10\x90\x01\x12\x0f\n\nOP_RSA_PSS\x10\x91\x01\x12\x11\n\x0cOP_RSA_PKCS1\x10\x92\x01\x12\x12\n\rOP_ECDSA_P256\x10\x93\x01\x12\x12\n\rOP_ECDSA_P384\x10\x94\x01\x12\x12\n\rOP_ECDSA_P521\x10\x95\x01\x12\r\n\x08OP_EDDSA\x10\x96\x01\x12\x13\n\x0eOP_HMAC_SHA256\x10\x97\x01\x12\x13\n\x0eOP_HMAC_SHA512\x10\x98\x01\x12\r\n\x08OP_SPLIT\x10\xb0\x01\x12\r\n\x08OP_MERGE\x10\xb1\x01\x12\x0e\n\tOP_DEDUPE\x10\xb2\x01\x12\r\n\x08OP_DELTA\x10\xb3\x01\x12\r\n\x08OP_PATCH\x10\xb4\x01\x12\x10\n\x0bOP_TERMINAL\x10\xff\x01\x42[\n\x1eio.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'modules.operations_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\036io.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025'
  _globals['_OPERATIONCONFIG_PARAMETERSENTRY']._loaded_options = None
  _globals['_OPERATIONCONFIG_PARAMETERSENTRY']._serialized_options = b'8\001'
  _globals['_OPERATION']._serialized_start=613
  _globals['_OPERATION']._serialized_end=2312
  _globals['_OPERATIONCHAIN']._serialized_start=50
  _globals['_OPERATIONCHAIN']._serialized_end=123
  _globals['_OPERATIONCAPABILITY']._serialized_start=126
  _globals['_OPERATIONCAPABILITY']._serialized_end=351
  _globals['_OPERATIONCONFIG']._serialized_start=354
  _globals['_OPERATIONCONFIG']._serialized_end=610
  _globals['_OPERATIONCONFIG_PARAMETERSENTRY']._serialized_start=561
  _globals['_OPERATIONCONFIG_PARAMETERSENTRY']._serialized_end=610
# @@protoc_insertion_point(module_scope)

# 🌶️📦🔚
