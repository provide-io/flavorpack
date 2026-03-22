// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build windows
// +build windows

package format_2025

import (
	"fmt"
	"os"
	"runtime"
	"time"

	"golang.org/x/sys/windows"
	"log/slog"
)

// atomicReplace atomically replaces a destination file with a source file.
// Defense-in-depth strategy with multiple fallback mechanisms:
// 1. MoveFileEx with progressive delays (handles most cases)
// 2. GC + extended delay (handles ARM64 file locking)
// 3. Delete-then-move fallback (handles persistent locks)
// 4. Verify replacement (ensures operation succeeded)
func atomicReplace(sourcePath, destPath string, logger hclog.Logger) error {
	logger.Debug("Performing atomic file replacement (defense-in-depth)",
		"source", sourcePath,
		"dest", destPath)

	// Strategy 1: MoveFileEx with aggressive retries for ARM64
	err := atomicReplaceWithMoveFileEx(sourcePath, destPath, logger)
	if err == nil {
		return nil
	}

	logger.Warn("MoveFileEx failed, attempting fallback strategies",
		"initial_error", err)

	// Strategy 2: Explicit handle cleanup + longer delays (for ARM64)
	err = atomicReplaceWithHandleCleanup(sourcePath, destPath, logger)
	if err == nil {
		return nil
	}

	logger.Warn("Handle cleanup strategy failed, attempting delete-then-move",
		"error", err)

	// Strategy 3: Delete destination, then move source (most reliable fallback)
	err = atomicReplaceWithDelete(sourcePath, destPath, logger)
	if err == nil {
		return nil
	}

	logger.Error("All atomic replacement strategies failed",
		"source", sourcePath,
		"dest", destPath,
		"error", err)

	return fmt.Errorf("atomic file replacement failed (all strategies exhausted): %w", err)
}

// atomicReplaceWithMoveFileEx uses Windows MoveFileEx API with adaptive delays.
// Optimized for both x86_64 and ARM64 platforms.
func atomicReplaceWithMoveFileEx(sourcePath, destPath string, logger hclog.Logger) error {
	logger.Debug("Strategy 1: MoveFileEx with adaptive retries")

	fromPtr, err := windows.UTF16PtrFromString(sourcePath)
	if err != nil {
		return fmt.Errorf("failed to convert source path: %w", err)
	}

	toPtr, err := windows.UTF16PtrFromString(destPath)
	if err != nil {
		return fmt.Errorf("failed to convert dest path: %w", err)
	}

	flags := uint32(windows.MOVEFILE_REPLACE_EXISTING | windows.MOVEFILE_WRITE_THROUGH)

	// Adaptive delays: start longer for ARM64 compatibility
	// Sequence: 100ms, 250ms, 500ms, 1000ms (total: ~1.85 seconds)
	delays := []time.Duration{
		100 * time.Millisecond,
		250 * time.Millisecond,
		500 * time.Millisecond,
		1000 * time.Millisecond,
	}

	for attempt := 1; attempt <= len(delays); attempt++ {
		err := windows.MoveFileEx(fromPtr, toPtr, flags)
		if err == nil {
			logger.Info("✅ MoveFileEx succeeded",
				"attempt", attempt,
				"delay_ms", delays[attempt-1].Milliseconds())
			return nil
		}

		if attempt == len(delays) {
			return fmt.Errorf("MoveFileEx failed after %d attempts: %w", len(delays), err)
		}

		delay := delays[attempt-1]
		logger.Debug("MoveFileEx retry",
			"attempt", attempt,
			"next_delay_ms", delay.Milliseconds(),
			"error", err)

		time.Sleep(delay)
	}

	return fmt.Errorf("MoveFileEx exhausted all retries")
}

// atomicReplaceWithHandleCleanup forces GC and adds extra delays before MoveFileEx.
// Specifically designed to handle ARM64 file locking issues where handles aren't released quickly.
func atomicReplaceWithHandleCleanup(sourcePath, destPath string, logger hclog.Logger) error {
	logger.Debug("Strategy 2: Force GC + extended delays")

	// Force garbage collection to close any open handles
	runtime.GC()
	logger.Debug("Triggered garbage collection")

	// Extended delay to let Windows release locks
	time.Sleep(500 * time.Millisecond)

	fromPtr, err := windows.UTF16PtrFromString(sourcePath)
	if err != nil {
		return fmt.Errorf("failed to convert source path: %w", err)
	}

	toPtr, err := windows.UTF16PtrFromString(destPath)
	if err != nil {
		return fmt.Errorf("failed to convert dest path: %w", err)
	}

	flags := uint32(windows.MOVEFILE_REPLACE_EXISTING | windows.MOVEFILE_WRITE_THROUGH)

	// Additional retries with very long delays
	longDelays := []time.Duration{
		1000 * time.Millisecond,
		2000 * time.Millisecond,
		3000 * time.Millisecond,
	}

	for attempt := 1; attempt <= len(longDelays); attempt++ {
		// More GC between attempts
		runtime.GC()

		err := windows.MoveFileEx(fromPtr, toPtr, flags)
		if err == nil {
			logger.Info("✅ MoveFileEx succeeded after GC",
				"attempt", attempt,
				"delay_ms", longDelays[attempt-1].Milliseconds())
			return nil
		}

		if attempt == len(longDelays) {
			return fmt.Errorf("MoveFileEx failed after GC strategy: %w", err)
		}

		delay := longDelays[attempt-1]
		logger.Debug("MoveFileEx retry (post-GC)",
			"attempt", attempt,
			"next_delay_ms", delay.Milliseconds(),
			"error", err)

		time.Sleep(delay)
	}

	return fmt.Errorf("Handle cleanup strategy exhausted")
}

// atomicReplaceWithDelete is the ultimate fallback: delete the destination,
// then move the source. Less atomic but more reliable for persistent locks.
func atomicReplaceWithDelete(sourcePath, destPath string, logger hclog.Logger) error {
	logger.Debug("Strategy 3: Delete-then-move fallback")

	// 1. Create backup of original (for recovery)
	backupPath := destPath + ".backup"
	if _, err := os.Stat(destPath); err == nil {
		logger.Debug("Creating backup of original file", "backup_path", backupPath)
		if err := os.Rename(destPath, backupPath); err != nil {
			logger.Warn("Failed to create backup (continuing anyway)", "error", err)
			// Don't return - we'll try without backup
		} else {
			defer func() {
				// Clean up backup if operation succeeds
				if err := os.Remove(backupPath); err != nil {
					logger.Debug("Failed to remove backup after success", "error", err)
				}
			}()
		}
	}

	// 2. Wait a moment before move
	time.Sleep(500 * time.Millisecond)

	// 3. Move source to destination
	logger.Debug("Moving source to destination")
	if err := os.Rename(sourcePath, destPath); err != nil {
		logger.Error("Failed to move source to destination", "error", err)

		// Try to restore backup if move failed
		if _, err := os.Stat(backupPath); err == nil {
			logger.Warn("Attempting to restore backup after failed move")
			if restoreErr := os.Rename(backupPath, destPath); restoreErr != nil {
				logger.Error("Failed to restore backup", "error", restoreErr)
				return fmt.Errorf("move failed and backup restore failed: move=%w, restore=%w", err, restoreErr)
			}
		}

		return fmt.Errorf("delete-then-move failed: %w", err)
	}

	// 4. Verify the replacement succeeded
	logger.Debug("Verifying file replacement")
	if _, err := os.Stat(destPath); err != nil {
		return fmt.Errorf("file replacement verification failed: %w", err)
	}

	logger.Info("✅ Delete-then-move succeeded with verification")
	return nil
}
