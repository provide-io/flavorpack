//! Validation and checksum management

use super::super::index::Index;
use super::super::metadata::Metadata;
use super::super::paths::WorkenvPaths;
use crate::exceptions::{FlavorError, Result};
use log::{debug, warn};
use serde::{Deserialize, Serialize};
use std::fs;

/// Validate package checksum against cached value
pub(super) fn validate_package_checksum(
    paths: &WorkenvPaths,
    current_checksum: u32,
) -> Result<bool> {
    let checksum_path = paths.checksum_file();

    // Read stored checksum
    match fs::read_to_string(&checksum_path) {
        Ok(data) => {
            let stored_checksum = data.trim();
            let current_checksum_str = format!("{:08x}", current_checksum);

            if stored_checksum == current_checksum_str {
                debug!(
                    "✅ Package checksum matches cached version: {}",
                    current_checksum_str
                );
                Ok(true)
            } else {
                // Checksum mismatch - this is a potential security issue
                use crate::psp::format_2025::defaults::{ValidationLevel, get_validation_level};

                let validation_level = get_validation_level();
                match validation_level {
                    ValidationLevel::None | ValidationLevel::Minimal => {
                        warn!(
                            "⚠️ SECURITY WARNING: Package checksum mismatch! cached: {}, current: {}",
                            stored_checksum, current_checksum_str
                        );
                        warn!("⚠️ Cache may be compromised or package has changed");
                        warn!(
                            "⚠️ Continuing due to validation level: {:?}",
                            validation_level
                        );
                        Ok(false)
                    }
                    ValidationLevel::Relaxed => {
                        warn!(
                            "⚠️ SECURITY WARNING: Package checksum mismatch! cached: {}, current: {}",
                            stored_checksum, current_checksum_str
                        );
                        warn!("⚠️ Cache may be compromised or package has changed");
                        warn!("⚠️ Continuing due to relaxed validation");
                        Ok(false)
                    }
                    ValidationLevel::Standard => {
                        eprintln!(
                            "🚨 SECURITY WARNING: Package checksum mismatch! cached: {}, current: {}",
                            stored_checksum, current_checksum_str
                        );
                        eprintln!("🚨 Cache may be compromised or package has changed");
                        eprintln!(
                            "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)"
                        );
                        warn!(
                            "⚠️ Package checksum mismatch, continuing with standard validation: cached: {}, current: {}",
                            stored_checksum, current_checksum_str
                        );
                        Ok(false)
                    }
                    ValidationLevel::Strict => {
                        log::error!(
                            "🚨 CRITICAL: Package checksum mismatch! cached: {}, current: {}",
                            stored_checksum,
                            current_checksum_str
                        );
                        log::error!("🚨 Cache may be compromised or package has changed");
                        log::error!(
                            "🚨 Refusing to continue. Set FLAVOR_VALIDATION=relaxed to bypass (NOT RECOMMENDED)"
                        );
                        Err(FlavorError::Generic(format!(
                            "package checksum mismatch: cached={}, current={}",
                            stored_checksum, current_checksum_str
                        )))
                    }
                }
            }
        }
        Err(e) => {
            if e.kind() == std::io::ErrorKind::NotFound {
                debug!("🔍 No cached checksum found");
            } else {
                debug!("⚠️ Failed to read cached checksum: {}", e);
            }
            Ok(false) // No checksum file is not an error, just means cache is invalid
        }
    }
}

/// Save package checksum to cache
pub fn save_package_checksum(paths: &WorkenvPaths, checksum: u32) -> Result<()> {
    let instance_dir = paths.instance();
    fs::create_dir_all(&instance_dir)?;

    let checksum_path = paths.checksum_file();
    let checksum_str = format!("{:08x}", checksum);

    fs::write(&checksum_path, &checksum_str)?;
    debug!("💾 Saved package checksum: {}", checksum_str);

    Ok(())
}

/// Serializable subset of the Index for JSON export
#[derive(Debug, Serialize, Deserialize)]
pub struct IndexMetadata {
    pub format_version: u32,
    pub package_size: u64,
    pub launcher_size: u64,
    pub metadata_offset: u64,
    pub metadata_size: u64,
    pub slot_table_offset: u64,
    pub slot_table_size: u64,
    pub slot_count: u32,
    pub flags: u32,
    pub index_checksum: String,
    pub metadata_checksum: String,
    pub build_timestamp: u64,
    pub page_size: u32,
    pub capabilities: u64,
    pub requirements: u64,
}

/// Save index metadata to JSON file for inspection
pub fn save_index_metadata(paths: &WorkenvPaths, index: &Index) -> Result<()> {
    let instance_dir = paths.instance();
    fs::create_dir_all(&instance_dir)?;

    // Create a serializable version of the index
    // Copy values from packed struct to avoid unaligned access
    let format_version = index.format_version;
    let package_size = index.package_size;
    let launcher_size = index.launcher_size;
    let metadata_offset = index.metadata_offset;
    let metadata_size = index.metadata_size;
    let slot_table_offset = index.slot_table_offset;
    let slot_table_size = index.slot_table_size;
    let slot_count = index.slot_count;
    let flags = index.flags;
    let index_checksum_val = index.index_checksum;
    let metadata_checksum = index.metadata_checksum;
    let build_timestamp = index.build_timestamp;
    let page_size = index.page_size;
    let capabilities = index.capabilities;
    let requirements = index.requirements;

    let index_metadata = IndexMetadata {
        format_version,
        package_size,
        launcher_size,
        metadata_offset,
        metadata_size,
        slot_table_offset,
        slot_table_size,
        slot_count,
        flags,
        index_checksum: format!("{:08x}", index_checksum_val),
        metadata_checksum: hex::encode(metadata_checksum),
        build_timestamp,
        page_size,
        capabilities,
        requirements,
    };

    let index_path = paths.index_metadata_file();
    let json = serde_json::to_string_pretty(&index_metadata)?;

    fs::write(&index_path, &json)?;
    debug!("💾 Saved index metadata to {:?}", index_path);

    Ok(())
}

/// Check if work environment is valid using checksums
pub fn check_workenv_validity_full(
    paths: &WorkenvPaths,
    index: &Index,
    _metadata: &Metadata,
) -> Result<bool> {
    // First check if extraction is complete
    let complete_path = paths.complete_file();
    if !complete_path.exists() {
        debug!("🔍 No extraction completion marker found");
        return Ok(false);
    }

    // Check package checksum
    validate_package_checksum(paths, index.index_checksum)
}
