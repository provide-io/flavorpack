// Package format_2025 provides checksum utilities supporting multiple algorithms with prefixed format.
//
// Format: "algorithm:hexvalue" (e.g., "sha256:c0ffee123...", "adler32:babe1337")
package format_2025

import (
	"crypto/sha256"
	"crypto/sha512"
	"encoding/hex"
	"fmt"
	"hash"
	"hash/adler32"
	"strings"
)

// ChecksumAlgorithm represents supported checksum algorithms
type ChecksumAlgorithm int

const (
	ChecksumSHA256 ChecksumAlgorithm = iota
	ChecksumSHA512
	ChecksumAdler32
	ChecksumBlake2b
)

func (c ChecksumAlgorithm) String() string {
	switch c {
	case ChecksumSHA256:
		return "sha256"
	case ChecksumSHA512:
		return "sha512"
	case ChecksumAdler32:
		return "adler32"
	case ChecksumBlake2b:
		return "blake2b"
	default:
		return "unknown"
	}
}

// ParseChecksum parses a checksum string that may or may not have a prefix
func ParseChecksum(checksumStr string) (ChecksumAlgorithm, string, error) {
	if strings.Contains(checksumStr, ":") {
		// Prefixed format
		parts := strings.SplitN(checksumStr, ":", 2)
		if len(parts) != 2 {
			return ChecksumSHA256, "", fmt.Errorf("invalid checksum format: %s", checksumStr)
		}

		var algo ChecksumAlgorithm
		switch parts[0] {
		case "sha256":
			algo = ChecksumSHA256
		case "sha512":
			algo = ChecksumSHA512
		case "adler32":
			algo = ChecksumAdler32
		case "blake2b":
			algo = ChecksumBlake2b
		default:
			return ChecksumSHA256, "", fmt.Errorf("unknown checksum algorithm: %s", parts[0])
		}

		return algo, parts[1], nil
	}

	// Legacy format - guess based on length
	var algo ChecksumAlgorithm
	switch len(checksumStr) {
	case 64:
		algo = ChecksumSHA256
	case 128:
		algo = ChecksumSHA512
	case 8:
		algo = ChecksumAdler32
	default:
		algo = ChecksumSHA256 // Default
	}

	return algo, checksumStr, nil
}

// CalculateChecksum calculates checksum with prefix
func CalculateChecksum(data []byte, algorithm ChecksumAlgorithm) string {
	var h hash.Hash
	var prefix string

	switch algorithm {
	case ChecksumSHA256:
		h = sha256.New()
		prefix = "sha256:"
	case ChecksumSHA512:
		h = sha512.New()
		prefix = "sha512:"
	case ChecksumAdler32:
		h = adler32.New()
		prefix = "adler32:"
	case ChecksumBlake2b:
		// Would need golang.org/x/crypto/blake2b
		return "blake2b:not_implemented"
	default:
		h = sha256.New()
		prefix = "sha256:"
	}

	h.Write(data)
	hashBytes := h.Sum(nil)
	return prefix + hex.EncodeToString(hashBytes)
}

// VerifyChecksum verifies data against a checksum string
func VerifyChecksum(data []byte, checksumStr string) (bool, error) {
	algo, expected, err := ParseChecksum(checksumStr)
	if err != nil {
		return false, err
	}

	actual := CalculateChecksum(data, algo)

	// Compare just the hex part
	actualParts := strings.Split(actual, ":")
	actualHex := actualParts[len(actualParts)-1]

	return actualHex == expected, nil
}
