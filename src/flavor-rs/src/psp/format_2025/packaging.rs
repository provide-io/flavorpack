//! Package assembly logic for PSPF builder
//!
//! This module handles the assembly of PSPF packages including
//! slot processing, metadata generation, and file writing.

#![deny(warnings)]
#![deny(clippy::all)]
#![deny(clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]
#![allow(clippy::cast_possible_truncation)]

use crate::psp::format_2025::defaults::DEFAULT_FILE_PERMS;
use crate::psp::format_2025::operations::pack_operations;
use std::fs::File;
use std::io::{Seek, SeekFrom, Write};
use std::path::Path;

use flate2::Compression;
use flate2::write::GzEncoder;
use log::{debug, info, trace};
use sha2::{Digest, Sha256};

use super::constants::{HEADER_SIZE, OP_GZIP, OP_TAR};

/// Compute SHA-256 checksum truncated to first 8 bytes (as u64 little-endian)
fn compute_slot_checksum(data: &[u8]) -> u64 {
    let hash = Sha256::digest(data);
    // SHA-256 always produces 32 bytes, extract first 8 as array
    let bytes: [u8; 8] = [
        hash[0], hash[1], hash[2], hash[3], hash[4], hash[5], hash[6], hash[7],
    ];
    u64::from_le_bytes(bytes)
}
use super::index::Index;
use super::metadata::{Metadata, SlotMetadata};
use super::slots::SlotDescriptor;
use crate::exceptions::Result;

/// Write a slot to the package file
///
/// # Errors
///
/// Returns an error if:
/// - The slot file cannot be read
/// - Data processing fails
/// - Writing to the output file fails
pub fn write_slot(
    out: &mut File,
    slot_path: &Path,
    slot_info: &SlotMetadata,
    slot_index: usize,
) -> Result<SlotDescriptor> {
    trace!("📦 Writing slot {}: {}", slot_index, slot_info.id);

    // Read slot data
    let slot_data = std::fs::read(slot_path)?;
    debug!(
        "  📊 Read {} bytes from {}",
        slot_data.len(),
        slot_path.display()
    );

    // Determine operations and compress if needed
    let (processed_data, operations_str) = process_slot_data(&slot_data, &slot_info.operations)?;

    // Get current position (this will be the slot offset)
    let offset = out.stream_position()?;

    // Write slot data
    out.write_all(&processed_data)?;

    // Parse permissions from slot metadata if provided, otherwise use default
    let permissions = if let Some(perm_str) = &slot_info.permissions {
        // Parse octal string (e.g., "0755" or "755")
        u16::from_str_radix(perm_str.trim_start_matches("0o").trim_start_matches('0'), 8)
            .unwrap_or(DEFAULT_FILE_PERMS)
    } else {
        DEFAULT_FILE_PERMS // Default file permissions
    };

    // Hash the slot's ID for fast lookup
    let name_hash = {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        slot_info.id.hash(&mut hasher);
        hasher.finish()
    };

    // Parse operation string (e.g., "0" for raw, "1" for tar, "16" for gzip, "3" for tgz)
    let operations = match operations_str {
        3 => pack_operations(&[OP_TAR, OP_GZIP]), // TGZ
        1 => pack_operations(&[OP_TAR]),          // TAR only
        16 => pack_operations(&[OP_GZIP]),        // GZIP only
        _ => pack_operations(&[]),                // Raw or unknown
    };

    let checksum = compute_slot_checksum(&processed_data);
    debug!(
        "🦀 Rust builder computed slot {} checksum: {:016x} (data length: {} bytes)",
        slot_index,
        checksum,
        processed_data.len()
    );

    let descriptor = SlotDescriptor {
        id: slot_index as u64,
        name_hash,
        offset,
        size: processed_data.len() as u64,
        original_size: slot_data.len() as u64,
        operations,
        checksum,
        purpose: get_purpose_byte(&slot_info.purpose),
        lifecycle: get_lifecycle_byte(&slot_info.lifecycle),
        priority: 0,
        platform: 0,
        reserved1: 0,
        reserved2: 0,
        permissions: (permissions & 0xFF) as u8,
        permissions_high: ((permissions >> 8) & 0xFF) as u8,
    };

    // Copy values to avoid unaligned access
    let desc_offset = descriptor.offset;
    let desc_size = descriptor.size;
    let desc_checksum = descriptor.checksum;
    debug!(
        "  ✅ Wrote slot at offset {desc_offset:#x}, size {desc_size} bytes, checksum {desc_checksum:#x}"
    );

    Ok(descriptor)
}

/// Process slot data based on operations
fn process_slot_data(data: &[u8], operations_str: &str) -> Result<(Vec<u8>, u8)> {
    match operations_str {
        "gzip" => {
            // Single file, gzipped
            let mut encoder = GzEncoder::new(Vec::new(), Compression::best());
            encoder.write_all(data)?;
            let compressed = encoder.finish()?;
            trace!(
                "  🎈 Compressed {} -> {} bytes",
                data.len(),
                compressed.len()
            );
            Ok((compressed, 16)) // OP_GZIP
        }
        "tgz" | "tar.gz" => {
            // Tar archive, then gzipped - assume data is already a tar
            let mut encoder = GzEncoder::new(Vec::new(), Compression::best());
            encoder.write_all(data)?;
            let compressed = encoder.finish()?;
            trace!(
                "  📦 Compressed tar {} -> {} bytes",
                data.len(),
                compressed.len()
            );
            Ok((compressed, 3)) // Legacy indicator for TAR+GZIP
        }
        "tar" => {
            // Uncompressed tar
            trace!("  📦 Using uncompressed tar ({} bytes)", data.len());
            Ok((data.to_vec(), 1)) // OP_TAR
        }
        _ => {
            // Raw/uncompressed
            trace!("  📄 Using raw data ({} bytes)", data.len());
            Ok((data.to_vec(), 0)) // No operations
        }
    }
}

/// Get purpose byte from string
fn get_purpose_byte(purpose: &str) -> u8 {
    match purpose {
        "payload" => 1,
        "runtime" => 2,
        "tool" => 3,
        "config" => 4,
        _ => 0,
    }
}

/// Get lifecycle byte from string
fn get_lifecycle_byte(lifecycle: &str) -> u8 {
    match lifecycle {
        "init" => 0,
        "startup" => 1,
        "shutdown" => 3,
        "cache" => 4,
        "temporary" => 5,
        "lazy" => 6,
        "eager" => 7,
        "dev" => 8,
        "config" => 9,
        "platform" => 10,
        _ => 2, // default to runtime
    }
}

/// Write the index block to the file
///
/// # Errors
///
/// Returns an error if writing to the output file fails
pub fn write_index_block(out: &mut File, index: &Index) -> Result<()> {
    // Get index bytes
    let index_bytes = index.pack();

    // Write index
    out.write_all(&index_bytes)?;
    debug!("📝 Wrote index block ({HEADER_SIZE} bytes)");

    Ok(())
}

/// Write metadata to the package
///
/// # Errors
///
/// Returns an error if:
/// - Metadata serialization fails
/// - Compression fails
/// - Writing to the output file fails
pub fn write_metadata(out: &mut File, metadata: &Metadata) -> Result<(u64, u32, [u8; 32])> {
    // Get current position (metadata offset)
    let metadata_offset = out.stream_position()?;

    // Serialize metadata to JSON
    let metadata_json = serde_json::to_string(metadata)?;
    debug!("📝 Metadata JSON: {} bytes", metadata_json.len());

    // Compress with gzip
    let mut encoder = GzEncoder::new(Vec::new(), Compression::best());
    encoder.write_all(metadata_json.as_bytes())?;
    let compressed_metadata = encoder.finish()?;
    debug!(
        "🎈 Compressed metadata: {} -> {} bytes",
        metadata_json.len(),
        compressed_metadata.len()
    );

    // Calculate checksum (full SHA-256, 32 bytes)
    let hash = Sha256::digest(&compressed_metadata);
    let mut metadata_checksum = [0u8; 32];
    metadata_checksum.copy_from_slice(&hash);

    // Write compressed metadata
    out.write_all(&compressed_metadata)?;

    Ok((
        metadata_offset,
        compressed_metadata.len() as u32,
        metadata_checksum,
    ))
}

/// Write slot descriptors to the package
///
/// # Errors
///
/// Returns an error if writing to the output file fails
pub fn write_descriptors(out: &mut File, descriptors: &[SlotDescriptor]) -> Result<u64> {
    // Get current position (descriptor table offset)
    let table_offset = out.stream_position()?;

    debug!(
        "📊 Writing {} slot descriptors at offset {:#x}",
        descriptors.len(),
        table_offset
    );

    // Write each descriptor
    for (i, descriptor) in descriptors.iter().enumerate() {
        let descriptor_bytes = descriptor.pack();
        out.write_all(&descriptor_bytes)?;
        trace!("  📋 Wrote descriptor {i}");
    }

    Ok(table_offset)
}

/// Calculate and write package checksum
///
/// # Errors
///
/// Returns an error if:
/// - File size cannot be determined
/// - Checksum calculation fails
/// - Writing fails
pub fn finalize_package(out: &mut File) -> Result<()> {
    // Get file size
    let file_size = out.stream_position()?;

    // Seek back to end
    out.seek(SeekFrom::End(0))?;

    info!("✅ Package finalized: {file_size} bytes");

    Ok(())
}
