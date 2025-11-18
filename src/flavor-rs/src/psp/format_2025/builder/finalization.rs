//! Package finalization and index writing

use super::super::constants::{
    MAGIC_TRAILER_SIZE, MAGIC_WAND_EMOJI_BYTES, PACKAGE_EMOJI_BYTES, SLOT_ALIGNMENT,
    SLOT_DESCRIPTOR_SIZE,
};
use super::super::index::Index;
use super::super::manifest::BuildManifest;
use super::super::slots::{SlotDescriptor, align_offset};
use crate::api::BuildOptions;
use crate::exceptions::Result;
use log::{debug, info, trace};
use std::fs::File;
use std::io::{self, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

/// Write metadata to output file
pub(super) fn write_metadata_bytes(
    out: &mut File,
    compressed: &[u8],
    index: &mut Index,
) -> Result<()> {
    let metadata_pos = out.stream_position()?;
    debug!("📝 Writing metadata at position {:#x}", metadata_pos);

    out.write_all(compressed)?;
    let metadata_end = out.stream_position()?;

    index.metadata_offset = metadata_pos;
    index.metadata_size = compressed.len() as u64;

    debug!(
        "📝 Wrote metadata: start={:#x}, size={}, end={:#x}",
        metadata_pos,
        compressed.len(),
        metadata_end
    );

    // Verify position math
    assert_eq!(
        metadata_end,
        metadata_pos + compressed.len() as u64,
        "Metadata end position mismatch!"
    );

    Ok(())
}

/// Reserve space for descriptor table
pub(super) fn reserve_descriptor_space(
    out: &mut File,
    descriptors: &[SlotDescriptor],
    index: &mut Index,
) -> Result<u64> {
    let current_pos = out.stream_position()?;
    debug!("📍 Current position after metadata: {:#x}", current_pos);

    let descriptor_table_offset = align_offset(current_pos, SLOT_ALIGNMENT);
    debug!(
        "📍 Aligned descriptor table offset: {:#x} (aligned from {:#x})",
        descriptor_table_offset, current_pos
    );

    index.slot_table_offset = descriptor_table_offset;
    index.slot_table_size = (descriptors.len() * SLOT_DESCRIPTOR_SIZE) as u64;
    index.slot_count = descriptors.len() as u32;

    info!(
        "🔍 Setting descriptor_offset to {:#x} for {} descriptors",
        descriptor_table_offset,
        descriptors.len()
    );

    // Reserve space
    let descriptor_table_size = (descriptors.len() * SLOT_DESCRIPTOR_SIZE) as u64;
    out.seek(SeekFrom::Start(
        descriptor_table_offset + descriptor_table_size,
    ))?;

    debug!(
        "📊 Reserved {} bytes for {} descriptors at offset {:#x}",
        descriptor_table_size,
        descriptors.len(),
        descriptor_table_offset
    );

    Ok(descriptor_table_offset)
}

/// Stream slot data from files to output
pub(super) fn stream_slot_data(
    out: &mut File,
    descriptors: &mut [SlotDescriptor],
    slot_paths: &[PathBuf],
) -> Result<()> {
    trace!("📦 Streaming slot data to output");

    for (i, (descriptor, slot_path)) in descriptors.iter_mut().zip(slot_paths).enumerate() {
        // Skip empty paths (self-referential slots)
        if slot_path.as_os_str().is_empty() {
            debug!("⏭️  Skipping slot {} (self-referential, no data)", i);
            descriptor.offset = 0; // No offset for self-ref slots
            continue;
        }

        // Align position
        let current = out.stream_position()?;
        let aligned = align_offset(current, SLOT_ALIGNMENT);
        if aligned > current {
            out.write_all(&vec![0u8; (aligned - current) as usize])?;
        }

        // Write slot and update descriptor with actual offset
        let slot_offset = out.stream_position()?;
        descriptor.offset = slot_offset;

        // Stream file directly to output
        let mut slot_file = File::open(slot_path)?;
        let bytes_copied = io::copy(&mut slot_file, out)?;

        debug!(
            "📍 Wrote slot {}: offset={:#x}, size={} bytes",
            i, slot_offset, bytes_copied
        );
    }

    Ok(())
}

/// Write descriptor table at reserved location
pub(super) fn write_descriptor_table(
    out: &mut File,
    descriptors: &[SlotDescriptor],
    descriptor_table_offset: u64,
) -> Result<u64> {
    let end_pos = out.stream_position()?;
    out.seek(SeekFrom::Start(descriptor_table_offset))?;

    for (i, descriptor) in descriptors.iter().enumerate() {
        let descriptor_bytes = descriptor.pack();
        out.write_all(&descriptor_bytes)?;
        trace!("✍️ Wrote 64-byte descriptor for slot {}", i);
    }

    debug!(
        "📋 Wrote {} descriptors at offset {:#x}",
        descriptors.len(),
        descriptor_table_offset
    );

    // Return to end of data
    out.seek(SeekFrom::Start(end_pos))?;
    Ok(end_pos)
}

/// Finalize package with MagicTrailer and make executable
pub(super) fn finalize_package(
    out: &mut File,
    index: &mut Index,
    end_pos: u64,
    output_path: &Path,
    manifest: &BuildManifest,
    options: &BuildOptions,
) -> Result<()> {
    trace!("🎬 Finalizing package with MagicTrailer");

    // Update package size before writing MagicTrailer
    index.package_size = end_pos + MAGIC_TRAILER_SIZE as u64;

    // Write MagicTrailer (8200 bytes: 📦 + index + 🪄)
    out.write_all(PACKAGE_EMOJI_BYTES)?;
    write_index(out, index)?;
    out.write_all(MAGIC_WAND_EMOJI_BYTES)?;

    // Make the output file executable
    #[cfg(unix)]
    {
        use super::super::defaults::DEFAULT_DIR_PERMS;
        use std::fs;
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(output_path)?.permissions();
        perms.set_mode(DEFAULT_DIR_PERMS as u32);
        fs::set_permissions(output_path, perms)?;
    }

    // Log success message
    log::info!("✅ Successfully built PSPF bundle: {output_path:?}");
    log::info!(
        "  Package: {} v{}",
        manifest.package.name,
        manifest.package.version
    );
    let launcher_display = options
        .launcher_bin
        .as_ref()
        .map(|p| p.display().to_string())
        .or_else(|| std::env::var("FLAVOR_LAUNCHER_BIN").ok())
        .unwrap_or_else(|| "unknown".to_string());
    log::info!("  Launcher: {}", launcher_display);
    log::info!("  Slots: {}", manifest.slots.len());
    let package_size = index.package_size;
    log::info!("  Size: {} bytes", package_size);

    Ok(())
}

/// Write index with calculated checksum
fn write_index(out: &mut File, index: &mut Index) -> Result<()> {
    // Calculate checksum with placeholder set to 0
    let mut bytes = index.pack();
    bytes[4..8].copy_from_slice(&[0, 0, 0, 0]);
    let checksum = adler::adler32_slice(&bytes);

    // Update the index structure with the calculated checksum
    index.index_checksum = checksum;

    // Get the bytes again with the updated checksum
    let final_bytes = index.pack();

    out.write_all(&final_bytes)?;
    Ok(())
}
