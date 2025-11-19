//! Extraction logic for PSPF slots
//!
//! This module handles the extraction of slots from PSPF packages,
//! including single files, tarballs, and permission management.

#![allow(warnings)]
#![deny(clippy::all)]
#![deny(clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]
#![allow(clippy::too_many_lines)]
#![allow(clippy::items_after_statements)]
#![allow(clippy::unnecessary_debug_formatting)]

use std::fs;
use std::io::Read;
use std::path::Path;

use flate2::read::GzDecoder;
use log::{debug, error, trace};
use tar::Archive;

#[cfg(unix)]
use super::defaults::DEFAULT_DIR_PERMS;
use super::reader::Reader;
use super::slots::SlotDescriptor;
use crate::exceptions::{FlavorError, Result};

/// Extract a slot to the specified directory
///
/// # Errors
///
/// Returns an error if:
/// - The slot cannot be read
/// - Extraction fails
/// - File operations fail
pub fn extract_slot(reader: &mut Reader, slot_index: usize, dest_dir: &Path) -> Result<()> {
    trace!("🎯 Extracting slot {slot_index} to {dest_dir:?}");

    // Get descriptors
    let descriptors = reader.read_slot_descriptors()?;
    trace!("📊 Found {} slot descriptors", descriptors.len());

    if slot_index >= descriptors.len() {
        debug!(
            "❌ Slot {} not found (available: 0-{})",
            slot_index,
            descriptors.len() - 1
        );
        return Err(FlavorError::Generic(format!(
            "Slot index {slot_index} out of range"
        )));
    }

    let descriptor = &descriptors[slot_index];

    // Use operations instead of codec
    use crate::psp::format_2025::operations::unpack_operations;
    let operations = unpack_operations(descriptor.operations);

    // Copy values to avoid unaligned access
    let desc_offset = descriptor.offset;
    let desc_size = descriptor.size;
    trace!(
        "📏 Slot {slot_index} descriptor: offset={desc_offset:#x}, size={desc_size}, operations={operations:?}"
    );

    // Read slot data using backend (raw/compressed)
    let slot_data = reader.read_slot(descriptor)?;
    trace!(
        "📦 Read {} bytes (raw) for slot {}",
        slot_data.len(),
        slot_index
    );

    // Process data based on operations
    use crate::psp::format_2025::constants::{OP_GZIP, OP_TAR};

    let mut processed_data = slot_data;

    // Apply operations in reverse order (since they're applied forward during packing)
    for &op in operations.iter().rev() {
        processed_data = match op {
            OP_GZIP => {
                // Decompress gzip
                trace!("🗜️ Decompressing GZIP operation for slot {slot_index}");
                let mut decoder = GzDecoder::new(&processed_data[..]);
                let mut decompressed = Vec::new();
                decoder
                    .read_to_end(&mut decompressed)
                    .map_err(|e| FlavorError::Generic(format!("Failed to decompress GZIP: {e}")))?;
                trace!(
                    "✅ Decompressed {} -> {} bytes",
                    processed_data.len(),
                    decompressed.len()
                );
                decompressed
            }
            OP_TAR => {
                // TAR operation - no processing needed during extraction
                trace!("📦 TAR operation for slot {slot_index} (will extract later)");
                processed_data
            }
            unknown_op => {
                error!("❌ FATAL: Unknown operation {unknown_op} for slot {slot_index}");
                return Err(FlavorError::Generic(format!(
                    "Unknown operation {unknown_op} for slot {slot_index}"
                )));
            }
        };
    }

    let decompressed_data = processed_data;

    trace!(
        "📊 Slot {} decompressed size: {} bytes",
        slot_index,
        decompressed_data.len()
    );

    // Get metadata for slot info
    let metadata = reader.read_metadata()?;

    // Get slot info from metadata
    let (slot_id, mut slot_target, slot_operations, slot_purpose) =
        if slot_index < metadata.slots.len() {
            let slot_info = &metadata.slots[slot_index];
            (
                slot_info.id.clone(),
                slot_info.target.clone(),
                slot_info.operations.clone(),
                slot_info.purpose.clone(),
            )
        } else {
            (
                format!("slot_{slot_index}"),
                format!("slot_{slot_index}"),
                String::new(),
                String::new(),
            )
        };

    // Substitute {workenv} placeholder in target path
    // Since we're already extracting to dest_dir (which IS the workenv),
    // we need to remove the {workenv}/ prefix from the target
    if slot_target.contains("{workenv}") {
        slot_target = slot_target.replace("{workenv}/", "");
        slot_target = slot_target.replace("{workenv}", "");
    }

    debug!(
        "🎯 Slot {slot_index} operations: '{slot_operations}', purpose: '{slot_purpose}', id: '{slot_id}'"
    );

    // Process based on operations
    if operations.contains(&OP_TAR) {
        // Has TAR operation - extract as tarball
        if !is_tarball(&decompressed_data) {
            error!("❌ FATAL: Slot {slot_index} has TAR operation but data is not a tarball!");
            return Err(FlavorError::Generic(format!(
                "Operation mismatch: slot {slot_index} has TAR operation but is not a tar archive"
            )));
        }
        debug!("📦 Slot {slot_index} is a tar archive, extracting...");
        extract_tarball(&decompressed_data, dest_dir)?;
    } else {
        // No TAR operation - treat as single file
        let target_path = dest_dir.join(&slot_target);
        extract_single_file(&decompressed_data, &target_path, &descriptors, slot_index)?;
    }

    Ok(())
}

/// Extract a single gzipped file
fn extract_single_file(
    decompressed_data: &[u8],
    dest_dir: &Path,
    descriptors: &[SlotDescriptor],
    slot_index: usize,
) -> Result<()> {
    // This is a single gzipped file (not a tarball)
    // Per PSPF spec: OP_GZIP = single file that has been gzipped
    // dest_dir IS the full file path (e.g., bin/uv)
    debug!("📝 Writing single gzipped file directly to {dest_dir:?}");

    // Create parent directory if needed (secure permissions)
    if let Some(parent) = dest_dir.parent() {
        create_parent_directory(parent)?;
    } else {
        debug!("⚠️ No parent directory for dest_dir: {dest_dir:?}");
    }

    // Write the file directly to the specified path
    write_file_with_logging(dest_dir, decompressed_data)?;

    // Set file permissions based on descriptor or defaults
    set_file_permissions(dest_dir, descriptors, slot_index)?;

    Ok(())
}

/// Create a parent directory with secure permissions
fn create_parent_directory(parent: &Path) -> Result<()> {
    debug!("📁 Creating parent directory for single file: {parent:?}");
    fs::create_dir_all(parent)?;
    debug!("✅ Created parent directory: {parent:?}");

    // Set secure directory permissions
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        // Only set permissions if we just created the directory
        if parent.exists() {
            match fs::set_permissions(
                parent,
                fs::Permissions::from_mode(u32::from(DEFAULT_DIR_PERMS)),
            ) {
                Ok(()) => debug!("✅ Set permissions on parent directory"),
                Err(e) => debug!("⚠️ Could not set permissions on parent directory: {e}"),
            }
        }
    }

    Ok(())
}

/// Write a file with logging
fn write_file_with_logging(path: &Path, data: &[u8]) -> Result<()> {
    debug!("📝 Writing {} bytes to file: {:?}", data.len(), path);
    match fs::write(path, data) {
        Ok(()) => {
            debug!("✅ Successfully wrote file: {path:?}");
            Ok(())
        }
        Err(e) => {
            error!("❌ Failed to write file {path:?}: {e}");
            Err(FlavorError::Generic(format!("Failed to write file: {e}")))
        }
    }
}

/// Set file permissions based on descriptor or defaults
#[cfg(unix)]
fn set_file_permissions(
    path: &Path,
    descriptors: &[SlotDescriptor],
    slot_index: usize,
) -> Result<()> {
    use std::os::unix::fs::PermissionsExt;

    // Get permissions from descriptor
    let descriptor = &descriptors[slot_index];
    // Combine both permission bytes (low and high)
    let perms = u16::from(descriptor.permissions) | (u16::from(descriptor.permissions_high) << 8);
    let mode = if perms != 0 {
        u32::from(perms)
    } else {
        // Default to secure file permissions
        u32::from(crate::psp::format_2025::defaults::DEFAULT_FILE_PERMS) // 0600
    };

    match fs::set_permissions(path, fs::Permissions::from_mode(mode)) {
        Ok(()) => {
            debug!("✅ Set permissions {mode:o} on {path:?}");
            Ok(())
        }
        Err(e) => {
            error!("❌ Failed to set permissions on {path:?}: {e}");
            Err(FlavorError::Generic(format!(
                "Failed to set permissions: {e}"
            )))
        }
    }
}

#[cfg(not(unix))]
fn set_file_permissions(
    _path: &Path,
    _descriptors: &[SlotDescriptor],
    _slot_index: usize,
) -> Result<()> {
    // No-op on non-Unix systems
    Ok(())
}

/// Check if data looks like a tar archive
fn is_tarball(data: &[u8]) -> bool {
    // Check for tar magic number at offset 257
    if data.len() > 262 {
        // tar archives have "ustar" at offset 257
        &data[257..262] == b"ustar"
    } else {
        false
    }
}

/// Extract a tarball to a directory
///
/// # Errors
///
/// Returns an error if:
/// - Directory creation fails
/// - Tarball extraction fails
/// - Permission setting fails
pub fn extract_tarball(data: &[u8], dest_dir: &Path) -> Result<()> {
    debug!("📦 Extracting tarball to {dest_dir:?}");

    // Create destination directory if it doesn't exist
    if !dest_dir.exists() {
        fs::create_dir_all(dest_dir)?;
    }

    // Create tar archive reader
    let mut tar = Archive::new(std::io::Cursor::new(data));

    // Extract all files
    for entry_result in tar.entries()? {
        let mut entry = entry_result?;
        let path = entry.path()?;
        let dest_path = dest_dir.join(&path);

        trace!("📄 Extracting: {path:?}");

        // Create parent directories if needed
        if let Some(parent) = dest_path.parent() {
            if !parent.exists() {
                fs::create_dir_all(parent)?;
            }
        }

        // Extract the entry
        entry.unpack(&dest_path)?;

        // Set permissions for extracted files
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            if let Ok(metadata) = entry.header().mode() {
                let permissions = fs::Permissions::from_mode(metadata);
                let _ = fs::set_permissions(&dest_path, permissions);
            }
        }
    }

    debug!("✅ Tarball extracted successfully");
    Ok(())
}

/// Check if a gzipped data is a tarball
///
/// # Errors
///
/// Returns an error if decompression fails
pub fn is_gzipped_tarball(data: &[u8]) -> Result<bool> {
    // Try to decompress and check if it's a tarball
    let mut decoder = GzDecoder::new(data);
    let mut decompressed = Vec::new();
    decoder.read_to_end(&mut decompressed)?;
    Ok(is_tarball(&decompressed))
}
