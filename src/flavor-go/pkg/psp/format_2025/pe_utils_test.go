package format_2025

import (
	"bytes"
	"encoding/binary"
	"math"
	"testing"

	"github.com/hashicorp/go-hclog"
)

type syntheticPELayout struct {
	peOffset            int
	coffOffset          int
	optionalOffset      int
	dataDirOffset       int
	sectionTableOffset  int
	certEntryOffset     int
	debugEntryRVA       uint32
	debugEntryFileOff   int
	debugEntryFieldOff  int
	sectionOneRawOffset uint32
	sectionTwoRawOffset uint32
	sizeOfHeadersOffset int
	checksumOffset      int
}

func buildSyntheticPEForTests(t *testing.T, peOffset int, pe32Plus bool) ([]byte, syntheticPELayout) {
	t.Helper()

	layout := syntheticPELayout{
		peOffset:       peOffset,
		coffOffset:     peOffset + 4,
		optionalOffset: peOffset + 24,
	}
	if pe32Plus {
		layout.dataDirOffset = layout.optionalOffset + 112
	} else {
		layout.dataDirOffset = layout.optionalOffset + 96
	}
	layout.sectionTableOffset = layout.coffOffset + 20 + 0xE0
	layout.certEntryOffset = layout.dataDirOffset + (4 * 8)
	layout.debugEntryRVA = 0x1010
	layout.sectionOneRawOffset = 0x300
	layout.sectionTwoRawOffset = 0x500
	layout.debugEntryFileOff = int(layout.sectionOneRawOffset) + int(layout.debugEntryRVA-0x1000)
	layout.debugEntryFieldOff = layout.debugEntryFileOff + 24
	layout.sizeOfHeadersOffset = layout.optionalOffset + 60
	layout.checksumOffset = layout.optionalOffset + 64

	data := make([]byte, 0x800)
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], uint32(peOffset))
	copy(data[peOffset:peOffset+4], []byte{'P', 'E', 0, 0})

	binary.LittleEndian.PutUint16(data[layout.coffOffset+2:layout.coffOffset+4], 2)
	binary.LittleEndian.PutUint16(data[layout.coffOffset+16:layout.coffOffset+18], 0xE0)

	if pe32Plus {
		binary.LittleEndian.PutUint16(data[layout.optionalOffset:layout.optionalOffset+2], 0x20B)
	} else {
		binary.LittleEndian.PutUint16(data[layout.optionalOffset:layout.optionalOffset+2], 0x10B)
	}
	binary.LittleEndian.PutUint32(data[layout.sizeOfHeadersOffset:layout.sizeOfHeadersOffset+4], 0x200)
	binary.LittleEndian.PutUint32(data[layout.checksumOffset:layout.checksumOffset+4], 0xABCD)

	// Certificate table entry (#4).
	binary.LittleEndian.PutUint32(data[layout.certEntryOffset:layout.certEntryOffset+4], 0x180)
	binary.LittleEndian.PutUint32(data[layout.certEntryOffset+4:layout.certEntryOffset+8], 0x40)

	// Debug directory entry (#6).
	binary.LittleEndian.PutUint32(data[layout.dataDirOffset+(6*8):layout.dataDirOffset+(6*8)+4], layout.debugEntryRVA)
	binary.LittleEndian.PutUint32(data[layout.dataDirOffset+(6*8)+4:layout.dataDirOffset+(6*8)+8], 28)

	writeSectionHeader(data[layout.sectionTableOffset:], ".text", 0x200, 0x1000, layout.sectionOneRawOffset)
	writeSectionHeader(data[layout.sectionTableOffset+40:], ".rdata", 0x200, 0x2000, layout.sectionTwoRawOffset)

	// The debug directory entry itself lives in the first section.
	binary.LittleEndian.PutUint32(data[layout.debugEntryFieldOff:layout.debugEntryFieldOff+4], 0x340)

	return data, layout
}

func writeSectionHeader(data []byte, name string, virtualSize, virtualAddress, rawPointer uint32) {
	copy(data[:8], []byte(name))
	binary.LittleEndian.PutUint32(data[8:12], virtualSize)
	binary.LittleEndian.PutUint32(data[12:16], virtualAddress)
	binary.LittleEndian.PutUint32(data[16:20], 0x200)
	binary.LittleEndian.PutUint32(data[20:24], rawPointer)
}

func TestPEHeaderHelpers(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()

	if !isPEExecutable([]byte("MZ")) {
		t.Fatal("expected MZ prefix to be detected as PE")
	}
	if isPEExecutable([]byte("M")) {
		t.Fatal("expected short data to be rejected as PE")
	}

	peData, _ := buildSyntheticPEForTests(t, 0x80, false)
	offset, err := getPEHeaderOffset(peData)
	if err != nil {
		t.Fatalf("getPEHeaderOffset() error = %v", err)
	}
	if offset != 0x80 {
		t.Fatalf("getPEHeaderOffset() = 0x%x, want 0x80", offset)
	}

	if _, err := getPEHeaderOffset(peData[:0x20]); err == nil {
		t.Fatal("expected getPEHeaderOffset() to reject short DOS header")
	}

	invalidSig := append([]byte(nil), peData...)
	copy(invalidSig[0x80:0x84], []byte{'N', 'O', 'P', 'E'})
	if _, err := getPEHeaderOffset(invalidSig); err == nil {
		t.Fatal("expected getPEHeaderOffset() to reject invalid PE signature")
	}

	if !needsDOSStubExpansion(peData, logger) {
		t.Fatal("expected Go-style PE header to require DOS stub expansion")
	}

	rustStylePE, _ := buildSyntheticPEForTests(t, 0xF0, false)
	if needsDOSStubExpansion(rustStylePE, logger) {
		t.Fatal("expected adequate DOS stub to skip expansion")
	}

	if needsDOSStubExpansion([]byte("not-pe"), logger) {
		t.Fatal("expected non-PE data to skip expansion")
	}
}

func TestExpandDOSStubRewritesOffsets(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	original, layout := buildSyntheticPEForTests(t, 0x80, false)

	expanded, err := expandDOSStub(original, logger)
	if err != nil {
		t.Fatalf("expandDOSStub() error = %v", err)
	}
	if len(expanded) != len(original)+(TargetDOSStubSize-0x80) {
		t.Fatalf("expanded size = %d, want %d", len(expanded), len(original)+(TargetDOSStubSize-0x80))
	}

	newPEOffset, err := getPEHeaderOffset(expanded)
	if err != nil {
		t.Fatalf("getPEHeaderOffset(expanded) error = %v", err)
	}
	if newPEOffset != TargetDOSStubSize {
		t.Fatalf("new PE offset = 0x%x, want 0x%x", newPEOffset, TargetDOSStubSize)
	}

	padded := TargetDOSStubSize - layout.peOffset
	newOptionalOffset := layout.optionalOffset + padded
	newDataDirOffset := layout.dataDirOffset + padded
	newSectionTableOffset := layout.sectionTableOffset + padded
	newDebugEntryOffset := layout.debugEntryFileOff + padded

	if got := binary.LittleEndian.Uint32(expanded[newSectionTableOffset+20 : newSectionTableOffset+24]); got != layout.sectionOneRawOffset+uint32(padded) {
		t.Fatalf("first section raw offset = 0x%x, want 0x%x", got, layout.sectionOneRawOffset+uint32(padded))
	}
	if got := binary.LittleEndian.Uint32(expanded[newSectionTableOffset+60 : newSectionTableOffset+64]); got != layout.sectionTwoRawOffset+uint32(padded) {
		t.Fatalf("second section raw offset = 0x%x, want 0x%x", got, layout.sectionTwoRawOffset+uint32(padded))
	}
	if got := binary.LittleEndian.Uint32(expanded[newOptionalOffset+60 : newOptionalOffset+64]); got != 0x200+uint32(padded) {
		t.Fatalf("SizeOfHeaders = 0x%x, want 0x%x", got, 0x200+uint32(padded))
	}
	if got := binary.LittleEndian.Uint32(expanded[newOptionalOffset+64 : newOptionalOffset+68]); got != 0 {
		t.Fatalf("checksum = 0x%x, want 0", got)
	}
	if got := binary.LittleEndian.Uint32(expanded[newDataDirOffset+32 : newDataDirOffset+36]); got != 0x180+uint32(padded) {
		t.Fatalf("certificate offset = 0x%x, want 0x%x", got, 0x180+uint32(padded))
	}
	if got := binary.LittleEndian.Uint32(expanded[newDebugEntryOffset+24 : newDebugEntryOffset+28]); got != 0x340+uint32(padded) {
		t.Fatalf("debug entry raw pointer = 0x%x, want 0x%x", got, 0x340+uint32(padded))
	}

	if _, found := rvaToFileOffset(expanded, 0x9999, logger); found {
		t.Fatal("expected unmapped RVA to return false")
	}

	overflowData := append([]byte(nil), expanded...)
	binary.LittleEndian.PutUint32(overflowData[newSectionTableOffset+20:newSectionTableOffset+24], math.MaxUint32-0x10)
	if err := updateSectionOffsets(overflowData, 0x20, logger); err == nil {
		t.Fatal("expected updateSectionOffsets() to reject overflow")
	}
}

func TestPEUpdateHelpersEdgeCases(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	data, layout := buildSyntheticPEForTests(t, 0x80, false)

	// Trigger the "certificate offset < 0x80" branch and confirm checksum still clears.
	binary.LittleEndian.PutUint32(data[layout.certEntryOffset:layout.certEntryOffset+4], 0x40)
	binary.LittleEndian.PutUint32(data[layout.checksumOffset:layout.checksumOffset+4], 0xBEEF)
	if err := updateDataDirectories(data, 0x70, logger); err != nil {
		t.Fatalf("updateDataDirectories() error = %v", err)
	}
	if got := binary.LittleEndian.Uint32(data[layout.certEntryOffset : layout.certEntryOffset+4]); got != 0x40 {
		t.Fatalf("certificate offset changed unexpectedly: 0x%x", got)
	}
	if got := binary.LittleEndian.Uint32(data[layout.checksumOffset : layout.checksumOffset+4]); got != 0 {
		t.Fatalf("checksum = 0x%x, want 0", got)
	}

	// Trigger the early-return branch where the data directory entry is truncated.
	shortData := bytes.Repeat([]byte{0}, layout.dataDirOffset+39)
	copy(shortData, data[:layout.optionalOffset+22])
	if err := updateDataDirectories(shortData, 0x70, logger); err != nil {
		t.Fatalf("updateDataDirectories() truncated-data error = %v", err)
	}
}

func TestProcessLauncherForPSPFAndLauncherType(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	if got := GetLauncherType([]byte("plain bytes"), logger); got != "unknown" {
		t.Fatalf("GetLauncherType() = %q, want unknown", got)
	}
	plain := []byte("plain bytes")
	processedPlain, err := ProcessLauncherForPSPF(plain, logger)
	if err != nil {
		t.Fatalf("ProcessLauncherForPSPF(plain) error = %v", err)
	}
	if len(processedPlain) != len(plain) {
		t.Fatalf("ProcessLauncherForPSPF(plain) changed size: got %d want %d", len(processedPlain), len(plain))
	}

	goLauncher, _ := buildSyntheticPEForTests(t, 0x80, false)
	if got := GetLauncherType(goLauncher, logger); got != "go" {
		t.Fatalf("GetLauncherType(go) = %q, want go", got)
	}
	processedGo, err := ProcessLauncherForPSPF(goLauncher, logger)
	if err != nil {
		t.Fatalf("ProcessLauncherForPSPF(go) error = %v", err)
	}
	if len(processedGo) != len(goLauncher) {
		t.Fatalf("ProcessLauncherForPSPF(go) changed size: got %d want %d", len(processedGo), len(goLauncher))
	}

	unknownLauncher, _ := buildSyntheticPEForTests(t, 0x90, false)
	if got := GetLauncherType(unknownLauncher, logger); got != "unknown" {
		t.Fatalf("GetLauncherType(unknown) = %q, want unknown", got)
	}
	processedUnknown, err := ProcessLauncherForPSPF(unknownLauncher, logger)
	if err != nil {
		t.Fatalf("ProcessLauncherForPSPF(unknown) error = %v", err)
	}
	if len(processedUnknown) != len(unknownLauncher) {
		t.Fatalf("ProcessLauncherForPSPF(unknown) changed size: got %d want %d", len(processedUnknown), len(unknownLauncher))
	}

	rustLauncher, _ := buildSyntheticPEForTests(t, 0xF0, false)
	if got := GetLauncherType(rustLauncher, logger); got != "rust" {
		t.Fatalf("GetLauncherType(rust) = %q, want rust", got)
	}
	processedRust, err := ProcessLauncherForPSPF(rustLauncher, logger)
	if err != nil {
		t.Fatalf("ProcessLauncherForPSPF(rust) error = %v", err)
	}
	if len(processedRust) != len(rustLauncher) {
		t.Fatalf("ProcessLauncherForPSPF(rust) changed size: got %d want %d", len(processedRust), len(rustLauncher))
	}
}
