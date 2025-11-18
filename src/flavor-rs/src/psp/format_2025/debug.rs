//! Debug utilities for PSPF packages
//!
//! This module provides debug dumping functionality for analyzing
//! PSPF package internals.

#![deny(warnings)]
#![deny(clippy::all)]
#![deny(clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]

use std::fs;
use std::path::Path;

use log::{debug, trace};

use super::index::Index;
use super::reader::Reader;
use crate::exceptions::Result;

/// Debug dump - saves all package internals for analysis
///
/// # Errors
///
/// Returns an error if:
/// - The output directory cannot be created
/// - Package data cannot be read
/// - Files cannot be written
pub fn debug_dump(reader: &mut Reader, output_dir: &Path) -> Result<()> {
    debug!(
        "🔬 Starting comprehensive debug dump to {}",
        output_dir.display()
    );
    fs::create_dir_all(output_dir)?;

    // Dump index
    debug!("📊 Reading and dumping index...");
    let index = reader.read_index()?.clone();
    let meta_offset = index.metadata_offset;
    let meta_size = index.metadata_size;
    let desc_count = index.slot_count;
    trace!(
        "📏 Index: metadata at {meta_offset:#x} ({meta_size} bytes), {desc_count} slot descriptors"
    );

    // Manual JSON serialization for index (since it's packed struct)
    let index_json = format_index_json(&index);
    fs::write(output_dir.join("index.json"), &index_json)?;
    debug!("💾 Saved index.json");

    // Raw metadata as read from file
    debug!("🎯 Reading raw metadata from offset {meta_offset:#x}");
    let metadata_raw = reader
        .backend_mut()
        .read_at(meta_offset, usize::try_from(meta_size).unwrap_or(0))?;
    fs::write(output_dir.join("metadata_raw.bin"), &metadata_raw)?;

    // Analyze metadata format
    analyze_metadata_format(&metadata_raw);

    // Try to parse metadata
    debug!("🎭 Attempting to parse metadata...");
    match reader.read_metadata() {
        Ok(metadata) => {
            debug!("✅ Successfully parsed metadata");
            let metadata_json = serde_json::to_string_pretty(&metadata)?;
            fs::write(output_dir.join("metadata.json"), &metadata_json)?;
            debug!("💾 Saved parsed metadata.json");
            trace!(
                "  📦 Package: {} v{}",
                metadata.package.name, metadata.package.version
            );
            trace!("  🎰 {} slots defined", metadata.slots.len());
        }
        Err(e) => {
            debug!("❌ Failed to parse metadata: {e}");
        }
    }

    // Analyze slots via descriptors
    analyze_slots(reader, output_dir)?;

    debug!(
        "✨ Debug dump complete! Check {} for results",
        output_dir.display()
    );
    debug!("  📁 Files created: index.json, metadata_raw.bin, metadata.json, slot_*_header.bin");
    Ok(())
}

/// Format index as JSON
fn format_index_json(index: &Index) -> String {
    // Copy values to avoid unaligned access
    let version = index.format_version;
    let file_size = index.package_size;
    let launcher_size = index.launcher_size;
    let descriptor_count = index.slot_count;
    let metadata_offset = index.metadata_offset;
    let metadata_size = index.metadata_size;
    let public_key = index.public_key;

    format!(
        r#"{{
  "version": "0x{:08x}",
  "file_size": {},
  "launcher_size": {},
  "descriptor_count": {},
  "metadata_offset": "0x{:x}",
  "metadata_size": {},
  "metadata_format": "{}",
  "public_key": "{}"
}}"#,
        version,
        file_size,
        launcher_size,
        descriptor_count,
        metadata_offset,
        metadata_size,
        "JSON", // Always JSON format
        hex::encode(public_key)
    )
}

/// Analyze metadata format
fn analyze_metadata_format(metadata_raw: &[u8]) {
    trace!("🔍 Analyzing metadata format...");
    if metadata_raw.starts_with(b"\x1f\x8b") {
        debug!("✅ Metadata is gzip compressed");
        trace!(
            "  🎈 Gzip header: {:02x?}",
            &metadata_raw[..10.min(metadata_raw.len())]
        );
    } else if metadata_raw.starts_with(b"{") {
        debug!("📝 Metadata is uncompressed JSON");
        trace!(
            "  📄 First 50 chars: {}",
            String::from_utf8_lossy(&metadata_raw[..50.min(metadata_raw.len())])
        );
    } else if metadata_raw.starts_with(b"ustar")
        || (metadata_raw.len() > 257 && &metadata_raw[257..262] == b"ustar")
    {
        debug!("🚨 ERROR: Metadata is a tar archive - this is wrong!");
        debug!("🔴 This suggests we're reading from the wrong offset!");
        trace!(
            "  📦 Tar signature found at position: {}",
            if metadata_raw.starts_with(b"ustar") {
                0
            } else {
                257
            }
        );
    } else {
        debug!("❓ Unknown metadata format");
        trace!(
            "  🔬 Magic bytes: {:02x?}",
            &metadata_raw[..16.min(metadata_raw.len())]
        );
    }
}

/// Analyze slots
fn analyze_slots(reader: &mut Reader, output_dir: &Path) -> Result<()> {
    let descriptors = reader.read_slot_descriptors()?;
    debug!("🎰 Analyzing {} slots...", descriptors.len());

    for (i, descriptor) in descriptors.iter().enumerate() {
        let slot_offset = descriptor.offset;
        let slot_size = descriptor.size;
        let slot_checksum = descriptor.checksum;
        trace!(
            "  📏 Slot {i}: offset={slot_offset:#x}, size={slot_size} bytes, checksum={slot_checksum:#x}"
        );

        // Read slot header for analysis
        let preview_size = usize::try_from(slot_size).unwrap_or(512).min(512);
        let slot_preview = reader.backend_mut().read_at(slot_offset, preview_size)?;

        // Identify slot content type
        identify_slot_content(i, &slot_preview);

        fs::write(
            output_dir.join(format!("slot_{i}_header.bin")),
            &slot_preview,
        )?;
    }

    Ok(())
}

/// Identify slot content type
fn identify_slot_content(slot_index: usize, preview: &[u8]) {
    if preview.starts_with(b"\x1f\x8b") {
        trace!("    🎈 Slot {slot_index} is gzip compressed");
    } else if preview.starts_with(b"ustar")
        || (preview.len() > 257 && &preview[257..262] == b"ustar")
    {
        trace!("    📦 Slot {slot_index} is a tar archive");
    } else if preview.starts_with(b"PK") {
        trace!("    🗜️ Slot {slot_index} is a zip file");
    } else if preview.starts_with(b"{") || preview.starts_with(b"[") {
        trace!("    📄 Slot {slot_index} looks like JSON (unexpected!)");
        debug!(
            "    ⚠️ Preview: {}",
            String::from_utf8_lossy(&preview[..50.min(preview.len())])
        );
    } else {
        trace!("    📄 Slot {slot_index} has unknown format");
    }
}
