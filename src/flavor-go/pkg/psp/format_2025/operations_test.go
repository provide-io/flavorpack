// Package format_2025 implements PSPF/2025 operation chains
// This file contains tests for operation packing/unpacking
package format_2025

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestOperationPacking tests packing operations into 64-bit integers
func TestOperationPacking(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "operations_test",
		Level: hclog.Trace,
	})

	testCases := []struct {
		name       string
		operations []uint8
		expected   uint64
	}{
		{
			name:       "empty/raw",
			operations: []uint8{},
			expected:   0x0,
		},
		{
			name:       "single GZIP",
			operations: []uint8{OP_GZIP},
			expected:   0x10,
		},
		{
			name:       "single TAR",
			operations: []uint8{OP_TAR},
			expected:   0x01,
		},
		{
			name:       "TAR + GZIP",
			operations: []uint8{OP_TAR, OP_GZIP},
			expected:   0x1001,
		},
		{
			name:       "TAR + BZIP2",
			operations: []uint8{OP_TAR, OP_BZIP2},
			expected:   0x1301,
		},
		{
			name:       "TAR + ZSTD",
			operations: []uint8{OP_TAR, OP_ZSTD},
			expected:   0x1b01,
		},
		{
			name:       "TAR + GZIP + AES256_GCM",
			operations: []uint8{OP_TAR, OP_GZIP, OP_AES256_GCM},
			expected:   0x311001,
		},
		{
			name:       "max 8 operations",
			operations: []uint8{1, 2, 3, 4, 5, 6, 7, 8, 9}, // 9th should be ignored
			expected:   0x0807060504030201,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			logger.Info("🧪 Testing operation packing",
				"test", tc.name,
				"operations", tc.operations,
			)

			packed := PackOperations(tc.operations)

			logger.Debug("📦 Packed operations",
				"input", tc.operations,
				"output", fmt.Sprintf("0x%016x", packed),
				"expected", fmt.Sprintf("0x%016x", tc.expected),
			)

			if packed != tc.expected {
				t.Errorf("PackOperations(%v) = 0x%016x, want 0x%016x",
					tc.operations, packed, tc.expected)
			}

			logger.Info("✅ Test passed", "test", tc.name)
		})
	}
}

// TestOperationUnpacking tests unpacking 64-bit integers into operations
func TestOperationUnpacking(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "operations_test",
		Level: hclog.Trace,
	})

	testCases := []struct {
		name     string
		packed   uint64
		expected []uint8
	}{
		{
			name:     "empty/raw",
			packed:   0x0,
			expected: []uint8{},
		},
		{
			name:     "single GZIP",
			packed:   0x10,
			expected: []uint8{OP_GZIP},
		},
		{
			name:     "single TAR",
			packed:   0x01,
			expected: []uint8{OP_TAR},
		},
		{
			name:     "TAR + GZIP",
			packed:   0x1001,
			expected: []uint8{OP_TAR, OP_GZIP},
		},
		{
			name:     "TAR + GZIP + AES256_GCM",
			packed:   0x311001,
			expected: []uint8{OP_TAR, OP_GZIP, OP_AES256_GCM},
		},
		{
			name:     "8 operations",
			packed:   0x0807060504030201,
			expected: []uint8{1, 2, 3, 4, 5, 6, 7, 8},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			logger.Info("🔬 Testing operation unpacking",
				"test", tc.name,
				"packed", fmt.Sprintf("0x%016x", tc.packed),
			)

			operations := UnpackOperations(tc.packed)

			logger.Debug("📂 Unpacked operations",
				"input", fmt.Sprintf("0x%016x", tc.packed),
				"output", operations,
				"expected", tc.expected,
			)

			if !equalSlices(operations, tc.expected) {
				t.Errorf("UnpackOperations(0x%016x) = %v, want %v",
					tc.packed, operations, tc.expected)
			}

			logger.Info("✅ Test passed", "test", tc.name)
		})
	}
}

// TestOperationRoundTrip tests packing and unpacking are inverses
func TestOperationRoundTrip(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "operations_test",
		Level: hclog.Trace,
	})

	testCases := [][]uint8{
		{},
		{OP_GZIP},
		{OP_TAR},
		{OP_TAR, OP_GZIP},
		{OP_TAR, OP_BZIP2},
		{OP_TAR, OP_ZSTD, OP_AES256_GCM},
		{1, 2, 3, 4, 5, 6, 7, 8},
	}

	for i, ops := range testCases {
		t.Run(fmt.Sprintf("case_%d", i), func(t *testing.T) {
			logger.Info("🔄 Testing round-trip",
				"operations", ops,
			)

			packed := PackOperations(ops)
			logger.Trace("📦 Packed",
				"value", fmt.Sprintf("0x%016x", packed),
			)

			unpacked := UnpackOperations(packed)
			logger.Trace("📂 Unpacked",
				"value", unpacked,
			)

			// Truncate to 8 operations for comparison
			expected := ops
			if len(expected) > 8 {
				expected = expected[:8]
			}

			if !equalSlices(unpacked, expected) {
				t.Errorf("Round-trip failed: %v -> 0x%016x -> %v",
					ops, packed, unpacked)
			}

			logger.Info("✅ Round-trip successful", "operations", ops)
		})
	}
}

// TestPythonTestVectors tests against Python-generated test vectors
func TestPythonTestVectors(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "operations_test",
		Level: hclog.Trace,
	})

	logger.Info("🐍 Loading Python test vectors")

	// Load test vectors from JSON
	data, err := ioutil.ReadFile("testdata/operations.json")
	if err != nil {
		t.Fatalf("Failed to load test vectors: %v", err)
	}

	var testVectors []struct {
		Operations  []uint8 `json:"operations"`
		Packed      uint64  `json:"packed"`
		PackedHex   string  `json:"packed_hex"`
		Description string  `json:"description"`
	}

	if err := json.Unmarshal(data, &testVectors); err != nil {
		t.Fatalf("Failed to parse test vectors: %v", err)
	}

	logger.Info("📊 Loaded test vectors",
		"count", len(testVectors),
	)

	for _, tv := range testVectors {
		t.Run(tv.Description, func(t *testing.T) {
			logger.Info("🧪 Testing Python vector",
				"description", tv.Description,
				"expected", tv.PackedHex,
			)

			// Test packing
			packed := PackOperations(tv.Operations)
			if packed != tv.Packed {
				t.Errorf("PackOperations(%v) = 0x%016x, want %s",
					tv.Operations, packed, tv.PackedHex)
			}

			// Test unpacking
			unpacked := UnpackOperations(tv.Packed)
			if !equalSlices(unpacked, tv.Operations) {
				t.Errorf("UnpackOperations(%s) = %v, want %v",
					tv.PackedHex, unpacked, tv.Operations)
			}

			logger.Info("✅ Python vector verified",
				"description", tv.Description,
			)
		})
	}
}

// TestOperationNames tests operation constant to name mapping
func TestOperationNames(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "operations_test",
		Level: hclog.Trace,
	})

	testCases := []struct {
		op   uint8
		name string
	}{
		{OP_NONE, "NONE"},
		{OP_TAR, "TAR"},
		{OP_GZIP, "GZIP"},
		{OP_BZIP2, "BZIP2"},
		{OP_ZSTD, "ZSTD"},
		{OP_AES256_GCM, "AES256_GCM"},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			logger.Debug("🏷️ Testing operation name",
				"op", tc.op,
				"expected", tc.name,
			)

			name := OperationName(tc.op)
			if name != tc.name {
				t.Errorf("OperationName(%d) = %s, want %s",
					tc.op, name, tc.name)
			}

			logger.Trace("✓ Name verified",
				"op", tc.op,
				"name", name,
			)
		})
	}
}

// Helper function to compare slices
func equalSlices(a, b []uint8) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
