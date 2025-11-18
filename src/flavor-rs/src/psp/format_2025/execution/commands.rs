//! Command execution utilities

use super::super::launcher::command::resolve_executable;
use super::super::metadata::PackageInfo;
use super::placeholders::substitute_placeholders;
use crate::exceptions::{FlavorError, Result};
use glob::glob;
use log::{debug, info, warn};
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

/// Execute a command
pub fn execute_command(
    command: &str,
    workenv_dir: &Path,
    package: &PackageInfo,
    user_cwd: &Path,
    exec_env: &HashMap<String, String>,
) -> Result<()> {
    let command = substitute_placeholders(command, workenv_dir, package);
    let parts: Vec<_> = command.split_whitespace().collect();

    if parts.is_empty() {
        return Ok(());
    }

    run_command(parts[0], &parts[1..], workenv_dir, user_cwd, exec_env)
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
    command.env("FLAVOR_WORKENV", workenv_dir);

    // Add execution environment from metadata
    for (key, value) in exec_env {
        debug!("🌍 Setting env: {}={}", key, value);
        command.env(key, value);
    }

    // Prepend workenv/bin to PATH
    if let Ok(path) = env::var("PATH") {
        let workenv_string;
        let workenv_str = if let Some(s) = workenv_dir.to_str() {
            s
        } else {
            warn!("Work environment path contains non-UTF8 characters, using lossy conversion");
            workenv_string = workenv_dir.to_string_lossy().into_owned();
            &workenv_string
        };
        let new_path = format!("{workenv_str}/bin:{path}");
        command.env("PATH", new_path);
    }

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

/// Execute main command with environment
pub fn execute_main_command(
    command: &str,
    args: &[String],
    env: HashMap<String, String>,
    workdir: &Path,
) -> Result<i32> {
    let parts: Vec<_> = command.split_whitespace().collect();
    if parts.is_empty() {
        return Ok(0);
    }

    let resolved_cmd = resolve_executable(parts[0]);
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
