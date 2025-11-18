package format_2025

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/hashicorp/go-hclog"
)

// Global flag for lock acquisition status
var lockAcquired int32

// LockInfo represents lock file information
type LockInfo struct {
	PID int `json:"pid"`
}

// IsProcessRunning checks if a process with given PID is still running
func IsProcessRunning(pid int) bool {
	process, err := os.FindProcess(pid)
	if err != nil {
		return false
	}
	// On Unix, Signal(0) checks if process exists without actually sending a signal
	err = process.Signal(syscall.Signal(0))
	return err == nil
}

// TryAcquireLock attempts to acquire an exclusive lock for cache extraction
// Returns true if lock was acquired, false if cache is already being extracted
func TryAcquireLock(paths *WorkenvPaths, logger hclog.Logger) (bool, error) {
	// Create instance/extract directory if it doesn't exist
	extractDir := paths.Extract()
	if err := os.MkdirAll(extractDir, os.FileMode(DirPerms)); err != nil {
		logger.Debug("Failed to create extract directory", "error", err)
	}

	lockPath := paths.LockFile()
	pid := os.Getpid()

	// Check for stale lock first
	if _, err := os.Stat(lockPath); err == nil {
		logger.Debug("🔍 Lock file exists, checking if it's stale...")

		// Try to read the PID from the lock file
		if data, err := os.ReadFile(lockPath); err == nil {
			contents := strings.TrimSpace(string(data))
			if oldPid, err := strconv.Atoi(contents); err == nil {
				if !IsProcessRunning(oldPid) {
					logger.Info("🧹 Removing stale lock from dead process", "pid", oldPid)
					os.Remove(lockPath)
				} else {
					logger.Debug("🔒 Lock held by active process", "pid", oldPid)
					return false, nil
				}
			} else {
				// Invalid PID in lock file, remove it
				logger.Info("🧹 Removing invalid lock file (couldn't parse PID)")
				os.Remove(lockPath)
			}
		} else {
			// Can't read lock file, try to remove it
			logger.Info("🧹 Removing unreadable lock file")
			os.Remove(lockPath)
		}
	}

	// Try to create lock file exclusively
	file, err := os.OpenFile(lockPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
	if err != nil {
		if os.IsExist(err) {
			logger.Debug("🔒 Lock file exists, another process is extracting")
			return false, nil
		}
		return false, err
	}
	defer file.Close()

	// Write our PID to the lock file
	if _, err := fmt.Fprintf(file, "%d\n", pid); err != nil {
		os.Remove(lockPath)
		return false, err
	}

	logger.Debug("🔒 Acquired extraction lock", "pid", pid)
	atomic.StoreInt32(&lockAcquired, 1)
	return true, nil
}

// ReleaseLock releases the extraction lock
func ReleaseLock(paths *WorkenvPaths, logger hclog.Logger) {
	lockPath := paths.LockFile()
	if err := os.Remove(lockPath); err != nil {
		logger.Debug("⚠️ Failed to remove lock file", "error", err)
	} else {
		logger.Debug("🔓 Released extraction lock")
	}
	atomic.StoreInt32(&lockAcquired, 0)
}

// WaitForExtraction waits for another process to finish extraction
func WaitForExtraction(paths *WorkenvPaths, timeoutSecs int, logger hclog.Logger) error {
	lockPath := paths.LockFile()
	maxAttempts := timeoutSecs * 10 // Check every 100ms

	for attempt := 0; attempt < maxAttempts; attempt++ {
		if _, err := os.Stat(lockPath); os.IsNotExist(err) {
			logger.Debug("✅ Extraction lock released, cache should be ready")
			// Give a bit more time for files to be fully written
			time.Sleep(100 * time.Millisecond)
			return nil
		}

		if attempt%10 == 0 {
			logger.Debug("⏳ Waiting for extraction to complete...",
				"elapsed", fmt.Sprintf("%d/%ds", attempt/10, timeoutSecs))
		}

		time.Sleep(100 * time.Millisecond)
	}

	return fmt.Errorf("timeout waiting for cache extraction to complete")
}

// MarkExtractionComplete marks cache extraction as complete
func MarkExtractionComplete(paths *WorkenvPaths, logger hclog.Logger) error {
	extractDir := paths.Extract()
	if err := os.MkdirAll(extractDir, os.FileMode(DirPerms)); err != nil {
		return err
	}
	markerPath := paths.CompleteFile()
	file, err := os.Create(markerPath)
	if err != nil {
		return err
	}
	defer file.Close()

	if _, err := fmt.Fprintf(file, "%d\n", os.Getpid()); err != nil {
		return err
	}
	logger.Debug("✅ Marked extraction as complete")
	return nil
}

// IsExtractionComplete checks if cache extraction is complete
func IsExtractionComplete(paths *WorkenvPaths) bool {
	_, err := os.Stat(paths.CompleteFile())
	return err == nil
}

// MarkExtractionIncomplete marks cache as incomplete (used during signal handling)
func MarkExtractionIncomplete(paths *WorkenvPaths, logger hclog.Logger) {
	extractDir := paths.Extract()
	os.MkdirAll(extractDir, os.FileMode(DirPerms))
	// Remove the complete marker if it exists
	os.Remove(paths.CompleteFile())
	logger.Debug("⚠️ Marked extraction as incomplete")
}

// IsLockAcquired checks if lock is currently acquired
func IsLockAcquired() bool {
	return atomic.LoadInt32(&lockAcquired) != 0
}

// CleanupStaleExtractions cleans up stale extraction directories from dead processes
func CleanupStaleExtractions(paths *WorkenvPaths, logger hclog.Logger) error {
	tmpDir := paths.Tmp()

	// If the directory doesn't exist, nothing to clean
	if _, err := os.Stat(tmpDir); os.IsNotExist(err) {
		return nil
	}

	// List all directories in tmp/
	entries, err := os.ReadDir(tmpDir)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		if entry.IsDir() {
			// Try to parse PID from directory name
			if pid, err := strconv.Atoi(entry.Name()); err == nil {
				// Check if process is still running
				if !IsProcessRunning(pid) {
					staleDir := filepath.Join(tmpDir, entry.Name())
					logger.Info("🧹 Cleaning up stale extraction directory from dead process", "pid", pid)
					if err := os.RemoveAll(staleDir); err != nil {
						logger.Debug("⚠️ Failed to remove stale directory", "path", staleDir, "error", err)
					}
				}
			}
		}
	}

	return nil
}
