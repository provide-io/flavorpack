// Package format_2025 implements PSPF/2025 operation chains
// Operations can be chained together (up to 8) and packed into a 64-bit integer
package format_2025

import (
	"github.com/hashicorp/go-hclog"
)

// Operation constants matching Python/protobuf definitions
const (
	// 0x00: No operation
	OP_NONE uint8 = 0x00

	// 0x01-0x0F: Bundle operations (15 slots)
	OP_TAR        uint8 = 0x01
	OP_TAR_SORTED uint8 = 0x02
	OP_TAR_STREAM uint8 = 0x03
	OP_CPIO       uint8 = 0x04
	OP_CPIO_NEWC  uint8 = 0x05
	OP_AR         uint8 = 0x06
	OP_AR_BSD     uint8 = 0x07
	OP_ZIP_STORE  uint8 = 0x08
	OP_ZIP_STREAM uint8 = 0x09
	OP_7Z         uint8 = 0x0A
	OP_RAR        uint8 = 0x0B
	OP_PAX        uint8 = 0x0C
	OP_USTAR      uint8 = 0x0D

	// 0x10-0x2F: Compression operations (32 slots)
	OP_GZIP        uint8 = 0x10
	OP_GZIP_FAST   uint8 = 0x11
	OP_GZIP_BEST   uint8 = 0x12
	OP_BZIP2       uint8 = 0x13
	OP_BZIP2_FAST  uint8 = 0x14
	OP_BZIP2_BEST  uint8 = 0x15
	OP_XZ          uint8 = 0x16
	OP_XZ_FAST     uint8 = 0x17
	OP_XZ_BEST     uint8 = 0x18
	OP_LZMA        uint8 = 0x19
	OP_LZMA2       uint8 = 0x1A
	OP_ZSTD        uint8 = 0x1B
	OP_ZSTD_FAST   uint8 = 0x1C
	OP_ZSTD_BEST   uint8 = 0x1D
	OP_LZ4         uint8 = 0x1E
	OP_LZ4_HC      uint8 = 0x1F
	OP_SNAPPY      uint8 = 0x20
	OP_BROTLI      uint8 = 0x21
	OP_BROTLI_TEXT uint8 = 0x22
	OP_DEFLATE     uint8 = 0x23
	OP_DEFLATE64   uint8 = 0x24
	OP_PPM         uint8 = 0x25
	OP_PPMD        uint8 = 0x26

	// 0x30-0x4F: Encryption operations (32 slots)
	OP_AES128_GCM         uint8 = 0x30
	OP_AES256_GCM         uint8 = 0x31
	OP_AES128_CBC         uint8 = 0x32
	OP_AES256_CBC         uint8 = 0x33
	OP_AES128_CTR         uint8 = 0x34
	OP_AES256_CTR         uint8 = 0x35
	OP_CHACHA20_POLY1305  uint8 = 0x36
	OP_XCHACHA20_POLY1305 uint8 = 0x37
	OP_SALSA20            uint8 = 0x38
	OP_XSALSA20_POLY1305  uint8 = 0x39
	OP_RSA_2048           uint8 = 0x3A
	OP_RSA_4096           uint8 = 0x3B
	OP_ED25519            uint8 = 0x3C
	OP_X25519             uint8 = 0x3D
	OP_SECP256K1          uint8 = 0x3E
	OP_SECP256R1          uint8 = 0x3F
	OP_NACL_BOX           uint8 = 0x40
	OP_NACL_SECRETBOX     uint8 = 0x41
	OP_AGE                uint8 = 0x42
	OP_PGP                uint8 = 0x43

	// 0x50-0x6F: Encoding operations (32 slots)
	OP_BASE64           uint8 = 0x50
	OP_BASE64_URL       uint8 = 0x51
	OP_BASE32           uint8 = 0x52
	OP_BASE16           uint8 = 0x53
	OP_HEX              uint8 = 0x54
	OP_ASCII85          uint8 = 0x55
	OP_UUENCODE         uint8 = 0x56
	OP_XXENCODE         uint8 = 0x57
	OP_QUOTED_PRINTABLE uint8 = 0x58
	OP_PUNYCODE         uint8 = 0x59
	OP_PERCENT          uint8 = 0x5A

	// 0x70-0x8F: Hash operations (32 slots)
	OP_SHA256      uint8 = 0x70
	OP_SHA512      uint8 = 0x71
	OP_SHA3_256    uint8 = 0x72
	OP_SHA3_512    uint8 = 0x73
	OP_BLAKE2B     uint8 = 0x74
	OP_BLAKE2S     uint8 = 0x75
	OP_BLAKE3      uint8 = 0x76
	OP_MD5         uint8 = 0x77
	OP_SHA1        uint8 = 0x78
	OP_XXHASH      uint8 = 0x79
	OP_XXHASH3     uint8 = 0x7A
	OP_SIPHASH     uint8 = 0x7B
	OP_HIGHWAYHASH uint8 = 0x7C
	OP_ADLER32     uint8 = 0x7D
	OP_CRC32       uint8 = 0x7E
	OP_CRC64       uint8 = 0x7F

	// 0x90-0xAF: Signature operations (32 slots)
	OP_ED25519_SIGN uint8 = 0x90
	OP_RSA_PSS      uint8 = 0x91
	OP_RSA_PKCS1    uint8 = 0x92
	OP_ECDSA_P256   uint8 = 0x93
	OP_ECDSA_P384   uint8 = 0x94
	OP_ECDSA_P521   uint8 = 0x95
	OP_EDDSA        uint8 = 0x96
	OP_HMAC_SHA256  uint8 = 0x97
	OP_HMAC_SHA512  uint8 = 0x98

	// 0xB0-0xCF: Transform operations (32 slots)
	OP_SPLIT  uint8 = 0xB0
	OP_MERGE  uint8 = 0xB1
	OP_DEDUPE uint8 = 0xB2
	OP_DELTA  uint8 = 0xB3
	OP_PATCH  uint8 = 0xB4

	// 0xFF: Terminal
	OP_TERMINAL uint8 = 0xFF
)

var logger = hclog.New(&hclog.LoggerOptions{
	Name:  "pspf2025.operations",
	Level: hclog.Trace,
})

// PackOperations packs a list of operations into a 64-bit integer
// Up to 8 operations can be packed, each taking 8 bits
func PackOperations(operations []uint8) uint64 {
	logger.Trace("📦 Packing operations",
		"count", len(operations),
		"operations", operations,
	)

	var packed uint64
	for i, op := range operations {
		if i >= 8 {
			logger.Warn("⚠️ Too many operations, truncating to 8",
				"provided", len(operations),
			)
			break
		}
		packed |= uint64(op) << (i * 8)
		logger.Trace("🔧 Packed operation",
			"index", i,
			"op", op,
			"shift", i*8,
			"current", packed,
		)
	}

	logger.Debug("✅ Operations packed",
		"result", packed,
	)
	return packed
}

// UnpackOperations unpacks a 64-bit integer into a list of operations
// Returns only non-zero operations (stops at first 0x00)
func UnpackOperations(packed uint64) []uint8 {
	logger.Trace("📂 Unpacking operations",
		"packed", packed,
	)

	operations := make([]uint8, 0, 8)
	for i := 0; i < 8; i++ {
		op := uint8((packed >> (i * 8)) & 0xFF)
		if op == OP_NONE {
			break
		}
		operations = append(operations, op)
		logger.Trace("🔍 Unpacked operation",
			"index", i,
			"op", op,
		)
	}

	logger.Debug("✅ Operations unpacked",
		"count", len(operations),
		"operations", operations,
	)
	return operations
}

// operationNames maps operation constants to their names
var operationNames = map[uint8]string{
	OP_NONE: "NONE",

	// Bundle operations
	OP_TAR:        "TAR",
	OP_TAR_SORTED: "TAR_SORTED",
	OP_TAR_STREAM: "TAR_STREAM",
	OP_CPIO:       "CPIO",
	OP_CPIO_NEWC:  "CPIO_NEWC",
	OP_AR:         "AR",
	OP_AR_BSD:     "AR_BSD",
	OP_ZIP_STORE:  "ZIP_STORE",
	OP_ZIP_STREAM: "ZIP_STREAM",
	OP_7Z:         "7Z",
	OP_RAR:        "RAR",
	OP_PAX:        "PAX",
	OP_USTAR:      "USTAR",

	// Compression operations
	OP_GZIP:        "GZIP",
	OP_GZIP_FAST:   "GZIP_FAST",
	OP_GZIP_BEST:   "GZIP_BEST",
	OP_BZIP2:       "BZIP2",
	OP_BZIP2_FAST:  "BZIP2_FAST",
	OP_BZIP2_BEST:  "BZIP2_BEST",
	OP_XZ:          "XZ",
	OP_XZ_FAST:     "XZ_FAST",
	OP_XZ_BEST:     "XZ_BEST",
	OP_LZMA:        "LZMA",
	OP_LZMA2:       "LZMA2",
	OP_ZSTD:        "ZSTD",
	OP_ZSTD_FAST:   "ZSTD_FAST",
	OP_ZSTD_BEST:   "ZSTD_BEST",
	OP_LZ4:         "LZ4",
	OP_LZ4_HC:      "LZ4_HC",
	OP_SNAPPY:      "SNAPPY",
	OP_BROTLI:      "BROTLI",
	OP_BROTLI_TEXT: "BROTLI_TEXT",
	OP_DEFLATE:     "DEFLATE",
	OP_DEFLATE64:   "DEFLATE64",
	OP_PPM:         "PPM",
	OP_PPMD:        "PPMD",

	// Encryption operations
	OP_AES128_GCM:         "AES128_GCM",
	OP_AES256_GCM:         "AES256_GCM",
	OP_AES128_CBC:         "AES128_CBC",
	OP_AES256_CBC:         "AES256_CBC",
	OP_AES128_CTR:         "AES128_CTR",
	OP_AES256_CTR:         "AES256_CTR",
	OP_CHACHA20_POLY1305:  "CHACHA20_POLY1305",
	OP_XCHACHA20_POLY1305: "XCHACHA20_POLY1305",
	OP_SALSA20:            "SALSA20",
	OP_XSALSA20_POLY1305:  "XSALSA20_POLY1305",
	OP_RSA_2048:           "RSA_2048",
	OP_RSA_4096:           "RSA_4096",
	OP_ED25519:            "ED25519",
	OP_X25519:             "X25519",
	OP_SECP256K1:          "SECP256K1",
	OP_SECP256R1:          "SECP256R1",
	OP_NACL_BOX:           "NACL_BOX",
	OP_NACL_SECRETBOX:     "NACL_SECRETBOX",
	OP_AGE:                "AGE",
	OP_PGP:                "PGP",
}

// OperationName returns the name of an operation
func OperationName(op uint8) string {
	if name, ok := operationNames[op]; ok {
		return name
	}
	return "UNKNOWN"
}

// IsCompressionOp returns true if the operation is a compression operation
func IsCompressionOp(op uint8) bool {
	return op >= 0x10 && op <= 0x2F
}

// IsEncryptionOp returns true if the operation is an encryption operation
func IsEncryptionOp(op uint8) bool {
	return op >= 0x30 && op <= 0x4F
}

// IsBundleOp returns true if the operation is a bundle/archive operation
func IsBundleOp(op uint8) bool {
	return op >= 0x01 && op <= 0x0F
}
