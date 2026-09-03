// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/provide-io/flavor/go/flavor/internal/workenv"
)

// resolveWorkenvPaths decides where this package extracts to and creates the
// root directory. FLAVOR_WORKENV names the workenv directly; its cache root is
// two levels up, because NewWorkenvPaths derives the rest of the layout.
func resolveWorkenvPaths(exePath string, logger *slog.Logger) (*WorkenvPaths, string, error) {
	var paths *WorkenvPaths
	if customWorkenv := os.Getenv(EnvWorkenv); customWorkenv != "" {
		logger.Info("📁 Using custom work environment from FLAVOR_WORKENV", "path", customWorkenv)
		cacheDir := filepath.Dir(filepath.Dir(customWorkenv))
		paths = NewWorkenvPaths(cacheDir, exePath)
	} else {
		// workenv.GetCacheRoot keeps the location consistent across platforms.
		paths = NewWorkenvPaths(workenv.GetCacheRoot(), exePath)
	}

	workenvDir := paths.Workenv()
	if err := mkdirAllValidated(workenvDir, os.FileMode(DirPerms)); err != nil {
		logger.Error("❌ Failed to create work environment directory", "error", err)
		return nil, "", fmt.Errorf("failed to create work environment directory: %w", err)
	}
	logger.Info("📁 Work environment", "path", workenvDir)

	return paths, workenvDir, nil
}

// createWorkenvDirectory creates one directory the metadata asked for, after
// checking the substituted path has not escaped the work environment.
//
// A mode that will not parse, or will not apply, is logged and not fatal: the
// directory exists, which is what the package needs.
func createWorkenvDirectory(dirSpec DirectorySpec, workenvDir string, logger *slog.Logger) error {
	dirPath := strings.ReplaceAll(dirSpec.Path, "{workenv}", workenvDir)

	if err := ensurePathWithinWorkenv(dirPath, workenvDir, dirSpec.Path); err != nil {
		return fmt.Errorf("directory path %q escapes work environment directory", dirSpec.Path)
	}

	logger.Debug("📁 Creating directory", "path", dirPath)
	if err := mkdirAllValidated(dirPath, os.FileMode(DirPerms)); err != nil {
		logger.Error("❌ Failed to create directory", "path", dirPath, "error", err)
		return fmt.Errorf("failed to create directory %s: %w", dirPath, err)
	}

	if dirSpec.Mode == "" {
		return nil
	}

	mode, err := strconv.ParseUint(strings.TrimPrefix(dirSpec.Mode, "0"), 8, 32)
	if err != nil {
		return nil
	}
	if err := chmodValidatedFn(dirPath, os.FileMode(mode)); err != nil {
		logger.Debug("Failed to set permissions", "path", dirPath, "mode", dirSpec.Mode, "error", err)
	} else {
		logger.Debug("🔒 Set permissions", "path", dirPath, "mode", dirSpec.Mode)
	}

	return nil
}

// createWorkenvDirectories creates every directory the metadata declares.
func createWorkenvDirectories(metadata *Metadata, workenvDir string, logger *slog.Logger) error {
	if metadata.Workenv == nil || metadata.Workenv.Directories == nil {
		return nil
	}
	for _, dirSpec := range metadata.Workenv.Directories {
		if err := createWorkenvDirectory(dirSpec, workenvDir, logger); err != nil {
			return err
		}
	}
	return nil
}

// workenvSlotPaths maps every slot to the work environment root, which is
// where a validated extraction has already placed its contents.
func workenvSlotPaths(metadata *Metadata, paths *WorkenvPaths) map[int]string {
	slotPaths := make(map[int]string, len(metadata.Slots))
	for _, slot := range metadata.Slots {
		slotPaths[slot.Slot] = paths.Workenv()
	}
	return slotPaths
}
