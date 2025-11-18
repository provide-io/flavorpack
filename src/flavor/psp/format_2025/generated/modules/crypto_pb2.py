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
    'modules/crypto.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x14modules/crypto.proto\x12\x10pspf_2025.crypto\"\x85\x02\n\nCryptoInfo\x12\x32\n\tsignature\x18\x01 \x01(\x0b\x32\x1f.pspf_2025.crypto.SignatureInfo\x12\'\n\x04keys\x18\x02 \x03(\x0b\x32\x19.pspf_2025.crypto.KeyInfo\x12\x33\n\tintegrity\x18\x03 \x03(\x0b\x32 .pspf_2025.crypto.IntegrityCheck\x12+\n\x05trust\x18\x04 \x01(\x0b\x32\x1c.pspf_2025.crypto.TrustChain\x12\x38\n\nencryption\x18\x05 \x01(\x0b\x32$.pspf_2025.crypto.EncryptionSettings\"\xa9\x01\n\rSignatureInfo\x12\x37\n\talgorithm\x18\x01 \x01(\x0e\x32$.pspf_2025.crypto.SignatureAlgorithm\x12\x12\n\npublic_key\x18\x02 \x01(\x0c\x12\x11\n\tsignature\x18\x03 \x01(\x0c\x12\x11\n\ttimestamp\x18\x04 \x01(\x04\x12\x0e\n\x06key_id\x18\x05 \x01(\t\x12\x15\n\rmetadata_hash\x18\x06 \x01(\x0c\"\xd2\x01\n\x07KeyInfo\x12\x0e\n\x06key_id\x18\x01 \x01(\t\x12+\n\x08key_type\x18\x02 \x01(\x0e\x32\x19.pspf_2025.crypto.KeyType\x12)\n\x05usage\x18\x03 \x01(\x0e\x32\x1a.pspf_2025.crypto.KeyUsage\x12\x12\n\npublic_key\x18\x04 \x01(\x0c\x12\x12\n\ncreated_at\x18\x05 \x01(\x04\x12\x12\n\nexpires_at\x18\x06 \x01(\x04\x12\x11\n\talgorithm\x18\x07 \x01(\t\x12\x10\n\x08key_size\x18\x08 \x01(\r\"\x8d\x01\n\x0eIntegrityCheck\x12\x36\n\talgorithm\x18\x01 \x01(\x0e\x32#.pspf_2025.crypto.ChecksumAlgorithm\x12\x10\n\x08\x63hecksum\x18\x02 \x01(\x0c\x12\x11\n\tdata_size\x18\x03 \x01(\x04\x12\r\n\x05scope\x18\x04 \x01(\t\x12\x0f\n\x07slot_id\x18\x05 \x01(\r\"\xb7\x01\n\nTrustChain\x12\x33\n\x0c\x63\x65rtificates\x18\x01 \x03(\x0b\x32\x1d.pspf_2025.crypto.Certificate\x12.\n\x07\x61nchors\x18\x02 \x03(\x0b\x32\x1d.pspf_2025.crypto.TrustAnchor\x12\x17\n\x0fvalidation_time\x18\x03 \x01(\t\x12+\n\x05level\x18\x04 \x01(\x0e\x32\x1c.pspf_2025.crypto.TrustLevel\"\x96\x01\n\x0b\x43\x65rtificate\x12\x13\n\x0b\x63\x65rtificate\x18\x01 \x01(\x0c\x12\x0e\n\x06issuer\x18\x02 \x01(\t\x12\x0f\n\x07subject\x18\x03 \x01(\t\x12\x12\n\nnot_before\x18\x04 \x01(\x04\x12\x11\n\tnot_after\x18\x05 \x01(\x04\x12\x15\n\rserial_number\x18\x06 \x01(\t\x12\x13\n\x0b\x66ingerprint\x18\x07 \x01(\x0c\"V\n\x0bTrustAnchor\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x12\n\npublic_key\x18\x02 \x01(\x0c\x12\x11\n\talgorithm\x18\x03 \x01(\t\x12\x12\n\ncreated_at\x18\x04 \x01(\x04\"\xb1\x01\n\x12\x45ncryptionSettings\x12\x11\n\tencrypted\x18\x01 \x01(\x08\x12\x38\n\talgorithm\x18\x02 \x01(\x0e\x32%.pspf_2025.crypto.EncryptionAlgorithm\x12\x0e\n\x06key_id\x18\x03 \x01(\x0c\x12\x0c\n\x04salt\x18\x04 \x01(\x0c\x12\x17\n\x0fiteration_count\x18\x05 \x01(\r\x12\x17\n\x0f\x65ncrypted_slots\x18\x06 \x03(\r*p\n\x12SignatureAlgorithm\x12\x12\n\x0eSIGNATURE_NONE\x10\x00\x12\x15\n\x11SIGNATURE_ED25519\x10\x01\x12\x15\n\x11SIGNATURE_RSA4096\x10\x02\x12\x18\n\x14SIGNATURE_ECDSA_P256\x10\x03*S\n\x07KeyType\x12\x14\n\x10KEY_TYPE_SIGNING\x10\x00\x12\x17\n\x13KEY_TYPE_ENCRYPTION\x10\x01\x12\x19\n\x15KEY_TYPE_VERIFICATION\x10\x02*v\n\x08KeyUsage\x12\x12\n\x0eKEY_USAGE_NONE\x10\x00\x12\x12\n\x0eKEY_USAGE_SIGN\x10\x01\x12\x14\n\x10KEY_USAGE_VERIFY\x10\x02\x12\x15\n\x11KEY_USAGE_ENCRYPT\x10\x04\x12\x15\n\x11KEY_USAGE_DECRYPT\x10\x08*|\n\x11\x43hecksumAlgorithm\x12\x14\n\x10\x43HECKSUM_ADLER32\x10\x00\x12\x12\n\x0e\x43HECKSUM_CRC32\x10\x01\x12\x13\n\x0f\x43HECKSUM_SHA256\x10\x02\x12\x13\n\x0f\x43HECKSUM_XXHASH\x10\x03\x12\x13\n\x0f\x43HECKSUM_BLAKE3\x10\x04*i\n\nTrustLevel\x12\x0e\n\nTRUST_NONE\x10\x00\x12\x15\n\x11TRUST_SELF_SIGNED\x10\x01\x12\x16\n\x12TRUST_ORGANIZATION\x10\x02\x12\x0c\n\x08TRUST_CA\x10\x03\x12\x0e\n\nTRUST_ROOT\x10\x04*\x82\x01\n\x13\x45ncryptionAlgorithm\x12\x13\n\x0f\x45NCRYPTION_NONE\x10\x00\x12\x19\n\x15\x45NCRYPTION_AES256_GCM\x10\x01\x12 \n\x1c\x45NCRYPTION_CHACHA20_POLY1305\x10\x02\x12\x19\n\x15\x45NCRYPTION_AES256_CBC\x10\x03\x42[\n\x1eio.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'modules.crypto_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\036io.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025'
  _globals['_SIGNATUREALGORITHM']._serialized_start=1442
  _globals['_SIGNATUREALGORITHM']._serialized_end=1554
  _globals['_KEYTYPE']._serialized_start=1556
  _globals['_KEYTYPE']._serialized_end=1639
  _globals['_KEYUSAGE']._serialized_start=1641
  _globals['_KEYUSAGE']._serialized_end=1759
  _globals['_CHECKSUMALGORITHM']._serialized_start=1761
  _globals['_CHECKSUMALGORITHM']._serialized_end=1885
  _globals['_TRUSTLEVEL']._serialized_start=1887
  _globals['_TRUSTLEVEL']._serialized_end=1992
  _globals['_ENCRYPTIONALGORITHM']._serialized_start=1995
  _globals['_ENCRYPTIONALGORITHM']._serialized_end=2125
  _globals['_CRYPTOINFO']._serialized_start=43
  _globals['_CRYPTOINFO']._serialized_end=304
  _globals['_SIGNATUREINFO']._serialized_start=307
  _globals['_SIGNATUREINFO']._serialized_end=476
  _globals['_KEYINFO']._serialized_start=479
  _globals['_KEYINFO']._serialized_end=689
  _globals['_INTEGRITYCHECK']._serialized_start=692
  _globals['_INTEGRITYCHECK']._serialized_end=833
  _globals['_TRUSTCHAIN']._serialized_start=836
  _globals['_TRUSTCHAIN']._serialized_end=1019
  _globals['_CERTIFICATE']._serialized_start=1022
  _globals['_CERTIFICATE']._serialized_end=1172
  _globals['_TRUSTANCHOR']._serialized_start=1174
  _globals['_TRUSTANCHOR']._serialized_end=1260
  _globals['_ENCRYPTIONSETTINGS']._serialized_start=1263
  _globals['_ENCRYPTIONSETTINGS']._serialized_end=1440
# @@protoc_insertion_point(module_scope)

# 🌶️📦🔚
