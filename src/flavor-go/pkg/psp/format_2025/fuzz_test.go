package format_2025

import (
	"bytes"
	"testing"
)

// FuzzOperationsRoundTrip verifies pack→unpack is a perfect round-trip
// for any sequence of up to 8 non-zero operation bytes.
func FuzzOperationsRoundTrip(f *testing.F) {
	// Seed with known operation combinations
	f.Add([]byte{OP_GZIP})
	f.Add([]byte{OP_TAR, OP_GZIP})
	f.Add([]byte{OP_GZIP, OP_TAR})
	f.Add([]byte{OP_BZIP2})
	f.Add([]byte{OP_ZSTD, OP_TAR})
	f.Add([]byte{1, 2, 3, 4, 5, 6, 7, 8})
	f.Add([]byte{})

	f.Fuzz(func(t *testing.T, raw []byte) {
		// Filter: keep up to 8 non-zero bytes (zero is the sentinel for "no op")
		ops := make([]uint8, 0, 8)
		for _, b := range raw {
			if b != 0 {
				ops = append(ops, b)
			}
			if len(ops) == 8 {
				break
			}
		}

		packed := PackOperations(ops)
		unpacked := UnpackOperations(packed)

		if len(ops) != len(unpacked) {
			t.Fatalf("length mismatch: pack(%v) -> %d -> unpack -> %v",
				ops, packed, unpacked)
		}
		for i := range ops {
			if ops[i] != unpacked[i] {
				t.Fatalf("element %d: want %d got %d (ops=%v packed=%d unpacked=%v)",
					i, ops[i], unpacked[i], ops, packed, unpacked)
			}
		}
	})
}

// FuzzUnpackSlotDescriptor verifies UnpackSlotDescriptor never panics on
// arbitrary 64-byte inputs and that pack/unpack round-trips perfectly.
func FuzzUnpackSlotDescriptor(f *testing.F) {
	// Seed with known valid vectors
	for _, v := range regressionVectors {
		f.Add(v.Binary)
	}
	// Add edge cases
	f.Add(make([]byte, SlotDescriptorSize))
	f.Add(bytes.Repeat([]byte{0xFF}, SlotDescriptorSize))

	f.Fuzz(func(t *testing.T, data []byte) {
		if len(data) != SlotDescriptorSize {
			return
		}
		desc, err := UnpackSlotDescriptor(data)
		if err != nil {
			return // Parse errors are acceptable
		}
		repacked := desc.Pack()
		if !bytes.Equal(data, repacked) {
			t.Errorf("round-trip mismatch:\n  input:    %x\n  repacked: %x", data, repacked)
		}
	})
}

// FuzzUnpackNoPanic verifies UnpackOperations never panics on arbitrary input.
func FuzzUnpackNoPanic(f *testing.F) {
	f.Add(uint64(0))
	f.Add(uint64(0x0000000000000010))
	f.Add(uint64(0xFFFFFFFFFFFFFFFF))
	f.Add(uint64(0x1001))

	f.Fuzz(func(t *testing.T, packed uint64) {
		ops := UnpackOperations(packed)
		// Re-pack must be consistent
		repacked := PackOperations(ops)
		reopened := UnpackOperations(repacked)
		if len(ops) != len(reopened) {
			t.Fatalf("unpack→pack→unpack length mismatch: %v -> %d -> %v", ops, repacked, reopened)
		}
	})
}
