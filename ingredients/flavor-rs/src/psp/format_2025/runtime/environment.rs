//! Runtime environment configuration structures

use serde::{Deserialize, Serialize};

/// Runtime environment configuration
/// 
/// Defines how environment variables should be processed during package execution.
/// Operations are applied in the following order:
/// 1. `unset` - Remove variables (with pass pattern preservation)
/// 2. `map` - Rename variables
/// 3. `set` - Add or override variables
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct RuntimeEnv {
    /// Patterns for variables to preserve/pass through
    /// 
    /// These variables are protected from unset operations and are
    /// validated to ensure they exist after processing.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub pass: Vec<String>,
    
    /// Patterns for variables to unset/remove
    /// 
    /// Supports:
    /// - Exact matches: `"TEMP"`
    /// - Glob patterns: `"PYTHON*"`, `"*_OLD"`
    /// - Special pattern `"*"` to clear all except preserved
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub unset: Vec<String>,
    
    /// Variable mapping/renaming operations
    /// 
    /// Format: `"OLD_NAME=NEW_NAME"`
    /// The old variable is removed and its value assigned to the new name.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub map: Vec<String>,
    
    /// Variables to set or override
    /// 
    /// Format: `"VAR_NAME=value"`
    /// Always applied last, overriding any existing values.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub set: Vec<String>,
}

impl RuntimeEnv {
    /// Check if the runtime environment has any operations defined
    pub fn is_empty(&self) -> bool {
        self.pass.is_empty() 
            && self.unset.is_empty() 
            && self.map.is_empty() 
            && self.set.is_empty()
    }
    
    /// Get the total number of operations defined
    pub fn operation_count(&self) -> usize {
        self.pass.len() + self.unset.len() + self.map.len() + self.set.len()
    }
}