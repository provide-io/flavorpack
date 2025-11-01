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

// ProcessLauncherForPSPF processes launcher binary for PSPF embedding compatibility.
// This is the main entry point for PE manipulation. It detects Go binaries
// with minimal DOS stubs and expands them to match Rust binaries for Windows compatibility.
//
// Returns the processed launcher binary (expanded if needed, unchanged otherwise)
func ProcessLauncherForPSPF(launcherData []byte, logger hclog.Logger) ([]byte, error) {
	if !isPEExecutable(launcherData) {
		// Not a Windows PE executable, return unchanged (Unix binary)
		logger.Trace("Launcher is not a PE executable, no processing needed")
		return launcherData, nil
	}

	if !needsDOSStubExpansion(launcherData, logger) {
		// PE executable with adequate DOS stub (Rust/MSVC binary)
		logger.Trace("PE launcher has adequate DOS stub, no processing needed")
		return launcherData, nil
	}

	// Go binary with minimal DOS stub - needs expansion
	logger.Info("Processing Go launcher for Windows PSPF compatibility")
	return expandDOSStub(launcherData, logger)
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
