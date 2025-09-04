//! Runtime environment processing module
//! 
//! This module handles the complex logic of processing runtime environment variables
//! for PSPF packages, including pattern matching, preservation, and transformation.

use crate::exceptions::{FlavorError, Result};
use glob::Pattern;
use log::{debug, trace, warn};
use std::collections::HashMap;

mod environment;
mod patterns;
mod operations;

pub use environment::RuntimeEnv;
pub use patterns::PatternProcessor;
pub use operations::{UnsetOperation, MapOperation, SetOperation};

/// Process runtime environment variables according to the specification
/// 
/// # Arguments
/// 
/// * `runtime_env` - Optional runtime environment configuration
/// * `env_map` - Mutable reference to the environment variables map
/// 
/// # Returns
/// 
/// Returns a Result with unit type on success, or a FlavorError on failure
/// 
/// # Example
/// 
/// ```no_run
/// use std::collections::HashMap;
/// let mut env = HashMap::new();
/// env.insert("PATH".to_string(), "/usr/bin".to_string());
/// 
/// // Process with runtime configuration
/// process_runtime_env(Some(&runtime_env), &mut env)?;
/// ```
pub fn process_runtime_env(
    runtime_env: Option<&RuntimeEnv>,
    env_map: &mut HashMap<String, String>,
) -> Result<()> {
    let Some(runtime) = runtime_env else {
        debug!("🔧 No runtime environment configuration to process");
        return Ok(());
    };

    debug!("🔧 Processing runtime environment configuration");
    
    // Build pattern processor for pass/preserve operations
    let pattern_processor = PatternProcessor::new(&runtime.pass);
    
    // Process unset operations first (highest priority)
    if !runtime.unset.is_empty() {
        UnsetOperation::new(&runtime.unset, &pattern_processor)
            .execute(env_map)?;
    }
    
    // Process map operations (variable renaming)
    if !runtime.map.is_empty() {
        MapOperation::new(&runtime.map, &pattern_processor)
            .execute(env_map)?;
    }
    
    // Process set operations (add/override variables)
    if !runtime.set.is_empty() {
        SetOperation::new(&runtime.set)
            .execute(env_map)?;
    }
    
    // Verify all required pass patterns are satisfied
    pattern_processor.verify_requirements(env_map)?;
    
    debug!("✅ Runtime environment processing complete");
    Ok(())
}