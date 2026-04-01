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
                validate_package_checksum_mismatch(
                    stored_checksum,
                    &current_checksum_str,
                    crate::psp::format_2025::defaults::get_validation_level(),
                )
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

fn validate_package_checksum_mismatch(
    stored_checksum: &str,
    current_checksum: &str,
    validation_level: crate::psp::format_2025::defaults::ValidationLevel,
) -> Result<bool> {
    use crate::psp::format_2025::defaults::ValidationLevel;

    match validation_level {
        ValidationLevel::None | ValidationLevel::Minimal => {
            warn!(
                "⚠️ SECURITY WARNING: Package checksum mismatch! cached: {}, current: {}",
                stored_checksum, current_checksum
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
                stored_checksum, current_checksum
            );
            warn!("⚠️ Cache may be compromised or package has changed");
            warn!("⚠️ Continuing due to relaxed validation");
            Ok(false)
        }
        ValidationLevel::Standard => {
            eprintln!(
                "🚨 SECURITY WARNING: Package checksum mismatch! cached: {}, current: {}",
                stored_checksum, current_checksum
            );
            eprintln!("🚨 Cache may be compromised or package has changed");
            eprintln!(
                "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)"
            );
            warn!(
                "⚠️ Package checksum mismatch, continuing with standard validation: cached: {}, current: {}",
                stored_checksum, current_checksum
            );
            Ok(false)
        }
        ValidationLevel::Strict => {
            log::error!(
                "🚨 CRITICAL: Package checksum mismatch! cached: {}, current: {}",
                stored_checksum,
                current_checksum
            );
            log::error!("🚨 Cache may be compromised or package has changed");
            log::error!(
                "🚨 Refusing to continue. Set FLAVOR_VALIDATION=relaxed to bypass (NOT RECOMMENDED)"
            );
            Err(FlavorError::Generic(format!(
                "package checksum mismatch: cached={}, current={}",
                stored_checksum, current_checksum
            )))
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

#[cfg(test)]
mod tests {
    use super::{
        check_workenv_validity_full, save_index_metadata, save_package_checksum,
        validate_package_checksum, validate_package_checksum_mismatch,
    };
    use crate::psp::format_2025::defaults::ValidationLevel;
    use crate::psp::format_2025::index::Index;
    use crate::psp::format_2025::metadata::{ExecutionInfo, Metadata, PackageInfo, SlotMetadata};
    use crate::psp::format_2025::paths::WorkenvPaths;
    use std::collections::HashMap;
    use std::fs;
    use std::path::PathBuf;

    fn sample_metadata() -> Metadata {
        Metadata {
            format: "PSPF/2025".to_string(),
            format_version: Some("2025.1".to_string()),
            package: PackageInfo {
                name: "demo".to_string(),
                version: "1.0.0".to_string(),
            },
            slots: vec![SlotMetadata {
                index: 0,
                id: "app".to_string(),
                source: "src".to_string(),
                target: "{workenv}/app".to_string(),
                size: 1,
                checksum: "deadbeef".to_string(),
                operations: "none".to_string(),
                purpose: "code".to_string(),
                lifecycle: "runtime".to_string(),
                permissions: None,
                resolution: None,
                self_ref: None,
            }],
            execution: ExecutionInfo {
                primary_slot: 0,
                command: "python app.py".to_string(),
                env: HashMap::new(),
            },
            verification: None,
            build: None,
            launcher: None,
            compatibility: None,
            cache_validation: None,
            runtime: None,
            workenv: None,
            setup_commands: Vec::new(),
            policy: None,
        }
    }

    #[test]
    fn save_and_validate_package_checksum_round_trip() {
        let temp = tempfile::tempdir().expect("tempdir");
        let paths = WorkenvPaths::new(
            PathBuf::from(temp.path()),
            PathBuf::from("demo.psp").as_path(),
        );

        save_package_checksum(&paths, 0xdeadbeef).expect("save checksum");

        assert!(validate_package_checksum(&paths, 0xdeadbeef).expect("validate checksum"));
    }

    #[test]
    fn validate_package_checksum_mismatch_varies_by_validation_level() {
        assert!(
            !validate_package_checksum_mismatch("deadbeef", "cafebabe", ValidationLevel::Relaxed)
                .expect("relaxed mismatch should be non-fatal")
        );
        assert!(
            !validate_package_checksum_mismatch("deadbeef", "cafebabe", ValidationLevel::Standard)
                .expect("standard mismatch should be non-fatal")
        );
        assert!(
            validate_package_checksum_mismatch("deadbeef", "cafebabe", ValidationLevel::Strict)
                .is_err()
        );
    }

    #[test]
    fn save_index_metadata_writes_expected_json_fields() {
        let temp = tempfile::tempdir().expect("tempdir");
        let paths = WorkenvPaths::new(
            PathBuf::from(temp.path()),
            PathBuf::from("demo.psp").as_path(),
        );
        let mut index = Index::new();
        index.format_version = 0x2025_0001;
        index.package_size = 1234;
        index.index_checksum = 0xfeedbeef;
        index.metadata_checksum = [0xAB; 32];

        save_index_metadata(&paths, &index).expect("save index metadata");

        let data = fs::read_to_string(paths.index_metadata_file()).expect("read index metadata");
        assert!(data.contains("\"format_version\": 539295745"));
        assert!(data.contains("\"package_size\": 1234"));
        assert!(data.contains("\"index_checksum\": \"feedbeef\""));
        assert!(data.contains(&"ab".repeat(32)));
    }

    #[test]
    fn check_workenv_validity_requires_complete_marker_and_matching_checksum() {
        let temp = tempfile::tempdir().expect("tempdir");
        let paths = WorkenvPaths::new(
            PathBuf::from(temp.path()),
            PathBuf::from("demo.psp").as_path(),
        );
        let metadata = sample_metadata();
        let mut index = Index::new();
        index.index_checksum = 0x12345678;

        assert!(
            !check_workenv_validity_full(&paths, &index, &metadata)
                .expect("missing marker should be invalid")
        );

        fs::create_dir_all(paths.extract()).expect("create extract dir");
        fs::write(paths.complete_file(), b"ok").expect("write completion marker");
        save_package_checksum(&paths, index.index_checksum).expect("save checksum");

        assert!(
            check_workenv_validity_full(&paths, &index, &metadata)
                .expect("matching state should be valid")
        );
    }
}
