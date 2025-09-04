//! Runtime environment processing for PSPF/2025
//!
//! This module handles the runtime.env configuration from PSPF metadata,
//! allowing packages to control their execution environment through
//! environment variable operations.
//!
//! The implementation has been refactored into sub-modules for better
//! maintainability and reduced cognitive complexity.

// Re-export the refactored runtime module components
pub use runtime_impl::{process_runtime_env, RuntimeEnv};

// Implementation modules
mod runtime_impl {
    pub use environment::RuntimeEnv;
    use patterns::PatternProcessor;
    use operations::{UnsetOperation, MapOperation, SetOperation};
    
    use log::{debug};
    use std::collections::HashMap;
    
    /// Process runtime environment configuration
    ///
    /// Operations are processed in this order:
    /// 1. Analyze pass patterns - Build list of variables to preserve
    /// 2. unset - Remove specified variables (skipping those marked to preserve)
    /// 3. map - Rename variables
    /// 4. set - Set specific values
    /// 5. pass verification - Check that required variables/patterns exist
    /// 
    /// # Arguments
    /// 
    /// * `env_map` - Mutable reference to environment variables
    /// * `runtime_env` - Runtime environment configuration
    pub fn process_runtime_env(env_map: &mut HashMap<String, String>, runtime_env: &RuntimeEnv) {
        debug!("🔧 Processing runtime environment configuration");
        
        // Build pattern processor for pass/preserve operations
        let pattern_processor = PatternProcessor::new(&runtime_env.pass);
        
        // Process unset operations first (highest priority)
        if !runtime_env.unset.is_empty() {
            if let Err(e) = UnsetOperation::new(&runtime_env.unset, &pattern_processor)
                .execute(env_map) {
                debug!("⚠️ Error during unset operations: {}", e);
            }
        }
        
        // Process map operations (variable renaming)
        if !runtime_env.map.is_empty() {
            if let Err(e) = MapOperation::new(&runtime_env.map, &pattern_processor)
                .execute(env_map) {
                debug!("⚠️ Error during map operations: {}", e);
            }
        }
        
        // Process set operations (add/override variables)
        if !runtime_env.set.is_empty() {
            if let Err(e) = SetOperation::new(&runtime_env.set)
                .execute(env_map) {
                debug!("⚠️ Error during set operations: {}", e);
            }
        }
        
        // Verify all required pass patterns are satisfied
        if let Err(e) = pattern_processor.verify_requirements(env_map) {
            debug!("⚠️ Pass pattern verification failed: {}", e);
        }
        
        debug!("✅ Runtime environment processing complete");
    }

    // Include the module implementations inline to avoid file system issues
    mod environment {
        use serde::{Deserialize, Serialize};

        /// Runtime environment configuration
        /// 
        /// Defines how environment variables should be processed during package execution.
        #[derive(Debug, Clone, Default, Deserialize, Serialize)]
        pub struct RuntimeEnv {
            /// Patterns for variables to preserve/pass through
            #[serde(default, skip_serializing_if = "Vec::is_empty")]
            pub pass: Vec<String>,
            
            /// Patterns for variables to unset/remove
            #[serde(default, skip_serializing_if = "Vec::is_empty")]
            pub unset: Vec<String>,
            
            /// Variable mapping/renaming operations
            #[serde(default, skip_serializing_if = "Vec::is_empty")]
            pub map: Vec<String>,
            
            /// Variables to set or override
            #[serde(default, skip_serializing_if = "Vec::is_empty")]
            pub set: Vec<String>,
        }
    }

    mod patterns {
        use glob::Pattern;
        use log::{debug, trace};
        use std::collections::{HashMap, HashSet};
        use crate::exceptions::{FlavorError, Result};

        /// Handles pattern matching for environment variable preservation
        pub struct PatternProcessor {
            patterns: Vec<CompiledPattern>,
            exact_matches: HashSet<String>,
        }

        enum CompiledPattern {
            Exact(String),
            Glob(Pattern),
        }

        impl PatternProcessor {
            pub fn new(pass_patterns: &[String]) -> Self {
                let mut patterns = Vec::new();
                let mut exact_matches = HashSet::new();
                
                for pattern in pass_patterns {
                    if pattern.contains('*') || pattern.contains('?') {
                        if let Ok(p) = Pattern::new(pattern) {
                            patterns.push(CompiledPattern::Glob(p));
                        } else {
                            exact_matches.insert(pattern.clone());
                            patterns.push(CompiledPattern::Exact(pattern.clone()));
                        }
                    } else {
                        exact_matches.insert(pattern.clone());
                        patterns.push(CompiledPattern::Exact(pattern.clone()));
                    }
                }
                
                debug!(
                    "📋 Pattern processor: {} patterns ({} exact)",
                    patterns.len(),
                    exact_matches.len()
                );
                
                Self { patterns, exact_matches }
            }
            
            pub fn should_preserve(&self, key: &str) -> bool {
                if self.exact_matches.contains(key) {
                    return true;
                }
                
                for pattern in &self.patterns {
                    if let CompiledPattern::Glob(glob) = pattern {
                        if glob.matches(key) {
                            return true;
                        }
                    }
                }
                
                false
            }
            
            pub fn verify_requirements(&self, env_map: &HashMap<String, String>) -> Result<()> {
                let mut missing = Vec::new();
                
                for pattern in &self.patterns {
                    if let CompiledPattern::Exact(key) = pattern {
                        if !env_map.contains_key(key) {
                            missing.push(key.clone());
                        }
                    }
                }
                
                if !missing.is_empty() {
                    return Err(FlavorError::Execution(format!(
                        "Required environment variables not found: {}",
                        missing.join(", ")
                    )));
                }
                
                Ok(())
            }
        }
    }

    mod operations {
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
            pub fn new(patterns: &'a [String], processor: &'a PatternProcessor) -> Self {
                Self { patterns, processor }
            }
            
            pub fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
                debug!("🗑️ Processing {} unset patterns", self.patterns.len());
                
                for pattern in self.patterns {
                    if pattern == "*" {
                        self.unset_all_except_preserved(env_map)?;
                    } else if pattern.contains('*') || pattern.contains('?') {
                        self.unset_glob_pattern(pattern, env_map)?;
                    } else {
                        self.unset_exact_match(pattern, env_map)?;
                    }
                }
                
                Ok(())
            }
            
            fn unset_all_except_preserved(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
                let all_keys: Vec<String> = env_map.keys().cloned().collect();
                
                for key in all_keys {
                    if !self.processor.should_preserve(&key) {
                        env_map.remove(&key);
                        trace!("  🗑️ Unset: {}", key);
                    }
                }
                
                Ok(())
            }
            
            fn unset_glob_pattern(&self, pattern: &str, env_map: &mut HashMap<String, String>) -> Result<()> {
                let glob_pattern = Pattern::new(pattern).map_err(|e| {
                    FlavorError::Configuration(format!("Invalid glob pattern '{}': {}", pattern, e))
                })?;
                
                let matching_keys: Vec<String> = env_map.keys()
                    .filter(|k| glob_pattern.matches(k))
                    .cloned()
                    .collect();
                
                for key in matching_keys {
                    if !self.processor.should_preserve(&key) {
                        env_map.remove(&key);
                        trace!("  🗑️ Unset (glob): {}", key);
                    }
                }
                
                Ok(())
            }
            
            fn unset_exact_match(&self, key: &str, env_map: &mut HashMap<String, String>) -> Result<()> {
                if !self.processor.should_preserve(key) {
                    if env_map.remove(key).is_some() {
                        debug!("🗑️ Unset: {}", key);
                    }
                }
                Ok(())
            }
        }

        /// Handles map operations on environment variables
        pub struct MapOperation<'a> {
            mappings: &'a [String],
            processor: &'a PatternProcessor,
        }

        impl<'a> MapOperation<'a> {
            pub fn new(mappings: &'a [String], processor: &'a PatternProcessor) -> Self {
                Self { mappings, processor }
            }
            
            pub fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
                debug!("🔄 Processing {} map operations", self.mappings.len());
                
                for mapping in self.mappings {
                    let parts: Vec<&str> = mapping.splitn(2, '=').collect();
                    
                    if parts.len() != 2 {
                        warn!("⚠️ Invalid map format '{}'", mapping);
                        continue;
                    }
                    
                    let (old_key, new_key) = (parts[0], parts[1]);
                    
                    if !self.processor.should_preserve(old_key) {
                        if let Some(value) = env_map.remove(old_key) {
                            debug!("🔄 Mapped: {} -> {}", old_key, new_key);
                            env_map.insert(new_key.to_string(), value);
                        }
                    }
                }
                
                Ok(())
            }
        }

        /// Handles set operations on environment variables
        pub struct SetOperation<'a> {
            assignments: &'a [String],
        }

        impl<'a> SetOperation<'a> {
            pub fn new(assignments: &'a [String]) -> Self {
                Self { assignments }
            }
            
            pub fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
                debug!("📝 Processing {} set operations", self.assignments.len());
                
                for assignment in self.assignments {
                    let parts: Vec<&str> = assignment.splitn(2, '=').collect();
                    
                    if parts.len() != 2 {
                        warn!("⚠️ Invalid set format '{}'", assignment);
                        continue;
                    }
                    
                    let (key, value) = (parts[0], parts[1]);
                    debug!("📝 Set: {} = '{}'", key, value);
                    env_map.insert(key.to_string(), value.to_string());
                }
                
                Ok(())
            }
        }
    }
}

// Keep backward compatibility with metadata module
use super::metadata;

// Re-export RuntimeEnv from metadata if it's used there
pub use metadata::RuntimeEnv as MetadataRuntimeEnv;