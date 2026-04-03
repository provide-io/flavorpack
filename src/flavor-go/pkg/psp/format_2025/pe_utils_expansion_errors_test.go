//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"encoding/binary"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// buildMinimalPEAtOffset80 builds a minimal PE binary at peOffset 0x80 with
// zero sections and zero optional header size.  It is small enough that after
// DOS-stub expansion (adding 0x70 bytes of padding to reach 0xF0) the
// expanded binary will be too short for updateSizeOfHeaders to access the
// SizeOfHeaders field (which lives at newPEOffset + 4 + 20 + 60 = 0x144,
// requiring at least 0x148 bytes; expanded size is only 0x106).
//
// The binary must be at least 0x96 bytes so that updateSectionOffsets can
// read the optional-header-size field (coffOffset+16 = 0x94) from the
// already-expanded buffer.
func buildMinimalPEAtOffset80ForTests() []byte {
	const size = 0x96 // 150 bytes — big enough for section-offset pass, too small for SizeOfHeaders
	data := make([]byte, size)
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], 0x80) // e_lfanew -> PE at 0x80
	copy(data[0x80:0x84], []byte{'P', 'E', 0, 0})
	// COFF header: NumberOfSections=0 (offset 0x86 = coffOffset+2)
	binary.LittleEndian.PutUint16(data[0x86:0x88], 0)
	// Optional header size = 0 (offset 0x94 = coffOffset+16)
	binary.LittleEndian.PutUint16(data[0x94:0x96], 0)
	return data
}

// ---------------------------------------------------------------------------
// expandDOSStub: updateSizeOfHeaders failure path
// ---------------------------------------------------------------------------

// TestExpandDOSStubSizeOfHeadersFails covers the error path inside expandDOSStub
// where updateSizeOfHeaders fails because the expanded binary is too short to
// contain the SizeOfHeaders field.
//
// The minimal PE at 0x80 with 0 sections expands from 150 bytes to 262 bytes.
// updateSizeOfHeaders looks for the field at expanded-peOffset+4+80 = 0x144,
// requiring at least 0x148 bytes — which 262 (0x106) does not satisfy.
func TestExpandDOSStubSizeOfHeadersFails(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	data := buildMinimalPEAtOffset80ForTests()

	_, err := expandDOSStub(data, logger)
	if err == nil {
		t.Fatal("expected error from expandDOSStub when SizeOfHeaders field is beyond file bounds, got nil")
	}
}

// ---------------------------------------------------------------------------
// ProcessLauncherForPSPF: unknown launcher type path
// ---------------------------------------------------------------------------

// TestProcessLauncherForPSPFUnknownType covers the "unknown" launcher type
// default branch in ProcessLauncherForPSPF (PE with offset between 0x81 and 0xE7).
func TestProcessLauncherForPSPFUnknownType(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()

	// Build a PE with offset 0xA0 — not 0x80 (go), not >= 0xE8 (rust), so "unknown"
	data := make([]byte, 0x200)
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], 0xA0)
	copy(data[0xA0:0xA4], []byte{'P', 'E', 0, 0})

	result, err := ProcessLauncherForPSPF(data, logger)
	if err != nil {
		t.Fatalf("ProcessLauncherForPSPF(unknown) error = %v", err)
	}
	if len(result) != len(data) {
		t.Fatalf("ProcessLauncherForPSPF(unknown) changed data length: got %d, want %d", len(result), len(data))
	}
}
