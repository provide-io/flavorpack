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

// TestBytesEqualEqualSlices covers the happy path where two identical slices compare equal.
func TestBytesEqualEqualSlices(t *testing.T) {
	t.Parallel()

	a := []byte{0x01, 0x02, 0x03}
	b := []byte{0x01, 0x02, 0x03}
	if !bytesEqual(a, b) {
		t.Fatal("expected bytesEqual to return true for equal slices")
	}

	// Different lengths
	if bytesEqual(a, []byte{0x01, 0x02}) {
		t.Fatal("expected bytesEqual to return false for different-length slices")
	}

	// Same length, different content
	if bytesEqual(a, []byte{0x01, 0x02, 0xFF}) {
		t.Fatal("expected bytesEqual to return false for different content")
	}
}

// TestGetPEHeaderOffsetDataTooShortForSig covers the path where data has a valid
// DOS header (>= 0x40 bytes) but is truncated before the PE signature.
func TestGetPEHeaderOffsetDataTooShortForSig(t *testing.T) {
	t.Parallel()

	// Build a minimal DOS header pointing to PE offset 0x80, but truncate the
	// data so it doesn't include the full 4-byte PE signature.
	data := make([]byte, 0x82) // just 0x82 bytes — PE sig would need 0x80..0x83
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], 0x80)
	// Don't write PE signature — data ends at 0x82, PE sig needs 0x84

	_, err := getPEHeaderOffset(data)
	if err == nil {
		t.Fatal("expected error when data is too short to contain PE header at the indicated offset")
	}
}

// TestNeedsDOSStubExpansionAtExactTarget covers the "PE at offset 0x80 == 0x80 already"
// branch — this PE offset equals the Go minimal size but also equals TargetDOSStubSize.
// Wait: TargetDOSStubSize is 0xF0, so 0x80 != 0x80 from that perspective.
// The actual gap: needsDOSStubExpansion returns true for 0x80, false for >= 0x81 (non-0x80).
// The uncovered branch is the "adequate DOS stub" trace path (peOffset != 0x80).
// Build PE at offset 0x90 (neither Go 0x80 nor Rust 0xF0) → returns false, hits the Trace log.
func TestNeedsDOSStubExpansionAdequateSize(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()
	// 0x90 is not 0x80 → returns false, covers the Trace log branch
	peData, _ := buildSyntheticPEForTests(t, 0x90, false)
	if needsDOSStubExpansion(peData, logger) {
		t.Fatal("expected needsDOSStubExpansion to return false for PE at 0x90")
	}
}

// TestExpandDOSStubAlreadyAdequate covers the early-return path where the current
// PE offset is already >= TargetDOSStubSize.
func TestExpandDOSStubAlreadyAdequate(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Build PE at exactly TargetDOSStubSize (0xF0) — already at target, no expansion needed.
	peData, _ := buildSyntheticPEForTests(t, TargetDOSStubSize, false)
	result, err := expandDOSStub(peData, logger)
	if err != nil {
		t.Fatalf("expandDOSStub() error = %v", err)
	}
	// Should return the original data unchanged.
	if len(result) != len(peData) {
		t.Fatalf("expandDOSStub() changed size unexpectedly: got %d want %d", len(result), len(peData))
	}
}

// TestExpandDOSStubNonPEData covers the error path where data is not a PE executable.
func TestExpandDOSStubNonPEData(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	_, err := expandDOSStub([]byte("this is not a PE binary"), logger)
	if err == nil {
		t.Fatal("expected error for non-PE input to expandDOSStub")
	}
}

// TestUpdateSizeOfHeadersBeyondBounds covers the "offset beyond file bounds" error.
func TestUpdateSizeOfHeadersBeyondBounds(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Build minimal data that has a valid e_lfanew pointer but the SizeOfHeaders
	// field would be beyond the buffer.
	// coffOffset = peOffset + 4, sizeOfHeadersOffset = coffOffset + 20 + 60 = peOffset + 84
	// peOffset = 0x80 = 128; sizeOfHeadersOffset = 128 + 84 = 212
	// Truncate data to 210 bytes → beyond bounds.
	peData, _ := buildSyntheticPEForTests(t, 0x80, false)
	truncated := peData[:212] // just below sizeOfHeadersOffset + 4

	if err := updateSizeOfHeaders(truncated, 0x70, logger); err == nil {
		t.Fatal("expected error when SizeOfHeaders offset is beyond file bounds")
	}
}

// TestUpdateDebugDirectoryNoRdataSection covers the path where rvaToFileOffset
// returns (0, false) because the debug directory RVA cannot be mapped to a file offset.
// We do this by setting a debug RVA that points outside any section.
func TestUpdateDebugDirectoryRVANotMapped(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Build a synthetic PE and then set the debug directory RVA to something
	// that doesn't fall within any section.
	data, layout := buildSyntheticPEForTests(t, 0x80, false)

	// Set debug directory RVA to 0xFFFF0000 — well outside any section.
	debugDirEntryOffset := layout.dataDirOffset + (6 * 8)
	binary.LittleEndian.PutUint32(data[debugDirEntryOffset:debugDirEntryOffset+4], 0xFFFF0000)
	binary.LittleEndian.PutUint32(data[debugDirEntryOffset+4:debugDirEntryOffset+8], 28)

	// Should not return an error — the unmapped RVA path returns nil (skips update).
	if err := updateDebugDirectory(data, 0x70, logger); err != nil {
		t.Fatalf("updateDebugDirectory() error = %v when RVA not mapped", err)
	}
}

// TestUpdateDebugDirectoryNoDebugDir covers the path where the debug directory
// RVA or size is zero (no debug directory present) — returns nil immediately.
func TestUpdateDebugDirectoryNoDebugDir(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	data, layout := buildSyntheticPEForTests(t, 0x80, false)
	// Zero out the debug directory RVA/size to simulate "no debug directory".
	debugDirEntryOffset := layout.dataDirOffset + (6 * 8)
	binary.LittleEndian.PutUint32(data[debugDirEntryOffset:debugDirEntryOffset+4], 0)
	binary.LittleEndian.PutUint32(data[debugDirEntryOffset+4:debugDirEntryOffset+8], 0)

	if err := updateDebugDirectory(data, 0x70, logger); err != nil {
		t.Fatalf("updateDebugDirectory() error = %v when debug dir is absent", err)
	}
}

// TestUpdateDebugDirectoryEntryBeyondBounds covers the path where the debug directory
// entry offset itself is beyond file bounds (early return nil).
func TestUpdateDebugDirectoryEntryBeyondBounds(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	data, layout := buildSyntheticPEForTests(t, 0x80, false)
	// Truncate to just before the debug directory entry (need at least 8 bytes for it).
	debugDirEntryOffset := layout.dataDirOffset + (6 * 8)
	truncated := data[:debugDirEntryOffset+6] // only 6 bytes, entry needs 8

	if err := updateDebugDirectory(truncated, 0x70, logger); err != nil {
		t.Fatalf("updateDebugDirectory() error = %v for truncated data (should skip)", err)
	}
}

// TestGetLauncherTypeGoMarkerAbsent covers the GetLauncherType branch where peOffset
// is between 0x81 and 0xE7 (neither Go 0x80 nor Rust 0xE8+).
func TestGetLauncherTypeUnknownOffset(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// PE at 0xA0: not 0x80, not >= 0xE8 → "unknown"
	peData, _ := buildSyntheticPEForTests(t, 0xA0, false)
	if got := GetLauncherType(peData, logger); got != "unknown" {
		t.Fatalf("GetLauncherType() = %q, want %q", got, "unknown")
	}
}

// TestProcessLauncherForPSPFRustNeedsExpansion covers the ProcessLauncherForPSPF path
// where the launcher is detected as "rust" (PE offset >= 0xE8) but needsDOSStubExpansion
// returns true (PE offset == 0x80). Actually, for Rust detection we need offset >= 0xE8
// but < TargetDOSStubSize (0xF0) so expansion IS needed. Use offset 0xE8.
func TestProcessLauncherForPSPFRustNeedsExpansion(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// PE at 0xE8: detected as "rust" (>= 0xE8), and 0xE8 < TargetDOSStubSize (0xF0)
	// so needsDOSStubExpansion would return... wait, needsDOSStubExpansion checks
	// peOffset == 0x80 specifically. 0xE8 != 0x80 → returns false.
	// So this path actually doesn't trigger expansion.
	// The "rust needs expansion" would need peOffset == 0x80 but type == "rust",
	// which is mutually exclusive (0x80 → "go").
	// Therefore the "rust + needsDOSStubExpansion=true" branch is structurally unreachable.
	// We test "rust + already adequate" (0xE8 with needsDOSStubExpansion=false).
	rustAtE8, _ := buildSyntheticPEForTests(t, 0xE8, false)
	if got := GetLauncherType(rustAtE8, logger); got != "rust" {
		t.Fatalf("GetLauncherType() = %q, want rust for 0xE8", got)
	}
	result, err := ProcessLauncherForPSPF(rustAtE8, logger)
	if err != nil {
		t.Fatalf("ProcessLauncherForPSPF(rust 0xE8) error = %v", err)
	}
	if len(result) != len(rustAtE8) {
		t.Fatalf("ProcessLauncherForPSPF(rust 0xE8) changed size: got %d want %d", len(result), len(rustAtE8))
	}
}

// TestGetLauncherTypeInvalidPESignature covers the GetLauncherType path where
// getPEHeaderOffset returns an error (invalid PE signature at the indicated offset).
func TestGetLauncherTypeInvalidPESignature(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// Build a synthetic PE with invalid PE signature (not 'PE\x00\x00').
	data := make([]byte, 0x200)
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], 0x80)
	// Write invalid PE signature — getPEHeaderOffset will fail.
	copy(data[0x80:0x84], []byte{'N', 'O', 'P', 'E'})

	if got := GetLauncherType(data, logger); got != "unknown" {
		t.Fatalf("GetLauncherType() = %q, want %q for invalid PE sig", got, "unknown")
	}
}

// TestProcessLauncherForPSPFWithRustNeedingExpansion covers the Rust launcher path
// where needsDOSStubExpansion returns true (PE at 0x80 but type detected as rust).
// NOTE: GetLauncherType returns "go" for 0x80, "rust" for >= 0xE8.
// To exercise the "rust but already adequate" branch, build PE at 0xF0.
// The "rust needs expansion" branch would need PE at exactly 0x80 typed as "rust" —
// not achievable without modification. Instead test "rust already adequate" (0xF0 >= TargetDOSStubSize).
func TestProcessLauncherForPSPFRustAlreadyAdequate(t *testing.T) {
	t.Parallel()

	logger := logging.NewNullLogger()

	// PE at 0xF0 = TargetDOSStubSize: detected as rust, needsDOSStubExpansion returns false.
	rustLauncher, _ := buildSyntheticPEForTests(t, 0xF0, false)
	result, err := ProcessLauncherForPSPF(rustLauncher, logger)
	if err != nil {
		t.Fatalf("ProcessLauncherForPSPF(rust adequate) error = %v", err)
	}
	if len(result) != len(rustLauncher) {
		t.Fatalf("ProcessLauncherForPSPF(rust adequate) changed size: got %d want %d", len(result), len(rustLauncher))
	}
}
