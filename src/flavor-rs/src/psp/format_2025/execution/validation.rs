//! Validation and checksum management

use super::super::index::Index;
use super::super::metadata::{CacheValidationInfo, Metadata};
use super::super::paths::WorkenvPaths;
use super::placeholders::substitute_placeholders;
use crate::exceptions::Result;
use log::debug;
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

/// Reports a workenv built by a different package as unusable, at every
/// validation level.
///
/// The stored value identifies the package that produced this workenv, so a
/// mismatch means the cache belongs to another build and its contents are
/// stale. Extraction runs again and replaces them.
///
/// This is a cache-validity question, not an authenticity one. Authenticity is
/// settled earlier by signature verification, which runs on every launch and
/// aborts under `Strict`. Neither checksum covers the extracted tree, so a
/// mismatch says nothing about whether that tree was modified; re-extraction
/// overwrites it either way.
fn validate_package_checksum_mismatch(
    stored_checksum: &str,
    current_checksum: &str,
    validation_level: crate::psp::format_2025::defaults::ValidationLevel,
) -> Result<bool> {
    debug!(
        "🔍 Work environment belongs to package {}, this one is {}; extracting again \
         (validation level: {:?})",
        stored_checksum, current_checksum, validation_level
    );
    Ok(false)
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

/// Check whether the setup steps ran to completion.
///
/// The extraction marker says the payload was unpacked; it says nothing about
/// whether the wheels were installed afterwards. `cache_validation` names a
/// file the setup steps write *last*, so its presence -- with the expected
/// content -- is the only evidence that setup finished. Without this check, a
/// setup interrupted midway leaves a workenv that is extracted, checksum-clean
/// and missing `bin/`, and every later run reuses it and fails at exec with
/// "No such file or directory".
fn setup_completed(paths: &WorkenvPaths, metadata: &Metadata, cache: &CacheValidationInfo) -> bool {
    let workenv = paths.workenv();
    let check_path = substitute_placeholders(&cache.check_file, &workenv, &metadata.package);
    let expected = substitute_placeholders(&cache.expected_content, &workenv, &metadata.package);

    let Ok(actual) = fs::read_to_string(&check_path) else {
        debug!("🔍 Setup completion marker missing: {check_path}");
        return false;
    };

    if expected.is_empty() || actual.trim() == expected.trim() {
        true
    } else {
        debug!(
            "🔍 Setup completion marker says {:?}, expected {:?}",
            actual.trim(),
            expected.trim()
        );
        false
    }
}

/// Check if work environment is valid using checksums
pub fn check_workenv_validity_full(
    paths: &WorkenvPaths,
    index: &Index,
    metadata: &Metadata,
) -> Result<bool> {
    // First check if extraction is complete
    let complete_path = paths.complete_file();
    if !complete_path.exists() {
        debug!("🔍 No extraction completion marker found");
        return Ok(false);
    }

    // Then that setup finished, which extraction alone does not imply.
    if let Some(cache) = &metadata.cache_validation {
        if !setup_completed(paths, metadata, cache) {
            debug!("🔍 Work environment is incomplete; setup will run again");
            return Ok(false);
        }
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
    use crate::psp::format_2025::metadata::{
        CacheValidationInfo, ExecutionInfo, Metadata, PackageInfo, SlotMetadata,
    };
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
            execution: Some(ExecutionInfo {
                command: "python app.py".to_string(),
                env: HashMap::new(),
            }),
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
    fn a_rebuilt_package_invalidates_the_cache_rather_than_refusing() {
        // A rebuilt package must stay launchable. The checksum identifies the
        // package that filled the cache, so a mismatch means the cache is
        // stale and extraction should run again -- the answer the missing-file
        // branch already gives. Failing instead strands the package behind a
        // hidden metadata directory only a hand-written `rm` can clear.
        for level in [
            ValidationLevel::None,
            ValidationLevel::Minimal,
            ValidationLevel::Relaxed,
            ValidationLevel::Standard,
            ValidationLevel::Strict,
        ] {
            let reusable = validate_package_checksum_mismatch("deadbeef", "cafebabe", level)
                .unwrap_or_else(|err| panic!("{level:?} refused a rebuilt package: {err}"));
            assert!(!reusable, "{level:?} reused a workenv from another package");
        }
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

    /// A workenv that extracted but never finished installing must not be reused.
    ///
    /// This is the shape that broke in the field: setup was interrupted, so
    /// `metadata/installed` was never written, but the extraction marker and the
    /// package checksum both survived. Every later run reused the half-built
    /// workenv and died at exec with "No such file or directory".
    #[test]
    fn an_extracted_but_unfinished_workenv_is_not_reused() {
        let temp = tempfile::tempdir().expect("tempdir");
        let paths = WorkenvPaths::new(
            PathBuf::from(temp.path()),
            PathBuf::from("demo.psp").as_path(),
        );
        let mut metadata = sample_metadata();
        metadata.cache_validation = Some(CacheValidationInfo {
            check_file: "{workenv}/metadata/installed".to_string(),
            expected_content: "{package_name}-{version}".to_string(),
        });
        let mut index = Index::new();
        index.index_checksum = 0x12345678;

        // Extraction finished and the checksum matches: everything the old
        // check looked at is in order.
        fs::create_dir_all(paths.extract()).expect("create extract dir");
        fs::write(paths.complete_file(), b"ok").expect("write completion marker");
        save_package_checksum(&paths, index.index_checksum).expect("save checksum");

        assert!(
            !check_workenv_validity_full(&paths, &index, &metadata).expect("check runs"),
            "a workenv with no setup marker must be rebuilt, not reused"
        );

        // Setup finishes and writes its marker.
        let marker = paths.workenv().join("metadata/installed");
        fs::create_dir_all(marker.parent().expect("marker parent")).expect("create metadata dir");
        fs::write(&marker, b"demo-1.0.0").expect("write setup marker");

        assert!(
            check_workenv_validity_full(&paths, &index, &metadata).expect("check runs"),
            "a workenv whose setup completed is reusable"
        );
    }

    /// A marker left by a different version is not evidence for this one.
    #[test]
    fn a_setup_marker_from_another_version_is_rejected() {
        let temp = tempfile::tempdir().expect("tempdir");
        let paths = WorkenvPaths::new(
            PathBuf::from(temp.path()),
            PathBuf::from("demo.psp").as_path(),
        );
        let mut metadata = sample_metadata();
        metadata.cache_validation = Some(CacheValidationInfo {
            check_file: "{workenv}/metadata/installed".to_string(),
            expected_content: "{package_name}-{version}".to_string(),
        });
        let mut index = Index::new();
        index.index_checksum = 0x12345678;

        fs::create_dir_all(paths.extract()).expect("create extract dir");
        fs::write(paths.complete_file(), b"ok").expect("write completion marker");
        save_package_checksum(&paths, index.index_checksum).expect("save checksum");

        let marker = paths.workenv().join("metadata/installed");
        fs::create_dir_all(marker.parent().expect("marker parent")).expect("create metadata dir");
        fs::write(&marker, b"demo-0.9.0").expect("write stale setup marker");

        assert!(
            !check_workenv_validity_full(&paths, &index, &metadata).expect("check runs"),
            "a marker naming another version must not validate this one"
        );
    }

    /// Packages whose manifest declares no cache_validation keep working.
    #[test]
    fn a_manifest_without_cache_validation_is_unaffected() {
        let temp = tempfile::tempdir().expect("tempdir");
        let paths = WorkenvPaths::new(
            PathBuf::from(temp.path()),
            PathBuf::from("demo.psp").as_path(),
        );
        let metadata = sample_metadata(); // cache_validation: None
        let mut index = Index::new();
        index.index_checksum = 0x12345678;

        fs::create_dir_all(paths.extract()).expect("create extract dir");
        fs::write(paths.complete_file(), b"ok").expect("write completion marker");
        save_package_checksum(&paths, index.index_checksum).expect("save checksum");

        assert!(check_workenv_validity_full(&paths, &index, &metadata).expect("check runs"));
    }
}
