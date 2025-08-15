use anyhow::{anyhow, Context, Result};
use log::{debug, error, info, trace};
use std::env;
use std::os::unix::process::CommandExt;
use std::path::Path;
use std::process::{Command, Stdio};
use tempfile::TempDir;

mod verify;
mod metadata;
mod reader;
mod runtime;
mod cli;
mod execution;

use metadata::*;
use reader::Reader;
use runtime::process_runtime_env;
use cli::*;
use execution::*;

fn main() -> Result<()> {
    // Initialize logging
    env_logger::Builder::from_env(
        env_logger::Env::default()
            .filter_or("FLAVOR_LOG_LEVEL", "error")
            .write_style_or("FLAVOR_LOG_STYLE", "auto")
    )
    .target(env_logger::Target::Stderr)
    .format_timestamp(None)
    .format_module_path(false)
    .init();

    // Get the path to our own executable
    let exe_path = env::current_exe()?;
    debug!("🏷️ Executable path: {:?}", exe_path);
    
    // Get our current working directory to preserve it
    let user_cwd = env::current_dir()
        .context("Failed to get current directory")?;
    debug!("📂 User working directory: {:?}", user_cwd);

    // Parse arguments
    let args: Vec<String> = env::args().collect();
    debug!("🎯 Command line args: {:?}", args);

    // Check if we're running in verify mode
    if env::var("FLAVOR_VERIFY").is_ok() {
        info!("🔍 Running in verify mode");
        return verify::verify_package(&exe_path);
    }

    // Check for CLI mode
    if env::var("FLAVOR_LAUNCHER_CLI").is_ok() {
        debug!("🖥️ Running in CLI mode");
        
        if args.len() < 2 {
            show_bundle_info(&exe_path)?;
            return Ok(());
        }

        match args[1].as_str() {
            "info" => show_bundle_info(&exe_path)?,
            "run" => run_bundle(&exe_path, &args[2..])?,
            "extract" => {
                if args.len() < 4 {
                    eprintln!("Usage: {} extract <slot> <dir>", args[0]);
                    std::process::exit(1);
                }
                extract_slot(&exe_path, &args[2], &args[3])?;
            }
            "metadata" => show_metadata(&exe_path)?,
            "verify" => verify_bundle(&exe_path)?,
            _ => {
                eprintln!("Unknown command: {}", args[1]);
                eprintln!("Available commands: info, run, extract, metadata, verify");
                std::process::exit(1);
            }
        }
        return Ok(());
    }

    // 📖 Create reader for our bundle
    let mut reader = Reader::new(&exe_path)?;
    info!("📖 Reading PSPF bundle");

    // 📋 Read metadata
    let metadata = reader.read_metadata()?;
    info!("📦 Package: {} v{}", metadata.package.name, metadata.package.version);
    debug!("🎯 Primary slot: {}", metadata.execution.primary_slot);
    debug!("🔧 Command: {}", metadata.execution.command);

    // 🗂️ Create work environment directory
    let workenv_dir = TempDir::new_in(env::temp_dir())
        .context("Failed to create work environment directory")?;
    info!("📁 Work environment: {:?}", workenv_dir.path());

    // 📤 Extract all slots
    info!("📤 Extracting {} slots...", metadata.slots.len());
    let mut slot_paths = std::collections::HashMap::new();
    for (i, slot) in metadata.slots.iter().enumerate() {
        debug!("📦 Extracting slot {}: {} ({} bytes)", i, slot.name, slot.size);
        let slot_path = reader.extract_slot(i, workenv_dir.path())?;
        debug!("✅ Extracted to: {:?}", slot_path);
        slot_paths.insert(slot.index, slot_path);
    }

    // 🔍 Check work environment validity
    // If a validation file is specified, check if the environment is already set up
    let workenv_valid = if let Some(cache_validation) = &metadata.cache_validation {
        check_workenv_validity(workenv_dir.path(), cache_validation)
    } else {
        false
    };
    
    if workenv_valid {
        info!("✅ Work environment is valid, skipping setup");
    } else {
        // 🔧 Run setup commands
        if !metadata.setup_commands.is_empty() {
            info!("🔧 Running {} setup commands...", metadata.setup_commands.len());
            execute_setup_commands(&metadata.setup_commands, workenv_dir.path(), &metadata.package, &user_cwd)?;
        }
    }
    
    // 🎯 Prepare execution
    let mut command = metadata.execution.command.clone();
    
    // 🔄 Substitute slot references in command
    for (idx, path) in &slot_paths {
        let placeholder = format!("{{slot:{}}}", idx);
        command = command.replace(&placeholder, path.to_str().unwrap());
    }
    
    // 🔄 Substitute work environment and package info
    command = command.replace("{workenv}", workenv_dir.path().to_str().unwrap());
    command = command.replace("{package_name}", &metadata.package.name);
    command = command.replace("{version}", &metadata.package.version);
    
    debug!("🎯 Final command: {}", command);

    // 🔪 Parse command
    let parts: Vec<&str> = command.split_whitespace().collect();
    if parts.is_empty() {
        error!("❌ Empty command");
        return Err(anyhow!("Empty command"));
    }
    debug!("🔪 Command parts: {:?}", parts);
    
    // 🏷️ Get original command name for argv[0]
    let original_cmd = env::args().next().unwrap_or_else(|| "flavor".to_string());
    let binary_name = Path::new(&original_cmd)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("flavor");
    debug!("🏷️ Setting argv[0] to binary name: {} (from: {})", binary_name, original_cmd);

    // Build command with custom argv[0]
    let mut cmd = Command::new(parts[0]);
    
    // Set argv[0] to the original binary name
    // This makes the Python process see the correct command name in sys.argv[0]
    cmd.arg0(binary_name);
    
    // Add command arguments
    if parts.len() > 1 {
        cmd.args(&parts[1..]);
    }
    
    // Add original arguments (skip our own executable name)
    let args: Vec<String> = env::args().skip(1).collect();
    if !args.is_empty() {
        cmd.args(&args);
    }

    // 🌍 CRITICAL: Inherit all parent environment variables
    let mut env_map: std::collections::HashMap<String, String> = env::vars().collect();
    debug!("🌍 Inheriting parent environment: {} variables", env_map.len());
    
    // 🏷️ Add original command information to environment
    // These can be used as fallbacks if argv[0] isn't sufficient
    env_map.insert("FLAVOR_ORIGINAL_COMMAND".to_string(), original_cmd.clone());
    env_map.insert("FLAVOR_COMMAND_NAME".to_string(), binary_name.to_string());
    debug!("🏷️ Added command name environment variables");
    
    // 🔄 Process runtime.env configuration if present
    if let Some(runtime) = &metadata.runtime {
        if let Some(runtime_env) = &runtime.env {
            debug!("🔄 Processing runtime.env configuration");
            process_runtime_env(&mut env_map, runtime_env);
        }
    }
    
    // Apply the processed environment to the command
    for (key, value) in &env_map {
        cmd.env(key, value);
    }

    // Set additional environment from package metadata
    debug!("➕ Adding package-defined environment variables: count={}", metadata.execution.environment.len());
    for (k, mut v) in metadata.execution.environment {
        // Substitute slot references
        for (idx, path) in &slot_paths {
            let placeholder = format!("{{slot:{}}}", idx);
            v = v.replace(&placeholder, path.to_str().unwrap());
        }
        // Substitute work environment and package info
        v = v.replace("{workenv}", workenv_dir.path().to_str().unwrap());
        v = v.replace("{package_name}", &metadata.package.name);
        v = v.replace("{version}", &metadata.package.version);
        cmd.env(&k, &v);
        trace!("➕ Added package env var: {}={}", k, v);
    }

    // Set FLAVOR_WORKENV
    cmd.env("FLAVOR_WORKENV", workenv_dir.path());
    trace!("🏠 Set FLAVOR_WORKENV={:?}", workenv_dir.path());

    // Update PATH to include workenv/bin
    if let Ok(path) = env::var("PATH") {
        let workenv_bin = workenv_dir.path().join("bin");
        let new_path = format!("{}:{}", workenv_bin.display(), path);
        cmd.env("PATH", new_path);
        trace!("🛤️ Updated PATH to include workenv/bin");
    }

    // Set working directory
    cmd.current_dir(&user_cwd);
    debug!("📍 Set working directory: {:?}", user_cwd);

    // Execute the command
    info!("🚀 Executing: {} with argv[0]={}", parts[0], binary_name);
    debug!("🚀 Full command with args: {:?}", parts);
    debug!("🚀 Additional user args: {:?}", args);
    
    let mut child = cmd
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .with_context(|| format!("Failed to execute command: {}", parts[0]))?;
    
    // Wait for process to complete
    let status = child.wait()?;
    
    // Get exit code
    let exit_code = status.code().unwrap_or(1);
    
    // Log exit status
    if exit_code == 0 {
        info!("✅ Process exited successfully");
    } else {
        error!("❌ Process exited with code: {}", exit_code);
    }
    std::process::exit(exit_code);
}