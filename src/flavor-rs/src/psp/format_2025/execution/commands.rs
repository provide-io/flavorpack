// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! Command execution utilities

use super::super::launcher::command::resolve_executable;
use super::super::metadata::PackageInfo;
use super::placeholders::substitute_placeholders;
use crate::exceptions::{FlavorError, Result};
use glob::glob;
use log::{debug, info};
use serde_json::Value;
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::Path;
use std::process::Command;

/// Execute setup commands
pub fn execute_setup_commands(
    commands: &[Value],
    workenv_dir: &Path,
    package: &PackageInfo,
    user_cwd: &Path,
    exec_env: &HashMap<String, String>,
) -> Result<()> {
    for (i, cmd_value) in commands.iter().enumerate() {
        debug!("🔧 Executing setup command {}/{}", i + 1, commands.len());

        let cmd_obj = cmd_value
            .as_object()
            .ok_or_else(|| FlavorError::Generic("Setup command must be an object".to_string()))?;

        let cmd_type = cmd_obj
            .get("type")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                FlavorError::Generic("Setup command missing 'type' field".to_string())
            })?;

        match cmd_type {
            "execute" => {
                let command = cmd_obj
                    .get("command")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| {
                        FlavorError::Generic("Execute command missing 'command' field".to_string())
                    })?;

                execute_command(command, workenv_dir, package, user_cwd, exec_env)?;
            }

            "enumerate_and_execute" => {
                let base_command =
                    cmd_obj
                        .get("command")
                        .and_then(|v| v.as_str())
                        .ok_or_else(|| {
                            FlavorError::Generic(
                                "Enumerate command missing 'command' field".to_string(),
                            )
                        })?;

                let enumerate = cmd_obj
                    .get("enumerate")
                    .and_then(|v| v.as_object())
                    .ok_or_else(|| {
                        FlavorError::Generic(
                            "Enumerate command missing 'enumerate' field".to_string(),
                        )
                    })?;

                let path = enumerate
                    .get("path")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| {
                        FlavorError::Generic("Enumerate missing 'path' field".to_string())
                    })?;

                let pattern = enumerate
                    .get("pattern")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| {
                        FlavorError::Generic("Enumerate missing 'pattern' field".to_string())
                    })?;

                let enum_path = substitute_placeholders(path, workenv_dir, package);
                let glob_pattern = format!("{enum_path}/{pattern}");

                debug!("📁 Enumerating files matching: {glob_pattern}");

                for entry in glob(&glob_pattern)
                    .map_err(|e| FlavorError::Generic(format!("Glob error: {e}")))?
                {
                    match entry {
                        Ok(path) => {
                            let command = format!("{} {}", base_command, path.display());
                            execute_command(&command, workenv_dir, package, user_cwd, exec_env)?;
                        }
                        Err(e) => {
                            return Err(FlavorError::Generic(format!(
                                "Failed to enumerate files: {e}"
                            )));
                        }
                    }
                }
            }

            "write_file" => {
                let file_path = cmd_obj
                    .get("path")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| {
                        FlavorError::Generic("Write file command missing 'path' field".to_string())
                    })?;

                let content = cmd_obj
                    .get("content")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| {
                        FlavorError::Generic(
                            "Write file command missing 'content' field".to_string(),
                        )
                    })?;

                let file_path = substitute_placeholders(file_path, workenv_dir, package);
                let content = substitute_placeholders(content, workenv_dir, package);

                if let Some(parent) = Path::new(&file_path).parent() {
                    fs::create_dir_all(parent)?;
                }

                debug!("📝 Writing file: {file_path}");
                fs::write(&file_path, content)?;
            }

            "chmod" => {
                // Change file permissions (POSIX only)
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;

                    let file_pattern =
                        cmd_obj
                            .get("path")
                            .and_then(|v| v.as_str())
                            .ok_or_else(|| {
                                FlavorError::Generic(
                                    "chmod command missing 'path' field".to_string(),
                                )
                            })?;

                    let mode_str = cmd_obj
                        .get("mode")
                        .and_then(|v| v.as_str())
                        .unwrap_or("700");

                    // Parse octal mode (e.g., "700" -> 0o700)
                    let mode = u32::from_str_radix(mode_str, 8).unwrap_or(
                        crate::psp::format_2025::defaults::DEFAULT_EXECUTABLE_PERMS as u32,
                    );

                    let file_pattern = substitute_placeholders(file_pattern, workenv_dir, package);

                    // Handle glob patterns like {workenv}/bin/*
                    if file_pattern.contains('*') {
                        // Extract directory and pattern
                        if let Some(dir_end) = file_pattern.rfind('/') {
                            let dir_path = &file_pattern[..dir_end];
                            let pattern = &file_pattern[dir_end + 1..];

                            if let Ok(entries) = fs::read_dir(dir_path) {
                                for entry in entries.flatten() {
                                    if pattern == "*"
                                        || entry
                                            .file_name()
                                            .to_string_lossy()
                                            .contains(&pattern[..pattern.len() - 1])
                                    {
                                        let path = entry.path();
                                        if path.is_file() {
                                            let permissions = fs::Permissions::from_mode(mode);
                                            if let Err(e) = fs::set_permissions(&path, permissions)
                                            {
                                                debug!(
                                                    "⚠️ Could not chmod {:o} on {:?}: {}",
                                                    mode, path, e
                                                );
                                            } else {
                                                debug!(
                                                    "✅ Set permissions {:o} on {:?}",
                                                    mode, path
                                                );
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        // Single file
                        let path = Path::new(&file_pattern);
                        if path.exists() {
                            let permissions = fs::Permissions::from_mode(mode);
                            if let Err(e) = fs::set_permissions(path, permissions) {
                                debug!("⚠️ Could not chmod {:o} on {:?}: {}", mode, path, e);
                            } else {
                                debug!("✅ Set permissions {:o} on {:?}", mode, path);
                            }
                        }
                    }
                }

                #[cfg(not(unix))]
                {
                    debug!("⚠️ chmod not supported on non-Unix platforms");
                }
            }

            _ => {
                return Err(FlavorError::Generic(format!(
                    "Unknown setup command type: {cmd_type}"
                )));
            }
        }
    }

    Ok(())
}

/// Split a command string into parts, respecting single and double quotes.
/// Handles simple quoting (no escape sequences within quotes).
pub fn shell_split(input: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut chars = input.chars().peekable();
    let mut in_single_quote = false;
    let mut in_double_quote = false;

    while let Some(c) = chars.next() {
        match c {
            '\'' if !in_double_quote => {
                in_single_quote = !in_single_quote;
            }
            '"' if !in_single_quote => {
                in_double_quote = !in_double_quote;
            }
            '\\' if in_double_quote => {
                // Inside double quotes, backslash escapes the next character
                if let Some(next) = chars.next() {
                    current.push(next);
                }
            }
            c if c.is_whitespace() && !in_single_quote && !in_double_quote => {
                if !current.is_empty() {
                    parts.push(std::mem::take(&mut current));
                }
            }
            _ => {
                current.push(c);
            }
        }
    }

    if !current.is_empty() {
        parts.push(current);
    }

    parts
}

/// Execute a command
pub fn execute_command(
    command: &str,
    workenv_dir: &Path,
    package: &PackageInfo,
    user_cwd: &Path,
    exec_env: &HashMap<String, String>,
) -> Result<()> {
    let command = substitute_placeholders(command, workenv_dir, package);
    let parts = shell_split(&command);

    if parts.is_empty() {
        return Ok(());
    }

    let part_refs: Vec<&str> = parts.iter().map(|s| s.as_str()).collect();
    run_command(
        part_refs[0],
        &part_refs[1..],
        workenv_dir,
        user_cwd,
        exec_env,
    )
}

/// Run a command with arguments
pub fn run_command(
    cmd: &str,
    args: &[&str],
    workenv_dir: &Path,
    user_cwd: &Path,
    exec_env: &HashMap<String, String>,
) -> Result<()> {
    debug!("🏃 Running: {cmd} {args:?} in {user_cwd:?}");

    let resolved_cmd = resolve_executable(cmd);
    let mut command = Command::new(&resolved_cmd);
    command.args(args);
    command.current_dir(user_cwd);

    // Inherit all parent environment variables
    for (key, value) in env::vars() {
        command.env(&key, &value);
    }

    // Override/add FLAVOR_WORKENV environment variable
    command.env(crate::env_vars::WORKENV, workenv_dir);

    // Add execution environment from metadata
    for (key, value) in exec_env {
        debug!("🌍 Setting env: {}={}", key, value);
        command.env(key, value);
    }

    // Prepend workenv bin directory to PATH (platform-aware)
    let path = build_workenv_path(workenv_dir, env::var("PATH").ok().as_deref());
    command.env("PATH", path);

    let output = command.output()?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);

        if !stdout.is_empty() {
            info!("Command stdout:\n{stdout}");
        }

        return Err(FlavorError::Generic(format!(
            "Command failed with status {}: {}\n{}",
            output.status.code().unwrap_or(-1),
            cmd,
            stderr
        )));
    }

    Ok(())
}

fn build_workenv_path(workenv_dir: &Path, existing_path: Option<&str>) -> String {
    let bin_dir = if cfg!(windows) { "Scripts" } else { "bin" };
    let sep = if cfg!(windows) { ";" } else { ":" };
    let bin_path = workenv_dir.join(bin_dir);

    match existing_path {
        Some(path) if !path.is_empty() => format!("{}{sep}{path}", bin_path.display()),
        _ => format!("{}", bin_path.display()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::psp::format_2025::metadata::PackageInfo;
    use serde_json::json;
    use std::collections::HashMap;
    use tempfile::tempdir;

    #[test]
    fn test_build_workenv_path_without_existing_path_uses_only_bin_dir() {
        let workenv_dir = Path::new("/tmp/test_workenv");
        let path = build_workenv_path(workenv_dir, None);

        #[cfg(not(windows))]
        assert_eq!(path, "/tmp/test_workenv/bin");

        #[cfg(windows)]
        assert!(path.contains("test_workenv\\Scripts"));
    }

    /// Test that `run_command` prepends the correct bin directory to PATH.
    ///
    /// On macOS/Linux the subdirectory is "bin" and the separator is ":".
    /// On Windows the subdirectory is "Scripts" and the separator is ";".
    /// The Windows branch is verified at compile time via `cfg!(windows)`.
    #[test]
    fn test_run_command_path_has_correct_bin_dir_and_separator() {
        // Use a platform-appropriate temp path so path separator assertions work on Windows.
        let temp = tempfile::tempdir().expect("tempdir");
        let workenv = temp.path().join("test_workenv");
        let workenv_dir: &Path = &workenv;
        let original_path = env::var("PATH").unwrap_or_default();
        let expected_path = build_workenv_path(workenv_dir, Some(&original_path));

        // On the current platform (macOS/Linux in CI), verify the directory name
        #[cfg(not(windows))]
        {
            assert!(
                expected_path.contains("/test_workenv/bin:"),
                "PATH should contain workenv/bin: but was: {expected_path}"
            );
        }

        #[cfg(windows)]
        {
            // Use platform-joined path for correct separator assertion.
            let sep = std::path::MAIN_SEPARATOR;
            let expected_scripts = format!("{sep}test_workenv{sep}Scripts;");
            assert!(
                expected_path.contains(&expected_scripts),
                "PATH should contain workenv\\Scripts; but was: {expected_path}"
            );
        }

        // Verify the expected PATH contains the original PATH after the separator
        assert!(
            expected_path.contains(&original_path),
            "New PATH should contain the original PATH"
        );
    }

    #[test]
    fn test_shell_split_basic() {
        let result = shell_split("echo hello world");
        assert_eq!(result, vec!["echo", "hello", "world"]);
    }

    #[test]
    fn test_shell_split_quoted() {
        let result = shell_split(r#"echo "hello world" foo"#);
        assert_eq!(result, vec!["echo", "hello world", "foo"]);
    }

    #[test]
    fn test_shell_split_single_quoted() {
        let result = shell_split("echo 'hello world' foo");
        assert_eq!(result, vec!["echo", "hello world", "foo"]);
    }

    #[test]
    fn test_shell_split_empty() {
        let result = shell_split("");
        assert!(result.is_empty());
    }

    #[test]
    fn test_shell_split_handles_escaped_double_quote_content() {
        let result = shell_split("echo \"hello \\\"quoted\\\" world\"");
        assert_eq!(result, vec!["echo", "hello \"quoted\" world"]);
    }

    #[test]
    fn test_execute_command_ignores_empty_command() {
        let workenv = tempdir().expect("tempdir");
        let cwd = tempdir().expect("tempdir");
        let package = PackageInfo {
            name: "demo".to_string(),
            version: "1.0.0".to_string(),
        };
        let env = HashMap::new();

        execute_command("", workenv.path(), &package, cwd.path(), &env)
            .expect("empty command should be a no-op");
    }

    #[test]
    fn test_execute_setup_commands_write_file_creates_parent_and_substitutes_placeholders() {
        let workenv = tempdir().expect("tempdir");
        let cwd = tempdir().expect("tempdir");
        let package = PackageInfo {
            name: "demo".to_string(),
            version: "1.0.0".to_string(),
        };
        let env = HashMap::new();

        let commands = vec![json!({
            "type": "write_file",
            "path": "{workenv}/config/settings.txt",
            "content": "package={package_name}"
        })];

        execute_setup_commands(&commands, workenv.path(), &package, cwd.path(), &env)
            .expect("write_file setup command");

        let written = fs::read_to_string(workenv.path().join("config/settings.txt"))
            .expect("read written config");
        assert_eq!(written, "package=demo");
    }

    #[test]
    fn test_execute_setup_commands_rejects_unknown_command_type() {
        let workenv = tempdir().expect("tempdir");
        let cwd = tempdir().expect("tempdir");
        let package = PackageInfo {
            name: "demo".to_string(),
            version: "1.0.0".to_string(),
        };
        let env = HashMap::new();

        let commands = vec![json!({
            "type": "mystery"
        })];

        let err = execute_setup_commands(&commands, workenv.path(), &package, cwd.path(), &env)
            .expect_err("unknown command type should fail");
        assert!(err.to_string().contains("Unknown setup command type"));
    }

    #[cfg(unix)]
    #[test]
    fn test_execute_command_runs_shell_command_and_injects_environment() {
        let workenv = tempdir().expect("tempdir");
        let cwd = tempdir().expect("tempdir");
        let package = PackageInfo {
            name: "demo".to_string(),
            version: "1.0.0".to_string(),
        };
        let env = HashMap::from([(String::from("CUSTOM_ENV"), String::from("value"))]);
        let output_file = workenv.path().join("captured.txt");

        execute_command(
            "sh -c 'printf \"%s|%s\" \"$FLAVOR_WORKENV\" \"$CUSTOM_ENV\" > \"$1\"' sh {workenv}/captured.txt",
            workenv.path(),
            &package,
            cwd.path(),
            &env,
        )
        .expect("execute command");

        let contents = fs::read_to_string(&output_file).expect("read captured output");
        assert_eq!(contents, format!("{}|value", workenv.path().display()));
    }

    #[cfg(unix)]
    #[test]
    fn test_execute_command_propagates_nonzero_exit_status() {
        let workenv = tempdir().expect("tempdir");
        let cwd = tempdir().expect("tempdir");
        let package = PackageInfo {
            name: "demo".to_string(),
            version: "1.0.0".to_string(),
        };
        let env = HashMap::new();

        let err = execute_command("sh -c 'exit 7'", workenv.path(), &package, cwd.path(), &env)
            .expect_err("command should fail");
        assert!(err.to_string().contains("status 7"));
    }

    #[cfg(unix)]
    #[test]
    fn test_execute_setup_commands_enumerate_and_execute_runs_for_each_match() {
        let workenv = tempdir().expect("tempdir");
        let cwd = tempdir().expect("tempdir");
        let package = PackageInfo {
            name: "demo".to_string(),
            version: "1.0.0".to_string(),
        };
        let env = HashMap::new();

        let inputs = workenv.path().join("inputs");
        fs::create_dir_all(&inputs).expect("create inputs");
        fs::write(inputs.join("alpha.txt"), b"alpha").expect("write alpha");
        fs::write(inputs.join("beta.txt"), b"beta").expect("write beta");

        let hits = workenv.path().join("hits.txt");
        let commands = vec![json!({
            "type": "enumerate_and_execute",
            "command": format!(
                "sh -c 'printf \"%s\\n\" \"${{1##*/}}\" >> \"{}\"' sh",
                hits.display()
            ),
            "enumerate": {
                "path": "{workenv}/inputs",
                "pattern": "*.txt"
            }
        })];

        execute_setup_commands(&commands, workenv.path(), &package, cwd.path(), &env)
            .expect("enumerate_and_execute");

        let mut lines: Vec<_> = fs::read_to_string(&hits)
            .expect("read hits")
            .lines()
            .map(str::to_owned)
            .collect();
        lines.sort();

        assert_eq!(lines, vec!["alpha.txt", "beta.txt"]);
    }

    #[cfg(unix)]
    #[test]
    fn test_execute_setup_commands_chmod_applies_default_permissions_to_glob_matches() {
        use std::os::unix::fs::PermissionsExt;

        let workenv = tempdir().expect("tempdir");
        let cwd = tempdir().expect("tempdir");
        let package = PackageInfo {
            name: "demo".to_string(),
            version: "1.0.0".to_string(),
        };
        let env = HashMap::new();

        let bin_dir = workenv.path().join("bin");
        fs::create_dir_all(&bin_dir).expect("create bin dir");
        let executable = bin_dir.join("tool");
        fs::write(&executable, b"#!/bin/sh\n").expect("write tool");

        let commands = vec![json!({
            "type": "chmod",
            "path": "{workenv}/bin/*",
            "mode": "not-octal"
        })];

        execute_setup_commands(&commands, workenv.path(), &package, cwd.path(), &env)
            .expect("chmod setup command");

        let mode = fs::metadata(&executable)
            .expect("stat executable")
            .permissions()
            .mode()
            & 0o777;
        assert_eq!(
            mode,
            u32::from(crate::psp::format_2025::defaults::DEFAULT_EXECUTABLE_PERMS)
        );
    }

    #[test]
    fn test_execute_main_command_returns_zero_for_empty_command() {
        let cwd = tempdir().expect("tempdir");
        let result = execute_main_command("", &[], HashMap::new(), cwd.path())
            .expect("empty command should be accepted");
        assert_eq!(result, 0);
    }

    #[cfg(unix)]
    #[test]
    fn test_execute_main_command_propagates_exit_status() {
        let cwd = tempdir().expect("tempdir");
        let result = execute_main_command("sh -c 'exit 7'", &[], HashMap::new(), cwd.path())
            .expect("command should execute");
        assert_eq!(result, 7);
    }
}

/// Execute main command with environment
pub fn execute_main_command(
    command: &str,
    args: &[String],
    env: HashMap<String, String>,
    workdir: &Path,
) -> Result<i32> {
    let parts = shell_split(command);
    if parts.is_empty() {
        return Ok(0);
    }

    let resolved_cmd = resolve_executable(&parts[0]);
    let mut cmd = Command::new(&resolved_cmd);

    // Add command arguments
    if parts.len() > 1 {
        cmd.args(&parts[1..]);
    }

    // Add user arguments
    cmd.args(args);

    // Set working directory
    cmd.current_dir(workdir);

    // Set environment
    cmd.envs(env);

    // Execute and get status
    let status = cmd.status()?;

    Ok(status.code().unwrap_or(1))
}
