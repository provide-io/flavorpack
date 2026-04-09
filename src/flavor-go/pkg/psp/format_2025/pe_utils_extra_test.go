//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"encoding/binary"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestNeedsDOSStubExpansionInvalidPESig covers the getPEHeaderOffset failure path
// inside needsDOSStubExpansion: data that looks like MZ but has an invalid PE sig.
func TestNeedsDOSStubExpansionInvalidPESig(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	data := make([]byte, 0x200)
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], 0x80)
	// Write invalid PE signature so getPEHeaderOffset returns an error.
	copy(data[0x80:0x84], []byte{'N', 'O', 'P', 'E'})

	// Should return false (error path → false).
	if needsDOSStubExpansion(data, logger) {
		t.Fatal("expected false when getPEHeaderOffset fails")
	}
}

// TestExpandDOSStubInvalidPESignatureAtOffset covers the getPEHeaderOffset error
// inside expandDOSStub: data has MZ header but invalid signature at pointed offset.
func TestExpandDOSStubInvalidPESignatureAtOffset(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Build a buffer with MZ magic and a small PE offset (triggers expansion attempt),
	// but put an invalid PE signature there so getPEHeaderOffset fails.
	data := make([]byte, 0x200)
	data[0] = 'M'
	data[1] = 'Z'
	// Use offset 0x40 so currentPEOffset < TargetDOSStubSize (expansion needed),
	// but the PE signature at 0x40 is invalid.
	binary.LittleEndian.PutUint32(data[0x3C:0x40], 0x40)
	copy(data[0x40:0x44], []byte{'B', 'A', 'D', '!'})

	_, err := expandDOSStub(data, logger)
	if err == nil {
		t.Fatal("expected error from expandDOSStub when PE signature is invalid")
	}
}

// TestProcessLauncherForPSPFNonPE covers the early return in ProcessLauncherForPSPF
// when the input is not a Windows PE executable (Unix binary path).
func TestProcessLauncherForPSPFNonPE(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Not a PE binary — should be returned unchanged.
	input := []byte("#!/bin/sh\necho hello\n")
	result, err := ProcessLauncherForPSPF(input, logger)
	if err != nil {
		t.Fatalf("ProcessLauncherForPSPF(non-PE) error = %v", err)
	}
	if string(result) != string(input) {
		t.Fatalf("ProcessLauncherForPSPF(non-PE) modified input: got %q want %q", result, input)
	}
}

// TestUpdateDataDirectoriesPE32Plus covers the PE32+ (magic 0x20B) branch in
// updateDataDirectories where dataDirOffset uses +112 instead of +96.
func TestUpdateDataDirectoriesPE32Plus(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Build a PE32+ synthetic PE.
	data, _ := buildSyntheticPEForTests(t, 0x80, true /* pe32Plus */)

	// Should succeed without error.
	if err := updateDataDirectories(data, 0x10, logger); err != nil {
		t.Fatalf("updateDataDirectories(PE32+) error = %v", err)
	}
}

// TestUpdateSectionOffsetsNegativePadding covers the error path where paddingSize < 0.
func TestUpdateSectionOffsetsNegativePadding(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	data, _ := buildSyntheticPEForTests(t, 0x80, false)
	if err := updateSectionOffsets(data, -1, logger); err == nil {
		t.Fatal("expected error for negative paddingSize, got nil")
	}
}

// TestUpdateSectionOffsetsSectionWithZeroRawPointer covers the branch where a section's
// PointerToRawData is 0 (skipped without update). Build a PE where the second section
// has rawPointer=0 to ensure that branch is exercised.
func TestUpdateSectionOffsetsSectionWithZeroRawPointer(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	data, layout := buildSyntheticPEForTests(t, 0x80, false)

	// Overwrite the second section's PointerToRawData with 0.
	secondSectionOffset := layout.sectionTableOffset + 40 // 40 bytes per section header
	ptrOffset := secondSectionOffset + 20                 // PointerToRawData at offset 20
	binary.LittleEndian.PutUint32(data[ptrOffset:ptrOffset+4], 0)

	if err := updateSectionOffsets(data, 0x10, logger); err != nil {
		t.Fatalf("updateSectionOffsets() error = %v", err)
	}

	// Verify zero pointer stayed zero.
	if got := binary.LittleEndian.Uint32(data[ptrOffset : ptrOffset+4]); got != 0 {
		t.Fatalf("expected zero section pointer to remain zero, got 0x%x", got)
	}
}

// TestUpdateDebugDirectoryDebugEntryWithZeroRawPointer covers the branch inside
// updateDebugDirectory where a debug entry's PointerToRawData is > 0 but < 0x80
// (the condition `currentPtr > 0 && currentPtr >= 0x80`), i.e., the entry is skipped.
func TestUpdateDebugDirectoryDebugEntryWithSmallPointer(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	data, layout := buildSyntheticPEForTests(t, 0x80, false)

	// Set debug entry's PointerToRawData to a small value (0x10, < 0x80).
	// The debug entry lives at debugEntryFieldOff+24 relative to the debug struct,
	// but debugEntryFieldOff already points to the PointerToRawData field in the layout.
	binary.LittleEndian.PutUint32(data[layout.debugEntryFieldOff:layout.debugEntryFieldOff+4], 0x10)

	if err := updateDebugDirectory(data, 0x70, logger); err != nil {
		t.Fatalf("updateDebugDirectory() error = %v", err)
	}

	// Pointer should be unchanged because it's < 0x80.
	if got := binary.LittleEndian.Uint32(data[layout.debugEntryFieldOff : layout.debugEntryFieldOff+4]); got != 0x10 {
		t.Fatalf("expected debug pointer to remain 0x10, got 0x%x", got)
	}
}

// TestUpdateDebugDirectoryPE32Plus covers the PE32+ (magic 0x20B) branch in
// updateDebugDirectory where dataDirOffset uses +112 instead of +96.
func TestUpdateDebugDirectoryPE32Plus(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Build a PE32+ synthetic PE.
	data, _ := buildSyntheticPEForTests(t, 0x80, true /* pe32Plus */)

	if err := updateDebugDirectory(data, 0x10, logger); err != nil {
		t.Fatalf("updateDebugDirectory(PE32+) error = %v", err)
	}
}

// TestUpdateDebugDirectoryEntryPointerBeyondBounds covers the loop branch inside
// updateDebugDirectory where the debug entry's PointerToRawData field itself is
// beyond the file bounds (the `ptrRawDataOffset+4 > len(data)` check). We do this
// by truncating the data just before the PointerToRawData field (last 4 bytes of entry).
func TestUpdateDebugDirectoryEntryPointerFieldBeyondBounds(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	data, layout := buildSyntheticPEForTests(t, 0x80, false)

	// The debug entry offset = debugEntryFileOff.
	// PointerToRawData is at offset 24 within a 28-byte IMAGE_DEBUG_DIRECTORY entry.
	// ptrRawDataOffset = debugEntryFileOff + 24.
	// Truncate to debugEntryFileOff + 26 (just before the 4-byte field).
	ptrRawDataOffset := layout.debugEntryFileOff + 24
	truncated := data[:ptrRawDataOffset+2] // only 2 bytes before the field needs 4

	if err := updateDebugDirectory(truncated, 0x70, logger); err != nil {
		t.Fatalf("updateDebugDirectory() error = %v for truncated entry pointer field", err)
	}
}
