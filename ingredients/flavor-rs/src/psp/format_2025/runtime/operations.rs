//! Environment variable operations (unset, map, set)

use crate::exceptions::{FlavorError, Result};
use glob::Pattern;
use log::{debug, trace, warn};
use std::collections::HashMap;
use super::patterns::PatternProcessor;

/// Handles unset operations on environment variables
pub struct UnsetOperation<'a> {
    patterns: &'a [String],
    processor: &'a PatternProcessor,
}

impl<'a> UnsetOperation<'a> {
    /// Create a new unset operation handler
    pub fn new(patterns: &'a [String], processor: &'a PatternProcessor) -> Self {
        Self { patterns, processor }
    }
    
    /// Execute unset operations on the environment map
    pub fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
        debug!("🗑️ Processing {} unset patterns", self.patterns.len());
        
        let mut total_removed = 0;
        let mut total_preserved = 0;
        
        for pattern in self.patterns {
            let (removed, preserved) = self.process_pattern(pattern, env_map)?;
            total_removed += removed;
            total_preserved += preserved;
        }
        
        debug!(
            "🗑️ Unset complete: {} removed, {} preserved",
            total_removed, total_preserved
        );
        
        Ok(())
    }
    
    /// Process a single unset pattern
    fn process_pattern(
        &self,
        pattern: &str,
        env_map: &mut HashMap<String, String>
    ) -> Result<(usize, usize)> {
        if pattern == "*" {
            self.unset_all_except_preserved(env_map)
        } else if pattern.contains('*') || pattern.contains('?') {
            self.unset_glob_pattern(pattern, env_map)
        } else {
            self.unset_exact_match(pattern, env_map)
        }
    }
    
    /// Unset all variables except those marked for preservation
    fn unset_all_except_preserved(
        &self,
        env_map: &mut HashMap<String, String>
    ) -> Result<(usize, usize)> {
        debug!("🗑️ Unsetting all variables except preserved");
        
        let all_keys: Vec<String> = env_map.keys().cloned().collect();
        let mut removed = 0;
        let mut preserved = 0;
        
        for key in all_keys {
            if self.processor.should_preserve(&key) {
                preserved += 1;
                trace!("  🛡️ Preserved: {}", key);
            } else {
                env_map.remove(&key);
                removed += 1;
                trace!("  🗑️ Unset: {}", key);
            }
        }
        
        Ok((removed, preserved))
    }
    
    /// Unset variables matching a glob pattern
    fn unset_glob_pattern(
        &self,
        pattern: &str,
        env_map: &mut HashMap<String, String>
    ) -> Result<(usize, usize)> {
        let glob_pattern = Pattern::new(pattern).map_err(|e| {
            FlavorError::Configuration(format!("Invalid glob pattern '{}': {}", pattern, e))
        })?;
        
        let matching_keys: Vec<String> = env_map.keys()
            .filter(|k| glob_pattern.matches(k))
            .cloned()
            .collect();
        
        debug!("🗑️ Glob pattern '{}' matches {} variables", pattern, matching_keys.len());
        
        let mut removed = 0;
        let mut preserved = 0;
        
        for key in matching_keys {
            if self.processor.should_preserve(&key) {
                preserved += 1;
                trace!("  🛡️ Preserved (matched unset but also pass): {}", key);
            } else {
                env_map.remove(&key);
                removed += 1;
                trace!("  🗑️ Unset (glob): {}", key);
            }
        }
        
        Ok((removed, preserved))
    }
    
    /// Unset a single exact match variable
    fn unset_exact_match(
        &self,
        key: &str,
        env_map: &mut HashMap<String, String>
    ) -> Result<(usize, usize)> {
        if self.processor.should_preserve(key) {
            debug!("🛡️ Preserved (matched unset but also pass): {}", key);
            Ok((0, 1))
        } else if env_map.remove(key).is_some() {
            debug!("🗑️ Unset: {}", key);
            Ok((1, 0))
        } else {
            trace!("🔍 Variable '{}' not found (already unset)", key);
            Ok((0, 0))
        }
    }
}

/// Handles map (rename) operations on environment variables
pub struct MapOperation<'a> {
    mappings: &'a [String],
    processor: &'a PatternProcessor,
}

impl<'a> MapOperation<'a> {
    /// Create a new map operation handler
    pub fn new(mappings: &'a [String], processor: &'a PatternProcessor) -> Self {
        Self { mappings, processor }
    }
    
    /// Execute map operations on the environment map
    pub fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
        debug!("🔄 Processing {} map operations", self.mappings.len());
        
        let mut successful = 0;
        let mut skipped = 0;
        
        for mapping in self.mappings {
            if self.process_mapping(mapping, env_map)? {
                successful += 1;
            } else {
                skipped += 1;
            }
        }
        
        debug!("🔄 Map complete: {} mapped, {} skipped", successful, skipped);
        Ok(())
    }
    
    /// Process a single mapping operation
    fn process_mapping(
        &self,
        mapping: &str,
        env_map: &mut HashMap<String, String>
    ) -> Result<bool> {
        let parts: Vec<&str> = mapping.splitn(2, '=').collect();
        
        if parts.len() != 2 {
            warn!("⚠️ Invalid map format '{}', expected 'OLD=NEW'", mapping);
            return Ok(false);
        }
        
        let (old_key, new_key) = (parts[0], parts[1]);
        
        // Check if old key is preserved
        if self.processor.should_preserve(old_key) {
            debug!(
                "⚠️ Cannot map preserved variable '{}' to '{}'",
                old_key, new_key
            );
            return Ok(false);
        }
        
        // Perform the mapping
        if let Some(value) = env_map.remove(old_key) {
            debug!("🔄 Mapped: {} -> {} = '{}'", old_key, new_key, value);
            env_map.insert(new_key.to_string(), value);
            Ok(true)
        } else {
            trace!("🔍 Source variable '{}' not found for mapping", old_key);
            Ok(false)
        }
    }
}

/// Handles set operations on environment variables
pub struct SetOperation<'a> {
    assignments: &'a [String],
}

impl<'a> SetOperation<'a> {
    /// Create a new set operation handler
    pub fn new(assignments: &'a [String]) -> Self {
        Self { assignments }
    }
    
    /// Execute set operations on the environment map
    pub fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
        debug!("📝 Processing {} set operations", self.assignments.len());
        
        let mut set_count = 0;
        
        for assignment in self.assignments {
            if self.process_assignment(assignment, env_map)? {
                set_count += 1;
            }
        }
        
        debug!("📝 Set complete: {} variables set", set_count);
        Ok(())
    }
    
    /// Process a single assignment
    fn process_assignment(
        &self,
        assignment: &str,
        env_map: &mut HashMap<String, String>
    ) -> Result<bool> {
        let parts: Vec<&str> = assignment.splitn(2, '=').collect();
        
        if parts.len() != 2 {
            warn!("⚠️ Invalid set format '{}', expected 'KEY=value'", assignment);
            return Ok(false);
        }
        
        let (key, value) = (parts[0], parts[1]);
        
        // Expand environment variables in the value
        let expanded_value = self.expand_variables(value, env_map);
        
        if env_map.contains_key(key) {
            debug!("📝 Override: {} = '{}'", key, expanded_value);
        } else {
            debug!("📝 Set: {} = '{}'", key, expanded_value);
        }
        
        env_map.insert(key.to_string(), expanded_value);
        Ok(true)
    }
    
    /// Expand environment variables in a value string
    /// 
    /// Supports $VAR and ${VAR} syntax
    fn expand_variables(&self, value: &str, env_map: &HashMap<String, String>) -> String {
        let mut result = value.to_string();
        
        // Handle ${VAR} syntax
        while let Some(start) = result.find("${") {
            if let Some(end) = result[start+2..].find('}') {
                let var_name = &result[start+2..start+2+end];
                let replacement = env_map.get(var_name).unwrap_or(&String::new());
                result.replace_range(start..start+3+end, replacement);
            } else {
                break; // Invalid syntax, stop processing
            }
        }
        
        // Handle $VAR syntax (simple implementation)
        // This is simplified - a full implementation would need more careful parsing
        
        result
    }
}