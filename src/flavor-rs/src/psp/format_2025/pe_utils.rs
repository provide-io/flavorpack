//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

//! Windows PE Executable Utilities
//!
//! Provides utilities for manipulating Windows PE (Portable Executable) files
//! to ensure compatibility with PSPF format when data is appended after the executable.

use anyhow::{Context, Result};
use log::{debug, info, trace, warn};

/// Target DOS stub size to match Rust MSVC binaries (240 bytes / 0xF0)
const TARGET_DOS_STUB_SIZE: usize = 0xF0;

/// Check if data starts with a valid Windows PE executable header.
///
/// # Arguments
/// * `data` - Binary data to check
///
/// # Returns
/// `true` if data starts with "MZ" signature (PE executable)
pub fn is_pe_executable(data: &[u8]) -> bool {
    data.len() >= 2 && data[0] == b'M' && data[1] == b'Z'
}

/// Read the PE header offset from the DOS header.
///
/// The offset is stored at position 0x3C (e_lfanew field) as a 4-byte
/// little-endian integer.
///
/// # Arguments
/// * `data` - PE executable data
///
/// # Returns
/// PE header offset, or None if invalid
pub fn get_pe_header_offset(data: &[u8]) -> Option<usize> {
    if data.len() < 0x40 {
        return None;
    }

    // Read e_lfanew field at offset 0x3C (little-endian u32)
    let pe_offset = u32::from_le_bytes([data[0x3C], data[0x3D], data[0x3E], data[0x3F]]) as usize;

    // Validate PE signature at that offset
    if data.len() < pe_offset + 4 {
        return None;
    }

    let pe_signature = &data[pe_offset..pe_offset + 4];
    if pe_signature != b"PE\x00\x00" {
        warn!(
            "Invalid PE signature at offset 0x{:x}: expected 'PE\\x00\\x00', got {:?}",
            pe_offset,
            String::from_utf8_lossy(pe_signature)
        );
        return None;
    }

    Some(pe_offset)
}

/// Check if a PE executable needs DOS stub expansion.
///
/// Go binaries use minimal DOS stub (128 bytes / 0x80) which is incompatible
/// with Windows PE loader when PSPF data is appended. This function detects
/// such binaries.
///
/// # Arguments
/// * `data` - PE executable data
///
/// # Returns
/// `true` if DOS stub needs expansion (Go binary with 0x80 stub)
pub fn needs_dos_stub_expansion(data: &[u8]) -> bool {
    if !is_pe_executable(data) {
        return false;
    }

    let pe_offset = match get_pe_header_offset(data) {
        Some(offset) => offset,
        None => return false,
    };

    // Check if this is a Go binary with minimal DOS stub (0x80 = 128 bytes)
    // Rust/MSVC binaries typically use 0xE8-0xF0 (232-240 bytes)
    if pe_offset == 0x80 {
        debug!(
            "Detected Go binary with minimal DOS stub: pe_offset=0x{:x} ({} bytes)",
            pe_offset, pe_offset
        );
        return true;
    }

    trace!(
        "PE binary has adequate DOS stub size: pe_offset=0x{:x} ({} bytes)",
        pe_offset, pe_offset
    );
    false
}

/// Update section PointerToRawData values after DOS stub expansion.
///
/// When expanding the DOS stub, all content after the DOS stub shifts forward
/// by padding_size bytes. This includes all section data. The section table
/// contains PointerToRawData fields (absolute file offsets) that must be
/// updated to point to the new section locations.
///
/// # Arguments
/// * `data` - PE executable data (modified in-place)
/// * `padding_size` - Number of bytes added to DOS stub
///
/// # Returns
/// Result indicating success or failure
fn update_section_offsets(data: &mut [u8], padding_size: usize) -> Result<()> {
    // Get PE header location
    let pe_offset = u32::from_le_bytes([data[0x3C], data[0x3D], data[0x3E], data[0x3F]]) as usize;
    let coff_offset = pe_offset + 4;

    // Read number of sections
    let num_sections = u16::from_le_bytes([data[coff_offset + 2], data[coff_offset + 3]]) as usize;

    // Read optional header size
    let opt_hdr_size =
        u16::from_le_bytes([data[coff_offset + 16], data[coff_offset + 17]]) as usize;

    // Section table offset
    let section_table_offset = coff_offset + 20 + opt_hdr_size;

    debug!(
        "Updating {} section offset(s), padding_size=0x{:x}",
        num_sections, padding_size
    );

    // Update each section's PointerToRawData
    let mut updated = 0;
    for i in 0..num_sections {
        let section_offset = section_table_offset + (i * 40);
        let ptr_offset = section_offset + 20;

        // Read current PointerToRawData
        let current_ptr = u32::from_le_bytes([
            data[ptr_offset],
            data[ptr_offset + 1],
            data[ptr_offset + 2],
            data[ptr_offset + 3],
        ]);

        // Update if non-zero
        if current_ptr > 0 {
            let new_ptr = current_ptr + padding_size as u32;
            let new_bytes = new_ptr.to_le_bytes();
            data[ptr_offset..ptr_offset + 4].copy_from_slice(&new_bytes);

            trace!(
                "Updated section {} offset: 0x{:x} -> 0x{:x}",
                i, current_ptr, new_ptr
            );
            updated += 1;
        }
    }

    debug!("Updated {}/{} section offset(s)", updated, num_sections);
    Ok(())
}

/// Update data directory file offsets after DOS stub expansion.
///
/// The Certificate Table (data directory entry #4) is special: it uses absolute
/// file offsets instead of RVAs. When the DOS stub expands, this offset must
/// be updated. Other data directories use RVAs (relative to image base) and
/// don't need updating.
///
/// # Arguments
/// * `data` - PE executable data (modified in-place)
/// * `padding_size` - Number of bytes added to DOS stub
///
/// # Returns
/// Result indicating success or failure
fn update_data_directories(data: &mut [u8], padding_size: usize) -> Result<()> {
    // Get PE header location
    let pe_offset = u32::from_le_bytes([data[0x3C], data[0x3D], data[0x3E], data[0x3F]]) as usize;
    let coff_offset = pe_offset + 4;

    // Read magic number to identify PE32 vs PE32+
    let magic = u16::from_le_bytes([data[coff_offset + 20], data[coff_offset + 21]]);
    let is_pe32_plus = magic == 0x20B;

    // Data directory offset in optional header
    // PE32: starts at optional header + 96
    // PE32+: starts at optional header + 112
    let data_dir_offset = if is_pe32_plus {
        coff_offset + 20 + 112
    } else {
        coff_offset + 20 + 96
    };

    // Certificate Table is the 5th entry (index 4) in data directory array
    // Each entry is 8 bytes (4 bytes RVA/offset + 4 bytes size)
    let cert_entry_offset = data_dir_offset + (4 * 8);

    if cert_entry_offset + 8 > data.len() {
        trace!(
            "Certificate table entry beyond file bounds, skipping update: offset=0x{:x}, file_size={}",
            cert_entry_offset,
            data.len()
        );
        return Ok(());
    }

    // Read certificate table entry
    let cert_file_offset = u32::from_le_bytes([
        data[cert_entry_offset],
        data[cert_entry_offset + 1],
        data[cert_entry_offset + 2],
        data[cert_entry_offset + 3],
    ]);
    let cert_size = u32::from_le_bytes([
        data[cert_entry_offset + 4],
        data[cert_entry_offset + 5],
        data[cert_entry_offset + 6],
        data[cert_entry_offset + 7],
    ]);

    trace!(
        "Checked certificate table: offset=0x{:x}, size={}",
        cert_file_offset, cert_size
    );

    // Update certificate table offset if it exists and is after the DOS stub
    if cert_file_offset >= 0x80 {
        let new_cert_offset = cert_file_offset + padding_size as u32;
        let new_bytes = new_cert_offset.to_le_bytes();
        data[cert_entry_offset..cert_entry_offset + 4].copy_from_slice(&new_bytes);
        debug!(
            "Updated certificate table offset: 0x{:x} -> 0x{:x}",
            cert_file_offset, new_cert_offset
        );
    }

    // Zero out PE checksum (not validated for executable files, only for drivers/DLLs)
    // CheckSum field is at optional header + 64
    let checksum_offset = coff_offset + 20 + 64;
    data[checksum_offset..checksum_offset + 4].copy_from_slice(&0u32.to_le_bytes());
    trace!("Zeroed PE checksum (not required for executables)");

    Ok(())
}

/// Map a Relative Virtual Address (RVA) to a file offset by walking the section table.
///
/// # Arguments
/// * `data` - PE executable data
/// * `rva` - Relative Virtual Address to map
///
/// # Returns
/// File offset if mapping succeeded, None otherwise
fn rva_to_file_offset(data: &[u8], rva: u32) -> Option<u32> {
    // Get PE header location
    let pe_offset = u32::from_le_bytes([data[0x3C], data[0x3D], data[0x3E], data[0x3F]]) as usize;
    let coff_offset = pe_offset + 4;

    // Read number of sections
    let num_sections = u16::from_le_bytes([data[coff_offset + 2], data[coff_offset + 3]]) as usize;

    // Read optional header size
    let opt_hdr_size =
        u16::from_le_bytes([data[coff_offset + 16], data[coff_offset + 17]]) as usize;

    // Section table offset
    let section_table_offset = coff_offset + 20 + opt_hdr_size;

    // Walk section table to find which section contains this RVA
    for i in 0..num_sections {
        let section_offset = section_table_offset + (i * 40);

        // Read section header fields
        // VirtualAddress is at offset 12 in section header
        // VirtualSize is at offset 8 in section header
        // PointerToRawData is at offset 20 in section header

        let virtual_addr = u32::from_le_bytes([
            data[section_offset + 12],
            data[section_offset + 13],
            data[section_offset + 14],
            data[section_offset + 15],
        ]);
        let virtual_size = u32::from_le_bytes([
            data[section_offset + 8],
            data[section_offset + 9],
            data[section_offset + 10],
            data[section_offset + 11],
        ]);
        let pointer_to_raw_data = u32::from_le_bytes([
            data[section_offset + 20],
            data[section_offset + 21],
            data[section_offset + 22],
            data[section_offset + 23],
        ]);

        // Check if RVA falls within this section
        if rva >= virtual_addr && rva < virtual_addr + virtual_size {
            let offset_within_section = rva - virtual_addr;
            let file_offset = pointer_to_raw_data + offset_within_section;
            trace!(
                "Mapped RVA 0x{:x} to file offset 0x{:x} (section {}, VA=0x{:x})",
                rva, file_offset, i, virtual_addr
            );
            return Some(file_offset);
        }
    }

    trace!("RVA 0x{:x} not found in any section", rva);
    None
}

/// Update debug directory entries' PointerToRawData values after DOS stub expansion.
///
/// The Debug Directory (data directory entry #6) contains an array of IMAGE_DEBUG_DIRECTORY
/// structures. Each structure has both AddressOfRawData (RVA) and PointerToRawData (absolute
/// file offset). The PointerToRawData field MUST be updated when the DOS stub expands.
///
/// # Arguments
/// * `data` - PE executable data (modified in-place)
/// * `padding_size` - Number of bytes added to DOS stub
///
/// # Returns
/// Result indicating success or failure
fn update_debug_directory(data: &mut [u8], padding_size: usize) -> Result<()> {
    // Get PE header location
    let pe_offset = u32::from_le_bytes([data[0x3C], data[0x3D], data[0x3E], data[0x3F]]) as usize;
    let coff_offset = pe_offset + 4;

    // Read magic number to identify PE32 vs PE32+
    let magic = u16::from_le_bytes([data[coff_offset + 20], data[coff_offset + 21]]);
    let is_pe32_plus = magic == 0x20B;

    // Data directory offset in optional header
    let data_dir_offset = if is_pe32_plus {
        coff_offset + 20 + 112
    } else {
        coff_offset + 20 + 96
    };

    // Debug Directory is the 7th entry (index 6) in data directory array
    let debug_dir_entry_offset = data_dir_offset + (6 * 8);

    if debug_dir_entry_offset + 8 > data.len() {
        trace!(
            "Debug directory entry beyond file bounds, skipping: offset=0x{:x}",
            debug_dir_entry_offset
        );
        return Ok(());
    }

    // Read debug directory entry (RVA and size)
    let debug_dir_rva = u32::from_le_bytes([
        data[debug_dir_entry_offset],
        data[debug_dir_entry_offset + 1],
        data[debug_dir_entry_offset + 2],
        data[debug_dir_entry_offset + 3],
    ]);
    let debug_dir_size = u32::from_le_bytes([
        data[debug_dir_entry_offset + 4],
        data[debug_dir_entry_offset + 5],
        data[debug_dir_entry_offset + 6],
        data[debug_dir_entry_offset + 7],
    ]);

    // If no debug directory, skip
    if debug_dir_rva == 0 || debug_dir_size == 0 {
        trace!("No debug directory present (RVA or size is 0)");
        return Ok(());
    }

    // Map debug directory RVA to file offset
    let debug_dir_file_offset = if let Some(offset) = rva_to_file_offset(data, debug_dir_rva) {
        offset
    } else {
        trace!(
            "Unable to map debug directory RVA 0x{:x} to file offset, skipping",
            debug_dir_rva
        );
        return Ok(());
    };

    debug!(
        "Found debug directory: RVA=0x{:x}, file_offset=0x{:x}, size={}",
        debug_dir_rva, debug_dir_file_offset, debug_dir_size
    );

    // Calculate number of debug directory entries (each is 28 bytes)
    let num_debug_entries = (debug_dir_size as usize) / 28;
    debug!("Debug directory entry count: {}", num_debug_entries);

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

    let mut updated = 0;
    for i in 0..num_debug_entries {
        let entry_offset = (debug_dir_file_offset as usize) + (i * 28);

        // PointerToRawData is at offset 24 within the debug directory entry
        let ptr_raw_data_offset = entry_offset + 24;

        if ptr_raw_data_offset + 4 > data.len() {
            trace!(
                "Debug entry {} PointerToRawData beyond file bounds, offset=0x{:x}",
                i, ptr_raw_data_offset
            );
            continue;
        }

        // Read current PointerToRawData
        let current_ptr = u32::from_le_bytes([
            data[ptr_raw_data_offset],
            data[ptr_raw_data_offset + 1],
            data[ptr_raw_data_offset + 2],
            data[ptr_raw_data_offset + 3],
        ]);

        // Update if >= 0x80 (after DOS stub start)
        if current_ptr >= 0x80 {
            let new_ptr = current_ptr + padding_size as u32;
            data[ptr_raw_data_offset..ptr_raw_data_offset + 4]
                .copy_from_slice(&new_ptr.to_le_bytes());

            trace!(
                "Updated debug entry {} PointerToRawData: 0x{:x} -> 0x{:x}",
                i, current_ptr, new_ptr
            );
            updated += 1;
        }
    }

    if updated > 0 {
        debug!(
            "Updated {}/{} debug directory entries",
            updated, num_debug_entries
        );
    }

    Ok(())
}

/// Update SizeOfHeaders field in the Optional Header after DOS stub expansion.
///
/// The SizeOfHeaders field specifies the combined size of the DOS stub, PE headers,
/// and section table, rounded to the file alignment. When the DOS stub expands,
/// this field must be updated to match the new total header size.
///
/// Windows PE loader validates that sections start at or after SizeOfHeaders.
/// A mismatch causes loader rejection, especially on ARM64 (exit code 126).
///
/// # Arguments
/// * `data` - PE executable data (modified in-place)
/// * `padding_size` - Number of bytes added to DOS stub
///
/// # Returns
/// Success or error
///
/// # Errors
/// Returns error if PE structure is invalid
fn update_size_of_headers(data: &mut [u8], padding_size: usize) -> Result<()> {
    // Get PE header location
    let pe_offset = u32::from_le_bytes([data[0x3C], data[0x3D], data[0x3E], data[0x3F]]) as usize;
    let coff_offset = pe_offset + 4;

    // SizeOfHeaders is at optional header + 60 bytes
    // Optional header starts at COFF header + 20
    let size_of_headers_offset = coff_offset + 20 + 60;

    if size_of_headers_offset + 4 > data.len() {
        anyhow::bail!(
            "SizeOfHeaders offset 0x{:x} beyond file bounds",
            size_of_headers_offset
        );
    }

    // Read current SizeOfHeaders value
    let current_size = u32::from_le_bytes([
        data[size_of_headers_offset],
        data[size_of_headers_offset + 1],
        data[size_of_headers_offset + 2],
        data[size_of_headers_offset + 3],
    ]);

    // Update to reflect expanded DOS stub
    let new_size = current_size + padding_size as u32;
    data[size_of_headers_offset..size_of_headers_offset + 4]
        .copy_from_slice(&new_size.to_le_bytes());

    debug!(
        "Updated SizeOfHeaders field: old_size=0x{:x}, new_size=0x{:x}, padding={}",
        current_size, new_size, padding_size
    );

    Ok(())
}

/// Expand the DOS stub of a PE executable to match Rust/MSVC binary size.
///
/// This fixes Windows PE loader rejection of Go binaries when PSPF data
/// is appended. The DOS stub is expanded from 128 bytes (0x80) to 240 bytes
/// (0xF0) to match Rust binaries.
///
/// Process:
/// 1. Extract MZ header and DOS stub (first 64 bytes + stub code)
/// 2. Extract PE header and remainder
/// 3. Insert padding to expand stub to target size
/// 4. Update e_lfanew pointer to new PE offset
///
/// # Arguments
/// * `data` - Original PE executable data
///
/// # Returns
/// Modified PE executable with expanded DOS stub
///
/// # Errors
/// Returns error if data is not a valid PE executable
pub fn expand_dos_stub(data: Vec<u8>) -> Result<Vec<u8>> {
    if !is_pe_executable(&data) {
        anyhow::bail!("Data is not a Windows PE executable");
    }

    let current_pe_offset = get_pe_header_offset(&data).context("Invalid PE header offset")?;

    if current_pe_offset >= TARGET_DOS_STUB_SIZE {
        debug!(
            "DOS stub already adequate size: current=0x{:x}, target=0x{:x}",
            current_pe_offset, TARGET_DOS_STUB_SIZE
        );
        return Ok(data);
    }

    // Calculate padding needed
    let padding_size = TARGET_DOS_STUB_SIZE - current_pe_offset;

    info!(
        "Expanding DOS stub for Windows compatibility: current_pe_offset=0x{:x}, target_pe_offset=0x{:x}, padding_bytes={}",
        current_pe_offset, TARGET_DOS_STUB_SIZE, padding_size
    );

    // Build new executable:
    // 1. MZ header + DOS stub (up to current PE offset)
    // 2. Padding (zeros to expand stub)
    // 3. PE header and remainder
    let mut new_data = Vec::with_capacity(data.len() + padding_size);
    new_data.extend_from_slice(&data[..current_pe_offset]);
    new_data.extend(vec![0u8; padding_size]);
    new_data.extend_from_slice(&data[current_pe_offset..]);

    // Update e_lfanew pointer at offset 0x3C to point to new PE header location
    let target_bytes = (TARGET_DOS_STUB_SIZE as u32).to_le_bytes();
    new_data[0x3C..0x40].copy_from_slice(&target_bytes);

    // CRITICAL: Update all section PointerToRawData values
    // When we shift the file content forward, section data moves but the section
    // table entries still point to old offsets. We must update them.
    update_section_offsets(&mut new_data, padding_size)?;

    // Update SizeOfHeaders to reflect expanded DOS stub size
    update_size_of_headers(&mut new_data, padding_size)?;

    // Update data directories (Certificate Table uses absolute file offsets)
    update_data_directories(&mut new_data, padding_size)?;

    // Update debug directory entries (PointerToRawData fields use absolute file offsets)
    update_debug_directory(&mut new_data, padding_size)?;

    // Verify the modification
    let new_pe_offset =
        get_pe_header_offset(&new_data).context("Failed to read PE offset after modification")?;

    if new_pe_offset != TARGET_DOS_STUB_SIZE {
        anyhow::bail!(
            "Failed to update PE offset: expected 0x{:x}, got 0x{:x}",
            TARGET_DOS_STUB_SIZE,
            new_pe_offset
        );
    }

    debug!(
        "DOS stub expansion complete: original_size={}, new_size={}, bytes_added={}, new_pe_offset=0x{:x}",
        data.len(),
        new_data.len(),
        padding_size,
        new_pe_offset
    );

    Ok(new_data)
}

/// Detect launcher type from PE characteristics.
///
/// Go and Rust compilers produce PE files with different characteristics:
/// - Go: Minimal DOS stub (PE offset 0x80 / 128 bytes)
/// - Rust: Larger DOS stub (PE offset 0xE8 / 232 bytes or more)
///
/// # Arguments
/// * `launcher_data` - Launcher binary data
///
/// # Returns
/// "go", "rust", or "unknown"
pub fn get_launcher_type(launcher_data: &[u8]) -> &'static str {
    if !is_pe_executable(launcher_data) {
        return "unknown";
    }

    let pe_offset = match get_pe_header_offset(launcher_data) {
        Some(offset) => offset,
        None => return "unknown",
    };

    // Go binaries have PE offset 0x80, Rust has 0xE8 or larger
    if pe_offset == 0x80 {
        debug!("Detected Go launcher, pe_offset=0x{:x}", pe_offset);
        "go"
    } else if pe_offset >= 0xE8 {
        debug!("Detected Rust launcher, pe_offset=0x{:x}", pe_offset);
        "rust"
    } else {
        debug!("Unknown launcher type, pe_offset=0x{:x}", pe_offset);
        "unknown"
    }
}

/// Process launcher binary for PSPF embedding compatibility.
///
/// This is the main entry point for PE manipulation. It uses a hybrid approach:
/// - Go launchers: Use PE overlay (no modifications, PSPF appended after sections)
/// - Rust launchers: Use DOS stub expansion (PSPF at fixed 0xF0 offset)
///
/// Phase 29: Go binaries are fundamentally incompatible with DOS stub expansion
/// due to their PE structure (15 sections, unusual section names, missing data
/// directories). The PE overlay approach is the industry standard and preserves
/// 100% PE structure integrity.
///
/// # Arguments
/// * `launcher_data` - Original launcher binary
///
/// # Returns
/// Processed launcher binary (expanded if Rust, unchanged if Go/Unix)
pub fn process_launcher_for_pspf(launcher_data: Vec<u8>) -> Result<Vec<u8>> {
    if !is_pe_executable(&launcher_data) {
        // Not a Windows PE executable, return unchanged (Unix binary)
        trace!("Launcher is not a PE executable, no processing needed");
        return Ok(launcher_data);
    }

    let launcher_type = get_launcher_type(&launcher_data);

    match launcher_type {
        "go" => {
            // Go launcher: Use PE overlay approach (zero modifications)
            // PSPF data will be appended after all PE sections
            // NOTE: PE resource embedding is disabled for Rust builder due to
            // UpdateResourceW API corruption issues. Go builder uses winres library
            // which properly reconstructs the PE file.
            info!("Using PE overlay approach for Go launcher (appended data)");
            debug!(
                "Note: PE resource embedding disabled in Rust builder - Go builder recommended for Windows+Go"
            );
            Ok(launcher_data)
        }
        "rust" => {
            // Rust launcher: Use DOS stub expansion (PSPF at fixed 0xF0 offset)
            if needs_dos_stub_expansion(&launcher_data) {
                info!("Expanding DOS stub for Rust launcher (PSPF at 0xF0)");
                expand_dos_stub(launcher_data)
            } else {
                trace!("Rust launcher already has adequate DOS stub");
                Ok(launcher_data)
            }
        }
        _ => {
            // Unknown launcher type: Safe default is no modification (PE overlay)
            info!("Unknown launcher type, using PE overlay approach");
            Ok(launcher_data)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_pe_executable() {
        let pe_data = b"MZ\x90\x00";
        assert!(is_pe_executable(pe_data));

        let elf_data = b"\x7fELF";
        assert!(!is_pe_executable(elf_data));

        let short_data = b"M";
        assert!(!is_pe_executable(short_data));
    }

    #[test]
    fn test_needs_dos_stub_expansion() {
        // Create minimal PE with DOS stub at 0x80
        let mut go_binary = vec![0u8; 256];
        go_binary[0] = b'M';
        go_binary[1] = b'Z';
        // Set e_lfanew to 0x80
        go_binary[0x3C..0x40].copy_from_slice(&0x80u32.to_le_bytes());
        // Add PE signature at 0x80
        go_binary[0x80..0x84].copy_from_slice(b"PE\x00\x00");

        assert!(needs_dos_stub_expansion(&go_binary));

        // Create PE with adequate DOS stub at 0xF0
        let mut rust_binary = vec![0u8; 512];
        rust_binary[0] = b'M';
        rust_binary[1] = b'Z';
        // Set e_lfanew to 0xF0
        rust_binary[0x3C..0x40].copy_from_slice(&0xF0u32.to_le_bytes());
        // Add PE signature at 0xF0
        rust_binary[0xF0..0xF4].copy_from_slice(b"PE\x00\x00");

        assert!(!needs_dos_stub_expansion(&rust_binary));
    }
}
