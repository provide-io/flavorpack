//! Workenv validation functionality

use crate::error::{FlavorError, Result};
use crate::platform::placeholders::PlaceholderContext;
use log::{debug, warn};
use std::fs;
use std::path::Path;

/// Workenv validator
pub struct WorkenvValidator {
    workenv_path: std::path::PathBuf,
}

impl WorkenvValidator {
    /// Create a new validator
    pub fn new<P: AsRef<Path>>(workenv_path: P) -> Self {
        Self {
            workenv_path: workenv_path.as_ref().to_path_buf(),
        }
    }
    
    /// Check if extraction is complete
    pub fn is_extraction_complete(&self) -> bool {
        self.workenv_path.join(".extraction.complete").exists()
    }
    
    /// Check if extraction is in progress
    pub fn is_extraction_in_progress(&self) -> bool {
        self.workenv_path.join(".extraction.lock").exists()
    }
    
    /// Mark extraction as complete
    pub fn mark_extraction_complete(&self) -> Result<()> {
        let marker = self.workenv_path.join(".extraction.complete");
        fs::write(&marker, "1")?;
        Ok(())
    }
    
    /// Check cache validation
    pub fn check_cache_validity(
        &self,
        check_file: &str,
        expected_content: &str,
    ) -> bool {
        // Substitute placeholders in check file path
        let ctx = PlaceholderContext::new()
            .with_workenv(&self.workenv_path);
        
        let check_path = ctx.substitute(check_file);
        
        debug!("🔍 Checking work environment validity: {}", check_path);
        
        match fs::read_to_string(&check_path) {
            Ok(content) => {
                let is_valid = content.trim() == expected_content;
                if is_valid {
                    debug!("✅ Work environment validation passed");
                } else {
                    debug!(
                        "❌ Work environment validation failed: expected '{}', got '{}'",
                        expected_content,
                        content.trim()
                    );
                }
                is_valid
            }
            Err(_) => {
                debug!("❌ Work environment validation file not found");
                false
            }
        }
    }
    
    /// Check if workenv needs refresh
    pub fn needs_refresh(&self) -> bool {
        // Check for incomplete extraction marker
        if self.workenv_path.join(".extraction.incomplete").exists() {
            return true;
        }
        
        // Check if extraction is not complete
        if !self.is_extraction_complete() {
            return true;
        }
        
        false
    }
    
    /// Clear cache markers
    pub fn clear_markers(&self) -> Result<()> {
        let markers = [
            ".extraction.complete",
            ".extraction.incomplete",
            ".extraction.lock",
        ];
        
        for marker in &markers {
            let path = self.workenv_path.join(marker);
            if path.exists() {
                fs::remove_file(&path)?;
            }
        }
        
        Ok(())
    }
}

/// Check if work environment is valid (convenience function)
pub fn check_workenv_validity(
    workenv_dir: &Path,
    validation: &crate::psp::format_2025::metadata::CacheValidationInfo,
) -> bool {
    let validator = WorkenvValidator::new(workenv_dir);
    validator.check_cache_validity(&validation.check_file, &validation.expected_content)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    
    #[test]
    fn test_extraction_markers() {
        let temp_dir = TempDir::new().unwrap();
        let workenv = temp_dir.path();
        
        let validator = WorkenvValidator::new(workenv);
        
        // Initially not complete
        assert!(!validator.is_extraction_complete());
        
        // Mark as complete
        validator.mark_extraction_complete().unwrap();
        assert!(validator.is_extraction_complete());
        
        // Clear markers
        validator.clear_markers().unwrap();
        assert!(!validator.is_extraction_complete());
    }
    
    #[test]
    fn test_cache_validation() {
        let temp_dir = TempDir::new().unwrap();
        let workenv = temp_dir.path();
        
        // Create metadata directory and file
        let metadata_dir = workenv.join("metadata");
        fs::create_dir_all(&metadata_dir).unwrap();
        fs::write(metadata_dir.join("installed"), "test-1.0.0").unwrap();
        
        let validator = WorkenvValidator::new(workenv);
        
        // Valid content
        assert!(validator.check_cache_validity(
            "{workenv}/metadata/installed",
            "test-1.0.0"
        ));
        
        // Invalid content
        assert!(!validator.check_cache_validity(
            "{workenv}/metadata/installed",
            "test-2.0.0"
        ));
        
        // Missing file
        assert!(!validator.check_cache_validity(
            "{workenv}/metadata/missing",
            "anything"
        ));
    }
    
    #[test]
    fn test_needs_refresh() {
        let temp_dir = TempDir::new().unwrap();
        let workenv = temp_dir.path();
        
        let validator = WorkenvValidator::new(workenv);
        
        // Initially needs refresh (no completion marker)
        assert!(validator.needs_refresh());
        
        // After marking complete, doesn't need refresh
        validator.mark_extraction_complete().unwrap();
        assert!(!validator.needs_refresh());
        
        // With incomplete marker, needs refresh
        fs::write(workenv.join(".extraction.incomplete"), "1").unwrap();
        assert!(validator.needs_refresh());
    }
}