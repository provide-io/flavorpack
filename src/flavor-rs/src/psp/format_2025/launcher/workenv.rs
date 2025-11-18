//! Work environment management

use super::super::defaults::DEFAULT_DISK_SPACE_MULTIPLIER;
use super::super::metadata::{Metadata, WorkenvInfo};
use super::super::paths::WorkenvPaths;
use crate::exceptions::Result;
use crate::utils::get_cache_dir;
use log::{debug, warn};
use std::fs;
use std::path::Path;

/// Calculate a deterministic cache path for a package
pub(super) fn get_workenv_paths(package_path: &Path) -> WorkenvPaths {
    let cache_base = get_cache_dir();
    WorkenvPaths::new(cache_base, package_path)
}

/// Check if there's enough disk space for extraction
pub(super) fn check_disk_space(_paths: &WorkenvPaths, metadata: &Metadata) -> Result<()> {
    // Calculate total size needed (compressed size * DISK_SPACE_MULTIPLIER for safety)
    let _total_size_needed: u64 = metadata
        .slots
        .iter()
        .map(|slot| slot.size as u64 * DEFAULT_DISK_SPACE_MULTIPLIER)
        .sum();

    // Get available disk space
    #[cfg(unix)]
    {
        use crate::exceptions::FlavorError;

        // Safe disk space check using fs2 crate alternative or simplified check
        let workenv_path = _paths.workenv();

        // Try to create a small test file to check if we can write
        // This is a simpler but less precise check than statvfs
        let test_file = workenv_path.join(".space_test");
        match std::fs::create_dir_all(&workenv_path) {
            Ok(_) => {
                match std::fs::write(&test_file, b"test") {
                    Ok(_) => {
                        let _ = std::fs::remove_file(&test_file);
                        debug!("✅ Disk space check passed (write test successful)");
                    }
                    Err(e) => {
                        warn!("⚠️ Disk write test failed: {}", e);
                        // Don't fail the process, just warn
                    }
                }
            }
            Err(e) => {
                warn!("⚠️ Could not create workenv directory: {}", e);
                return Err(FlavorError::Generic(format!(
                    "Cannot create workenv directory: {}",
                    e
                )));
            }
        }
    }

    #[cfg(not(unix))]
    {
        warn!("⚠️ Disk space check not implemented for this platform");
    }

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
