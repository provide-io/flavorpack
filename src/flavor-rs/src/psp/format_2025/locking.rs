//! Lock file management for concurrent execution safety

use crate::exceptions::{FlavorError, Result};
use log::{debug, info};
use std::fs;
use std::io::Write;
use std::sync::atomic::{AtomicBool, Ordering};

use super::paths::WorkenvPaths;

/// Global flag for lock acquisition status
static LOCK_ACQUIRED: AtomicBool = AtomicBool::new(false);

/// Check if a process with given PID is still running.
/// Uses `kill -0` on Unix (works on both Linux and macOS, unlike /proc)
/// and `tasklist` on Windows.
#[cfg(unix)]
pub fn is_process_running(pid: u32) -> bool {
    std::process::Command::new("kill")
        .args(["-0", &pid.to_string()])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

#[cfg(windows)]
pub fn is_process_running(pid: u32) -> bool {
    std::process::Command::new("tasklist")
        .args(["/FI", &format!("PID eq {}", pid), "/NH"])
        .output()
        .map(|output| {
            let stdout = String::from_utf8_lossy(&output.stdout);
            stdout.contains(&pid.to_string())
        })
        .unwrap_or(false)
}

#[cfg(not(any(unix, windows)))]
pub fn is_process_running(_pid: u32) -> bool {
    // On other platforms, conservatively assume process is not running
    false
}

/// Try to acquire an exclusive lock for cache extraction
/// Returns true if lock was acquired, false if cache is already being extracted
pub fn try_acquire_lock(paths: &WorkenvPaths) -> Result<bool> {
    // Create instance/extract directory if it doesn't exist
    let extract_dir = paths.extract();
    if let Err(e) = fs::create_dir_all(&extract_dir) {
        debug!("Failed to create extract directory: {}", e);
    }

    let lock_path = paths.lock_file();
    let pid = std::process::id();

    // Check for stale lock first
    if lock_path.exists() {
        debug!("🔍 Lock file exists, checking if it's stale...");

        // Try to read the PID from the lock file
        if let Ok(contents) = fs::read_to_string(&lock_path) {
            if let Ok(old_pid) = contents.trim().parse::<u32>() {
                if is_process_running(old_pid) {
                    debug!("🔒 Lock held by active process (PID: {old_pid})");
                    return Ok(false);
                } else {
                    info!("🧹 Removing stale lock from dead process (PID: {old_pid})");
                    fs::remove_file(&lock_path)?;
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
            writeln!(file, "{pid}")?;
            debug!("🔒 Acquired extraction lock (PID: {pid})");
            LOCK_ACQUIRED.store(true, Ordering::SeqCst);
            Ok(true)
        }
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
            debug!("🔒 Lock file exists, another process is extracting");
            Ok(false)
        }
        Err(e) => Err(e.into()),
    }
}

/// Release the extraction lock
pub fn release_lock(paths: &WorkenvPaths) {
    let lock_path = paths.lock_file();
    if let Err(e) = fs::remove_file(&lock_path) {
        debug!("⚠️ Failed to remove lock file: {e}");
    } else {
        debug!("🔓 Released extraction lock");
    }
    LOCK_ACQUIRED.store(false, Ordering::SeqCst);
}

/// Wait for another process to finish extraction
pub fn wait_for_extraction(paths: &WorkenvPaths, timeout_secs: u64) -> Result<()> {
    use std::thread;
    use std::time::Duration;

    let lock_path = paths.lock_file();
    if !lock_path.exists() {
        debug!("✅ Extraction lock released, cache should be ready");
        thread::sleep(Duration::from_millis(100));
        return Ok(());
    }

    let max_attempts = timeout_secs * 10; // Check every 100ms

    for attempt in 0..max_attempts {
        if !lock_path.exists() {
            debug!("✅ Extraction lock released, cache should be ready");
            // Give a bit more time for files to be fully written
            thread::sleep(Duration::from_millis(100));
            return Ok(());
        }

        if attempt % 10 == 0 {
            debug!(
                "⏳ Waiting for extraction to complete... ({}/{}s)",
                attempt / 10,
                timeout_secs
            );
        }

        thread::sleep(Duration::from_millis(100));
    }

    Err(FlavorError::Generic(
        "Timeout waiting for cache extraction to complete".to_string(),
    ))
}

/// Mark cache extraction as complete
pub fn mark_extraction_complete(paths: &WorkenvPaths) -> Result<()> {
    let extract_dir = paths.extract();
    fs::create_dir_all(&extract_dir)?;
    let marker_path = paths.complete_file();
    let mut file = fs::File::create(&marker_path)?;
    writeln!(file, "{}", std::process::id())?;
    debug!("✅ Marked extraction as complete");
    Ok(())
}

/// Check if cache extraction is complete
pub fn is_extraction_complete(paths: &WorkenvPaths) -> bool {
    paths.complete_file().exists()
}

/// Mark cache as incomplete (used during signal handling)
pub fn mark_extraction_incomplete(paths: &WorkenvPaths) {
    let extract_dir = paths.extract();
    let _ = fs::create_dir_all(&extract_dir);
    // Note: We don't have an INCOMPLETE_FILE constant in the metadata architecture
    // This function might not be needed with atomic operations
    debug!("⚠️ Marked extraction as incomplete");
    // Remove the complete marker if it exists
    let _ = fs::remove_file(paths.complete_file());
}

/// Check if lock is currently acquired
pub fn is_lock_acquired() -> bool {
    LOCK_ACQUIRED.load(Ordering::SeqCst)
}

/// Clean up stale extraction directories from dead processes
pub fn cleanup_stale_extractions(paths: &WorkenvPaths) -> Result<()> {
    let tmp_dir = paths.tmp();

    // If the directory doesn't exist, nothing to clean
    if !tmp_dir.exists() {
        return Ok(());
    }

    // List all directories in tmp/
    if let Ok(entries) = fs::read_dir(&tmp_dir) {
        for entry in entries.flatten() {
            if let Ok(file_name) = entry.file_name().into_string() {
                // Try to parse PID from directory name
                if let Ok(pid) = file_name.parse::<u32>() {
                    // Check if process is still running
                    if !is_process_running(pid) {
                        let stale_dir = entry.path();
                        info!(
                            "🧹 Cleaning up stale extraction directory from dead process (PID: {})",
                            pid
                        );
                        if let Err(e) = fs::remove_dir_all(&stale_dir) {
                            debug!("⚠️ Failed to remove stale directory {:?}: {}", stale_dir, e);
                        }
                    }
                }
            }
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;
    use tempfile::tempdir;

    #[test]
    fn wait_for_extraction_returns_ok_when_no_lock_exists_even_with_zero_timeout() {
        let temp = tempdir().expect("tempdir");
        let package = PathBuf::from("bundle.psp");
        let paths = WorkenvPaths::new(temp.path().to_path_buf(), package.as_path());

        assert!(wait_for_extraction(&paths, 0).is_ok());
    }

    #[test]
    fn try_acquire_lock_handles_invalid_lock_content() {
        let temp = tempdir().expect("tempdir");
        let package = PathBuf::from("bundle.psp");
        let paths = WorkenvPaths::new(temp.path().to_path_buf(), package.as_path());
        let lock_path = paths.lock_file();
        fs::create_dir_all(lock_path.parent().expect("lock parent")).expect("create lock parent");
        fs::write(&lock_path, "not-a-pid\n").expect("write invalid lock");

        assert!(try_acquire_lock(&paths).expect("lock acquisition"));
        assert!(is_lock_acquired());
        release_lock(&paths);
        assert!(!is_lock_acquired());
    }

    #[test]
    fn mark_extraction_complete_round_trips_marker_state() {
        let temp = tempdir().expect("tempdir");
        let package = PathBuf::from("bundle.psp");
        let paths = WorkenvPaths::new(temp.path().to_path_buf(), package.as_path());

        assert!(!is_extraction_complete(&paths));
        mark_extraction_complete(&paths).expect("mark complete");
        assert!(is_extraction_complete(&paths));
        mark_extraction_incomplete(&paths);
        assert!(!is_extraction_complete(&paths));
    }

    #[test]
    fn cleanup_stale_extractions_removes_dead_pid_directories() {
        let temp = tempdir().expect("tempdir");
        let package = PathBuf::from("bundle.psp");
        let paths = WorkenvPaths::new(temp.path().to_path_buf(), package.as_path());
        let stale_dir = paths.tmp().join("4294967295");
        let active_dir = paths.tmp().join("not-a-pid");

        fs::create_dir_all(&stale_dir).expect("create stale dir");
        fs::create_dir_all(&active_dir).expect("create active dir");

        cleanup_stale_extractions(&paths).expect("cleanup stale extractions");

        assert!(!stale_dir.exists());
        assert!(active_dir.exists());
    }
}
