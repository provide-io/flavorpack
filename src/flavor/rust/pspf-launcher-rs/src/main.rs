use anyhow::{anyhow, Context, Result};
use log::{debug, error, info, trace};
use signal_hook::{consts::signal::*, iterator::Signals};
use std::env;
use std::fs;
use std::io::Write;
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::thread;
use std::time::Duration;

mod verify;
mod metadata;
mod reader;
mod runtime;
mod cli;
mod execution;
mod logging;

use reader::Reader;
use runtime::process_runtime_env;
use cli::*;
use execution::*;

// Global state for signal handling
static CHILD_PID: AtomicU32 = AtomicU32::new(0);
static EXTRACTING: AtomicBool = AtomicBool::new(false);
static LOCK_ACQUIRED: AtomicBool = AtomicBool::new(false);
static WORKENV_PATH: std::sync::RwLock<Option<PathBuf>> = std::sync::RwLock::new(None);

/// Get the appropriate cache directory for the current platform
fn get_cache_dir() -> PathBuf {
    if let Ok(cache_dir) = env::var("FLAVOR_CACHE") {
        return PathBuf::from(cache_dir);
    }
    
    #[cfg(target_os = "macos")]
    {
        if let Some(home) = env::var_os("HOME") {
            return PathBuf::from(home).join("Library/Caches/flavor");
        }
    }
    
    #[cfg(target_os = "linux")]
    {
        if let Ok(xdg_cache) = env::var("XDG_CACHE_HOME") {
            return PathBuf::from(xdg_cache).join("flavor");
        }
        if let Some(home) = env::var_os("HOME") {
            return PathBuf::from(home).join(".cache/flavor");
        }
    }
    
    // Fallback to temp dir
    env::temp_dir().join("flavor")
}

/// Calculate a deterministic cache path for a package
fn get_workenv_path(_package_name: &str, _version: &str, checksum: &str) -> PathBuf {
    let cache_base = get_cache_dir();
    
    // Use first 8 chars of checksum for brevity
    let checksum_prefix = if checksum.len() >= 8 {
        &checksum[..8]
    } else {
        checksum
    };
    
    // Build the path: cache_dir/checksum_prefix
    // We use just the checksum as the key since it's unique per package build
    cache_base.join(checksum_prefix)
}

/// Check if a process with given PID is still running
fn is_process_running(pid: u32) -> bool {
    unsafe {
        // kill with signal 0 just checks if process exists
        libc::kill(pid as i32, 0) == 0
    }
}

/// Try to acquire an exclusive lock for cache extraction
/// Returns true if lock was acquired, false if cache is already being extracted
fn try_acquire_lock(workenv_path: &Path) -> Result<bool> {
    let lock_path = workenv_path.join(".extraction.lock");
    let pid = std::process::id();
    
    // Check for stale lock first
    if lock_path.exists() {
        debug!("🔍 Lock file exists, checking if it's stale...");
        
        // Try to read the PID from the lock file
        if let Ok(contents) = fs::read_to_string(&lock_path) {
            if let Ok(old_pid) = contents.trim().parse::<u32>() {
                if !is_process_running(old_pid) {
                    info!("🧹 Removing stale lock from dead process (PID: {})", old_pid);
                    fs::remove_file(&lock_path)?;
                } else {
                    debug!("🔒 Lock held by active process (PID: {})", old_pid);
                    return Ok(false);
                }
            } else {
                // Invalid PID in lock file, remove it
                info!("🧹 Removing invalid lock file (couldn't parse PID)");
                fs::remove_file(&lock_path)?;
            }
        } else {
            // Can't read lock file, try to remove it
            info!("🧹 Removing unreadable lock file");
            fs::remove_file(&lock_path)?;
        }
    }
    
    // Try to create lock file exclusively
    match fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&lock_path)
    {
        Ok(mut file) => {
            // Write our PID to the lock file
            writeln!(file, "{}", pid)?;
            debug!("🔒 Acquired extraction lock (PID: {})", pid);
            LOCK_ACQUIRED.store(true, Ordering::SeqCst);
            Ok(true)
        }
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
            debug!("🔒 Lock file exists, another process is extracting");
            Ok(false)
        }
        Err(e) => Err(e.into())
    }
}

/// Release the extraction lock
fn release_lock(workenv_path: &Path) {
    let lock_path = workenv_path.join(".extraction.lock");
    if let Err(e) = fs::remove_file(&lock_path) {
        debug!("⚠️ Failed to remove lock file: {}", e);
    } else {
        debug!("🔓 Released extraction lock");
    }
}

/// Wait for another process to finish extraction
fn wait_for_extraction(workenv_path: &Path, timeout_secs: u64) -> Result<()> {
    let lock_path = workenv_path.join(".extraction.lock");
    let max_attempts = timeout_secs * 10; // Check every 100ms
    
    for attempt in 0..max_attempts {
        if !lock_path.exists() {
            debug!("✅ Extraction lock released, cache should be ready");
            // Give a bit more time for files to be fully written
            thread::sleep(Duration::from_millis(100));
            return Ok(());
        }
        
        if attempt % 10 == 0 {
            debug!("⏳ Waiting for extraction to complete... ({}/{}s)", attempt / 10, timeout_secs);
        }
        
        thread::sleep(Duration::from_millis(100));
    }
    
    Err(anyhow!("Timeout waiting for cache extraction to complete"))
}

/// Mark cache extraction as complete
fn mark_extraction_complete(workenv_path: &Path) -> Result<()> {
    let marker_path = workenv_path.join(".extraction.complete");
    let mut file = fs::File::create(&marker_path)?;
    writeln!(file, "{}", std::process::id())?;
    debug!("✅ Marked extraction as complete");
    Ok(())
}

/// Check if cache extraction is complete
fn is_extraction_complete(workenv_path: &Path) -> bool {
    workenv_path.join(".extraction.complete").exists()
}

/// Mark cache as incomplete (used during signal handling)
fn mark_extraction_incomplete(workenv_path: &Path) {
    let marker_path = workenv_path.join(".extraction.incomplete");
    if let Ok(mut file) = fs::File::create(&marker_path) {
        let _ = writeln!(file, "Interrupted at {}", chrono::Utc::now());
        debug!("⚠️ Marked extraction as incomplete");
    }
    // Remove the complete marker if it exists
    let _ = fs::remove_file(workenv_path.join(".extraction.complete"));
}

/// Setup signal handlers for graceful shutdown
fn setup_signal_handlers() -> Result<()> {
    let mut signals = Signals::new(&[SIGTERM, SIGINT])?;
    
    thread::spawn(move || {
        for sig in signals.forever() {
            match sig {
                SIGTERM => {
                    info!("📨 Received SIGTERM, initiating graceful shutdown...");
                    handle_shutdown_signal(SIGTERM);
                }
                SIGINT => {
                    info!("📨 Received SIGINT (Ctrl+C), initiating graceful shutdown...");
                    handle_shutdown_signal(SIGINT);
                }
                _ => unreachable!(),
            }
        }
    });
    
    debug!("✅ Signal handlers installed for SIGTERM and SIGINT");
    Ok(())
}

/// Handle shutdown signals
fn handle_shutdown_signal(sig: i32) {
    debug!("🛑 Processing shutdown signal: {}", sig);
    
    // If we're extracting, mark the cache as incomplete
    if EXTRACTING.load(Ordering::SeqCst) {
        info!("⚠️ Extraction interrupted by signal, marking cache as incomplete");
        if let Ok(guard) = WORKENV_PATH.read() {
            if let Some(ref workenv_path) = *guard {
                mark_extraction_incomplete(workenv_path);
            }
        }
    }
    
    // Release lock if we acquired it
    if LOCK_ACQUIRED.load(Ordering::SeqCst) {
        info!("🔓 Releasing extraction lock due to signal");
        if let Ok(guard) = WORKENV_PATH.read() {
            if let Some(ref workenv_path) = *guard {
                release_lock(workenv_path);
            }
        }
    }
    
    // Forward signal to child process if it exists
    let child_pid = CHILD_PID.load(Ordering::SeqCst);
    if child_pid > 0 {
        info!("📤 Forwarding signal {} to child process (PID: {})", sig, child_pid);
        unsafe {
            if libc::kill(child_pid as i32, sig) == 0 {
                debug!("✅ Signal forwarded successfully to child");
                
                // Give child time to exit gracefully (10 seconds)
                info!("⏳ Waiting up to 10 seconds for child to exit gracefully...");
                for i in 0..100 {
                    thread::sleep(Duration::from_millis(100));
                    if !is_process_running(child_pid) {
                        info!("✅ Child process exited gracefully after {:.1}s", i as f64 / 10.0);
                        std::process::exit(128 + sig);
                    }
                    if i % 10 == 0 && i > 0 {
                        debug!("⏳ Still waiting for child to exit... ({}/10s)", i / 10);
                    }
                }
                
                // Child didn't exit gracefully, force kill
                error!("⚠️ Child process didn't exit gracefully, sending SIGKILL");
                libc::kill(child_pid as i32, SIGKILL);
                thread::sleep(Duration::from_millis(100));
            } else {
                error!("❌ Failed to forward signal to child: {}", std::io::Error::last_os_error());
            }
        }
    } else {
        debug!("📝 No child process to forward signal to");
    }
    
    // Exit with standard Unix signal exit code (128 + signal number)
    std::process::exit(128 + sig);
}

fn main() -> Result<()> {
    // Initialize logging with JSON support
    if let Err(e) = logging::init_logger() {
        eprintln!("Failed to initialize logger: {}", e);
        // Fall back to basic stderr logging
    }

    // Check execution mode - default to exec (process replacement) for clean ps output
    // Set FLAVOR_EXEC_MODE=spawn to use child process with signal handling
    let exec_mode = env::var("FLAVOR_EXEC_MODE").unwrap_or_else(|_| "exec".to_string());
    let use_exec = exec_mode.to_lowercase() != "spawn";
    
    if use_exec {
        debug!("🔄 Using exec mode - process will be replaced");
    } else {
        debug!("👶 Using spawn mode - child process with signal handling");
        // Only setup signal handlers in spawn mode
        setup_signal_handlers()?;
        debug!("✅ Signal handlers installed");
    }

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

    // 🗂️ Create/use persistent work environment directory
    // Use the first slot's checksum as a unique identifier for the cache
    let cache_key = metadata.slots.first()
        .map(|s| s.checksum.as_str())
        .unwrap_or("unknown");
    
    let workenv_path = get_workenv_path(&metadata.package.name, &metadata.package.version, cache_key);
    
    // Create the directory if it doesn't exist
    fs::create_dir_all(&workenv_path)
        .context("Failed to create work environment directory")?;
    
    info!("📁 Work environment: {:?}", workenv_path);
    
    // Store workenv path for signal handler
    {
        let mut path_guard = WORKENV_PATH.write().unwrap();
        *path_guard = Some(workenv_path.clone());
    }

    // Check for incomplete extraction from previous interrupted run
    if workenv_path.join(".extraction.incomplete").exists() {
        info!("⚠️ Found incomplete extraction marker, clearing cache");
        // Remove incomplete marker and complete marker if they exist
        let _ = fs::remove_file(workenv_path.join(".extraction.incomplete"));
        let _ = fs::remove_file(workenv_path.join(".extraction.complete"));
        // Optionally, could clear the entire cache directory here
    }

    // 🔍 Check work environment validity BEFORE extraction
    let mut workenv_valid = if let Some(cache_validation) = &metadata.cache_validation {
        check_workenv_validity(&workenv_path, cache_validation) && is_extraction_complete(&workenv_path)
    } else {
        is_extraction_complete(&workenv_path)
    };

    let mut slot_paths = std::collections::HashMap::new();
    
    if workenv_valid {
        info!("✅ Work environment is valid, skipping extraction and setup");
        // Build slot paths without extraction since cache is valid
        for slot in &metadata.slots {
            let slot_path = if let Some(ref extract_to) = slot.extract_to {
                if extract_to == "." {
                    workenv_path.clone()
                } else {
                    workenv_path.join(extract_to)
                }
            } else {
                workenv_path.join(&slot.name)
            };
            slot_paths.insert(slot.index, slot_path);
        }
    } else {
        // Try to acquire lock for extraction
        let acquired_lock = try_acquire_lock(&workenv_path)?;
        
        if acquired_lock {
            // Mark that we're extracting (for signal handler)
            EXTRACTING.store(true, Ordering::SeqCst);
            
            // We got the lock, do the extraction
            info!("📤 Extracting {} slots...", metadata.slots.len());
            for (i, slot) in metadata.slots.iter().enumerate() {
                debug!("📦 Extracting slot {}: {} ({} bytes)", i, slot.name, slot.size);
                let slot_path = reader.extract_slot(i, &workenv_path)?;
                debug!("✅ Extracted to: {:?}", slot_path);
                slot_paths.insert(slot.index, slot_path);
            }
            
            // 🔧 Run setup commands only if cache was invalid
            if !metadata.setup_commands.is_empty() {
                info!("🔧 Running {} setup commands...", metadata.setup_commands.len());
                execute_setup_commands(&metadata.setup_commands, &workenv_path, &metadata.package, &user_cwd)?;
            }
            
            // Mark extraction as complete
            mark_extraction_complete(&workenv_path)?;
            EXTRACTING.store(false, Ordering::SeqCst);
            
            // Release the lock after extraction
            release_lock(&workenv_path);
            LOCK_ACQUIRED.store(false, Ordering::SeqCst);
        } else {
            // Another process is extracting, wait for it to complete
            info!("⏳ Another process is extracting, waiting...");
            wait_for_extraction(&workenv_path, 60)?; // Wait up to 60 seconds
            
            // Re-check validity after waiting
            workenv_valid = if let Some(cache_validation) = &metadata.cache_validation {
                check_workenv_validity(&workenv_path, cache_validation) && is_extraction_complete(&workenv_path)
            } else {
                // If no validation info, check extraction complete marker
                is_extraction_complete(&workenv_path)
            };
            
            if workenv_valid {
                info!("✅ Cache extraction completed by another process");
                // Build slot paths without extraction
                for slot in &metadata.slots {
                    let slot_path = if let Some(ref extract_to) = slot.extract_to {
                        if extract_to == "." {
                            workenv_path.clone()
                        } else {
                            workenv_path.join(extract_to)
                        }
                    } else {
                        workenv_path.join(&slot.name)
                    };
                    slot_paths.insert(slot.index, slot_path);
                }
            } else {
                return Err(anyhow!("Cache extraction by another process failed validation"));
            }
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
    command = command.replace("{workenv}", workenv_path.to_str().unwrap());
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
        v = v.replace("{workenv}", workenv_path.to_str().unwrap());
        v = v.replace("{package_name}", &metadata.package.name);
        v = v.replace("{version}", &metadata.package.version);
        cmd.env(&k, &v);
        trace!("➕ Added package env var: {}={}", k, v);
    }

    // Set FLAVOR_WORKENV
    cmd.env("FLAVOR_WORKENV", &workenv_path);
    trace!("🏠 Set FLAVOR_WORKENV={:?}", workenv_path);

    // Update PATH to include workenv/bin
    if let Ok(path) = env::var("PATH") {
        let workenv_bin = workenv_path.join("bin");
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
    
    // Check if we should use exec (process replacement) or spawn (child process)
    let exec_mode = env::var("FLAVOR_EXEC_MODE").unwrap_or_else(|_| "exec".to_string());
    let use_exec = exec_mode.to_lowercase() != "spawn";
    
    if use_exec {
        // Use exec to replace the current process entirely
        // This gives the cleanest ps output but we lose signal handling
        info!("🔄 Replacing process via exec()");
        
        // exec() never returns on success - it replaces the process
        let err = cmd.exec();
        
        // If we get here, exec failed
        error!("❌ Failed to exec command: {}", err);
        std::process::exit(1);
    } else {
        // Use spawn to create a child process (current behavior)
        // This allows signal handling but shows both processes in ps
        let mut child = cmd
            .stdin(Stdio::inherit())
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
            .with_context(|| format!("Failed to execute command: {}", parts[0]))?;
        
        // Store child PID for signal forwarding
        let child_pid = child.id();
        CHILD_PID.store(child_pid, Ordering::SeqCst);
        debug!("👶 Child process started with PID: {}", child_pid);
        
        // Wait for process to complete
        let status = child.wait()?;
        
        // Clear child PID since process has exited
        CHILD_PID.store(0, Ordering::SeqCst);
        debug!("👶 Child process completed");
        
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
}