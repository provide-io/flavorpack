//! Work environment management

use super::super::defaults::DEFAULT_DISK_SPACE_MULTIPLIER;
use super::super::metadata::{Metadata, WorkenvInfo};
use super::super::paths::WorkenvPaths;
use crate::exceptions::Result;
use crate::utils::get_cache_dir;
use log::debug;
use std::fs;
use std::path::Path;

/// Calculate a deterministic cache path for a package
pub(super) fn get_workenv_paths(package_path: &Path) -> WorkenvPaths {
    let cache_base = get_cache_dir();
    WorkenvPaths::new(cache_base, package_path)
}

/// Check if there's enough disk space for extraction
pub(super) fn check_disk_space(_paths: &WorkenvPaths, metadata: &Metadata) -> Result<()> {
    let total_size_needed = calculate_total_size_needed(metadata);
    let workenv_path = _paths.workenv();
    std::fs::create_dir_all(&workenv_path)?;
    let available_space = get_available_disk_space(&workenv_path)?;
    ensure_sufficient_disk_space(total_size_needed, available_space)?;
    debug!(
        "✅ Disk space check passed: required={} available={}",
        total_size_needed, available_space
    );
    Ok(())
}

/// Setup workenv directories with proper permissions
pub(super) fn setup_workenv_directories(
    workenv_path: &Path,
    workenv_info: &WorkenvInfo,
) -> Result<()> {
    if let Some(ref directories) = workenv_info.directories {
        for dir_spec in directories {
            // Substitute {workenv} placeholder in the path
            let path_str = if dir_spec.path.starts_with("{workenv}/") {
                &dir_spec.path["{workenv}/".len()..]
            } else if dir_spec.path == "{workenv}" {
                ""
            } else {
                &dir_spec.path
            };

            let dir_path = if path_str.is_empty() {
                workenv_path.to_path_buf()
            } else {
                workenv_path.join(path_str)
            };
            debug!("📁 Creating directory: {:?}", dir_path);
            fs::create_dir_all(&dir_path)?;

            // Set permissions on Unix systems
            #[cfg(unix)]
            {
                use super::super::defaults::DEFAULT_DIR_PERMS;
                use std::os::unix::fs::PermissionsExt;

                // Use specified mode or default to 0700 (user-only access)
                let mode_str = dir_spec.mode.as_deref().unwrap_or("0700");

                // Parse octal mode string (e.g., "0700")
                if let Ok(mode) = u32::from_str_radix(mode_str.trim_start_matches('0'), 8) {
                    let permissions = fs::Permissions::from_mode(mode);
                    fs::set_permissions(&dir_path, permissions)?;
                    debug!("🔒 Set permissions {} on {:?}", mode_str, dir_path);
                } else {
                    // Fallback to default dir permissions if parsing fails
                    let permissions = fs::Permissions::from_mode(DEFAULT_DIR_PERMS as u32);
                    fs::set_permissions(&dir_path, permissions)?;
                    debug!(
                        "🔒 Set default permissions {} on {:?}",
                        DEFAULT_DIR_PERMS, dir_path
                    );
                }
            }
        }
    }
    Ok(())
}

fn calculate_total_size_needed(metadata: &Metadata) -> u64 {
    metadata
        .slots
        .iter()
        .map(|slot| u64::try_from(slot.size.max(0)).unwrap_or(0))
        .map(|size| size.saturating_mul(DEFAULT_DISK_SPACE_MULTIPLIER))
        .sum()
}

fn ensure_sufficient_disk_space(required_bytes: u64, available_bytes: u64) -> Result<()> {
    use crate::exceptions::FlavorError;

    if available_bytes < required_bytes {
        return Err(FlavorError::Generic(format!(
            "Insufficient disk space: required {} bytes, available {} bytes",
            required_bytes, available_bytes
        )));
    }

    Ok(())
}

fn get_available_disk_space(path: &Path) -> Result<u64> {
    use crate::exceptions::FlavorError;
    fs2::available_space(path).map_err(|e| {
        FlavorError::Generic(format!("Failed to query disk space for {:?}: {}", path, e))
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::psp::format_2025::metadata::{
        ExecutionInfo, Metadata, PackageInfo, PlatformInfo, SlotMetadata,
    };

    fn sample_metadata(slot_sizes: &[i64]) -> Metadata {
        Metadata {
            format: "PSPF/2025".to_string(),
            format_version: None,
            package: PackageInfo {
                name: "pkg".to_string(),
                version: "1.0.0".to_string(),
            },
            slots: slot_sizes
                .iter()
                .enumerate()
                .map(|(index, size)| SlotMetadata {
                    index,
                    id: format!("slot-{index}"),
                    source: "src".to_string(),
                    target: format!("bin/{index}"),
                    size: *size,
                    checksum: "sum".to_string(),
                    operations: "raw".to_string(),
                    purpose: "code".to_string(),
                    lifecycle: "runtime".to_string(),
                    permissions: None,
                    resolution: None,
                    self_ref: None,
                })
                .collect(),
            execution: ExecutionInfo {
                primary_slot: 0,
                command: "echo hi".to_string(),
                env: std::collections::HashMap::new(),
            },
            verification: None,
            build: Some(crate::psp::format_2025::metadata::BuildInfo {
                tool: "builder".to_string(),
                tool_version: "1.0.0".to_string(),
                timestamp: "2026-01-01T00:00:00Z".to_string(),
                deterministic: true,
                platform: PlatformInfo {
                    os: "linux".to_string(),
                    arch: "amd64".to_string(),
                    host: "host".to_string(),
                },
            }),
            launcher: None,
            compatibility: None,
            cache_validation: None,
            runtime: None,
            workenv: None,
            setup_commands: Vec::new(),
        }
    }

    #[test]
    fn test_calculate_total_size_needed_uses_multiplier() {
        let metadata = sample_metadata(&[10, 20]);
        assert_eq!(
            calculate_total_size_needed(&metadata),
            30 * DEFAULT_DISK_SPACE_MULTIPLIER
        );
    }

    #[test]
    fn test_ensure_sufficient_disk_space_rejects_insufficient_capacity() {
        let result = ensure_sufficient_disk_space(4096, 1024);
        assert!(result.is_err());
    }

    #[test]
    fn test_ensure_sufficient_disk_space_accepts_available_capacity() {
        let result = ensure_sufficient_disk_space(1024, 4096);
        assert!(result.is_ok());
    }
}
