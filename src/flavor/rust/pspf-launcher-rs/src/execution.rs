//! Command execution and setup logic for PSPF packages
//! 
//! This module handles executing setup commands and the main application
//! command within the PSPF work environment.

use anyhow::{anyhow, Result};
use glob::glob;
use log::{debug, info};
use serde_json::Value;
use std::env;
use std::fs;
use std::path::Path;
use std::process::Command;

use crate::metadata::{CacheValidationInfo, PackageInfo};

/// Check if work environment is valid
/// 
/// Validates the work environment by checking if a specific file exists with expected content.
/// This allows skipping redundant setup if the environment is already properly initialized.
pub fn check_workenv_validity(workenv_dir: &Path, validation: &CacheValidationInfo) -> bool {
    let check_path = validation.check_file
        .replace("{workenv}", workenv_dir.to_str().unwrap());
    
    debug!("🔍 Checking work environment validity: {}", check_path);
    
    match fs::read_to_string(&check_path) {
        Ok(content) => {
            let is_valid = content.trim() == validation.expected_content;
            if is_valid {
                debug!("✅ Work environment validation passed");
            } else {
                debug!("❌ Work environment validation failed: expected '{}', got '{}'", 
                    validation.expected_content, content.trim());
            }
            is_valid
        }
        Err(_) => {
            debug!("❌ Work environment validation file not found");
            false
        }
    }
}

/// Execute setup commands
/// 
/// Processes and executes all setup commands required to initialize the work environment.
/// Supports multiple command types:
/// - execute: Run a shell command
/// - enumerate_and_execute: Run a command for each file matching a pattern
/// - write_file: Write content to a file
pub fn execute_setup_commands(
    commands: &[Value], 
    workenv_dir: &Path, 
    package: &PackageInfo,
    user_cwd: &Path
) -> Result<()> {
    for (i, cmd_value) in commands.iter().enumerate() {
        debug!("🔧 Executing setup command {}/{}", i + 1, commands.len());
        
        // Parse command object
        let cmd_obj = cmd_value.as_object()
            .ok_or_else(|| anyhow!("Setup command must be an object"))?;
        
        let cmd_type = cmd_obj.get("type")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Setup command missing 'type' field"))?;
        
        match cmd_type {
            "execute" => {
                let command = cmd_obj.get("command")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| anyhow!("Execute command missing 'command' field"))?;
                
                execute_command(command, workenv_dir, package, user_cwd)?;
            }
            
            "enumerate_and_execute" => {
                let base_command = cmd_obj.get("command")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| anyhow!("Enumerate command missing 'command' field"))?;
                
                let enumerate = cmd_obj.get("enumerate")
                    .and_then(|v| v.as_object())
                    .ok_or_else(|| anyhow!("Enumerate command missing 'enumerate' field"))?;
                
                let path = enumerate.get("path")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| anyhow!("Enumerate missing 'path' field"))?;
                
                let pattern = enumerate.get("pattern")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| anyhow!("Enumerate missing 'pattern' field"))?;
                
                // Substitute placeholders in path
                let enum_path = substitute_placeholders(path, workenv_dir, package);
                let glob_pattern = format!("{}/{}", enum_path, pattern);
                
                debug!("📁 Enumerating files matching: {}", glob_pattern);
                
                for entry in glob(&glob_pattern)? {
                    match entry {
                        Ok(path) => {
                            let command = format!("{} {}", base_command, path.display());
                            execute_command(&command, workenv_dir, package, user_cwd)?;
                        }
                        Err(e) => {
                            return Err(anyhow!("Failed to enumerate files: {}", e));
                        }
                    }
                }
            }
            
            "write_file" => {
                let file_path = cmd_obj.get("path")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| anyhow!("Write file command missing 'path' field"))?;
                
                let content = cmd_obj.get("content")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| anyhow!("Write file command missing 'content' field"))?;
                
                // Substitute placeholders
                let file_path = substitute_placeholders(file_path, workenv_dir, package);
                let content = substitute_placeholders(content, workenv_dir, package);
                
                // Create parent directories
                if let Some(parent) = Path::new(&file_path).parent() {
                    fs::create_dir_all(parent)?;
                }
                
                debug!("📝 Writing file: {}", file_path);
                fs::write(&file_path, content)?;
            }
            
            _ => {
                return Err(anyhow!("Unknown setup command type: {}", cmd_type));
            }
        }
    }
    
    Ok(())
}

/// Substitute placeholders in text
/// 
/// Replaces the following placeholders:
/// - {workenv}: Path to the work environment directory
/// - {package_name}: Name of the package
/// - {version}: Version of the package
pub fn substitute_placeholders(text: &str, workenv_dir: &Path, package: &PackageInfo) -> String {
    text.replace("{workenv}", workenv_dir.to_str().unwrap())
        .replace("{package_name}", &package.name)
        .replace("{version}", &package.version)
}

/// Execute a command
/// 
/// Executes a single command string after substituting placeholders.
/// The command is split on whitespace to separate the executable from arguments.
/// Preserves the user's current working directory.
pub fn execute_command(
    command: &str, 
    workenv_dir: &Path, 
    package: &PackageInfo, 
    user_cwd: &Path
) -> Result<()> {
    let command = substitute_placeholders(command, workenv_dir, package);
    let parts: Vec<_> = command.split_whitespace().collect();
    
    if parts.is_empty() {
        return Ok(());
    }
    
    run_command(parts[0], &parts[1..], workenv_dir, user_cwd)
}

/// Run a command with arguments
/// 
/// Executes a command with the given arguments in the user's current directory.
/// The work environment's bin directory is prepended to PATH.
/// Returns an error if the command fails to execute or returns non-zero exit code.
pub fn run_command(cmd: &str, args: &[&str], workenv_dir: &Path, user_cwd: &Path) -> Result<()> {
    debug!("🏃 Running: {} {:?} in {:?}", cmd, args, user_cwd);
    
    let mut command = Command::new(cmd);
    command.args(args);
    
    // Set working directory to user's directory
    command.current_dir(user_cwd);
    
    // Inherit all parent environment variables
    for (key, value) in env::vars() {
        command.env(&key, &value);
    }
    
    // Override/add FLAVOR_WORKENV environment variable
    command.env("FLAVOR_WORKENV", workenv_dir);
    
    // Prepend workenv/bin to PATH
    if let Ok(path) = env::var("PATH") {
        let new_path = format!("{}/bin:{}", workenv_dir.to_str().unwrap(), path);
        command.env("PATH", new_path);
    }
    
    let output = command.output()?;
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        
        if !stdout.is_empty() {
            info!("Command stdout:\n{}", stdout);
        }
        
        return Err(anyhow!(
            "Command failed with status {}: {}\n{}",
            output.status.code().unwrap_or(-1),
            cmd,
            stderr
        ));
    }
    
    Ok(())
}