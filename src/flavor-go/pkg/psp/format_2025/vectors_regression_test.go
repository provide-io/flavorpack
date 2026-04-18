// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

// Regression tests for test vector byte data integrity.
// These verify the reconstructed byte literals in testdata/vectors_test.go
// are correct after the fix for malformed byte literals (split hex values,
// double commas). The vectors are duplicated here since testdata/ is not
// importable as a Go package.

package format_2025

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"testing"
)

// vectorEntry mirrors the structure in testdata/vectors_test.go
type vectorEntry struct {
	Name        string
	Description string
	Binary      []byte
	ID          uint64
	Operations  uint64
}

// regressionVectors duplicates the test vectors from testdata/vectors_test.go
// so we can validate them from the parent package with access to Pack/Unpack.
var regressionVectors = []vectorEntry{
	{
		Name:        "raw_data",
		Description: "Raw data with no operations",
		Binary: []byte{
			0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x49, 0x1c, 0x9e, 0x8a, 0x87, 0x46, 0xb7, 0x59,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x78, 0x56, 0x34, 0x12, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x01, 0xa4, 0x00,
		},
		ID:         1,
		Operations: 0x0000000000000000,
	},
	{
		Name:        "gzip_only",
		Description: "Single GZIP operation",
		Binary: []byte{
			0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x5a, 0x3e, 0x75, 0x5a, 0x88, 0x9e, 0x34, 0x94,
			0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0xe8, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x01, 0xef, 0xcd, 0xab, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x01, 0x02, 0x00, 0x01, 0xa4, 0x00,
		},
		ID:         2,
		Operations: 0x0000000000000010,
	},
	{
		Name:        "tar_gzip",
		Description: "TAR followed by GZIP (tar.gz)",
		Binary: []byte{
			0x2a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xd7, 0x72, 0x47, 0x12, 0x10, 0xe0, 0x02, 0x8b,
			0x00, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0xef, 0xbe, 0xad, 0xde, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x01, 0x00, 0x01, 0xa4, 0x00,
		},
		ID:         42,
		Operations: 0x0000000000001001,
	},
	{
		Name:        "complex_chain",
		Description: "TAR -> ZSTD -> AES256_GCM",
		Binary: []byte{
			0xe7, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xa5, 0x57, 0x27, 0x3c, 0x92, 0x13, 0xca, 0x8f,
			0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x1b, 0x31, 0x00, 0x00, 0x00, 0x00, 0x00,
			0xbe, 0xba, 0xfe, 0xca, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x02, 0x00, 0x00, 0x01, 0xed, 0x00,
		},
		ID:         999,
		Operations: 0x0000000000311b01,
	},
}

// TestVectorSize verifies each test vector has exactly 64 bytes (SlotDescriptorSize).
func TestVectorSize(t *testing.T) {
	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			if len(tv.Binary) != SlotDescriptorSize {
				t.Errorf("vector %q has %d bytes, want %d (SlotDescriptorSize)",
					tv.Name, len(tv.Binary), SlotDescriptorSize)
			}
		})
	}
}

// TestVectorIDEncoding verifies the first 8 bytes of each vector encode
// the expected ID in little-endian format.
func TestVectorIDEncoding(t *testing.T) {
	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			if len(tv.Binary) < 8 {
				t.Fatalf("vector %q too short (%d bytes) to read ID", tv.Name, len(tv.Binary))
			}

			gotID := binary.LittleEndian.Uint64(tv.Binary[0:8])
			if gotID != tv.ID {
				t.Errorf("vector %q: ID from binary = %d (0x%016x), want %d (0x%016x)",
					tv.Name, gotID, gotID, tv.ID, tv.ID)
			}
		})
	}
}

// TestVectorOperationsEncoding verifies the operations field at bytes [40:48]
// matches the expected Operations value in little-endian format.
func TestVectorOperationsEncoding(t *testing.T) {
	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			if len(tv.Binary) < 48 {
				t.Fatalf("vector %q too short (%d bytes) to read Operations", tv.Name, len(tv.Binary))
			}

			gotOps := binary.LittleEndian.Uint64(tv.Binary[40:48])
			if gotOps != tv.Operations {
				t.Errorf("vector %q: Operations from binary = 0x%016x, want 0x%016x",
					tv.Name, gotOps, tv.Operations)
			}
		})
	}
}

// TestVectorUnpack verifies each vector can be unpacked into a valid SlotDescriptor
// with fields matching the declared ID and Operations.
func TestVectorUnpack(t *testing.T) {
	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			desc, err := UnpackSlotDescriptor(tv.Binary)
			if err != nil {
				t.Fatalf("vector %q: UnpackSlotDescriptor failed: %v", tv.Name, err)
			}

			if desc.ID != tv.ID {
				t.Errorf("vector %q: unpacked ID = %d, want %d", tv.Name, desc.ID, tv.ID)
			}

			if desc.Operations != tv.Operations {
				t.Errorf("vector %q: unpacked Operations = 0x%016x, want 0x%016x",
					tv.Name, desc.Operations, tv.Operations)
			}
		})
	}
}

// TestVectorRoundTrip verifies each vector can be unpacked and re-packed
// to produce identical binary output.
func TestVectorRoundTrip(t *testing.T) {
	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			desc, err := UnpackSlotDescriptor(tv.Binary)
			if err != nil {
				t.Fatalf("vector %q: UnpackSlotDescriptor failed: %v", tv.Name, err)
			}

			repacked := desc.Pack()

			if !bytes.Equal(repacked, tv.Binary) {
				t.Errorf("vector %q: round-trip mismatch", tv.Name)
				for i := range tv.Binary {
					if i < len(repacked) && tv.Binary[i] != repacked[i] {
						t.Errorf("  first diff at byte %d: original=0x%02x repacked=0x%02x",
							i, tv.Binary[i], repacked[i])
						break
					}
				}
			}
		})
	}
}

// TestVectorOperationsConsistency verifies that unpacking the Operations field
// from each vector produces the expected operation chain, and that re-packing
// those operations yields the same packed value.
func TestVectorOperationsConsistency(t *testing.T) {
	expectedOps := map[string][]uint8{
		"raw_data":      {},
		"gzip_only":     {OP_GZIP},
		"tar_gzip":      {OP_TAR, OP_GZIP},
		"complex_chain": {OP_TAR, OP_ZSTD, OP_AES256_GCM},
	}

	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			ops := UnpackOperations(tv.Operations)

			if expected, ok := expectedOps[tv.Name]; ok {
				if !equalSlices(ops, expected) {
					t.Errorf("vector %q: UnpackOperations(0x%016x) = %v, want %v",
						tv.Name, tv.Operations, ops, expected)
				}
			}

			repacked := PackOperations(ops)
			if repacked != tv.Operations {
				t.Errorf("vector %q: PackOperations(%v) = 0x%016x, want 0x%016x",
					tv.Name, ops, repacked, tv.Operations)
			}
		})
	}
}

// TestVectorNoMalformedPatterns verifies the byte data has no suspicious patterns
// that would indicate malformed hex literals (the original bug produced null bytes
// where data should have been, and corrupted field boundaries).
func TestVectorNoMalformedPatterns(t *testing.T) {
	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			desc, err := UnpackSlotDescriptor(tv.Binary)
			if err != nil {
				t.Fatalf("vector %q: UnpackSlotDescriptor failed: %v", tv.Name, err)
			}

			// NameHash (bytes 8-16) should be non-zero for all vectors
			if desc.NameHash == 0 {
				t.Errorf("vector %q: NameHash is zero, likely malformed byte data", tv.Name)
			}

			// Checksum (bytes 48-56) should be non-zero for all vectors
			if desc.Checksum == 0 {
				t.Errorf("vector %q: Checksum is zero, likely malformed byte data", tv.Name)
			}
		})
	}
}

// TestVectorFieldRanges verifies unpacked fields have reasonable values,
// catching issues where split hex bytes produce wrong field values.
func TestVectorFieldRanges(t *testing.T) {
	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			desc, err := UnpackSlotDescriptor(tv.Binary)
			if err != nil {
				t.Fatalf("vector %q: UnpackSlotDescriptor failed: %v", tv.Name, err)
			}

			if desc.ID != tv.ID {
				t.Errorf("vector %q: ID = %d, want %d", tv.Name, desc.ID, tv.ID)
			}

			if desc.Size == 0 {
				t.Errorf("vector %q: Size is zero", tv.Name)
			}
			if desc.OriginalSize == 0 {
				t.Errorf("vector %q: OriginalSize is zero", tv.Name)
			}

			t.Logf("vector %q: ID=%d NameHash=0x%016x Offset=%d Size=%d OrigSize=%d Ops=0x%016x Checksum=0x%x Perms=0%o",
				tv.Name, desc.ID, desc.NameHash, desc.Offset, desc.Size,
				desc.OriginalSize, desc.Operations, desc.Checksum, desc.GetPermissions())
		})
	}
}

// TestVectorExpectedBinaryPrefix verifies the known first 8 bytes of each vector
// as a canary for byte-level corruption.
func TestVectorExpectedBinaryPrefix(t *testing.T) {
	expectedPrefixes := map[string][]byte{
		"raw_data":      {0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // ID=1
		"gzip_only":     {0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // ID=2
		"tar_gzip":      {0x2a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // ID=42
		"complex_chain": {0xe7, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // ID=999
	}

	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			expected, ok := expectedPrefixes[tv.Name]
			if !ok {
				t.Skipf("no expected prefix for vector %q", tv.Name)
			}
			if !bytes.Equal(tv.Binary[:8], expected) {
				t.Errorf("vector %q: first 8 bytes = %x, want %x",
					tv.Name, tv.Binary[:8], expected)
			}
		})
	}
}

// TestVectorExpectedChecksums verifies known checksum values embedded in each vector.
func TestVectorExpectedChecksums(t *testing.T) {
	expectedChecksums := map[string]uint64{
		"raw_data":      0x12345678,
		"gzip_only":     0xABCDEF01,
		"tar_gzip":      0xDEADBEEF,
		"complex_chain": 0xCAFEBABE,
	}

	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			expected, ok := expectedChecksums[tv.Name]
			if !ok {
				t.Skipf("no expected checksum for vector %q", tv.Name)
			}

			desc, err := UnpackSlotDescriptor(tv.Binary)
			if err != nil {
				t.Fatalf("vector %q: UnpackSlotDescriptor failed: %v", tv.Name, err)
			}

			if desc.Checksum != expected {
				t.Errorf("vector %q: Checksum = 0x%x, want 0x%x",
					tv.Name, desc.Checksum, expected)
			}
		})
	}
}

// TestVectorCount ensures we have the expected number of test vectors.
func TestVectorCount(t *testing.T) {
	expected := 4
	if len(regressionVectors) != expected {
		t.Errorf("regressionVectors has %d entries, want %d", len(regressionVectors), expected)
	}

	seen := make(map[string]bool)
	for _, tv := range regressionVectors {
		if seen[tv.Name] {
			t.Errorf("duplicate vector name: %q", tv.Name)
		}
		seen[tv.Name] = true
	}
}

// TestVectorByteAlignment verifies that the Offset field in each vector
// respects 8-byte slot alignment (SlotAlignment constant).
func TestVectorByteAlignment(t *testing.T) {
	for _, tv := range regressionVectors {
		t.Run(tv.Name, func(t *testing.T) {
			desc, err := UnpackSlotDescriptor(tv.Binary)
			if err != nil {
				t.Fatalf("vector %q: UnpackSlotDescriptor failed: %v", tv.Name, err)
			}

			if desc.Offset%SlotAlignment != 0 {
				t.Errorf("vector %q: Offset=%d is not aligned to %d bytes",
					tv.Name, desc.Offset, SlotAlignment)
			}

			fmt.Printf("  %s: offset=%d size=%d original_size=%d\n",
				tv.Name, desc.Offset, desc.Size, desc.OriginalSize)
		})
	}
}
