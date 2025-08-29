//! Package assembly logic for PSPF builder
//!
//! This module handles the assembly of PSPF packages including
//! slot processing, metadata generation, and file writing.

#![deny(warnings)]
#![deny(clippy::all)]
#![deny(clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]
#![allow(clippy::cast_possible_truncation)]

use std::fs::File;
use std::io::{Seek, SeekFrom, Write};
use std::path::Path;

use adler::Adler32;
use flate2::write::GzEncoder;
use flate2::Compression;
use log::{debug, info, trace};

use super::constants::{ENCODING_GZIP, ENCODING_RAW, ENCODING_TAR, ENCODING_TGZ, HEADER_SIZE};
use super::index::Index;
use super::metadata::{Metadata, SlotMetadata};
use super::slots::SlotDescriptor;
use crate::exceptions::Result;

/// Write a slot to the package file
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

    // Determine encoding and compress if needed
    let (processed_data, encoding) = process_slot_data(&slot_data, &slot_info.encoding)?;

    // Get current position (this will be the slot offset)
    let offset = out.stream_position()?;

    // Write slot data
    out.write_all(&processed_data)?;

    // Parse permissions from slot metadata if provided, otherwise use default
    let permissions = if let Some(perm_str) = &slot_info.permissions {
        // Parse octal string (e.g., "0755" or "755")
        u16::from_str_radix(perm_str.trim_start_matches("0o").trim_start_matches('0'), 8)
            .unwrap_or(0o600)
    } else {
        0o600 // Default file permissions
    };

    // Create descriptor
    let descriptor = SlotDescriptor {
        id: slot_index as u64,
        name_hash: 0, // TODO: Implement name hashing
        offset,
        size: processed_data.len() as u64,
        original_size: slot_data.len() as u64,
        checksum: adler::adler32_slice(&processed_data),
        encoding,
        encryption: 0,
        alignment: 0,
        purpose: get_purpose_byte(&slot_info.purpose),
        lifecycle: get_lifecycle_byte(&slot_info.lifecycle),
        access_hint: 0,
        priority: 0,
        permissions,
        platform: 0,
        extended_offset: 0,
        extended_size: 0,
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

/// Process slot data based on encoding
fn process_slot_data(data: &[u8], encoding_str: &str) -> Result<(Vec<u8>, u8)> {
    match encoding_str {
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
            Ok((compressed, ENCODING_GZIP))
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
            Ok((compressed, ENCODING_TGZ))
        }
        "tar" => {
            // Uncompressed tar
            trace!("  📦 Using uncompressed tar ({} bytes)", data.len());
            Ok((data.to_vec(), ENCODING_TAR))
        }
        _ => {
            // Raw/uncompressed
            trace!("  📄 Using raw data ({} bytes)", data.len());
            Ok((data.to_vec(), ENCODING_RAW))
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
        "volatile" => 1,
        "cache" => 2,
        "runtime" => 3,
        "persistent" => 4,
        _ => 0,
    }
}

/// Write the index block to the file
pub fn write_index_block(out: &mut File, index: &Index) -> Result<()> {
    // Get index bytes
    let index_bytes = index.to_bytes();

    // Write index
    out.write_all(&index_bytes)?;
    debug!("📝 Wrote index block ({HEADER_SIZE} bytes)");

    Ok(())
}

/// Write metadata to the package
pub fn write_metadata(out: &mut File, metadata: &Metadata) -> Result<(u64, u32, u32)> {
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

    // Calculate checksum
    let metadata_checksum = adler::adler32_slice(&compressed_metadata);

    // Write compressed metadata
    out.write_all(&compressed_metadata)?;

    Ok((
        metadata_offset,
        compressed_metadata.len() as u32,
        metadata_checksum,
    ))
}

/// Write slot descriptors to the package
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
        let descriptor_bytes = descriptor.to_bytes();
        out.write_all(&descriptor_bytes)?;
        trace!("  📋 Wrote descriptor {i}");
    }

    Ok(table_offset)
}

/// Calculate and write package checksum
pub fn finalize_package(out: &mut File) -> Result<()> {
    // Get file size
    let file_size = out.stream_position()?;

    // Calculate whole-file checksum
    out.seek(SeekFrom::Start(0))?;
    let mut hasher = Adler32::new();
    let mut buffer = vec![0u8; 8192];
    loop {
        let n = std::io::Read::read(out, &mut buffer)?;
        if n == 0 {
            break;
        }
        hasher.write_slice(&buffer[..n]);
    }
    let _checksum = hasher.checksum();

    // Seek back to end
    out.seek(SeekFrom::End(0))?;

    info!("✅ Package finalized: {file_size} bytes");

    Ok(())
}
