//! Slot processing and validation

use super::super::constants::{OP_TAR, OP_GZIP};
use super::super::defaults::{DEFAULT_FILE_PERMS};
use super::super::manifest::ManifestSlot;
use super::super::metadata::SlotMetadata;
use super::super::operations::pack_operations;
use super::super::slots::SlotDescriptor;
use super::super::checksums::{calculate_checksum, ChecksumAlgorithm};
use crate::exceptions::{FlavorError, Result};
use log::{debug, error, info, trace};
use std::fs::File;
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use std::time::Instant;

/// Self-referential slot markers
const SELF_REF_MARKERS: &[&str] = &["$SELF", "$LAUNCHER", "$CURRENT"];

/// Check if a slot is self-referential
///
/// A slot is self-referential if its source field contains a special marker
/// ($SELF, $LAUNCHER, or $CURRENT), indicating it references the launcher
/// itself rather than packaged data.
fn is_self_referential(source: &str) -> bool {
    SELF_REF_MARKERS.contains(&source)
}

/// Process and validate slot data
pub(super) struct SlotProcessor {
    pub(super) manifest_slots: Vec<ManifestSlot>,
    pub(super) slot_descriptors: Vec<SlotDescriptor>,
    pub(super) metadata_slots: Vec<SlotMetadata>,
    pub(super) slot_paths: Vec<PathBuf>,
}

impl SlotProcessor {
    pub(super) fn new(manifest_slots: Vec<ManifestSlot>) -> Self {
        Self {
            manifest_slots,
            slot_descriptors: Vec::new(),
            metadata_slots: Vec::new(),
            slot_paths: Vec::new(),
        }
    }

    pub(super) fn process_slots(&mut self) -> Result<()> {
        debug!("🎰 Processing {} slots", self.manifest_slots.len());
        let slots_timer = Instant::now();

        // Process slots one by one
        let num_slots = self.manifest_slots.len();
        for i in 0..num_slots {
            // Work with index to avoid borrow checker issues
            let slot = &self.manifest_slots[i];

            trace!("📖 Processing slot {}: {}", i, slot.source);

            // Validate slot number if provided
            if let Some(declared_slot) = slot.slot {
                if declared_slot as usize != i {
                    error!(
                        "❌ Critical: Slot number mismatch - expected {}, declared {} for slot '{}'",
                        i, declared_slot, slot.id
                    );
                    std::process::exit(1);
                }
            }

            // Check if this is a self-referential slot
            if is_self_referential(&slot.source) {
                info!("✨ Slot {} is self-referential ({}), skipping packaging", i, slot.source);

                // Create metadata for self-ref slot (no actual data)
                let slot_meta = SlotMetadata {
                    index: i,
                    id: slot.id.clone(),
                    source: slot.source.clone(),
                    target: slot.target.clone(),
                    size: 0,  // No data to package
                    checksum: String::new(),  // No checksum needed
                    operations: String::new(),  // No operations
                    purpose: slot.purpose.clone(),
                    lifecycle: slot.lifecycle.clone(),
                    permissions: slot.permissions.clone().or_else(|| Some(format!("{:04o}", DEFAULT_FILE_PERMS))),
                    resolution: slot.resolution.clone().or_else(|| Some("build".to_string())),
                    self_ref: Some(true),  // Mark as self-referential
                };
                self.metadata_slots.push(slot_meta);

                // Create empty descriptor (size=0, no operations)
                let descriptor = SlotDescriptor {
                    id: i as u64,
                    name_hash: 0,
                    offset: 0,  // Will be set during finalization
                    size: 0,  // No data for self-ref slot
                    original_size: 0,
                    operations: 0,  // No operations
                    checksum: 0,
                    purpose: 0,
                    lifecycle: 0,
                    priority: 0,
                    platform: 0,
                    reserved1: 0,
                    reserved2: 0,
                    permissions: 0,
                    permissions_high: 0,
                };
                self.slot_descriptors.push(descriptor);

                // Add empty path (no file to stream)
                self.slot_paths.push(PathBuf::new());

                continue;  // Skip normal processing
            }

            // Normal slot processing (non-self-ref)
            // Resolve slot path
            let slot_path = self.resolve_slot_path(&slot.source)?;

            // Calculate checksums and size
            let (file_size, sha256_checksum, adler32_checksum) = self.calculate_slot_checksums(&slot_path, i)?;

            // Create metadata entry
            let slot_meta = SlotMetadata {
                index: i,
                id: slot.id.clone(),
                source: slot.source.clone(),
                target: slot.target.clone(),
                size: file_size as i64,
                checksum: sha256_checksum,
                operations: slot.operations.clone(),
                purpose: slot.purpose.clone(),
                lifecycle: slot.lifecycle.clone(),
                permissions: slot.permissions.clone().or_else(|| Some(format!("{:04o}", DEFAULT_FILE_PERMS))),
                resolution: slot.resolution.clone().or_else(|| Some("build".to_string())),
                self_ref: None,  // Normal slot, not self-referential
            };
            self.metadata_slots.push(slot_meta);

            // Create descriptor
            let descriptor = self.create_slot_descriptor(i, slot, file_size, adler32_checksum)?;
            self.slot_descriptors.push(descriptor);

            // Store path for later streaming
            self.slot_paths.push(slot_path);
        }

        debug!(
            "✅ Processed {} slots in {:?}",
            self.manifest_slots.len(),
            slots_timer.elapsed()
        );
        Ok(())
    }

    fn resolve_slot_path(&self, source: &str) -> Result<PathBuf> {
        let slot_path = if source.contains("{workenv}") {
            // Priority: 1. FLAVOR_WORKENV_BASE env var, 2. Current working directory
            let base_dir = if let Ok(env_base) = std::env::var("FLAVOR_WORKENV_BASE") {
                info!("🔍 Using FLAVOR_WORKENV_BASE: {}", env_base);
                PathBuf::from(env_base)
            } else {
                let cwd = std::env::current_dir().map_err(|e| {
                    FlavorError::Generic(format!("Failed to get current directory: {}", e))
                })?;
                info!("🔍 No FLAVOR_WORKENV_BASE, using CWD: {}", cwd.display());
                cwd
            };
            let resolved = source.replace("{workenv}", base_dir.to_str().unwrap_or("."));
            info!(
                "📍 Resolved slot path: {} -> {} (base: {})",
                source,
                resolved,
                base_dir.display()
            );
            PathBuf::from(resolved)
        } else {
            info!("📍 Slot path has no {{workenv}}: {}", source);
            PathBuf::from(source)
        };

        info!("Attempting to open slot file at: {:?}", slot_path);
        Ok(slot_path)
    }

    fn calculate_slot_checksums(&self, slot_path: &Path, index: usize) -> Result<(u64, String, u32)> {
        let slot_file = File::open(slot_path).map_err(|e| {
            FlavorError::Generic(format!("Failed to open slot {}: {}", slot_path.display(), e))
        })?;

        let file_metadata = slot_file.metadata()?;
        let file_size = file_metadata.len();
        trace!("📊 Slot {} size: {} bytes", index, file_size);

        // Calculate SHA-256 checksum
        let checksum_timer = Instant::now();
        let mut reader = BufReader::with_capacity(8 * 1024 * 1024, slot_file);
        let sha256_checksum = calculate_checksum(&mut reader, ChecksumAlgorithm::Sha256).map_err(|e| {
            FlavorError::Generic(format!("Failed to calculate SHA256 for slot {}: {}", index, e))
        })?;

        // Calculate Adler-32 checksum
        let slot_file2 = File::open(slot_path)?;
        let mut reader2 = BufReader::with_capacity(8 * 1024 * 1024, slot_file2);
        let mut adler = adler::Adler32::new();
        let mut buffer = vec![0u8; 8 * 1024 * 1024];
        loop {
            let bytes_read = reader2.read(&mut buffer).map_err(|e| {
                FlavorError::Generic(format!("Failed to read slot {} for Adler32: {}", index, e))
            })?;
            if bytes_read == 0 {
                break;
            }
            adler.write_slice(&buffer[..bytes_read]);
        }
        let adler32_checksum = adler.checksum();

        trace!("☑️ Checksums calculated in {:?}", checksum_timer.elapsed());
        info!("Slot {}: SHA256 checksum: {}", index, sha256_checksum);
        info!("Slot {}: Adler32 checksum: {:08x}", index, adler32_checksum);

        Ok((file_size, sha256_checksum, adler32_checksum))
    }

    fn create_slot_descriptor(&self, index: usize, slot: &ManifestSlot, file_size: u64, adler_checksum: u32) -> Result<SlotDescriptor> {
        // Parse operations from comma-separated string (e.g., "tar,gzip")
        let operations = if slot.operations.is_empty() || slot.operations == "none" || slot.operations == "raw" {
            vec![]
        } else if slot.operations == "tgz" {
            // Special case for "tgz" shorthand
            vec![OP_TAR, OP_GZIP]
        } else {
            // Parse comma-separated operations
            slot.operations.split(',')
                .map(|s| s.trim())
                .filter(|s| !s.is_empty())
                .filter_map(|s| match s {
                    "tar" => Some(OP_TAR),
                    "gzip" => Some(OP_GZIP),
                    _ => {
                        log::warn!("Unknown operation: {}, skipping", s);
                        None
                    }
                })
                .collect::<Vec<u8>>()
        };

        // Map purpose string to byte value
        let purpose_value = match slot.purpose.as_str() {
            "payload" => 0,
            "runtime" => 1,
            "tool" => 2,
            _ => 0,
        };

        // Map lifecycle string to byte value
        let lifecycle_value = match slot.lifecycle.as_str() {
            "init" => 0,
            "startup" => 1,
            "runtime" => 2,
            "shutdown" => 3,
            "cache" => 4,
            "temp" => 5,
            "lazy" => 6,
            "eager" => 7,
            "dev" => 8,
            "config" => 9,
            "platform" => 10,
            _ => 2,
        };

        // Create descriptor
        let mut descriptor = SlotDescriptor::new(index as u64);
        descriptor = descriptor.with_name(&slot.id);
        descriptor.size = file_size;
        descriptor.original_size = file_size;
        descriptor.checksum = adler_checksum as u64;
        descriptor.operations = pack_operations(&operations);
        descriptor.purpose = purpose_value;
        descriptor.lifecycle = lifecycle_value;

        // Parse permissions
        let perms = if let Some(ref perm_str) = slot.permissions {
            u16::from_str_radix(perm_str.trim_start_matches('0'), 8).unwrap_or(DEFAULT_FILE_PERMS)
        } else {
            DEFAULT_FILE_PERMS
        };
        descriptor.permissions = (perms & 0xFF) as u8;
        descriptor.permissions_high = ((perms >> 8) & 0xFF) as u8;

        trace!(
            "📍 Slot {}: {} size {} bytes, checksum {:08x}",
            index,
            slot.id,
            file_size,
            adler_checksum
        );

        Ok(descriptor)
    }
}
