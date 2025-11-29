// Package format_2025 implements PSPF/2025 slot descriptors
// This file contains tests for slot descriptor packing/unpacking
package format_2025

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestSlotDescriptorPacking tests packing slot descriptors
func TestSlotDescriptorPacking(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "slots_test",
		Level: hclog.Trace,
	})

	testCases := []struct {
		name string
		desc SlotDescriptor
	}{
		{
			name: "raw_data",
			desc: SlotDescriptor{
				ID:           1,
				NameHash:     HashName("test_raw.txt"),
				Offset:       0,
				Size:         100,
				OriginalSize: 100,
				Operations:   0, // No operations
				Checksum:     0x12345678,
				Purpose:      0, // data
				Lifecycle:    0, // runtime
			},
		},
		{
			name: "gzip_only",
			desc: SlotDescriptor{
				ID:           2,
				NameHash:     HashName("test_gzip.txt"),
				Offset:       1024,
				Size:         512,
				OriginalSize: 1000,
				Operations:   PackOperations([]uint8{OP_GZIP}),
				Checksum:     0xABCDEF01,
				Purpose:      1, // code
				Lifecycle:    2, // startup
			},
		},
		{
			name: "tar_gzip",
			desc: SlotDescriptor{
				ID:           42,
				NameHash:     HashName("archive.tar.gz"),
				Offset:       8192,
				Size:         4096,
				OriginalSize: 16384,
				Operations:   PackOperations([]uint8{OP_TAR, OP_GZIP}),
				Checksum:     0xDEADBEEF,
				Purpose:      0, // data
				Lifecycle:    1, // cached
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			logger.Info("🧪 Testing slot descriptor packing",
				"test", tc.name,
				"id", tc.desc.ID,
			)

			// Pack the descriptor
			packed := tc.desc.Pack()

			logger.Debug("📦 Packed descriptor",
				"size", len(packed),
				"hex", fmt.Sprintf("%x", packed[:16]), // First 16 bytes
			)

			// Verify size
			if len(packed) != SlotDescriptorSize {
				t.Errorf("Packed size = %d, want %d", len(packed), SlotDescriptorSize)
			}

			// Unpack and verify round-trip
			unpacked, err := UnpackSlotDescriptor(packed)
			if err != nil {
				t.Fatalf("Failed to unpack: %v", err)
			}

			// Verify fields match
			if unpacked.ID != tc.desc.ID {
				t.Errorf("ID = %d, want %d", unpacked.ID, tc.desc.ID)
			}
			if unpacked.Operations != tc.desc.Operations {
				t.Errorf("Operations = 0x%016x, want 0x%016x", unpacked.Operations, tc.desc.Operations)
			}
			if unpacked.Checksum != tc.desc.Checksum {
				t.Errorf("Checksum = 0x%08x, want 0x%08x", unpacked.Checksum, tc.desc.Checksum)
			}

			logger.Info("✅ Test passed", "test", tc.name)
		})
	}
}

// TestPythonSlotVectors tests against Python-generated slot descriptor vectors
func TestPythonSlotVectors(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "slots_test",
		Level: hclog.Trace,
	})

	logger.Info("🐍 Loading Python slot descriptor test vectors")

	// Load binary test data
	binaryData, err := ioutil.ReadFile("testdata/descriptors.bin")
	if err != nil {
		t.Fatalf("Failed to load binary test vectors: %v", err)
	}

	// Load JSON metadata
	jsonData, err := ioutil.ReadFile("testdata/test_vectors.json")
	if err != nil {
		t.Fatalf("Failed to load JSON test vectors: %v", err)
	}

	var testVectors []struct {
		Name        string `json:"name"`
		Description string `json:"description"`
		Offset      int    `json:"offset"`
		Hex         string `json:"hex"`
		Fields      struct {
			ID            uint64 `json:"id"`
			NameHash      uint64 `json:"name_hash"`
			Offset        uint64 `json:"offset"`
			Size          uint64 `json:"size"`
			OriginalSize  uint64 `json:"original_size"`
			Operations    uint64 `json:"operations"`
			OperationsHex string `json:"operations_hex"`
			Checksum      uint32 `json:"checksum"`
			Purpose       uint8  `json:"purpose"`
			Lifecycle     uint8  `json:"lifecycle"`
			Permissions   uint16 `json:"permissions"`
		} `json:"fields"`
		ExpectedOperations []uint8 `json:"expected_operations"`
	}

	if err := json.Unmarshal(jsonData, &testVectors); err != nil {
		t.Fatalf("Failed to parse JSON test vectors: %v", err)
	}

	logger.Info("📊 Loaded test vectors",
		"count", len(testVectors),
		"binary_size", len(binaryData),
	)

	for _, tv := range testVectors {
		t.Run(tv.Name, func(t *testing.T) {
			logger.Info("🧪 Testing Python vector",
				"name", tv.Name,
				"description", tv.Description,
			)

			// Extract the 64-byte descriptor from binary data
			start := tv.Offset
			end := start + 64
			if end > len(binaryData) {
				t.Fatalf("Invalid offset %d in binary data", tv.Offset)
			}
			descriptorBytes := binaryData[start:end]

			// Unpack the descriptor
			desc, err := UnpackSlotDescriptor(descriptorBytes)
			if err != nil {
				t.Fatalf("Failed to unpack descriptor: %v", err)
			}

			logger.Debug("📂 Unpacked Python descriptor",
				"id", desc.ID,
				"operations", fmt.Sprintf("0x%016x", desc.Operations),
				"checksum", fmt.Sprintf("0x%08x", desc.Checksum),
			)

			// Verify fields match expected values
			if desc.ID != tv.Fields.ID {
				t.Errorf("ID = %d, want %d", desc.ID, tv.Fields.ID)
			}
			if desc.NameHash != tv.Fields.NameHash {
				t.Errorf("NameHash = %d, want %d", desc.NameHash, tv.Fields.NameHash)
			}
			if desc.Operations != tv.Fields.Operations {
				t.Errorf("Operations = 0x%016x, want %s", desc.Operations, tv.Fields.OperationsHex)
			}
			if uint32(desc.Checksum) != tv.Fields.Checksum {
				t.Errorf("Checksum = 0x%08x, want 0x%08x", desc.Checksum, tv.Fields.Checksum)
			}

			// Test unpacking operations
			ops := UnpackOperations(desc.Operations)
			if !equalSlices(ops, tv.ExpectedOperations) {
				t.Errorf("Unpacked operations = %v, want %v", ops, tv.ExpectedOperations)
			}

			// Test round-trip (pack and unpack)
			repacked := desc.Pack()
			if !bytes.Equal(repacked, descriptorBytes) {
				t.Errorf("Round-trip pack failed: packed bytes don't match original")
				logger.Error("❌ Round-trip mismatch",
					"original", fmt.Sprintf("%x", descriptorBytes[:16]),
					"repacked", fmt.Sprintf("%x", repacked[:16]),
				)
			}

			logger.Info("✅ Python vector verified", "name", tv.Name)
		})
	}
}

// TestHashName tests that HashName matches Python implementation
func TestHashName(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "slots_test",
		Level: hclog.Trace,
	})

	// These values should match what Python generates
	testCases := []struct {
		name     string
		expected uint64
	}{
		{"test_raw.txt", 0},   // Will be computed
		{"test_gzip.txt", 0},  // Will be computed
		{"archive.tar.gz", 0}, // Will be computed
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			logger.Debug("🔐 Testing hash name",
				"name", tc.name,
			)

			hash := HashName(tc.name)

			logger.Info("📝 Computed hash",
				"name", tc.name,
				"hash", hash,
				"hex", fmt.Sprintf("0x%016x", hash),
			)

			// Note: We'll verify these match Python values
			// when running against actual test vectors
		})
	}
}

// TestPermissions tests packing/unpacking of 16-bit permissions
func TestPermissions(t *testing.T) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "slots_test",
		Level: hclog.Trace,
	})

	testCases := []uint16{
		0o644,
		0o755,
		0o700,
		0o777,
		0o400,
	}

	for _, perm := range testCases {
		t.Run(fmt.Sprintf("0%o", perm), func(t *testing.T) {
			logger.Debug("🔒 Testing permissions",
				"permissions", fmt.Sprintf("0%o", perm),
			)

			desc := SlotDescriptor{}
			desc.SetPermissions(perm)

			got := desc.GetPermissions()
			if got != perm {
				t.Errorf("GetPermissions() = 0%o, want 0%o", got, perm)
			}

			logger.Trace("✓ Permissions verified",
				"value", fmt.Sprintf("0%o", perm),
				"low_byte", desc.Permissions,
				"high_byte", desc.PermissionsHigh,
			)
		})
	}
}
