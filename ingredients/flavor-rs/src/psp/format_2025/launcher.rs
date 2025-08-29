//! PSPF/2025 package launcher

use crate::api::LaunchOptions;
use crate::exceptions::{FlavorError, Result};
use crate::utils::get_cache_dir;
use log::{debug, error, info, warn};
use std::collections::HashMap;
use std::env;
use std::fs;
#[cfg(unix)]
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};

use super::constants::DISK_SPACE_MULTIPLIER;
use super::execution::{
    check_workenv_validity_full, execute_setup_commands,
    save_index_metadata, save_package_checksum, substitute_placeholders,
};
use super::locking::{
    cleanup_stale_extractions, mark_extraction_complete, release_lock, 
    try_acquire_lock, wait_for_extraction,
};
use super::paths::WorkenvPaths;
use super::metadata::{Metadata, WorkenvInfo};
use super::reader::Reader;
use super::runtime::process_runtime_env;

// Use CHILD_PID from lib.rs
use crate::CHILD_PID;
static EXTRACTING: AtomicBool = AtomicBool::new(false);

/// Helper function to recursively copy a directory
fn copy_dir_all(src: &Path, dst: &Path) -> Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());
        
        if src_path.is_dir() {
            copy_dir_all(&src_path, &dst_path)?;
        } else {
            fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
}

/// Fix shebangs in scripts after atomic move
fn fix_shebangs(bin_dir: &Path, old_prefix: &Path, new_prefix: &Path) -> Result<()> {
    use std::io::{Read, Write};
    
    if !bin_dir.exists() {
        return Ok(());
    }
    
    for entry in fs::read_dir(bin_dir)? {
        let entry = entry?;
        let path = entry.path();
        
        if path.is_file() {
            // Read first few bytes to check for shebang
            let mut file = fs::File::open(&path)?;
            let mut header = [0u8; 2];
            if file.read_exact(&mut header).is_ok() && &header == b"#!" {
                // Read entire file
                file = fs::File::open(&path)?;
                let mut content = Vec::new();
                file.read_to_end(&mut content)?;
                
                // Find end of first line
                if let Some(newline_pos) = content.iter().position(|&b| b == b'\n') {
                    let first_line = &content[0..newline_pos];
                    let old_prefix_str = old_prefix.to_string_lossy();
                    let old_prefix_bytes = old_prefix_str.as_bytes();
                    
                    // Check if the shebang contains the old prefix
                    if first_line.windows(old_prefix_bytes.len())
                        .any(|window| window == old_prefix_bytes) 
                    {
                        // Replace old prefix with new prefix in first line
                        let mut new_content = Vec::new();
                        let first_line_str = String::from_utf8_lossy(first_line);
                        let new_prefix_str = new_prefix.to_string_lossy();
                        let new_first_line = first_line_str.replace(
                            old_prefix_str.as_ref(),
                            new_prefix_str.as_ref()
                        );
                        new_content.extend_from_slice(new_first_line.as_bytes());
                        new_content.extend_from_slice(&content[newline_pos..]);
                        
                        // Write back the modified content
                        let mut file = fs::File::create(&path)?;
                        file.write_all(&new_content)?;
                        
                        debug!("Fixed shebang in {:?}", path.file_name().unwrap_or_default());
                    }
                }
            }
        }
    }
    
    Ok(())
}

/// Calculate a deterministic cache path for a package
fn get_workenv_paths(package_path: &Path) -> WorkenvPaths {
    let cache_base = get_cache_dir();
    WorkenvPaths::new(cache_base, package_path)
}

/// Check if there's enough disk space for extraction
fn check_disk_space(paths: &WorkenvPaths, metadata: &Metadata) -> Result<()> {
    // Calculate total size needed (compressed size * DISK_SPACE_MULTIPLIER for safety)
    let total_size_needed: u64 = metadata.slots.iter()
        .map(|slot| slot.size as u64 * DISK_SPACE_MULTIPLIER)
        .sum();
    
    // Get available disk space
    #[cfg(unix)]
    {
        use std::mem;
        use std::ffi::CString;
        
        unsafe {
            let workenv_path = paths.workenv();
            let path_cstr = CString::new(workenv_path.to_string_lossy().as_bytes())
                .map_err(|e| FlavorError::Generic(format!("Invalid path for statvfs: {}", e)))?;
            let mut stat: libc::statvfs = mem::zeroed();
            
            if libc::statvfs(path_cstr.as_ptr(), &mut stat) != 0 {
                warn!("⚠️ Could not check disk space");
                return Ok(()); // Don't fail if we can't check
            }
            
            let available = stat.f_bavail as u64 * stat.f_frsize as u64;
            
            // Convert to human-readable sizes
            let needed_gb = total_size_needed as f64 / (1024.0 * 1024.0 * 1024.0);
            let available_gb = available as f64 / (1024.0 * 1024.0 * 1024.0);
            
            debug!("💾 Disk space check: need {:.2} GB, have {:.2} GB", needed_gb, available_gb);
            
            if available < total_size_needed {
                error!("❌ Insufficient disk space: need {:.2} GB, have {:.2} GB", 
                       needed_gb, available_gb);
                return Err(FlavorError::Generic(format!(
                    "insufficient disk space: need {:.2} GB, have {:.2} GB",
                    needed_gb, available_gb
                )));
            }
            
            debug!("✅ Sufficient disk space available");
        }
    }
    
    #[cfg(not(unix))]
    {
        warn!("⚠️ Disk space check not implemented for this platform");
    }
    
    Ok(())
}

/// Setup workenv directories with proper permissions
fn setup_workenv_directories(workenv_path: &Path, workenv_info: &WorkenvInfo) -> Result<()> {
    if let Some(ref directories) = workenv_info.directories {
        for dir_spec in directories {
            // Substitute {workenv} placeholder in the path
            let path_str = if dir_spec.path.starts_with("{workenv}/") {
                &dir_spec.path["{workenv}/".len()..]
            } else if dir_spec.path == "{workenv}" {
                ""
            } else {
                &dir_spec.path
            };

            let dir_path = if path_str.is_empty() {
                workenv_path.to_path_buf()
            } else {
                workenv_path.join(path_str)
            };
            debug!("📁 Creating directory: {:?}", dir_path);
            fs::create_dir_all(&dir_path)?;

            // Set permissions on Unix systems
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;

                // Use specified mode or default to 0700 (user-only access)
                let mode_str = dir_spec.mode.as_deref().unwrap_or("0700");

                // Parse octal mode string (e.g., "0700")
                if let Ok(mode) = u32::from_str_radix(mode_str.trim_start_matches('0'), 8) {
                    let permissions = fs::Permissions::from_mode(mode);
                    fs::set_permissions(&dir_path, permissions)?;
                    debug!("🔒 Set permissions {} on {:?}", mode_str, dir_path);
                } else {
                    // Fallback to 0700 if parsing fails
                    let permissions = fs::Permissions::from_mode(0o700);
                    fs::set_permissions(&dir_path, permissions)?;
                    debug!("🔒 Set default permissions 0700 on {:?}", dir_path);
                }
            }
        }
    }
    Ok(())
}

/// Extract slots from the package  
fn extract_slots(
    reader: &mut Reader,
    workenv_path: &Path,
) -> Result<(HashMap<usize, PathBuf>, Vec<PathBuf>)> {
    // Re-read metadata inside this function to avoid borrow issues
    debug!("📖 Reading metadata for slot extraction");
    let metadata = match reader.read_metadata() {
        Ok(m) => m.clone(),
        Err(e) => {
            error!("🚨 Failed to read metadata: {}", e);
            return Err(e);
        }
    };
    let mut slot_paths = HashMap::new();
    let mut volatile_paths = Vec::new();

    info!("📤 Extracting {} slots...", metadata.slots.len());
    
    // Print extraction progress to stderr
    use std::io::Write;
    let stderr = std::io::stderr();
    let mut stderr_handle = stderr.lock();

    // Extract slots by index
    for i in 0..metadata.slots.len() {
        let slot = &metadata.slots[i];
        debug!(
            "📦 Extracting slot {}: {} ({} bytes)",
            slot.index, slot.name, slot.size
        );
        
        // Write progress to stderr
        let _ = writeln!(
            stderr_handle,
            "[{}/{}] Extracting {}...",
            i + 1,
            metadata.slots.len(),
            slot.name
        );

        // Determine extraction path
        let extract_path = if let Some(ref extract_to) = slot.extract_to {
            if extract_to == "." || extract_to == "{workenv}" {
                // "." or "{workenv}" means extract to workenv root
                workenv_path.to_path_buf()
            } else if let Some(relative_path) = extract_to.strip_prefix("{workenv}/") {
                // Replace {workenv} placeholder with actual path
                workenv_path.join(relative_path)
            } else {
                // Use as-is (relative path)
                workenv_path.join(extract_to)
            }
        } else {
            workenv_path.join(&slot.name)
        };

        // Check if this is a single file (not a tarball)
        // Per PSPF spec: encoding "gzip" means single gzipped file, not a tarball
        // The extract_to path for single files is the full file path, not a directory
        let is_single_file =
            slot.extract_to.is_some() && slot.encoding == "gzip" && !slot.name.ends_with(".tar.gz");

        if is_single_file {
            // For single files, create parent directory only
            if let Some(parent) = extract_path.parent() {
                fs::create_dir_all(parent)?;
            }
        } else {
            // For tarballs, create the extraction directory
            fs::create_dir_all(&extract_path)?;
        }

        // Extract the slot (reader should handle the actual extraction)
        reader.extract_slot(i, &extract_path)?;

        debug!("✅ Extracted to: {extract_path:?}");

        // Track volatile slots for later cleanup
        if slot.lifecycle == "volatile" {
            debug!("📌 Marking slot {} as volatile for cleanup", slot.index);
            volatile_paths.push(extract_path.clone());
        }

        slot_paths.insert(i, extract_path);
    }

    Ok((slot_paths, volatile_paths))
}

/// Build slot paths without extraction (when cache is valid)
fn build_slot_paths(metadata: &Metadata, workenv_path: &Path) -> HashMap<usize, PathBuf> {
    let mut slot_paths = HashMap::new();

    for slot in &metadata.slots {
        let slot_path = if let Some(ref extract_to) = slot.extract_to {
            if extract_to == "." || extract_to == "{workenv}" {
                // "." or "{workenv}" means extract to workenv root
                workenv_path.to_path_buf()
            } else if let Some(relative_path) = extract_to.strip_prefix("{workenv}/") {
                // Replace {workenv} placeholder with actual path
                workenv_path.join(relative_path)
            } else {
                // Use as-is (relative path)
                workenv_path.join(extract_to)
            }
        } else {
            workenv_path.join(&slot.name)
        };
        slot_paths.insert(slot.index, slot_path);
    }

    slot_paths
}

/// Prepare the command to execute
fn prepare_command(
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

    // Combine command args with user args
    let mut all_args = command_parts;
    all_args.extend_from_slice(args);

    // Prepare environment
    let mut env_map: HashMap<String, String> = env::vars().collect();

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
                env_map.insert(key.clone(), expanded_value);
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

/// Launch a PSPF/2025 package
pub fn launch(package_path: &Path, args: &[String], options: LaunchOptions) -> Result<i32> {
    info!("PSPF Rust Launcher starting...");
    debug!("🦀 Rust launcher starting");
    debug!("📖 Reading PSPF bundle");

    // Create reader for the bundle
    let mut reader = Reader::new(package_path)?;
    
    // Read index for checksum validation
    let index = reader.read_index()?.clone();

    // Verify integrity unless explicitly skipped
    if !options.insecure {
        debug!("🔍 Verifying package integrity");
        // Call verifier
        let verify_result = super::verifier::verify(package_path)?;
        if !verify_result.signature_valid {
            return Err(FlavorError::Generic(
                "Package signature verification failed".to_string(),
            ));
        }
    } else {
        warn!("⚠️ INSECURE MODE: Skipping integrity verification");
    }

    // Read metadata and clone to avoid borrow issues
    let metadata = reader.read_metadata()?.clone();
    info!(
        "📦 Package: {} v{}",
        metadata.package.name, metadata.package.version
    );

    // Log build timestamps early (always to stderr via logging)
    if let Some(ref build_info) = metadata.build {
        info!(
            "🕐 Package built: {} with {} v{}",
            build_info.timestamp, build_info.tool, build_info.tool_version
        );
    }

    debug!("🎯 Primary slot: {}", metadata.execution.primary_slot);
    debug!("🔧 Command: {}", metadata.execution.command);

    // Get work environment paths
    let paths = if let Ok(custom_workenv) = env::var("FLAVOR_WORKENV") {
        // Use custom workenv path from environment variable
        info!(
            "📁 Using custom work environment from FLAVOR_WORKENV: {}",
            custom_workenv
        );
        let cache_dir = PathBuf::from(custom_workenv).parent()
            .and_then(|p| p.parent())
            .map(|p| p.to_path_buf())
            .unwrap_or_else(|| get_cache_dir());
        WorkenvPaths::new(cache_dir, package_path)
    } else if let Some(ref workdir) = options.workdir {
        let cache_dir = PathBuf::from(workdir).parent()
            .and_then(|p| p.parent())
            .map(|p| p.to_path_buf())
            .unwrap_or_else(|| get_cache_dir());
        WorkenvPaths::new(cache_dir, package_path)
    } else {
        get_workenv_paths(package_path)
    };
    
    let workenv_path = paths.workenv();

    // Create the directory if it doesn't exist
    fs::create_dir_all(&workenv_path)?;

    info!("📁 Work environment: {workenv_path:?}");

    // Setup workenv directories if specified
    if let Some(ref workenv_info) = metadata.workenv {
        setup_workenv_directories(&workenv_path, workenv_info)?;
    }

    // Clean up any stale extraction directories from dead processes
    if let Err(e) = cleanup_stale_extractions(&paths) {
        debug!("⚠️ Failed to clean up stale extractions: {}", e);
    }

    // Check work environment validity
    // If FLAVOR_WORKENV_CACHE is set to false, always treat as invalid to force extraction
    let use_cache = env::var("FLAVOR_WORKENV_CACHE")
        .map(|v| v.to_lowercase() != "false" && v != "0")
        .unwrap_or(true);

    let workenv_valid = if !use_cache {
        info!("📦 FLAVOR_WORKENV_CACHE=false, forcing fresh extraction");
        false
    } else {
        debug!("🔍 Checking cache validity");
        match check_workenv_validity_full(&paths, &index, &metadata) {
            Ok(valid) => {
                if valid {
                    info!("✅ Cache is valid, skipping extraction");
                } else {
                    info!("❌ Cache invalid, will extract");
                }
                valid
            }
            Err(e) => {
                // Critical checksum mismatch error
                return Err(e);
            }
        }
    };

    let (_slot_paths, _volatile_paths) = if workenv_valid {
        info!("✅ Work environment is valid, skipping extraction and setup");
        (build_slot_paths(&metadata, &workenv_path), Vec::new())
    } else {
        // Check disk space before extraction
        check_disk_space(&paths, &metadata)?;
        
        // Try to acquire lock for extraction
        let acquired_lock = try_acquire_lock(&paths)?;

        if acquired_lock {
            EXTRACTING.store(true, Ordering::SeqCst);

            // Create temporary extraction directory
            let temp_extract_dir = paths.temp_extraction(std::process::id());
            fs::create_dir_all(&temp_extract_dir)?;
            info!("📁 Created temporary extraction directory: {:?}", temp_extract_dir);

            // Extract slots to temporary directory
            let extraction_result = (|| -> Result<((HashMap<usize, PathBuf>, Vec<PathBuf>), PathBuf)> {
                let (slot_path_map, volatile) = extract_slots(&mut reader, &temp_extract_dir)?;
                Ok(((slot_path_map, volatile), temp_extract_dir.clone()))
            })();

            let ((slot_path_map, volatile), temp_dir) = match extraction_result {
                Ok(result) => result,
                Err(e) => {
                    // Clean up temporary directory on extraction failure
                    error!("❌ Extraction failed, cleaning up temporary directory");
                    if let Err(cleanup_err) = fs::remove_dir_all(&temp_extract_dir) {
                        warn!("⚠️ Failed to clean up temp directory: {}", cleanup_err);
                    }
                    EXTRACTING.store(false, Ordering::SeqCst);
                    release_lock(&paths);
                    return Err(e);
                }
            };

            // Write metadata to package metadata directory directly in cache (not in temp)
            // Use hidden .{workenv}.pspf/package/ structure as a sibling to workenv
            let package_metadata_dir = paths.metadata().join("package");
            fs::create_dir_all(&package_metadata_dir)?;
            let metadata_file = package_metadata_dir.join("psp.json");
            let metadata_json = serde_json::to_string_pretty(&metadata)?;
            fs::write(&metadata_file, metadata_json)?;
            debug!("📝 Wrote metadata to {metadata_file:?}");

            // Run setup commands in temp directory
            if !metadata.setup_commands.is_empty() {
                info!(
                    "🔧 Running {} setup commands...",
                    metadata.setup_commands.len()
                );
                let user_cwd = env::current_dir()?;
                if let Err(e) = execute_setup_commands(
                    &metadata.setup_commands,
                    &temp_dir,
                    &metadata.package,
                    &user_cwd,
                    &metadata.execution.env,
                ) {
                    // Clean up temporary directory on setup failure
                    error!("❌ Setup commands failed, cleaning up temporary directory");
                    if let Err(cleanup_err) = fs::remove_dir_all(&temp_extract_dir) {
                        warn!("⚠️ Failed to clean up temp directory: {}", cleanup_err);
                    }
                    EXTRACTING.store(false, Ordering::SeqCst);
                    release_lock(&paths);
                    return Err(e);
                }
            }

            // Remove volatile files after setup (in temp directory)
            if !volatile.is_empty() {
                info!("🧹 Cleaning up {} volatile slot(s)...", volatile.len());
                for volatile_path in &volatile {
                    if volatile_path.exists() {
                        debug!("🗑️ Removing volatile path: {volatile_path:?}");
                        if volatile_path.is_dir() {
                            if let Err(e) = fs::remove_dir_all(volatile_path) {
                                warn!("Failed to remove volatile directory {volatile_path:?}: {e}");
                            }
                        } else if let Err(e) = fs::remove_file(volatile_path) {
                            warn!("Failed to remove volatile file {volatile_path:?}: {e}");
                        }
                    }
                }
            }

            // Atomically move extracted content from temp to final location
            info!("🔄 Moving extracted content to final location...");
            
            // List all top-level items in temp directory
            let entries = fs::read_dir(&temp_dir)?;
            for entry in entries {
                let entry = entry?;
                let file_name = entry.file_name();
                let source = entry.path();
                let dest = workenv_path.join(&file_name);
                
                // Remove destination if it exists (for overwrite)
                if dest.exists() {
                    if dest.is_dir() {
                        fs::remove_dir_all(&dest)?;
                    } else {
                        fs::remove_file(&dest)?;
                    }
                }
                
                // Move from temp to final location
                debug!("Moving {:?} to {:?}", source, dest);
                if let Err(e) = fs::rename(&source, &dest) {
                    // If rename fails (e.g., cross-filesystem), fall back to copy
                    warn!("Rename failed, falling back to copy: {}", e);
                    if source.is_dir() {
                        // Recursive copy for directories
                        copy_dir_all(&source, &dest)?;
                        fs::remove_dir_all(&source)?;
                    } else {
                        fs::copy(&source, &dest)?;
                        fs::remove_file(&source)?;
                    }
                }
            }
            
            // Fix shebangs in bin directory
            let bin_dir = workenv_path.join("bin");
            if bin_dir.exists() {
                info!("🔧 Fixing shebangs in scripts...");
                if let Err(e) = fix_shebangs(&bin_dir, &temp_extract_dir, &workenv_path) {
                    warn!("⚠️ Failed to fix some shebangs: {}", e);
                }
            }
            
            // Remove the now-empty temp directory
            if let Err(e) = fs::remove_dir_all(&temp_extract_dir) {
                debug!("⚠️ Failed to remove temp directory: {}", e);
            }

            // Save index metadata for inspection
            if let Err(e) = save_index_metadata(&paths, &index) {
                debug!("⚠️ Failed to save index metadata: {}", e);
            }

            // Mark extraction as complete
            mark_extraction_complete(&paths)?;
            EXTRACTING.store(false, Ordering::SeqCst);
            
            // Save package checksum for future cache validation
            if let Err(e) = save_package_checksum(&paths, index.index_checksum) {
                debug!("⚠️ Failed to save package checksum: {}", e);
            }

            // Release the lock
            release_lock(&paths);

            (slot_path_map, volatile)
        } else {
            // Another process is extracting, wait for it
            info!("⏳ Another process is extracting, waiting...");
            wait_for_extraction(&paths, 60)?;

            // Re-check validity
            match check_workenv_validity_full(&paths, &index, &metadata) {
                Ok(valid_after_wait) => {
                    if valid_after_wait {
                        info!("✅ Cache extraction completed by another process");
                        (build_slot_paths(&metadata, &workenv_path), Vec::new())
                    } else {
                        return Err(FlavorError::Generic(
                            "Cache extraction by another process failed validation".to_string(),
                        ));
                    }
                }
                Err(e) => {
                    // Critical checksum mismatch error
                    return Err(e);
                }
            }
        }
    };

    // Prepare command
    let (executable, cmd_args, env_map) =
        prepare_command(&metadata, &workenv_path, package_path, args)?;

    // Get execution mode
    let exec_mode = env::var("FLAVOR_EXEC_MODE").unwrap_or_else(|_| "exec".to_string());
    let use_exec = exec_mode.to_lowercase() != "spawn";

    if use_exec {
        debug!("🔄 Using exec mode - process will be replaced");

        // On Unix, we can replace the current process
        #[cfg(unix)]
        {
            let mut cmd = Command::new(&executable);
            cmd.args(&cmd_args);
            cmd.env_clear(); // Clear inherited environment first
            cmd.envs(&env_map);
            cmd.current_dir(env::current_dir()?);

            // Check if the executable is a script (has a shebang)
            let is_script = if let Ok(file) = fs::File::open(&executable) {
                use std::io::{BufRead, BufReader};
                let reader = BufReader::new(file);
                if let Some(Ok(first_line)) = reader.lines().next() {
                    let has_shebang = first_line.starts_with("#!");
                    debug!("🔍 Checking if executable is script: {} - First line: {:?} - Has shebang: {}", 
                           executable, &first_line[..first_line.len().min(50)], has_shebang);
                    has_shebang
                } else {
                    debug!("🔍 Could not read first line of {}", executable);
                    false
                }
            } else {
                debug!(
                    "⚠️ Could not open executable to check for shebang: {}",
                    executable
                );
                false
            };

            // Only set argv[0] for binary executables, not scripts
            // Scripts with shebangs can fail with permission denied when argv[0] is changed
            if !is_script {
                // Get the binary name for argv[0]
                let binary_name = package_path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .ok_or_else(|| FlavorError::Generic("Invalid package path".to_string()))?;
                // Set argv[0] to the binary name
                cmd.arg0(binary_name);
                info!("🚀 Executing binary: {executable} with argv[0]={binary_name}");
            } else {
                info!("🚀 Executing script: {executable}");
            }

            debug!("🚀 Full command with args: {cmd_args:?}");
            info!("🔄 Replacing process via exec()");

            // This replaces the current process and never returns on success
            let error = cmd.exec();
            return Err(FlavorError::Generic(format!("Failed to exec: {error}")));
        }

        #[cfg(not(unix))]
        {
            // On non-Unix, fall back to spawn mode
            debug!("📝 exec() not available on this platform, using spawn mode");
        }
    }

    // Spawn mode - create child process
    debug!("👶 Using spawn mode - child process");

    let mut cmd = Command::new(&executable);
    cmd.args(&cmd_args);
    cmd.env_clear(); // Clear inherited environment first
    cmd.envs(&env_map);
    cmd.current_dir(env::current_dir()?);

    info!("🚀 Spawning: {executable}");

    let mut child = cmd.spawn()?;

    // Store child PID for signal handling (if needed by binary)
    CHILD_PID.store(child.id(), Ordering::SeqCst);

    // Wait for child to exit
    let status = child.wait()?;

    // Return exit code
    Ok(status.code().unwrap_or(1))
}
