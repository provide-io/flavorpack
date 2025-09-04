//! Pattern matching and preservation logic

use glob::Pattern;
use log::{debug, trace};
use std::collections::{HashMap, HashSet};
use crate::exceptions::{FlavorError, Result};

/// Handles pattern matching for environment variable preservation
pub struct PatternProcessor {
    /// Compiled patterns for variables to preserve
    patterns: Vec<CompiledPattern>,
    /// Set of exact matches for fast lookup
    exact_matches: HashSet<String>,
}

/// A compiled pattern that can be either exact or glob
enum CompiledPattern {
    Exact(String),
    Glob(Pattern),
}

impl PatternProcessor {
    /// Create a new pattern processor from a list of pass patterns
    pub fn new(pass_patterns: &[String]) -> Self {
        let mut patterns = Vec::new();
        let mut exact_matches = HashSet::new();
        
        for pattern in pass_patterns {
            if pattern.contains('*') || pattern.contains('?') {
                // Compile as glob pattern
                match Pattern::new(pattern) {
                    Ok(p) => patterns.push(CompiledPattern::Glob(p)),
                    Err(e) => {
                        debug!("⚠️ Invalid glob pattern '{}': {}, treating as exact", pattern, e);
                        exact_matches.insert(pattern.clone());
                        patterns.push(CompiledPattern::Exact(pattern.clone()));
                    }
                }
            } else {
                // Exact match
                exact_matches.insert(pattern.clone());
                patterns.push(CompiledPattern::Exact(pattern.clone()));
            }
        }
        
        debug!(
            "📋 Initialized pattern processor: {} patterns ({} exact, {} glob)",
            patterns.len(),
            exact_matches.len(),
            patterns.len() - exact_matches.len()
        );
        
        Self { patterns, exact_matches }
    }
    
    /// Check if a variable should be preserved based on pass patterns
    pub fn should_preserve(&self, key: &str) -> bool {
        // Fast path for exact matches
        if self.exact_matches.contains(key) {
            return true;
        }
        
        // Check glob patterns
        for pattern in &self.patterns {
            if let CompiledPattern::Glob(glob) = pattern {
                if glob.matches(key) {
                    return true;
                }
            }
        }
        
        false
    }
    
    /// Get all keys that match the preservation patterns
    pub fn get_preserved_keys(&self, env_map: &HashMap<String, String>) -> Vec<String> {
        env_map.keys()
            .filter(|key| self.should_preserve(key))
            .cloned()
            .collect()
    }
    
    /// Verify that all required pass patterns are satisfied
    /// 
    /// # Errors
    /// 
    /// Returns an error if any exact match patterns are not found in the environment
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
                "Required environment variables not found after processing: {}",
                missing.join(", ")
            )));
        }
        
        // Log pattern match statistics for glob patterns
        for pattern in &self.patterns {
            if let CompiledPattern::Glob(glob) = pattern {
                let matches: Vec<_> = env_map.keys()
                    .filter(|k| glob.matches(k))
                    .collect();
                    
                if matches.is_empty() {
                    debug!("⚠️ Pass pattern '{}' matched no variables", glob.as_str());
                } else {
                    trace!(
                        "✅ Pass pattern '{}' matched {} variables",
                        glob.as_str(),
                        matches.len()
                    );
                }
            }
        }
        
        Ok(())
    }
}