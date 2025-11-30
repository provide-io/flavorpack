package operations

import (
	"fmt"
	"strings"
)

// PackOperations packs a list of operations into a 64-bit integer.
// Each operation takes 8 bits, allowing up to 8 operations in the chain.
// Operations are packed in execution order (first operation in LSB).
func PackOperations(operations []uint8) (uint64, error) {
	if len(operations) > 8 {
		return 0, fmt.Errorf("maximum 8 operations allowed, got %d", len(operations))
	}

	var packed uint64
	for i, op := range operations {
		packed |= uint64(op) << (i * 8)
	}

	return packed, nil
}

// UnpackOperations unpacks a 64-bit integer into a list of operations.
func UnpackOperations(packed uint64) []uint8 {
	var operations []uint8

	for i := 0; i < 8; i++ {
		op := uint8((packed >> (i * 8)) & 0xFF)
		if op == 0 { // OP_NONE terminates the chain
			break
		}
		operations = append(operations, op)
	}

	return operations
}

// OperationsToString converts packed operations to human-readable string.
func OperationsToString(packed uint64) string {
	if packed == 0 {
		return "raw"
	}

	operations := UnpackOperations(packed)

	// Check for common operation chains
	chain := operationsToChain(operations)
	if name, ok := commonChains[chain]; ok {
		return name
	}

	// Fall back to pipe format
	var names []string
	for _, op := range operations {
		names = append(names, strings.ToLower(GetName(op)))
	}

	return strings.Join(names, "|")
}

// StringToOperations parses operation string to packed operations.
func StringToOperations(opString string) (uint64, error) {
	if opString == "" || strings.ToLower(opString) == "raw" {
		return 0, nil
	}

	opString = strings.ToLower(opString)

	// Check for exact match in operation chains first
	if ops, ok := namedChains[opString]; ok {
		return PackOperations(ops)
	}

	// Handle pipe-separated operations
	if strings.Contains(opString, "|") {
		var operations []uint8
		for _, part := range strings.Split(opString, "|") {
			part = strings.TrimSpace(strings.ToUpper(part))
			if part == "" {
				continue
			}

			op, ok := namedOperations[part]
			if !ok {
				return 0, fmt.Errorf("unsupported v0 operation: %s", part)
			}
			operations = append(operations, op)
		}
		return PackOperations(operations)
	}

	// Single operation
	if ops, ok := namedChains[opString]; ok {
		return PackOperations(ops)
	}

	return 0, fmt.Errorf("unknown v0 operation string: %s", opString)
}

// operationsToChain converts operations slice to string for map lookup
func operationsToChain(ops []uint8) string {
	parts := make([]string, len(ops))
	for i, op := range ops {
		parts[i] = fmt.Sprintf("%02x", op)
	}
	return strings.Join(parts, "-")
}

// Common operation chains
var commonChains = map[string]string{
	"01-10": "tar.gz",  // TAR + GZIP
	"01-13": "tar.bz2", // TAR + BZIP2
	"01-16": "tar.xz",  // TAR + XZ
	"01-1b": "tar.zst", // TAR + ZSTD
	"10":    "gzip",
	"13":    "bzip2",
	"16":    "xz",
	"1b":    "zstd",
	"01":    "tar",
}

// Named chains for parsing
var namedChains = map[string][]uint8{
	// Raw data
	"raw": {},

	// Single operations
	"gzip":  {OP_GZIP},
	"bzip2": {OP_BZIP2},
	"xz":    {OP_XZ},
	"zstd":  {OP_ZSTD},
	"tar":   {OP_TAR},

	// Common compound operations
	"tar.gz":  {OP_TAR, OP_GZIP},
	"tar.bz2": {OP_TAR, OP_BZIP2},
	"tar.xz":  {OP_TAR, OP_XZ},
	"tar.zst": {OP_TAR, OP_ZSTD},

	// Alternative names
	"tgz":  {OP_TAR, OP_GZIP},
	"tbz2": {OP_TAR, OP_BZIP2},
	"txz":  {OP_TAR, OP_XZ},
}

// Named operations for parsing
var namedOperations = map[string]uint8{
	"TAR":   OP_TAR,
	"GZIP":  OP_GZIP,
	"BZIP2": OP_BZIP2,
	"XZ":    OP_XZ,
	"ZSTD":  OP_ZSTD,
}

// ApplyChain applies a chain of operations to data
func ApplyChain(data []byte, operations []uint8) ([]byte, error) {
	current := data

	for _, opID := range operations {
		op, err := Get(opID)
		if err != nil {
			return nil, fmt.Errorf("operation 0x%02x: %w", opID, err)
		}

		result, err := op.Apply(current)
		if err != nil {
			return nil, fmt.Errorf("applying %s: %w", op.Name(), err)
		}

		current = result
	}

	return current, nil
}

// ReverseChain reverses a chain of operations on data
func ReverseChain(data []byte, operations []uint8) ([]byte, error) {
	current := data

	// Apply operations in reverse order
	for i := len(operations) - 1; i >= 0; i-- {
		opID := operations[i]
		op, err := Get(opID)
		if err != nil {
			return nil, fmt.Errorf("operation 0x%02x: %w", opID, err)
		}

		if !op.CanReverse() {
			return nil, fmt.Errorf("operation %s is not reversible", op.Name())
		}

		result, err := op.Reverse(current)
		if err != nil {
			return nil, fmt.Errorf("reversing %s: %w", op.Name(), err)
		}

		current = result
	}

	return current, nil
}
