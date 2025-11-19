//! Runtime environment processing for PSPF/2025
//!
//! This module handles the runtime.env configuration from PSPF metadata,
//! allowing packages to control their execution environment through
//! environment variable operations.
//!
//! The implementation has been refactored into sub-modules for better
//! maintainability and reduced cognitive complexity.

// Use RuntimeEnv from metadata module
use super::metadata::RuntimeEnv;

// Re-export the refactored runtime module components
pub use runtime_impl::process_runtime_env;

// Implementation modules
mod runtime_impl {
    use super::RuntimeEnv;
    use operations::{MapOperation, SetOperation, UnsetOperation};
    use patterns::PatternProcessor;

    use log::debug;
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
        // On Windows, automatically add critical system variables
        // These are required for Python and other programs to initialize properly
        #[cfg(target_os = "windows")]
        let pass_patterns = {
            let mut patterns = runtime_env.pass.clone().unwrap_or_default();
            let windows_critical_vars = vec![
                "SYSTEMROOT".to_string(),
                "WINDIR".to_string(),
                "TEMP".to_string(),
                "TMP".to_string(),
                "PATHEXT".to_string(),
                "COMSPEC".to_string(),
            ];

            for var in windows_critical_vars {
                if !patterns.contains(&var) {
                    debug!("💻 Auto-adding Windows critical variable: {}", var);
                    patterns.push(var);
                }
            }
            patterns
        };

        #[cfg(not(target_os = "windows"))]
        let pass_patterns = runtime_env.pass.clone().unwrap_or_default();

        let pattern_processor = PatternProcessor::new(&pass_patterns);

        // Process unset operations first (highest priority)
        if let Some(unset_patterns) = &runtime_env.unset {
            if unset_patterns.is_empty() {
                debug!("📭 No unset patterns (empty list)");
            } else {
                debug!("📋 Unset patterns found: {:?}", unset_patterns);
                match UnsetOperation::new(unset_patterns, &pattern_processor).execute(env_map) {
                    Ok(_) => debug!("✅ Unset operations completed successfully"),
                    Err(e) => debug!("⚠️ Error during unset operations: {}", e),
                }
            }
        } else {
            debug!("📭 No unset patterns configured");
        }

        // Process map operations (variable renaming)
        if let Some(map_ops) = &runtime_env.map {
            if !map_ops.is_empty() {
                // Convert HashMap to Vec of key=value strings
                let map_strings: Vec<String> = map_ops
                    .iter()
                    .map(|(k, v)| format!("{}={}", k, v))
                    .collect();
                if let Err(e) = MapOperation::new(&map_strings, &pattern_processor).execute(env_map)
                {
                    debug!("⚠️ Error during map operations: {}", e);
                }
            }
        }

        // Process set operations (add/override variables)
        if let Some(set_ops) = &runtime_env.set {
            if !set_ops.is_empty() {
                // Convert HashMap to Vec of key=value strings
                let set_strings: Vec<String> = set_ops
                    .iter()
                    .map(|(k, v)| format!("{}={}", k, v))
                    .collect();
                if let Err(e) = SetOperation::new(&set_strings).execute(env_map) {
                    debug!("⚠️ Error during set operations: {}", e);
                }
            }
        }

        // Verify all required pass patterns are satisfied
        if let Err(e) = pattern_processor.verify_requirements(env_map) {
            debug!("⚠️ Pass pattern verification failed: {}", e);
        }

        debug!("✅ Runtime environment processing complete");
    }

    mod patterns {
        use crate::exceptions::{FlavorError, Result};
        use glob::Pattern;
        use log::{debug, trace};
        use std::collections::{HashMap, HashSet};

        /// Handles pattern matching for environment variable preservation
        pub(super) struct PatternProcessor {
            patterns: Vec<CompiledPattern>,
            exact_matches: HashSet<String>,
        }

        enum CompiledPattern {
            Exact(String),
            Glob(Pattern),
        }

        impl PatternProcessor {
            pub(super) fn new(pass_patterns: &[String]) -> Self {
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

                Self {
                    patterns,
                    exact_matches,
                }
            }

            pub(super) fn should_preserve(&self, key: &str) -> bool {
                if self.exact_matches.contains(key) {
                    trace!("✅ Variable '{}' matches exact pattern", key);
                    return true;
                }

                for pattern in &self.patterns {
                    if let CompiledPattern::Glob(glob) = pattern {
                        if glob.matches(key) {
                            trace!("✅ Variable '{}' matches glob pattern: {}", key, glob);
                            return true;
                        }
                    }
                }

                trace!("❌ Variable '{}' does not match any preserve pattern", key);
                false
            }

            pub(super) fn verify_requirements(
                &self,
                env_map: &HashMap<String, String>,
            ) -> Result<()> {
                let mut missing = Vec::new();

                for pattern in &self.patterns {
                    if let CompiledPattern::Exact(key) = pattern {
                        if !env_map.contains_key(key) {
                            missing.push(key.clone());
                        }
                    }
                }

                if !missing.is_empty() {
                    return Err(FlavorError::LaunchError(format!(
                        "Required environment variables not found: {}",
                        missing.join(", ")
                    )));
                }

                Ok(())
            }
        }
    }

    mod operations {
        use super::patterns::PatternProcessor;
        use crate::exceptions::{FlavorError, Result};
        use glob::Pattern;
        use log::{debug, trace, warn};
        use std::collections::HashMap;

        /// Handles unset operations on environment variables
        pub(super) struct UnsetOperation<'a> {
            patterns: &'a [String],
            processor: &'a PatternProcessor,
        }

        impl<'a> UnsetOperation<'a> {
            pub(super) fn new(patterns: &'a [String], processor: &'a PatternProcessor) -> Self {
                Self {
                    patterns,
                    processor,
                }
            }

            pub(super) fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
                debug!("🗑️ Processing {} unset patterns", self.patterns.len());

                for pattern in self.patterns {
                    debug!("  Processing unset pattern: '{}'", pattern);
                    if pattern == "*" {
                        debug!("  Match: unset all except preserved");
                        self.unset_all_except_preserved(env_map)?;
                    } else if pattern.contains('*') || pattern.contains('?') {
                        debug!("  Match: glob pattern");
                        self.unset_glob_pattern(pattern, env_map)?;
                    } else {
                        debug!("  Match: exact pattern");
                        self.unset_exact_match(pattern, env_map)?;
                    }
                }

                Ok(())
            }

            fn unset_all_except_preserved(
                &self,
                env_map: &mut HashMap<String, String>,
            ) -> Result<()> {
                debug!("🔄 Unsetting all variables except preserved patterns");
                let all_keys: Vec<String> = env_map.keys().cloned().collect();
                let mut preserved_count = 0;
                let mut unset_count = 0;

                for key in all_keys {
                    if self.processor.should_preserve(&key) {
                        trace!("  ✅ Preserved: {}", key);
                        preserved_count += 1;
                    } else {
                        env_map.remove(&key);
                        trace!("  🗑️ Unset: {}", key);
                        unset_count += 1;
                    }
                }

                debug!(
                    "  Summary: {} preserved, {} unset",
                    preserved_count, unset_count
                );
                Ok(())
            }

            fn unset_glob_pattern(
                &self,
                pattern: &str,
                env_map: &mut HashMap<String, String>,
            ) -> Result<()> {
                let glob_pattern = Pattern::new(pattern).map_err(|e| {
                    FlavorError::Generic(format!("Invalid glob pattern '{}': {}", pattern, e))
                })?;

                let matching_keys: Vec<String> = env_map
                    .keys()
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

            fn unset_exact_match(
                &self,
                key: &str,
                env_map: &mut HashMap<String, String>,
            ) -> Result<()> {
                if !self.processor.should_preserve(key) && env_map.remove(key).is_some() {
                    debug!("🗑️ Unset: {}", key);
                }
                Ok(())
            }
        }

        /// Handles map operations on environment variables
        pub(super) struct MapOperation<'a> {
            mappings: &'a [String],
            processor: &'a PatternProcessor,
        }

        impl<'a> MapOperation<'a> {
            pub(super) fn new(mappings: &'a [String], processor: &'a PatternProcessor) -> Self {
                Self {
                    mappings,
                    processor,
                }
            }

            pub(super) fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
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
        pub(super) struct SetOperation<'a> {
            assignments: &'a [String],
        }

        impl<'a> SetOperation<'a> {
            pub(super) fn new(assignments: &'a [String]) -> Self {
                Self { assignments }
            }

            pub(super) fn execute(&self, env_map: &mut HashMap<String, String>) -> Result<()> {
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
