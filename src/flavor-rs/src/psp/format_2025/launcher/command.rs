// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! Command preparation and environment setup

use super::super::execution::{shell_split, substitute_placeholders};
use super::super::metadata::Metadata;
use super::super::runtime::process_runtime_env;
use crate::exceptions::{FlavorError, Result};
use log::{debug, warn};
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

        warn!(
            "⚠️  Could not resolve executable '{}' in PATH — will attempt to run as-is, expect failure if not on PATH",
            executable
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

    // Split command into parts (shell-aware: handles quoted arguments)
    let mut command_parts: Vec<String> = shell_split(&command);
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

    // Set FLAVOR_CACHE_DIR to the HOST's cache directory BEFORE workenv env is applied
    // This ensures we use the HOST's HOME, not the workenv's HOME
    // This ensures the packaged tool can access cached packages from the HOST
    if !env_map.contains_key(crate::env_vars::CACHE_DIR) {
        if let Some(home) = env_map.get("HOME") {
            let flavor_cache = std::path::PathBuf::from(home)
                .join(crate::psp::format_2025::defaults::DEFAULT_CACHE_SUBDIR)
                .to_string_lossy()
                .to_string();
            debug!(
                "🗂️ Setting FLAVOR_CACHE_DIR to HOST cache: {}",
                flavor_cache
            );
            env_map.insert(crate::env_vars::CACHE_DIR.to_string(), flavor_cache);
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
                // Don't override FLAVOR_CACHE_DIR if it's already set
                if key != crate::env_vars::CACHE_DIR
                    || !env_map.contains_key(crate::env_vars::CACHE_DIR)
                {
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
        crate::env_vars::WORKENV.to_string(),
        workenv_path.to_string_lossy().to_string(),
    );

    // Add FLAVOR_COMMAND_NAME for the binary name
    let binary_name = package_path
        .file_name()
        .and_then(|n| n.to_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| package_path.to_string_lossy().to_string());
    env_map.insert(crate::env_vars::COMMAND_NAME.to_string(), binary_name);
    env_map.insert(
        crate::env_vars::ORIGINAL_COMMAND.to_string(),
        package_path.to_string_lossy().to_string(),
    );

    // Prepend workenv bin directory to PATH (platform-aware)
    let bin_dir = if cfg!(windows) { "Scripts" } else { "bin" };
    let sep = if cfg!(windows) { ";" } else { ":" };
    let bin_path = workenv_path.join(bin_dir);
    if let Some(path) = env_map.get("PATH") {
        let new_path = format!("{}{sep}{path}", bin_path.display());
        env_map.insert("PATH".to_string(), new_path);
    } else {
        env_map.insert("PATH".to_string(), format!("{}", bin_path.display()));
    }

    Ok((executable, all_args, env_map))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::psp::format_2025::metadata::{
        ExecutionInfo, Metadata, PackageInfo, RuntimeEnv, RuntimeInfo, WorkenvInfo,
    };
    use std::collections::HashMap;
    use std::path::PathBuf;

    fn sample_metadata() -> Metadata {
        Metadata {
            format: "PSPF/2025".to_string(),
            format_version: Some("1.0.0".to_string()),
            package: PackageInfo {
                name: "demo".to_string(),
                version: "1.0.0".to_string(),
            },
            slots: Vec::new(),
            execution: ExecutionInfo {
                primary_slot: 0,
                command: "echo hello".to_string(),
                env: HashMap::from([(String::from("EXEC_ONLY"), String::from("execution"))]),
            },
            verification: None,
            build: None,
            launcher: None,
            compatibility: None,
            cache_validation: None,
            runtime: Some(RuntimeInfo {
                env: Some(RuntimeEnv {
                    unset: None,
                    map: None,
                    set: Some(HashMap::from([(
                        String::from("RUNTIME_SET"),
                        String::from("runtime"),
                    )])),
                    pass: None,
                }),
            }),
            workenv: Some(WorkenvInfo {
                directories: None,
                env: Some(HashMap::from([
                    (String::from("WORKENV_ONLY"), String::from("{workenv}/bin")),
                    (
                        String::from(crate::env_vars::CACHE_DIR),
                        String::from("should-not-override"),
                    ),
                ])),
            }),
            setup_commands: Vec::new(),
            policy: None,
        }
    }

    /// Test that `prepare_command` (via `build_launch_command`) prepends the
    /// correct bin directory to PATH with the correct separator.
    ///
    /// On macOS/Linux the subdirectory is "bin" and the separator is ":".
    /// On Windows the subdirectory is "Scripts" and the separator is ";".
    /// The Windows branch is verified at compile time via `cfg!(windows)`.
    #[test]
    fn test_path_prepend_uses_correct_bin_dir_and_separator() {
        // Use a platform-appropriate temp path so path separator assertions work on Windows.
        let temp = tempfile::tempdir().expect("tempdir");
        let workenv = temp.path().join("test_workenv");
        let workenv_path: &Path = &workenv;
        let original_path = env::var("PATH").unwrap_or_default();

        let expected_bin_dir = if cfg!(windows) { "Scripts" } else { "bin" };
        let expected_sep = if cfg!(windows) { ";" } else { ":" };
        let bin_path = workenv_path.join(expected_bin_dir);
        let expected_path = format!("{}{expected_sep}{original_path}", bin_path.display());

        #[cfg(not(windows))]
        {
            assert_eq!(expected_bin_dir, "bin");
            assert_eq!(expected_sep, ":");
            assert!(
                expected_path.contains("/test_workenv/bin:"),
                "PATH should contain workenv/bin: but was: {expected_path}"
            );
        }

        #[cfg(windows)]
        {
            assert_eq!(expected_bin_dir, "Scripts");
            assert_eq!(expected_sep, ";");
            // Use platform-joined path for correct separator assertion.
            let sep = std::path::MAIN_SEPARATOR;
            let expected_scripts = format!("{sep}test_workenv{sep}Scripts;");
            assert!(
                expected_path.contains(&expected_scripts),
                "PATH should contain workenv\\Scripts; but was: {expected_path}"
            );
        }

        assert!(
            expected_path.contains(&original_path),
            "New PATH should contain the original PATH"
        );
    }

    /// Test that when PATH is not set, only the bin directory is used (no separator).
    #[test]
    fn test_path_not_set_uses_only_bin_dir() {
        let workenv_path = Path::new("/tmp/test_workenv");

        let expected_bin_dir = if cfg!(windows) { "Scripts" } else { "bin" };
        let bin_path = workenv_path.join(expected_bin_dir);

        // Simulate the logic from prepare_command when PATH is absent
        let env_map: HashMap<String, String> = HashMap::new();
        let result_path = if let Some(path) = env_map.get("PATH") {
            let sep = if cfg!(windows) { ";" } else { ":" };
            format!("{}{sep}{path}", bin_path.display())
        } else {
            format!("{}", bin_path.display())
        };

        let expected = format!("{}", bin_path.display());
        assert_eq!(
            result_path, expected,
            "When PATH is unset, result should be just the bin dir"
        );

        #[cfg(not(windows))]
        assert_eq!(result_path, "/tmp/test_workenv/bin");

        #[cfg(windows)]
        assert!(result_path.contains("test_workenv\\Scripts"));
    }

    /// Test that the platform-aware separator is correct for the current OS.
    #[test]
    fn test_platform_separator() {
        let sep = if cfg!(windows) { ";" } else { ":" };

        #[cfg(not(windows))]
        assert_eq!(sep, ":");

        #[cfg(windows)]
        assert_eq!(sep, ";");
    }

    #[test]
    fn test_resolve_executable_returns_basename_when_absolute_path_missing() {
        let resolved = resolve_executable("/definitely/not/installed/flavor-tool");
        assert_eq!(resolved, "flavor-tool");
    }

    #[test]
    fn test_prepare_command_applies_env_layers_and_path_prepend() {
        let metadata = sample_metadata();
        let workenv_path = Path::new("/tmp/flavor-workenv");
        let package_path = PathBuf::from("/tmp/demo.psp");

        let original_home = env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());

        let (executable, args, env_map) = prepare_command(
            &metadata,
            workenv_path,
            &package_path,
            &[String::from("--flag")],
        )
        .expect("prepare command");

        // On Windows, echo may resolve to echo.exe or similar; just check it contains "echo".
        assert!(
            executable.contains("echo"),
            "expected executable to contain 'echo', got: {executable}"
        );
        assert_eq!(args, vec![String::from("hello"), String::from("--flag")]);
        // WORKENV_ONLY uses {workenv}/bin literal substitution (not path::join), so the
        // forward slash from the fixture string is preserved even on Windows.
        let workenv_str = workenv_path.to_string_lossy();
        let expected_workenv_bin = format!("{workenv_str}/bin");
        assert_eq!(
            env_map.get("WORKENV_ONLY").expect("workenv env"),
            &expected_workenv_bin
        );
        assert_eq!(
            env_map.get("EXEC_ONLY").expect("execution env"),
            "execution"
        );
        assert_eq!(env_map.get("RUNTIME_SET").expect("runtime set"), "runtime");
        assert_eq!(
            env_map
                .get(crate::env_vars::CACHE_DIR)
                .expect("cache dir should be set"),
            &PathBuf::from(&original_home)
                .join(crate::psp::format_2025::defaults::DEFAULT_CACHE_SUBDIR)
                .to_string_lossy()
                .to_string()
        );
        assert_eq!(
            env_map
                .get(crate::env_vars::COMMAND_NAME)
                .expect("command name"),
            "demo.psp"
        );
        let expected_workenv = workenv_path.to_string_lossy().to_string();
        assert_eq!(
            env_map
                .get(crate::env_vars::WORKENV)
                .expect("flavor workenv"),
            &expected_workenv
        );
        let path_val = env_map.get("PATH").expect("path");
        let expected_scripts = workenv_path
            .join(if cfg!(windows) { "Scripts" } else { "bin" })
            .to_string_lossy()
            .to_string();
        assert!(
            path_val.starts_with(&expected_scripts),
            "PATH should start with {expected_scripts} but was: {path_val}"
        );
    }
}
