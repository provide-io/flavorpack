//! Path management for PSPF/2025 workenv structure

use super::defaults::{
    DEFAULT_COMPLETE_FILE, DEFAULT_EXTRACT_DIR, DEFAULT_INDEX_METADATA_FILE, DEFAULT_INSTANCE_DIR,
    DEFAULT_LOCK_FILE, DEFAULT_LOG_DIR, DEFAULT_PACKAGE_CHECKSUM_FILE, DEFAULT_PACKAGE_DIR,
    DEFAULT_PSP_METADATA_FILE, DEFAULT_PSPF_HIDDEN_PREFIX, DEFAULT_PSPF_SUFFIX, DEFAULT_TMP_DIR,
};
use std::path::{Path, PathBuf};

/// Manages all paths for a workenv with instance and package metadata
#[derive(Debug, Clone)]
pub struct WorkenvPaths {
    cache_dir: PathBuf,
    workenv_name: String,
}

impl WorkenvPaths {
    /// Create a new WorkenvPaths from cache directory and package path
    pub fn new(cache_dir: PathBuf, package_path: &Path) -> Self {
        // Extract workenv name from package filename
        let workenv_name = package_path
            .file_name()
            .and_then(|n| n.to_str())
            .map(|n| {
                // Remove .psp or .pspf extension if present
                n.strip_suffix(".psp")
                    .or_else(|| n.strip_suffix(".pspf"))
                    .unwrap_or(n)
            })
            .unwrap_or("unknown")
            .to_string();

        Self {
            cache_dir,
            workenv_name,
        }
    }

    // ==================== Content Paths ====================

    /// Get the main workenv directory path (content location)
    pub fn workenv(&self) -> PathBuf {
        self.cache_dir.join("workenv").join(&self.workenv_name)
    }

    // ==================== Metadata Paths ====================

    /// Get the hidden metadata directory path (.{name}.pspf) that contains both instance and package metadata
    pub fn metadata(&self) -> PathBuf {
        self.cache_dir.join("workenv").join(format!(
            "{}{}{}",
            DEFAULT_PSPF_HIDDEN_PREFIX, self.workenv_name, DEFAULT_PSPF_SUFFIX
        ))
    }

    /// Get the instance metadata directory (persistent)
    pub fn instance(&self) -> PathBuf {
        self.metadata().join(DEFAULT_INSTANCE_DIR)
    }

    /// Get the package metadata directory (replaced each extraction)
    pub fn package_metadata(&self) -> PathBuf {
        self.metadata().join(DEFAULT_PACKAGE_DIR)
    }

    /// Get the temporary extraction directory root
    pub fn tmp(&self) -> PathBuf {
        self.metadata().join(DEFAULT_TMP_DIR)
    }

    /// Get a specific temp extraction directory for a PID
    pub fn temp_extraction(&self, pid: u32) -> PathBuf {
        self.tmp().join(pid.to_string())
    }

    // ==================== Instance Paths ====================

    /// Get the extract operations directory
    pub fn extract(&self) -> PathBuf {
        self.instance().join(DEFAULT_EXTRACT_DIR)
    }

    /// Get the log directory
    pub fn log(&self) -> PathBuf {
        self.instance().join(DEFAULT_LOG_DIR)
    }

    /// Get the lock file path
    pub fn lock_file(&self) -> PathBuf {
        self.extract().join(DEFAULT_LOCK_FILE)
    }

    /// Get the completion marker file path
    pub fn complete_file(&self) -> PathBuf {
        self.extract().join(DEFAULT_COMPLETE_FILE)
    }

    /// Get the package checksum file path
    pub fn checksum_file(&self) -> PathBuf {
        self.instance().join(DEFAULT_PACKAGE_CHECKSUM_FILE)
    }

    /// Get the index metadata file path
    pub fn index_metadata_file(&self) -> PathBuf {
        self.instance().join(DEFAULT_INDEX_METADATA_FILE)
    }

    // ==================== Package Metadata Paths ====================

    /// Get the PSP metadata JSON file path
    pub fn psp_metadata_file(&self) -> PathBuf {
        self.package_metadata().join(DEFAULT_PSP_METADATA_FILE)
    }

    // ==================== Utility Methods ====================

    /// Get the workenv name
    pub fn name(&self) -> &str {
        &self.workenv_name
    }

    /// Check if the workenv exists
    pub fn workenv_exists(&self) -> bool {
        self.workenv().exists()
    }

    /// Check if metadata directory exists
    pub fn metadata_exists(&self) -> bool {
        self.metadata().exists()
    }

    /// Get all temp extraction directories
    pub fn list_temp_extractions(&self) -> std::io::Result<Vec<PathBuf>> {
        let tmp_dir = self.tmp();
        if !tmp_dir.exists() {
            return Ok(Vec::new());
        }

        let mut dirs = Vec::new();
        for entry in std::fs::read_dir(tmp_dir)? {
            let entry = entry?;
            if entry.file_type()?.is_dir() {
                dirs.push(entry.path());
            }
        }
        Ok(dirs)
    }
}

#[cfg(test)]
mod tests {
    use super::WorkenvPaths;
    use std::path::PathBuf;

    #[test]
    fn test_paths_structure() {
        let cache = PathBuf::from("/home/user/.cache/flavor");
        let package = PathBuf::from("/tmp/myapp.psp");
        let paths = WorkenvPaths::new(cache, &package);

        assert_eq!(paths.name(), "myapp");
        assert_eq!(
            paths.workenv(),
            PathBuf::from("/home/user/.cache/flavor/workenv/myapp")
        );
        assert_eq!(
            paths.metadata(),
            PathBuf::from("/home/user/.cache/flavor/workenv/.myapp.pspf")
        );
        assert_eq!(
            paths.instance(),
            PathBuf::from("/home/user/.cache/flavor/workenv/.myapp.pspf/instance")
        );
        assert_eq!(
            paths.lock_file(),
            PathBuf::from("/home/user/.cache/flavor/workenv/.myapp.pspf/instance/extract/lock")
        );
    }
}
