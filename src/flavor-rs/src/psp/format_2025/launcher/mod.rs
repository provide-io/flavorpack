//! PSPF/2025 package launcher

pub mod command;
mod extraction;
mod filesystem;
mod workenv;

use command::prepare_command;
use extraction::{build_slot_paths, extract_slots};
use filesystem::{copy_dir_all, fix_shebangs};
use workenv::{check_disk_space, get_workenv_paths, setup_workenv_directories};

use crate::api::LaunchOptions;
use crate::exceptions::{FlavorError, Result};
use crate::utils::get_cache_dir;
use log::{debug, error, info, trace, warn};
use std::env;
use std::fs;
#[cfg(unix)]
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};

use super::execution::{
    check_workenv_validity_full, execute_setup_commands, save_index_metadata, save_package_checksum,
};
use super::locking::{
    cleanup_stale_extractions, mark_extraction_complete, release_lock, try_acquire_lock,
    wait_for_extraction,
};
use super::paths::WorkenvPaths;
use super::reader::Reader;

// Use CHILD_PID from lib.rs
use crate::CHILD_PID;
static EXTRACTING: AtomicBool = AtomicBool::new(false);

fn cache_enabled_from_env(value: Option<String>) -> bool {
    value
        .map(|v| {
            let lowered = v.to_lowercase();
            lowered != "false" && lowered != "0"
        })
        .unwrap_or(true)
}

fn cache_dir_from_hint(hint: &str) -> PathBuf {
    PathBuf::from(hint)
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
        .unwrap_or_else(get_cache_dir)
}

fn select_workenv_paths(
    package_path: &Path,
    custom_workenv: Option<&str>,
    workdir: Option<&str>,
) -> WorkenvPaths {
    if let Some(custom_workenv) = custom_workenv {
        WorkenvPaths::new(cache_dir_from_hint(custom_workenv), package_path)
    } else if let Some(workdir) = workdir {
        WorkenvPaths::new(cache_dir_from_hint(workdir), package_path)
    } else {
        get_workenv_paths(package_path)
    }
}

// Type alias for extraction result to reduce complexity
type SlotPaths = std::collections::HashMap<usize, PathBuf>;
type ExtractionResult = ((SlotPaths, Vec<PathBuf>), PathBuf);

#[cfg(unix)]
fn executable_is_script(executable: &Path) -> bool {
    if let Ok(file) = fs::File::open(executable) {
        use std::io::{BufRead, BufReader};

        let reader = BufReader::new(file);
        if let Some(Ok(first_line)) = reader.lines().next() {
            let has_shebang = first_line.starts_with("#!");
            debug!(
                "🔍 Checking if executable is script: {} - First line: {:?} - Has shebang: {}",
                executable.display(),
                &first_line[..first_line.len().min(50)],
                has_shebang
            );
            return has_shebang;
        }

        debug!("🔍 Could not read first line of {}", executable.display());
        false
    } else {
        debug!(
            "⚠️ Could not open executable to check for shebang: {}",
            executable.display()
        );
        false
    }
}

/// Launch a PSPF/2025 package
///
/// # Errors
///
/// Returns an error if:
/// - The package cannot be read or is invalid
/// - Signature verification fails (in strict mode)
/// - Extraction fails
/// - Command execution fails
#[allow(clippy::cognitive_complexity)]
pub fn launch(package_path: &Path, args: &[String], options: LaunchOptions) -> Result<i32> {
    info!("🦀🦀🦀 Hello from Flavor's Rust Launcher 🦀🦀🦀");
    info!("PSPF Rust Launcher starting...");
    debug!("📖 Reading PSPF bundle");

    // Log environment variables at trace level
    trace!(
        "🔧 Environment variables: {} total",
        std::env::vars().count()
    );
    for (key, value) in std::env::vars() {
        if key.starts_with("FLAVOR_") {
            trace!("📝 Environment variable: {}={}", key, value);
        }
    }

    // Create reader for the bundle
    let mut reader = Reader::new(package_path)?;

    // Read index for checksum validation
    let index = reader.read_index()?.clone();

    // Verify integrity based on validation level
    use crate::psp::format_2025::defaults::{ValidationLevel, get_validation_level};

    let validation_level = get_validation_level();
    if matches!(validation_level, ValidationLevel::None) {
        eprintln!(
            "⚠️ SECURITY WARNING: Skipping all integrity verification (FLAVOR_VALIDATION=none)"
        );
        eprintln!("⚠️ This is NOT RECOMMENDED for production use");
        warn!("⚠️ VALIDATION DISABLED: Skipping integrity verification");
    } else {
        debug!(
            "🔍 Verifying package integrity (level: {:?})",
            validation_level
        );
        // Call verifier
        let verify_result = super::verifier::verify(package_path)?;
        if verify_result.valid {
            debug!("✅ Package integrity verified");
        } else if matches!(
            validation_level,
            ValidationLevel::Minimal | ValidationLevel::Relaxed
        ) {
            eprintln!("⚠️ SECURITY WARNING: Package signature verification failed");
            eprintln!("⚠️ Package may be corrupted or tampered with");
            eprintln!(
                "⚠️ Continuing due to validation level: {:?}",
                validation_level
            );
            warn!("⚠️ Package signature verification failed, continuing");
        } else if matches!(validation_level, ValidationLevel::Standard) {
            eprintln!("🚨 SECURITY WARNING: Package signature verification failed");
            eprintln!("🚨 Package may be corrupted or tampered with");
            eprintln!(
                "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)"
            );
            warn!("⚠️ Package signature verification failed, continuing with standard validation");
        } else if matches!(validation_level, ValidationLevel::Strict) {
            error!("❌ Package signature verification failed");
            return Err(FlavorError::Generic(
                "Package signature verification failed".to_string(),
            ));
        }
    }

    // Trust store check: verify the package signing key is trusted.
    // key_trusted is false only when the store exists AND the key is explicitly absent.
    let key_trusted = {
        use super::trust;

        let pk = &index.public_key;
        let mut trusted = true;
        if !pk.iter().all(|&b| b == 0) {
            match trust::compute_key_fingerprint(pk) {
                Ok(fp) => match trust::is_key_trusted(&fp, true) {
                    None => {
                        // No trust store exists — backwards-compatible, allow execution
                        debug!("🔑 No trusted-keys store found; skipping trust check");
                    }
                    Some(true) => {
                        debug!("✅ Package signing key is trusted (fp={})", &fp[..16]);
                    }
                    Some(false) => {
                        trusted = false;
                        let msg = format!(
                            "Package signing key is not in the trusted-keys store (fp={})",
                            fp
                        );
                        if matches!(validation_level, ValidationLevel::Strict) {
                            error!("❌ {}", msg);
                            return Err(FlavorError::Generic(msg));
                        } else {
                            eprintln!("flavor: warning: {msg}");
                            warn!("⚠️ {}", msg);
                        }
                    }
                },
                Err(e) => {
                    warn!(
                        "⚠️ Failed to compute key fingerprint for trust check: {}",
                        e
                    );
                }
            }
        }
        trusted
    };

    // Read metadata and clone to avoid borrow issues
    let metadata = reader.read_metadata()?.clone();

    // Policy enforcement: merge package constraints with operator policy
    {
        use crate::psp::format_2025::policy;

        let op_policy = policy::load_operator_policy();
        let pkg_policy = {
            // Deserialise the package-declared policy from the metadata "policy" JSON value.
            // If the key is absent or cannot be parsed, default to a permissive empty policy.
            if let Some(policy_value) = &metadata.policy {
                serde_json::from_value::<policy::PackagePolicy>(policy_value.clone())
                    .unwrap_or_default()
            } else {
                policy::PackagePolicy::default()
            }
        };
        let effective = policy::merge_policy(pkg_policy, op_policy);
        let has_sbom = metadata.slots.iter().any(|s| s.lifecycle == "attestation");
        let build_timestamp = index.build_timestamp;
        if let Err(e) = policy::enforce_policy(&effective, build_timestamp, has_sbom, key_trusted) {
            eprintln!("policy violation: {}", e);
            std::process::exit(1);
        }
        debug!("✅ Policy enforcement passed");
    }
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
    let custom_workenv = env::var(crate::env_vars::WORKENV).ok();
    let paths = select_workenv_paths(
        package_path,
        custom_workenv.as_deref(),
        options.workdir.as_deref(),
    );
    if let Some(ref custom_workenv) = custom_workenv {
        info!(
            "📁 Using custom work environment from FLAVOR_WORKENV: {}",
            custom_workenv
        );
    } else if let Some(ref workdir) = options.workdir {
        info!(
            "📁 Using work environment cache derived from LaunchOptions.workdir: {}",
            workdir
        );
    };

    let workenv_path = paths.workenv();

    // Create the directory if it doesn't exist
    fs::create_dir_all(&workenv_path)?;

    // Set secure permissions on workenv directory
    #[cfg(unix)]
    {
        use crate::psp::format_2025::defaults::DEFAULT_DIR_PERMS;
        use std::os::unix::fs::PermissionsExt;
        let permissions = fs::Permissions::from_mode(DEFAULT_DIR_PERMS as u32);
        fs::set_permissions(&workenv_path, permissions)?;
        debug!(
            "🔒 Set secure permissions {} on workenv directory",
            DEFAULT_DIR_PERMS
        );
    }

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
    let use_cache = cache_enabled_from_env(env::var(crate::env_vars::WORKENV_CACHE).ok());

    let workenv_valid = if use_cache {
        debug!("🔍 Checking cache validity");
        trace!("📂 Checking workenv at: {:?}", workenv_path);
        let checksum = index.index_checksum;
        trace!("📊 Package checksum: {:08x}", checksum);
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
    } else {
        info!("📦 FLAVOR_WORKENV_CACHE=false, forcing fresh extraction");
        false
    };

    let (_slot_paths, _init_paths) = if workenv_valid {
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

            // Set secure permissions on temp extraction directory
            #[cfg(unix)]
            {
                use crate::psp::format_2025::defaults::DEFAULT_DIR_PERMS;
                use std::os::unix::fs::PermissionsExt;
                let permissions = fs::Permissions::from_mode(DEFAULT_DIR_PERMS as u32);
                fs::set_permissions(&temp_extract_dir, permissions)?;
                debug!("🔒 Set secure permissions on temp extraction directory");
            }

            info!(
                "📁 Created temporary extraction directory: {:?}",
                temp_extract_dir
            );
            trace!("🗂️ Extracting to temp before atomic move");

            // Extract slots to temporary directory
            let extraction_result = (|| -> Result<ExtractionResult> {
                let (slot_path_map, init_slots) = extract_slots(&mut reader, &temp_extract_dir)?;
                Ok(((slot_path_map, init_slots), temp_extract_dir.clone()))
            })();

            let ((slot_path_map, init_slots), temp_dir) = match extraction_result {
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

            // Set secure permissions on metadata directory and its parent
            #[cfg(unix)]
            {
                use crate::psp::format_2025::defaults::DEFAULT_DIR_PERMS;
                use std::os::unix::fs::PermissionsExt;
                let permissions = fs::Permissions::from_mode(DEFAULT_DIR_PERMS as u32);
                // Set permissions on both the metadata parent directory and package subdirectory
                let metadata_parent = paths.metadata();
                fs::set_permissions(&metadata_parent, permissions.clone())?;
                fs::set_permissions(&package_metadata_dir, permissions)?;
                debug!("🔒 Set secure permissions on metadata directories");
            }
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

            // Remove init files after setup (in temp directory)
            if !init_slots.is_empty() {
                info!("🧹 Cleaning up {} init slot(s)...", init_slots.len());
                for init_path in &init_slots {
                    if init_path.exists() {
                        debug!("🗑️ Removing init path: {init_path:?}");
                        if init_path.is_dir() {
                            if let Err(e) = fs::remove_dir_all(init_path) {
                                warn!("Failed to remove init directory {init_path:?}: {e}");
                            }
                        } else if let Err(e) = fs::remove_file(init_path) {
                            warn!("Failed to remove init file {init_path:?}: {e}");
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

            (slot_path_map, init_slots)
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
    let exec_mode = env::var(crate::env_vars::EXEC_MODE).unwrap_or_else(|_| "exec".to_string());
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
            let is_script = executable_is_script(Path::new(&executable));

            // Only set argv[0] for binary executables, not scripts
            // Scripts with shebangs can fail with permission denied when argv[0] is changed
            if is_script {
                info!("🚀 Executing script: {executable}");
            } else {
                // Get the binary name for argv[0]
                let binary_name = package_path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .ok_or_else(|| FlavorError::Generic("Invalid package path".to_string()))?;
                // Set argv[0] to the binary name
                cmd.arg0(binary_name);
                info!("🚀 Executing binary: {executable} with argv[0]={binary_name}");
            }

            debug!("🚀 Full command with args: {cmd_args:?}");
            trace!("🔀 Using exec syscall to replace current process");
            trace!("  Binary: {}", executable);
            trace!("  Args: {:?}", cmd_args);
            trace!("  Env vars count computed");
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

#[cfg(test)]
#[allow(unsafe_code)]
mod tests {
    use super::*;
    #[cfg(unix)]
    use crate::api::BuildOptions;
    #[cfg(unix)]
    use crate::psp::format_2025::build;
    #[cfg(unix)]
    use serde_json::json;
    #[cfg(unix)]
    use std::env;
    use std::fs;
    use std::path::PathBuf;
    use tempfile::tempdir;

    #[cfg(unix)]
    fn build_real_bundle(temp: &tempfile::TempDir) -> PathBuf {
        let payload = temp.path().join("payload.txt");
        fs::write(&payload, b"payload contents").expect("write payload");

        let launcher = temp.path().join(if cfg!(windows) {
            "launcher.bat"
        } else {
            "launcher.sh"
        });
        let launcher_bytes = if cfg!(windows) {
            b"@echo off\r\nexit /b 0\r\n".as_slice()
        } else {
            b"#!/bin/sh\nexit 0\n".as_slice()
        };
        fs::write(&launcher, launcher_bytes).expect("write launcher");

        let manifest_path = temp.path().join("manifest.json");
        let output_path = temp.path().join("bundle.pspf");
        let manifest = json!({
            "package": {
                "name": "launcher-mod-demo",
                "version": "1.0.0"
            },
            "execution": {
                "command": if cfg!(windows) { "cmd /C exit 0" } else { "true" },
                "env": {}
            },
            "slots": [
                {
                    "slot": 0,
                    "id": "payload",
                    "source": payload.display().to_string(),
                    "target": "bin/payload.txt",
                    "operations": "",
                    "purpose": "payload",
                    "lifecycle": "runtime",
                    "permissions": "0644"
                }
            ]
        });
        fs::write(
            &manifest_path,
            serde_json::to_vec_pretty(&manifest).expect("serialize manifest"),
        )
        .expect("write manifest");

        let options = BuildOptions {
            launcher_bin: Some(launcher),
            skip_verification: false,
            private_key_path: None,
            public_key_path: None,
            key_seed: Some("launcher-mod-test-seed".to_string()),
            workenv_base: None,
        };

        build(&manifest_path, &output_path, options).expect("build real bundle");
        output_path
    }

    #[cfg(unix)]
    #[test]
    fn executable_is_script_detects_shebang_files() {
        let temp = tempdir().expect("tempdir");
        let script = temp.path().join("tool");
        fs::write(&script, b"#!/usr/bin/env python\nprint('ok')\n").expect("write script");

        assert!(executable_is_script(&script));
    }

    #[cfg(unix)]
    #[test]
    fn executable_is_script_rejects_plain_files() {
        let temp = tempdir().expect("tempdir");
        let binary = temp.path().join("tool");
        fs::write(&binary, b"\x7fELFbinary").expect("write binary");

        assert!(!executable_is_script(&binary));
    }

    #[cfg(unix)]
    #[test]
    fn executable_is_script_rejects_missing_files() {
        let temp = tempdir().expect("tempdir");
        let missing = temp.path().join("missing-tool");

        assert!(!executable_is_script(&missing));
    }

    #[test]
    fn cache_enabled_from_env_parses_falsey_values() {
        assert!(!cache_enabled_from_env(Some("false".to_string())));
        assert!(!cache_enabled_from_env(Some("0".to_string())));
        assert!(!cache_enabled_from_env(Some("FALSE".to_string())));
        assert!(cache_enabled_from_env(Some("true".to_string())));
        assert!(cache_enabled_from_env(None));
    }

    #[test]
    fn select_workenv_paths_prefers_custom_workenv_hint() {
        let package = Path::new("/tmp/example.psp");
        let custom_workenv = "/tmp/custom/cache/workenv/example";
        let workdir = "/tmp/ignored/workenv/example";

        let paths = select_workenv_paths(package, Some(custom_workenv), Some(workdir));

        assert_eq!(
            paths.workenv(),
            PathBuf::from("/tmp/custom/cache/workenv/example")
        );
    }

    #[test]
    fn select_workenv_paths_uses_workdir_then_default_cache_dir() {
        let package = Path::new("/tmp/example.psp");
        let workdir = "/tmp/workdir/cache/workenv/example";

        let from_workdir = select_workenv_paths(package, None, Some(workdir));
        assert_eq!(
            from_workdir.workenv(),
            PathBuf::from("/tmp/workdir/cache/workenv/example")
        );

        let default_paths = select_workenv_paths(package, None, None);
        assert_eq!(default_paths.name(), "example");
    }

    #[test]
    fn select_workenv_paths_falls_back_to_default_cache_dir_for_short_hint() {
        let package = Path::new("/tmp/example.psp");
        let paths = select_workenv_paths(package, Some("workenv"), None);

        assert_eq!(
            paths.workenv(),
            get_cache_dir().join("workenv").join("example")
        );
    }

    #[test]
    fn select_workenv_paths_uses_default_cache_when_hint_is_empty_like() {
        let package = Path::new("/tmp/example.psp");
        let paths = select_workenv_paths(package, Some("cache"), Some("ignored"));

        assert_eq!(
            paths.workenv(),
            get_cache_dir().join("workenv").join("example")
        );
    }

    #[test]
    fn launch_returns_error_for_invalid_bundle() {
        let temp = tempdir().expect("tempdir");
        let package = temp.path().join("bundle.psp");
        fs::write(&package, vec![0u8; 9000]).expect("write invalid bundle");

        let result = launch(&package, &[], LaunchOptions::default());
        assert!(result.is_err());
    }

    #[cfg(unix)]
    #[test]
    fn launch_executes_real_bundle_in_spawn_mode() {
        let temp = tempdir().expect("tempdir");
        let bundle = build_real_bundle(&temp);
        let workdir_hint = temp
            .path()
            .join("cache/workenv/launcher-mod-test")
            .display()
            .to_string();

        let original_exec_mode = env::var(crate::env_vars::EXEC_MODE).ok();
        let original_validation = env::var(crate::env_vars::VALIDATION).ok();
        let original_workenv = env::var(crate::env_vars::WORKENV).ok();

        unsafe {
            env::set_var(crate::env_vars::EXEC_MODE, "spawn");
            env::set_var(crate::env_vars::VALIDATION, "strict");
            env::remove_var(crate::env_vars::WORKENV);
        }

        let options = LaunchOptions {
            workdir: Some(workdir_hint),
        };
        let result = launch(&bundle, &[], options).expect("launch real bundle");
        assert_eq!(result, 0);

        match original_exec_mode {
            Some(value) => unsafe {
                env::set_var(crate::env_vars::EXEC_MODE, value);
            },
            None => unsafe {
                env::remove_var(crate::env_vars::EXEC_MODE);
            },
        }
        match original_validation {
            Some(value) => unsafe {
                env::set_var(crate::env_vars::VALIDATION, value);
            },
            None => unsafe {
                env::remove_var(crate::env_vars::VALIDATION);
            },
        }
        match original_workenv {
            Some(value) => unsafe {
                env::set_var(crate::env_vars::WORKENV, value);
            },
            None => unsafe {
                env::remove_var(crate::env_vars::WORKENV);
            },
        }
    }
}
