//! Command preparation and environment setup

use super::super::execution::substitute_placeholders;
use super::super::metadata::Metadata;
use super::super::runtime::process_runtime_env;
use crate::exceptions::{FlavorError, Result};
use log::debug;
use std::collections::HashMap;
use std::env;
use std::path::Path;

/// Resolve executable path using PATH environment variable
///
/// Handles absolute Unix paths (e.g., /usr/bin/python3) by extracting the basename.
/// On Windows, this handles .exe extension resolution automatically.
/// Falls back to the basename if resolution fails.
pub fn resolve_executable(executable: &str) -> String {
    // If it's an absolute Unix path (starts with /), extract just the basename
    // This handles cases like "/usr/bin/python3" -> "python3"
    let exec_name = if executable.starts_with('/') {
        executable.rsplit('/').next().unwrap_or(executable)
    } else {
        executable
    };

    // Try to resolve the executable (or basename) via PATH
    if let Ok(path) = which::which(exec_name) {
        let resolved = path.to_string_lossy().to_string();
        debug!("🔍 Resolved executable '{}' to '{}'", executable, resolved);
        resolved
    } else {
        // On Windows, try with .exe extension
        #[cfg(windows)]
        {
            let exe_variant = format!("{}.exe", exec_name);
            if let Ok(path) = which::which(&exe_variant) {
                let resolved = path.to_string_lossy().to_string();
                debug!(
                    "🔍 Resolved executable '{}' to '{}' (with .exe)",
                    executable, resolved
                );
                return resolved;
            }

            // Windows-specific fallbacks for common Unix commands
            let fallback_result = match exec_name {
                "python3" | "python3.exe" => {
                    // Try python.exe as fallback
                    which::which("python.exe")
                        .or_else(|_| which::which("python"))
                        .ok()
                }
                "sh" | "sh.exe" => {
                    // Try bash.exe as fallback
                    which::which("bash.exe")
                        .or_else(|_| which::which("bash"))
                        .ok()
                }
                _ => None,
            };

            if let Some(path) = fallback_result {
                let resolved = path.to_string_lossy().to_string();
                debug!(
                    "🔍 Resolved executable '{}' to '{}' (Windows fallback)",
                    executable, resolved
                );
                return resolved;
            }
        }

        debug!(
            "⚠️  Could not resolve executable '{}' in PATH, using basename: '{}'",
            executable, exec_name
        );
        exec_name.to_string()
    }
}

/// Prepare the command to execute
pub(super) fn prepare_command(
    metadata: &Metadata,
    workenv_path: &Path,
    package_path: &Path,
    args: &[String],
) -> Result<(String, Vec<String>, HashMap<String, String>)> {
    // Substitute placeholders in command
    let command =
        substitute_placeholders(&metadata.execution.command, workenv_path, &metadata.package);

    debug!("🎯 Final command: {command}");

    // Split command into parts
    let mut command_parts: Vec<String> = command.split_whitespace().map(String::from).collect();
    if command_parts.is_empty() {
        return Err(FlavorError::Generic("No command specified".to_string()));
    }

    let executable = command_parts.remove(0);
    let executable = resolve_executable(&executable);

    // Combine command args with user args
    let mut all_args = command_parts;
    all_args.extend_from_slice(args);

    // Prepare environment
    let mut env_map: HashMap<String, String> = env::vars().collect();

    // Set FLAVOR_CACHE to the HOST's cache directory BEFORE workenv env is applied
    // This ensures we use the HOST's HOME, not the workenv's HOME
    // This ensures the packaged tool can access cached packages from the HOST
    if !env_map.contains_key("FLAVOR_CACHE") {
        if let Some(home) = env_map.get("HOME") {
            let flavor_cache = format!(
                "{}/{}",
                home,
                crate::psp::format_2025::defaults::DEFAULT_CACHE_SUBDIR
            );
            debug!("🗂️ Setting FLAVOR_CACHE to HOST cache: {}", flavor_cache);
            env_map.insert("FLAVOR_CACHE".to_string(), flavor_cache);
        }
    }

    // Process runtime.env if present
    if let Some(runtime_info) = &metadata.runtime {
        if let Some(runtime_env) = &runtime_info.env {
            debug!("🔄 Processing runtime.env configuration");
            process_runtime_env(&mut env_map, runtime_env);
        }
    }

    // Add workenv environment variables (layer 2)
    if let Some(ref workenv_info) = metadata.workenv {
        if let Some(ref workenv_env) = workenv_info.env {
            for (key, value) in workenv_env {
                let expanded_value =
                    substitute_placeholders(value, workenv_path, &metadata.package);
                // Don't override FLAVOR_CACHE if it's already set
                if key != "FLAVOR_CACHE" || !env_map.contains_key("FLAVOR_CACHE") {
                    env_map.insert(key.clone(), expanded_value);
                }
            }
        }
    }

    // Add execution environment variables (layer 3)
    for (key, value) in &metadata.execution.env {
        env_map.insert(key.clone(), value.clone());
    }

    // Add FLAVOR_WORKENV
    env_map.insert(
        "FLAVOR_WORKENV".to_string(),
        workenv_path.to_string_lossy().to_string(),
    );

    // Add FLAVOR_COMMAND_NAME for the binary name
    let binary_name = package_path
        .file_name()
        .and_then(|n| n.to_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| package_path.to_string_lossy().to_string());
    env_map.insert("FLAVOR_COMMAND_NAME".to_string(), binary_name);
    env_map.insert(
        "FLAVOR_ORIGINAL_COMMAND".to_string(),
        package_path.to_string_lossy().to_string(),
    );

    // Prepend workenv/bin to PATH
    if let Some(path) = env_map.get("PATH") {
        let new_path = format!("{}/bin:{}", workenv_path.display(), path);
        env_map.insert("PATH".to_string(), new_path);
    } else {
        env_map.insert(
            "PATH".to_string(),
            format!("{}/bin", workenv_path.display()),
        );
    }

    Ok((executable, all_args, env_map))
}
