//go:build windows
// +build windows

package format_2025

import (
	"fmt"
	"time"

	"github.com/hashicorp/go-hclog"
	"golang.org/x/sys/windows"
)

// atomicReplace atomically replaces a destination file with a source file.
// This is used to safely replace the original file with the resource-embedded version.
// Uses MoveFileEx with retry logic to handle Windows file locking.
func atomicReplace(sourcePath, destPath string, logger hclog.Logger) error {
	logger.Debug("Performing atomic file replacement",
		"source", sourcePath,
		"dest", destPath)

	// Convert paths to UTF-16 for Windows API
	fromPtr, err := windows.UTF16PtrFromString(sourcePath)
	if err != nil {
		return fmt.Errorf("failed to convert source path to UTF-16: %w", err)
	}

	toPtr, err := windows.UTF16PtrFromString(destPath)
	if err != nil {
		return fmt.Errorf("failed to convert dest path to UTF-16: %w", err)
	}

	// Use MoveFileEx with REPLACE_EXISTING and WRITE_THROUGH for atomic replacement
	var flags uint32 = windows.MOVEFILE_REPLACE_EXISTING | windows.MOVEFILE_WRITE_THROUGH

	// Retry with exponential backoff
	maxAttempts := 3
	delay := 50 * time.Millisecond

	for attempt := 1; attempt <= maxAttempts; attempt++ {
		err = windows.MoveFileEx(fromPtr, toPtr, flags)
		if err == nil {
			if attempt > 1 {
				logger.Debug("Successfully replaced file atomically after retry", "attempt", attempt)
			}
			logger.Info("✅ Atomic file replacement successful",
				"source", sourcePath,
				"dest", destPath)
			return nil
		}

		if attempt == maxAttempts {
			logger.Error("Failed to replace file atomically after retries",
				"attempts", maxAttempts,
				"error", err)
			return fmt.Errorf("failed after %d attempts (Windows file lock): %w", maxAttempts, err)
		}

		logger.Debug("Retrying atomic file replacement (Windows file lock)",
			"attempt", attempt,
			"next_delay_ms", delay.Milliseconds(),
			"error", err)

		time.Sleep(delay)
		delay *= 2 // Exponential backoff
	}

	return nil
}
