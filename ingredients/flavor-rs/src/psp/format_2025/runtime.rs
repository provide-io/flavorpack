//! Runtime environment processing for PSPF/2025
//!
//! This module handles the runtime.env configuration from PSPF metadata,
//! allowing packages to control their execution environment through
//! environment variable operations.

use super::metadata::RuntimeEnv;
use glob::Pattern;
use log::{debug, info, trace, warn};
use std::collections::HashMap;

/// Process runtime environment configuration
///
/// Operations are processed in this order:
/// 1. Analyze pass patterns - Build list of variables to preserve
/// 2. unset - Remove specified variables (skipping those marked to preserve)
/// 3. map - Rename variables
/// 4. set - Set specific values
/// 5. pass verification - Check that required variables/patterns exist
pub fn process_runtime_env(env_map: &mut HashMap<String, String>, runtime_env: &RuntimeEnv) {
    // Log initial state
    debug!("🔍 Initial environment: {} variables", env_map.len());
    if log::log_enabled!(log::Level::Trace) {
        let mut keys: Vec<_> = env_map.keys().cloned().collect();
        keys.sort();
        for key in &keys[..keys.len().min(10)] {
            trace!(
                "  Initial env: {} = {}",
                key,
                env_map
                    .get(key)
                    .map(|v| {
                        if v.len() > 50 {
                            format!("{}...", &v[..50])
                        } else {
                            v.clone()
                        }
                    })
                    .unwrap_or_default()
            );
        }
        if keys.len() > 10 {
            trace!("  ... and {} more variables", keys.len() - 10);
        }
    }

    // Build pass patterns first to know what to preserve
    let mut pass_patterns: Vec<Pattern> = Vec::new();
    if let Some(pass_list) = &runtime_env.pass {
        debug!("🛡️ Building pass patterns: {} patterns", pass_list.len());
        for pattern in pass_list {
            if pattern.contains('*') || pattern.contains('?') {
                match Pattern::new(pattern) {
                    Ok(p) => {
                        pass_patterns.push(p);
                        trace!("  🛡️ Pass pattern: {pattern} (glob)");
                    }
                    Err(e) => warn!("Invalid pass glob pattern '{pattern}': {e}"),
                }
            } else {
                // Convert exact match to pattern for uniform handling
                match Pattern::new(pattern) {
                    Ok(p) => {
                        pass_patterns.push(p);
                        trace!("  🛡️ Pass pattern: {pattern} (exact)");
                    }
                    Err(e) => warn!("Invalid pass pattern '{pattern}': {e}"),
                }
            }
        }
    }

    // Helper function to check if a key should be preserved
    let should_preserve = |key: &str| -> bool {
        for pattern in &pass_patterns {
            if pattern.matches(key) {
                return true;
            }
        }
        false
    };

    // 1. Process unset operations (with preserve logic)
    if let Some(unset_list) = &runtime_env.unset {
        debug!(
            "🗑️ Processing unset operations: {} patterns",
            unset_list.len()
        );
        let mut removed_count = 0;
        let mut preserved_count = 0;
        let mut removed_keys = Vec::new();
        let mut preserved_keys = Vec::new();

        for pattern in unset_list {
            if pattern == "*" {
                // Special case: unset all (except preserved)
                debug!("🗑️ Unsetting ALL environment variables (pattern: '*'), except preserved");
                let all_keys: Vec<String> = env_map.keys().cloned().collect();

                for key in all_keys {
                    if should_preserve(&key) {
                        preserved_count += 1;
                        preserved_keys.push(key.clone());
                        trace!("  🛡️ Preserved: {key}");
                    } else if env_map.remove(&key).is_some() {
                        removed_count += 1;
                        removed_keys.push(key.clone());
                        trace!("  🗑️ Unset: {key}");
                    }
                }
            } else if pattern.contains('*') || pattern.contains('?') {
                // Glob pattern
                let glob_pattern = match Pattern::new(pattern) {
                    Ok(p) => p,
                    Err(e) => {
                        warn!("Invalid glob pattern '{pattern}': {e}, skipping");
                        continue;
                    }
                };

                let keys_to_check: Vec<String> = env_map
                    .keys()
                    .filter(|k| glob_pattern.matches(k))
                    .cloned()
                    .collect();

                debug!(
                    "🗑️ Glob pattern '{}' matches {} variables",
                    pattern,
                    keys_to_check.len()
                );
                for key in keys_to_check {
                    if should_preserve(&key) {
                        preserved_count += 1;
                        preserved_keys.push(key.clone());
                        trace!("  🛡️ Preserved (matched unset but also pass): {key}");
                    } else if env_map.remove(&key).is_some() {
                        removed_count += 1;
                        removed_keys.push(key.clone());
                        trace!("  🗑️ Unset (glob): {key}");
                    }
                }
            } else {
                // Exact match
                if should_preserve(pattern) {
                    preserved_count += 1;
                    preserved_keys.push(pattern.clone());
                    debug!("🛡️ Preserved (matched unset but also pass): {pattern}");
                } else if env_map.remove(pattern).is_some() {
                    removed_count += 1;
                    removed_keys.push(pattern.clone());
                    debug!("🗑️ Unset exact: {pattern}");
                } else {
                    trace!("  ⚠️ Variable not found: {pattern}");
                }
            }
        }

        if removed_count > 0 {
            info!("🗑️ Removed {removed_count} environment variables");
            if log::log_enabled!(log::Level::Debug) && removed_keys.len() <= 20 {
                for key in &removed_keys {
                    debug!("  - {key}");
                }
            }
        }

        if preserved_count > 0 {
            info!("🛡️ Preserved {preserved_count} environment variables (matched pass patterns)");
            if log::log_enabled!(log::Level::Debug) && preserved_keys.len() <= 20 {
                for key in &preserved_keys {
                    debug!("  + {key}");
                }
            }
        }
    }

    // 2. Process map operations
    if let Some(map_ops) = &runtime_env.map {
        debug!("🔄 Processing map operations: {} mappings", map_ops.len());
        let mut mapped_count = 0;

        for (from, to) in map_ops {
            if let Some(value) = env_map.remove(from) {
                let value_preview = if value.len() > 50 {
                    format!("{}...", &value[..50])
                } else {
                    value.clone()
                };
                env_map.insert(to.clone(), value);
                mapped_count += 1;
                debug!("  🔄 Mapped: {from} -> {to} (value: {value_preview})");
            } else {
                trace!("  ⚠️ Cannot map '{from}' -> '{to}': source not found");
            }
        }

        if mapped_count > 0 {
            info!("🔄 Mapped {mapped_count} environment variables");
        }
    }

    // 3. Process set operations
    if let Some(set_ops) = &runtime_env.set {
        debug!("✏️ Processing set operations: {} variables", set_ops.len());

        for (key, value) in set_ops {
            let value_preview = if value.len() > 50 {
                format!("{}...", &value[..50])
            } else {
                value.clone()
            };
            env_map.insert(key.clone(), value.clone());
            debug!("  ✏️ Set: {key} = {value_preview}");
        }

        info!("✏️ Set {} environment variables", set_ops.len());
    }

    // 4. Final pass verification (check that required variables exist)
    if let Some(pass_list) = &runtime_env.pass {
        debug!("✅ Final pass verification: {} patterns", pass_list.len());
        let mut missing_patterns = Vec::new();
        let mut found_vars = Vec::new();

        for pattern in pass_list {
            let mut pattern_matched = false;

            if pattern.contains('*') || pattern.contains('?') {
                // Glob pattern - check if any variable matches
                let glob_pattern = match Pattern::new(pattern) {
                    Ok(p) => p,
                    Err(e) => {
                        warn!("Invalid pass glob pattern '{pattern}': {e}");
                        continue;
                    }
                };

                for key in env_map.keys() {
                    if glob_pattern.matches(key) {
                        pattern_matched = true;
                        found_vars.push(key.clone());
                        trace!("  ✅ Found matching variable: {key} (pattern: {pattern})");
                    }
                }

                if !pattern_matched {
                    missing_patterns.push(pattern.clone());
                    warn!("  ⚠️ No variables found matching pattern: {pattern}");
                }
            } else {
                // Exact match
                if env_map.contains_key(pattern) {
                    found_vars.push(pattern.clone());
                    trace!("  ✅ Verified env var exists: {pattern}");
                } else {
                    missing_patterns.push(pattern.clone());
                    warn!("  ⚠️ Required environment variable not found: {pattern}");
                }
            }
        }

        if !missing_patterns.is_empty() {
            warn!(
                "⚠️ Missing {} required patterns/variables: {:?}",
                missing_patterns.len(),
                missing_patterns
            );
        }
        if !found_vars.is_empty() {
            let unique_found: std::collections::HashSet<_> = found_vars.iter().cloned().collect();
            debug!(
                "✅ Verified {} environment variables match pass patterns",
                unique_found.len()
            );
            if log::log_enabled!(log::Level::Trace) && unique_found.len() <= 20 {
                for var in &unique_found {
                    trace!("  + {var}");
                }
            }
        }
    }

    // Log final state
    debug!(
        "🎯 Final environment: {} variables after runtime.env processing",
        env_map.len()
    );
    if log::log_enabled!(log::Level::Trace) {
        let mut keys: Vec<_> = env_map.keys().cloned().collect();
        keys.sort();
        for key in &keys[..keys.len().min(10)] {
            trace!(
                "  Final env: {} = {}",
                key,
                env_map
                    .get(key)
                    .map(|v| {
                        if v.len() > 50 {
                            format!("{}...", &v[..50])
                        } else {
                            v.clone()
                        }
                    })
                    .unwrap_or_default()
            );
        }
        if keys.len() > 10 {
            trace!("  ... and {} more variables", keys.len() - 10);
        }
    }
}
