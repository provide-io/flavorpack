//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

// Package format_2025 implements the PSPF/2025 format specification
package format_2025

import (
	"encoding/binary"
	"fmt"

	"github.com/hashicorp/go-hclog"
)

// TargetDOSStubSize is the target DOS stub size to match Rust MSVC binaries (240 bytes / 0xF0)
const TargetDOSStubSize = 0xF0

// isPEExecutable checks if data starts with a valid Windows PE executable header.
// Returns true if data starts with "MZ" signature (PE executable)
func isPEExecutable(data []byte) bool {
	return len(data) >= 2 && data[0] == 'M' && data[1] == 'Z'
}

// getPEHeaderOffset reads the PE header offset from the DOS header.
// The offset is stored at position 0x3C (e_lfanew field) as a 4-byte little-endian integer.
// Returns the PE header offset, or an error if invalid.
func getPEHeaderOffset(data []byte) (int, error) {
	if len(data) < 0x40 {
		return 0, fmt.Errorf("data too short to contain DOS header")
	}

	// Read e_lfanew field at offset 0x3C (little-endian uint32)
	peOffset := int(binary.LittleEndian.Uint32(data[0x3C:0x40]))

	// Validate PE signature at that offset
	if len(data) < peOffset+4 {
		return 0, fmt.Errorf("data too short to contain PE header at offset 0x%x", peOffset)
	}

	peSignature := data[peOffset : peOffset+4]
	expectedSig := []byte{'P', 'E', 0, 0}
	if !bytesEqual(peSignature, expectedSig) {
		return 0, fmt.Errorf("invalid PE signature at offset 0x%x: expected 'PE\\x00\\x00', got %v", peOffset, peSignature)
	}

	return peOffset, nil
}

// needsDOSStubExpansion checks if a PE executable needs DOS stub expansion.
// Go binaries use minimal DOS stub (128 bytes / 0x80) which is incompatible
// with Windows PE loader when PSPF data is appended. This function detects such binaries.
// Returns true if DOS stub needs expansion (Go binary with 0x80 stub)
func needsDOSStubExpansion(data []byte, logger hclog.Logger) bool {
	if !isPEExecutable(data) {
		return false
	}

	peOffset, err := getPEHeaderOffset(data)
	if err != nil {
		return false
	}

	// Check if this is a Go binary with minimal DOS stub (0x80 = 128 bytes)
	// Rust/MSVC binaries typically use 0xE8-0xF0 (232-240 bytes)
	if peOffset == 0x80 {
		logger.Debug("Detected Go binary with minimal DOS stub", "pe_offset", fmt.Sprintf("0x%x", peOffset), "dos_stub_size", peOffset)
		return true
	}

	logger.Trace("PE binary has adequate DOS stub size", "pe_offset", fmt.Sprintf("0x%x", peOffset), "dos_stub_size", peOffset)
	return false
}

// updateSectionOffsets updates PointerToRawData values in section table.
// When expanding DOS stub, all file content shifts forward. Section table
// entries must be updated to reflect new section locations.
//
// Args:
//   - data: PE executable data (modified in-place)
//   - paddingSize: Number of bytes added to DOS stub
//   - logger: Logger instance
//
// Returns error if operation fails
func updateSectionOffsets(data []byte, paddingSize int, logger hclog.Logger) error {
	// Get PE header location
	peOffset := int(binary.LittleEndian.Uint32(data[0x3C:0x40]))
	coffOffset := peOffset + 4

	// Read number of sections
	numSections := int(binary.LittleEndian.Uint16(data[coffOffset+2 : coffOffset+4]))

	// Read optional header size
	optHdrSize := int(binary.LittleEndian.Uint16(data[coffOffset+16 : coffOffset+18]))

	// Section table offset
	sectionTableOffset := coffOffset + 20 + optHdrSize

	logger.Debug("Updating section offsets",
		"num_sections", numSections,
		"padding_size", paddingSize)

	// Update each section's PointerToRawData
	updated := 0
	for i := 0; i < numSections; i++ {
		sectionOffset := sectionTableOffset + (i * 40)
		ptrOffset := sectionOffset + 20

		// Read current PointerToRawData
		currentPtr := binary.LittleEndian.Uint32(data[ptrOffset : ptrOffset+4])

		// Update if non-zero
		if currentPtr > 0 {
			newPtr := currentPtr + uint32(paddingSize)
			binary.LittleEndian.PutUint32(data[ptrOffset:ptrOffset+4], newPtr)

			logger.Trace("Updated section offset",
				"section", i,
				"old_offset", fmt.Sprintf("0x%x", currentPtr),
				"new_offset", fmt.Sprintf("0x%x", newPtr))
			updated++
		}
	}

	logger.Debug("Section offsets updated",
		"updated_count", updated,
		"total_sections", numSections)

	return nil
}

// updateDataDirectories updates data directory file offsets after DOS stub expansion.
// The Certificate Table (data directory entry #4) is special: it uses absolute
// file offsets instead of RVAs. When the DOS stub expands, this offset must
// be updated. Other data directories use RVAs (relative to image base) and
// don't need updating.
//
// Args:
//   - data: PE executable data (modified in-place)
//   - paddingSize: Number of bytes added to DOS stub
//   - logger: Logger instance
//
// Returns error if operation fails
func updateDataDirectories(data []byte, paddingSize int, logger hclog.Logger) error {
	// Get PE header location
	peOffset := int(binary.LittleEndian.Uint32(data[0x3C:0x40]))
	coffOffset := peOffset + 4

	// Read magic number to identify PE32 vs PE32+
	magic := binary.LittleEndian.Uint16(data[coffOffset+20 : coffOffset+22])
	isPE32Plus := magic == 0x20B

	// Data directory offset in optional header
	// PE32: starts at optional header + 96
	// PE32+: starts at optional header + 112
	var dataDirOffset int
	if isPE32Plus {
		dataDirOffset = coffOffset + 20 + 112
	} else {
		dataDirOffset = coffOffset + 20 + 96
	}

	// Certificate Table is the 5th entry (index 4) in data directory array
	// Each entry is 8 bytes (4 bytes RVA/offset + 4 bytes size)
	certEntryOffset := dataDirOffset + (4 * 8)

	if certEntryOffset+8 > len(data) {
		logger.Trace("Certificate table entry beyond file bounds, skipping update",
			"entry_offset", fmt.Sprintf("0x%x", certEntryOffset),
			"file_size", len(data))
		return nil
	}

	// Read certificate table entry
	certFileOffset := binary.LittleEndian.Uint32(data[certEntryOffset : certEntryOffset+4])
	certSize := binary.LittleEndian.Uint32(data[certEntryOffset+4 : certEntryOffset+8])

	logger.Trace("Checked certificate table",
		"offset", fmt.Sprintf("0x%x", certFileOffset),
		"size", certSize)

	// Update certificate table offset if it exists and is after the DOS stub
	if certFileOffset >= 0x80 {
		newCertOffset := certFileOffset + uint32(paddingSize)
		binary.LittleEndian.PutUint32(data[certEntryOffset:certEntryOffset+4], newCertOffset)
		logger.Debug("Updated certificate table offset",
			"old_offset", fmt.Sprintf("0x%x", certFileOffset),
			"new_offset", fmt.Sprintf("0x%x", newCertOffset))
	}

	// Zero out PE checksum (not validated for executable files, only for drivers/DLLs)
	// CheckSum field is at optional header + 64
	checksumOffset := coffOffset + 20 + 64
	binary.LittleEndian.PutUint32(data[checksumOffset:checksumOffset+4], 0)
	logger.Trace("Zeroed PE checksum (not required for executables)")

	return nil
}

// rvaToFileOffset maps a Relative Virtual Address (RVA) to a file offset
// by walking the section table. Returns (fileOffset, found).
func rvaToFileOffset(data []byte, rva uint32, logger hclog.Logger) (uint32, bool) {
	// Get PE header location
	peOffset := int(binary.LittleEndian.Uint32(data[0x3C:0x40]))
	coffOffset := peOffset + 4

	// Read number of sections
	numSections := int(binary.LittleEndian.Uint16(data[coffOffset+2 : coffOffset+4]))

	// Read optional header size
	optHdrSize := int(binary.LittleEndian.Uint16(data[coffOffset+16 : coffOffset+18]))

	// Section table offset
	sectionTableOffset := coffOffset + 20 + optHdrSize

	// Walk section table to find which section contains this RVA
	for i := 0; i < numSections; i++ {
		sectionOffset := sectionTableOffset + (i * 40)

		// Read section header fields
		// VirtualAddress is at offset 12 in section header
		// VirtualSize is at offset 8 in section header
		// PointerToRawData is at offset 20 in section header
		// SizeOfRawData is at offset 16 in section header

		virtualAddr := binary.LittleEndian.Uint32(data[sectionOffset+12 : sectionOffset+16])
		virtualSize := binary.LittleEndian.Uint32(data[sectionOffset+8 : sectionOffset+12])
		pointerToRawData := binary.LittleEndian.Uint32(data[sectionOffset+20 : sectionOffset+24])

		// Check if RVA falls within this section
		if rva >= virtualAddr && rva < virtualAddr+virtualSize {
			// Calculate offset within section and convert to file offset
			offsetWithinSection := rva - virtualAddr
			fileOffset := pointerToRawData + offsetWithinSection
			logger.Trace("Mapped RVA to file offset",
				"rva", fmt.Sprintf("0x%x", rva),
				"section", i,
				"section_va", fmt.Sprintf("0x%x", virtualAddr),
				"file_offset", fmt.Sprintf("0x%x", fileOffset))
			return fileOffset, true
		}
	}

	logger.Trace("RVA not found in any section",
		"rva", fmt.Sprintf("0x%x", rva))
	return 0, false
}

// updateDebugDirectory updates PointerToRawData values in debug directory entries.
// The Debug Directory (data directory entry #6) contains an array of IMAGE_DEBUG_DIRECTORY
// structures. Each structure has both AddressOfRawData (RVA, doesn't need updating) and
// PointerToRawData (absolute file offset, MUST be updated when DOS stub expands).
//
// Args:
//   - data: PE executable data (modified in-place)
//   - paddingSize: Number of bytes added to DOS stub
//   - logger: Logger instance
//
// Returns error if operation fails
func updateDebugDirectory(data []byte, paddingSize int, logger hclog.Logger) error {
	// Get PE header location
	peOffset := int(binary.LittleEndian.Uint32(data[0x3C:0x40]))
	coffOffset := peOffset + 4

	// Read magic number to identify PE32 vs PE32+
	magic := binary.LittleEndian.Uint16(data[coffOffset+20 : coffOffset+22])
	isPE32Plus := magic == 0x20B

	// Data directory offset in optional header
	var dataDirOffset int
	if isPE32Plus {
		dataDirOffset = coffOffset + 20 + 112
	} else {
		dataDirOffset = coffOffset + 20 + 96
	}

	// Debug Directory is the 7th entry (index 6) in data directory array
	// Each entry is 8 bytes (4 bytes RVA + 4 bytes size)
	debugDirEntryOffset := dataDirOffset + (6 * 8)

	if debugDirEntryOffset+8 > len(data) {
		logger.Trace("Debug directory entry beyond file bounds, skipping",
			"entry_offset", fmt.Sprintf("0x%x", debugDirEntryOffset))
		return nil
	}

	// Read debug directory entry (RVA and size)
	debugDirRVA := binary.LittleEndian.Uint32(data[debugDirEntryOffset : debugDirEntryOffset+4])
	debugDirSize := binary.LittleEndian.Uint32(data[debugDirEntryOffset+4 : debugDirEntryOffset+8])

	// If no debug directory, skip
	if debugDirRVA == 0 || debugDirSize == 0 {
		logger.Trace("No debug directory present (RVA or size is 0)")
		return nil
	}

	// Map debug directory RVA to file offset
	debugDirFileOffset, found := rvaToFileOffset(data, debugDirRVA, logger)
	if !found {
		logger.Trace("Unable to map debug directory RVA to file offset, skipping debug directory update",
			"debug_dir_rva", fmt.Sprintf("0x%x", debugDirRVA))
		return nil
	}

	logger.Debug("Found debug directory",
		"rva", fmt.Sprintf("0x%x", debugDirRVA),
		"file_offset", fmt.Sprintf("0x%x", debugDirFileOffset),
		"size", debugDirSize)

	// Calculate number of debug directory entries
	// Each IMAGE_DEBUG_DIRECTORY is 28 bytes
	numDebugEntries := int(debugDirSize) / 28
	logger.Debug("Debug directory entry count", "count", numDebugEntries)

	// Update each debug directory entry's PointerToRawData field
	// IMAGE_DEBUG_DIRECTORY structure:
	//   offset 0: Characteristics (4 bytes)
	//   offset 4: TimeDateStamp (4 bytes)
	//   offset 8: MajorVersion (2 bytes)
	//   offset 10: MinorVersion (2 bytes)
	//   offset 12: Type (4 bytes)
	//   offset 16: SizeOfData (4 bytes)
	//   offset 20: AddressOfRawData (4 bytes, RVA)
	//   offset 24: PointerToRawData (4 bytes, FILE OFFSET) ← THIS NEEDS UPDATE

	updated := 0
	for i := 0; i < numDebugEntries; i++ {
		entryOffset := int(debugDirFileOffset) + (i * 28)

		// PointerToRawData is at offset 24 within the debug directory entry
		ptrRawDataOffset := entryOffset + 24

		if ptrRawDataOffset+4 > len(data) {
			logger.Trace("Debug entry PointerToRawData beyond file bounds",
				"entry", i,
				"offset", fmt.Sprintf("0x%x", ptrRawDataOffset))
			continue
		}

		// Read current PointerToRawData
		currentPtr := binary.LittleEndian.Uint32(data[ptrRawDataOffset : ptrRawDataOffset+4])

		// Update if non-zero and >= 0x80 (after DOS stub start)
		if currentPtr > 0 && currentPtr >= 0x80 {
			newPtr := currentPtr + uint32(paddingSize)
			binary.LittleEndian.PutUint32(data[ptrRawDataOffset:ptrRawDataOffset+4], newPtr)

			logger.Trace("Updated debug entry PointerToRawData",
				"entry", i,
				"old_offset", fmt.Sprintf("0x%x", currentPtr),
				"new_offset", fmt.Sprintf("0x%x", newPtr))
			updated++
		}
	}

	if updated > 0 {
		logger.Debug("Updated debug directory entries",
			"updated_count", updated,
			"total_entries", numDebugEntries)
	}

	return nil
}

// updateSizeOfHeaders updates the SizeOfHeaders field in the Optional Header after DOS stub expansion.
//
// The SizeOfHeaders field specifies the combined size of the DOS stub, PE headers,
// and section table, rounded to the file alignment. When the DOS stub expands,
// this field must be updated to match the new total header size.
//
// Windows PE loader validates that sections start at or after SizeOfHeaders.
// A mismatch causes loader rejection, especially on ARM64 (exit code 126).
func updateSizeOfHeaders(data []byte, paddingSize int, logger hclog.Logger) error {
	// Get PE header location
	peOffset := binary.LittleEndian.Uint32(data[0x3C:0x40])
	coffOffset := int(peOffset) + 4

	// SizeOfHeaders is at optional header + 60 bytes
	// Optional header starts at COFF header + 20
	sizeOfHeadersOffset := coffOffset + 20 + 60

	if sizeOfHeadersOffset+4 > len(data) {
		return fmt.Errorf("SizeOfHeaders offset 0x%x beyond file bounds", sizeOfHeadersOffset)
	}

	// Read current SizeOfHeaders value
	currentSize := binary.LittleEndian.Uint32(data[sizeOfHeadersOffset : sizeOfHeadersOffset+4])

	// Update to reflect expanded DOS stub
	newSize := currentSize + uint32(paddingSize)
	binary.LittleEndian.PutUint32(data[sizeOfHeadersOffset:sizeOfHeadersOffset+4], newSize)

	logger.Debug("Updated SizeOfHeaders field",
		"old_size", fmt.Sprintf("0x%x", currentSize),
		"new_size", fmt.Sprintf("0x%x", newSize),
		"padding", paddingSize)

	return nil
}

// expandDOSStub expands the DOS stub of a PE executable to match Rust/MSVC binary size.
// This fixes Windows PE loader rejection of Go binaries when PSPF data is appended.
// The DOS stub is expanded from 128 bytes (0x80) to 240 bytes (0xF0) to match Rust binaries.
//
// Process:
// 1. Extract MZ header and DOS stub (first 64 bytes + stub code)
// 2. Extract PE header and remainder
// 3. Insert padding to expand stub to target size
// 4. Update e_lfanew pointer to new PE offset
//
// Returns the modified PE executable with expanded DOS stub, or an error if data is invalid.
func expandDOSStub(data []byte, logger hclog.Logger) ([]byte, error) {
	if !isPEExecutable(data) {
		return nil, fmt.Errorf("data is not a Windows PE executable")
	}

	currentPEOffset, err := getPEHeaderOffset(data)
	if err != nil {
		return nil, fmt.Errorf("invalid PE header offset: %w", err)
	}

	if currentPEOffset >= TargetDOSStubSize {
		logger.Debug("DOS stub already adequate size",
			"current", fmt.Sprintf("0x%x", currentPEOffset),
			"target", fmt.Sprintf("0x%x", TargetDOSStubSize))
		return data, nil
	}

	// Calculate padding needed
	paddingSize := TargetDOSStubSize - currentPEOffset

	logger.Info("Expanding DOS stub for Windows compatibility",
		"current_pe_offset", fmt.Sprintf("0x%x", currentPEOffset),
		"target_pe_offset", fmt.Sprintf("0x%x", TargetDOSStubSize),
		"padding_bytes", paddingSize)

	// Build new executable:
	// 1. MZ header + DOS stub (up to current PE offset)
	// 2. Padding (zeros to expand stub)
	// 3. PE header and remainder
	newData := make([]byte, 0, len(data)+paddingSize)
	newData = append(newData, data[:currentPEOffset]...)
	newData = append(newData, make([]byte, paddingSize)...)
	newData = append(newData, data[currentPEOffset:]...)

	// Update e_lfanew pointer at offset 0x3C to point to new PE header location
	binary.LittleEndian.PutUint32(newData[0x3C:0x40], uint32(TargetDOSStubSize))

	// CRITICAL: Update section offsets
	// When we shift the file content forward, section data moves but the section
	// table entries still point to old offsets. We must update them.
	if err := updateSectionOffsets(newData, paddingSize, logger); err != nil {
		return nil, fmt.Errorf("failed to update section offsets: %w", err)
	}

	// Update SizeOfHeaders to reflect expanded DOS stub size
	if err := updateSizeOfHeaders(newData, paddingSize, logger); err != nil {
		return nil, fmt.Errorf("failed to update SizeOfHeaders: %w", err)
	}

	// Update data directories (Certificate Table uses absolute file offsets)
	if err := updateDataDirectories(newData, paddingSize, logger); err != nil {
		return nil, fmt.Errorf("failed to update data directories: %w", err)
	}

	// Update debug directory entries (PointerToRawData fields use absolute file offsets)
	if err := updateDebugDirectory(newData, paddingSize, logger); err != nil {
		return nil, fmt.Errorf("failed to update debug directory: %w", err)
	}

	// Verify the modification
	newPEOffset, err := getPEHeaderOffset(newData)
	if err != nil {
		return nil, fmt.Errorf("failed to read PE offset after modification: %w", err)
	}

	if newPEOffset != TargetDOSStubSize {
		return nil, fmt.Errorf("failed to update PE offset: expected 0x%x, got 0x%x", TargetDOSStubSize, newPEOffset)
	}

	logger.Debug("DOS stub expansion complete",
		"original_size", len(data),
		"new_size", len(newData),
		"bytes_added", paddingSize,
		"new_pe_offset", fmt.Sprintf("0x%x", newPEOffset))

	return newData, nil
}

// GetLauncherType detects launcher type from PE characteristics.
//
// Go and Rust compilers produce PE files with different characteristics:
// - Go: Minimal DOS stub (PE offset 0x80 / 128 bytes)
// - Rust: Larger DOS stub (PE offset 0xE8 / 232 bytes or more)
//
// Returns "go", "rust", or "unknown"
func GetLauncherType(launcherData []byte, logger hclog.Logger) string {
	if !isPEExecutable(launcherData) {
		return "unknown"
	}

	peOffset, err := getPEHeaderOffset(launcherData)
	if err != nil {
		return "unknown"
	}

	// Go binaries have PE offset 0x80, Rust has 0xE8 or larger
	if peOffset == 0x80 {
		logger.Debug("Detected Go launcher", "pe_offset", fmt.Sprintf("0x%x", peOffset))
		return "go"
	} else if peOffset >= 0xE8 {
		logger.Debug("Detected Rust launcher", "pe_offset", fmt.Sprintf("0x%x", peOffset))
		return "rust"
	} else {
		logger.Debug("Unknown launcher type", "pe_offset", fmt.Sprintf("0x%x", peOffset))
		return "unknown"
	}
}

// ProcessLauncherForPSPF processes launcher binary for PSPF embedding compatibility.
//
// This is the main entry point for PE manipulation. It uses a hybrid approach:
// - Go launchers: Use PE overlay (no modifications, PSPF appended after sections)
// - Rust launchers: Use DOS stub expansion (PSPF at fixed 0xF0 offset)
//
// Phase 29: Go binaries are fundamentally incompatible with DOS stub expansion
// due to their PE structure (15 sections, unusual section names, missing data
// directories). The PE overlay approach is the industry standard and preserves
// 100% PE structure integrity.
//
// Returns the processed launcher binary (expanded if Rust, unchanged if Go/Unix)
func ProcessLauncherForPSPF(launcherData []byte, logger hclog.Logger) ([]byte, error) {
	if !isPEExecutable(launcherData) {
		// Not a Windows PE executable, return unchanged (Unix binary)
		logger.Trace("Launcher is not a PE executable, no processing needed")
		return launcherData, nil
	}

	launcherType := GetLauncherType(launcherData, logger)

	switch launcherType {
	case "go":
		// Go launcher: Use PE overlay approach (zero modifications)
		// PSPF data will be appended after all PE sections
		logger.Info("Using PE overlay approach for Go launcher (no PE modifications)")
		return launcherData, nil

	case "rust":
		// Rust launcher: Use DOS stub expansion (PSPF at fixed 0xF0 offset)
		if needsDOSStubExpansion(launcherData, logger) {
			logger.Info("Expanding DOS stub for Rust launcher (PSPF at 0xF0)")
			return expandDOSStub(launcherData, logger)
		}
		logger.Trace("Rust launcher already has adequate DOS stub")
		return launcherData, nil

	default:
		// Unknown launcher type: Safe default is no modification (PE overlay)
		logger.Info("Unknown launcher type, using PE overlay approach")
		return launcherData, nil
	}
}

// bytesEqual is a helper function to compare two byte slices
func bytesEqual(a, b []byte) bool {
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
