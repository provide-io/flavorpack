// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build !windows
// +build !windows

package format_2025

import (
	"fmt"
	"os"

	"log/slog"
)

// atomicReplace atomically replaces a destination file with a source file.
// On Unix, os.Rename is already atomic, so this is a simple wrapper.
func atomicReplace(sourcePath, destPath string, logger *slog.Logger) error {
	logger.Debug("Performing atomic file replacement",
		"source", sourcePath,
		"dest", destPath)

	if err := os.Rename(sourcePath, destPath); err != nil {
		return fmt.Errorf("failed to rename file: %w", err)
	}

	logger.Info("✅ Atomic file replacement successful",
		"source", sourcePath,
		"dest", destPath)

	return nil
}
