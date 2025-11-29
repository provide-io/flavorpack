//! Slot extraction utilities

use super::super::metadata::Metadata;
use super::super::reader::Reader;
use crate::exceptions::Result;
use log::{debug, error, info};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Extract slots from the package
pub(super) fn extract_slots(
    reader: &mut Reader,
    workenv_path: &Path,
) -> Result<(HashMap<usize, PathBuf>, Vec<PathBuf>)> {
    // Re-read metadata inside this function to avoid borrow issues
    debug!("📖 Reading metadata for slot extraction");
    let metadata = match reader.read_metadata() {
        Ok(m) => m.clone(),
        Err(e) => {
            error!("🚨 Failed to read metadata: {}", e);
            return Err(e);
        }
    };
    let mut slot_paths = HashMap::new();
    let mut init_paths = Vec::new();

    info!("📤 Extracting {} slots...", metadata.slots.len());

    // Print extraction progress to stderr
    use std::io::Write;
    let stderr = std::io::stderr();
    let mut stderr_handle = stderr.lock();

    // Extract slots by index
    for i in 0..metadata.slots.len() {
        let slot = &metadata.slots[i];
        debug!(
            "📦 Extracting slot {}: {} ({} bytes)",
            slot.index, slot.id, slot.size
        );
        debug!("  Source: {}", slot.source);
        debug!("  Target: {}", slot.target);
        debug!("  Lifecycle: {}", slot.lifecycle);
        debug!("  Permissions: {:?}", slot.permissions);

        // Write progress to stderr
        let _ = writeln!(
            stderr_handle,
            "[{}/{}] Extracting {}...",
            i + 1,
            metadata.slots.len(),
            slot.id
        );

        // Determine extraction path
        // Target field specifies where to extract (relative to workenv)
        // But extract_slot expects a directory, so we need to pass workenv_path
        // The extract_slot function will use the metadata to determine the target path

        // Extract the slot to workenv (it will use metadata.target internally)
        reader.extract_slot(i, workenv_path)?;

        let extracted_path = workenv_path.join(&slot.target);
        debug!("✅ Extracted to: {extracted_path:?}");

        // Track init slots for later cleanup (removed after initialization)
        if slot.lifecycle == "init" {
            debug!("📌 Marking slot {} as init for cleanup", slot.index);
            init_paths.push(extracted_path.clone());
        }

        slot_paths.insert(i, extracted_path);
    }

    Ok((slot_paths, init_paths))
}

/// Build slot paths without extraction (when cache is valid)
pub(super) fn build_slot_paths(
    metadata: &Metadata,
    workenv_path: &Path,
) -> HashMap<usize, PathBuf> {
    let mut slot_paths = HashMap::new();

    for slot in &metadata.slots {
        // Target field specifies where to extract (relative to workenv)
        let slot_path = workenv_path.join(&slot.target);
        slot_paths.insert(slot.index, slot_path);
    }

    slot_paths
}
