//go:build !windows
// +build !windows

package format_2025

import (
	"fmt"
	"os"

	"github.com/hashicorp/go-hclog"
)

// atomicReplace atomically replaces a destination file with a source file.
// On Unix, os.Rename is already atomic, so this is a simple wrapper.
func atomicReplace(sourcePath, destPath string, logger hclog.Logger) error {
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
