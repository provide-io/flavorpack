//! Workenv directory creation and management

use crate::error::{FlavorError, Result};
use log::{debug, info};
use std::fs;
use std::path::Path;

/// Directory specification with permissions
#[derive(Debug, Clone)]
pub struct DirectorySpec {
    /// Path relative to workenv root
    pub path: String,
    /// Unix permissions mode (e.g., "0700")
    pub mode: Option<String>,
}

impl DirectorySpec {
    /// Create a new directory spec
    pub fn new<S: Into<String>>(path: S) -> Self {
        Self {
            path: path.into(),
            mode: None,
        }
    }
    
    /// Set the permissions mode
    pub fn with_mode<S: Into<String>>(mut self, mode: S) -> Self {
        self.mode = Some(mode.into());
        self
    }
}

/// Workenv directories manager
pub struct WorkenvDirectories {
    /// Base workenv path
    workenv_path: std::path::PathBuf,
    /// Default umask to apply
    umask: u32,
}

impl WorkenvDirectories {
    /// Create a new workenv directories manager
    pub fn new<P: AsRef<Path>>(workenv_path: P) -> Self {
        Self {
            workenv_path: workenv_path.as_ref().to_path_buf(),
            umask: 0o077, // Default to owner-only access
        }
    }
    
    /// Set the umask
    pub fn with_umask(mut self, umask: u32) -> Self {
        self.umask = umask;
        self
    }
    
    /// Create directories from specifications
    pub fn create_from_specs(&self, specs: &[DirectorySpec]) -> Result<()> {
        for spec in specs {
            self.create_directory(spec)?;
        }
        Ok(())
    }
    
    /// Create a single directory
    fn create_directory(&self, spec: &DirectorySpec) -> Result<()> {
        let dir_path = self.workenv_path.join(&spec.path);
        
        debug!("📁 Creating directory: {:?}", dir_path);
        fs::create_dir_all(&dir_path)?;
        
        // Set permissions on Unix systems
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            
            let mode = if let Some(ref mode_str) = spec.mode {
                // Parse explicit mode
                parse_octal_mode(mode_str)?
            } else {
                // Apply umask to default permissions
                0o777 & !self.umask
            };
            
            let permissions = fs::Permissions::from_mode(mode);
            fs::set_permissions(&dir_path, permissions)?;
            debug!("🔒 Set permissions {:o} on {:?}", mode, dir_path);
        }
        
        Ok(())
    }
    
    /// Create standard workenv directories
    pub fn create_standard_directories(&self) -> Result<()> {
        let standard_dirs = vec![
            DirectorySpec::new("tmp"),
            DirectorySpec::new("var"),
            DirectorySpec::new("var/log"),
            DirectorySpec::new("var/cache"),
            DirectorySpec::new("var/run"),
            DirectorySpec::new("etc"),
            DirectorySpec::new("home"),
            DirectorySpec::new("state"),
            DirectorySpec::new("bin"),
            DirectorySpec::new("lib"),
            DirectorySpec::new("share"),
        ];
        
        self.create_from_specs(&standard_dirs)
    }
}

/// Parse an octal mode string (e.g., "0700")
fn parse_octal_mode(mode_str: &str) -> Result<u32> {
    let trimmed = mode_str.trim_start_matches('0');
    u32::from_str_radix(trimmed, 8)
        .map_err(|_| FlavorError::invalid_config(format!("Invalid mode: {}", mode_str)))
}

/// Create workenv directories (convenience function)
pub fn create_workenv_directories<P: AsRef<Path>>(
    workenv_path: P,
    directories: Option<&[serde_json::Value]>,
) -> Result<()> {
    let manager = WorkenvDirectories::new(workenv_path);
    
    if let Some(dirs) = directories {
        let specs: Result<Vec<DirectorySpec>> = dirs
            .iter()
            .map(|v| {
                let obj = v.as_object()
                    .ok_or_else(|| FlavorError::invalid_config("Directory spec must be an object"))?;
                
                let path = obj.get("path")
                    .and_then(|p| p.as_str())
                    .ok_or_else(|| FlavorError::invalid_config("Directory spec missing 'path'"))?;
                
                let mode = obj.get("mode")
                    .and_then(|m| m.as_str())
                    .map(|s| s.to_string());
                
                Ok(DirectorySpec {
                    path: path.to_string(),
                    mode,
                })
            })
            .collect();
        
        manager.create_from_specs(&specs?)?;
    } else {
        manager.create_standard_directories()?;
    }
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    
    #[test]
    fn test_directory_creation() {
        let temp_dir = TempDir::new().unwrap();
        let workenv = temp_dir.path();
        
        let manager = WorkenvDirectories::new(workenv);
        let specs = vec![
            DirectorySpec::new("test1"),
            DirectorySpec::new("test2/nested"),
        ];
        
        manager.create_from_specs(&specs).unwrap();
        
        assert!(workenv.join("test1").exists());
        assert!(workenv.join("test2/nested").exists());
    }
    
    #[test]
    fn test_parse_octal_mode() {
        assert_eq!(parse_octal_mode("0700").unwrap(), 0o700);
        assert_eq!(parse_octal_mode("0755").unwrap(), 0o755);
        assert_eq!(parse_octal_mode("700").unwrap(), 0o700);
        assert_eq!(parse_octal_mode("0077").unwrap(), 0o077);
    }
    
    #[cfg(unix)]
    #[test]
    fn test_permissions() {
        use std::os::unix::fs::PermissionsExt;
        
        let temp_dir = TempDir::new().unwrap();
        let workenv = temp_dir.path();
        
        let manager = WorkenvDirectories::new(workenv).with_umask(0o077);
        let specs = vec![
            DirectorySpec::new("private"),
            DirectorySpec::new("custom").with_mode("0755"),
        ];
        
        manager.create_from_specs(&specs).unwrap();
        
        // Check that umask was applied to private dir (should be 0700)
        let private_meta = fs::metadata(workenv.join("private")).unwrap();
        let private_mode = private_meta.permissions().mode() & 0o777;
        assert_eq!(private_mode, 0o700);
        
        // Check that explicit mode was used for custom dir
        let custom_meta = fs::metadata(workenv.join("custom")).unwrap();
        let custom_mode = custom_meta.permissions().mode() & 0o777;
        assert_eq!(custom_mode, 0o755);
    }
}