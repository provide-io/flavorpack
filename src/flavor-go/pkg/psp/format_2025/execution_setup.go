// SPDX-License-Identifier: Apache-2.0
// Package format_2025 implements PSPF/2025 package format support
package format_2025

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/hashicorp/go-hclog"
)

// readAndVerifyMetadata reads package metadata and performs integrity verification.
func readAndVerifyMetadata(reader *Reader, logger hclog.Logger) (*Metadata, error) {
	validationLevel := getValidationLevel()

	switch validationLevel {
	case ValidationNone:
		fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Skipping all integrity verification (FLAVOR_VALIDATION=none)\n")
		fmt.Fprintf(os.Stderr, "⚠️ This is NOT RECOMMENDED for production use\n")
		logger.Warn("⚠️ VALIDATION DISABLED: Skipping integrity verification", "level", validationLevel)
	default:
		logger.Debug("🔍 Verifying package integrity", "level", validationLevel)
		if err := verifyPackageIntegrity(reader, validationLevel, logger); err != nil {
			return nil, err
		}
	}

	metadata, err := reader.ReadMetadata()
	if err != nil {
		logger.Error("❌ Failed to read metadata", "error", err)
		return nil, fmt.Errorf("failed to read metadata: %w", err)
	}

	logger.Info("📦 Package", "name", metadata.Package.Name, "version", metadata.Package.Version)
	logger.Debug("🎯 Primary slot", "slot", metadata.Execution.PrimarySlot)
	logger.Debug("🔧 Command", "command", metadata.Execution.Command)

	return metadata, nil
}

// verifyPackageIntegrity performs package integrity verification based on validation level.
func verifyPackageIntegrity(reader *Reader, level ValidationLevel, logger hclog.Logger) error {
	valid, err := reader.VerifyIntegritySeal()
	if err != nil {
		switch level {
		case ValidationMinimal, ValidationRelaxed:
			fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Failed to verify integrity seal: %v\n", err)
			fmt.Fprintf(os.Stderr, "⚠️ Continuing due to validation level: %v\n", level)
			logger.Warn("⚠️ Failed to verify integrity seal, continuing", "error", err, "level", level)
			return nil
		default: // ValidationStrict, ValidationStandard
			logger.Error("❌ Failed to verify integrity seal", "error", err)
			return fmt.Errorf("failed to verify integrity seal: %w", err)
		}
	}

	if !valid {
		switch level {
		case ValidationMinimal, ValidationRelaxed:
			fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Package integrity verification failed\n")
			fmt.Fprintf(os.Stderr, "⚠️ Package may be corrupted or tampered with\n")
			fmt.Fprintf(os.Stderr, "⚠️ Continuing due to validation level: %v\n", level)
			logger.Warn("⚠️ Package integrity verification failed, continuing", "level", level)
		case ValidationStandard:
			fmt.Fprintf(os.Stderr, "🚨 SECURITY WARNING: Package integrity verification failed\n")
			fmt.Fprintf(os.Stderr, "🚨 Package may be corrupted or tampered with\n")
			fmt.Fprintf(os.Stderr, "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)\n")
			logger.Warn("⚠️ Package integrity verification failed, continuing with standard validation")
		default: // ValidationStrict
			logger.Error("❌ Package integrity verification failed")
			return errors.New("package integrity verification failed")
		}
	} else {
		logger.Debug("✅ Package integrity verified")
	}

	return nil
}

// setupWorkenvDirectories creates and configures workenv directories from metadata.
func setupWorkenvDirectories(workenvDir string, metadata *Metadata, logger hclog.Logger) error {
	if metadata.Workenv == nil || metadata.Workenv.Directories == nil {
		return nil
	}

	for _, dirSpec := range metadata.Workenv.Directories {
		// Substitute {workenv} placeholder in the path
		dirPath := strings.ReplaceAll(dirSpec.Path, "{workenv}", workenvDir)
		logger.Debug("📁 Creating directory", "path", dirPath)
		if err := os.MkdirAll(dirPath, os.FileMode(DirPerms)); err != nil {
			logger.Error("❌ Failed to create directory", "path", dirPath, "error", err)
			return fmt.Errorf("failed to create directory %s: %w", dirPath, err)
		}

		// Set permissions if specified
		if dirSpec.Mode != "" {
			// Parse octal mode string (e.g., "0700")
			mode, err := strconv.ParseUint(strings.TrimPrefix(dirSpec.Mode, "0"), 8, 32)
			if err == nil {
				if err := os.Chmod(dirPath, os.FileMode(mode)); err != nil {
					logger.Debug("Failed to set permissions", "path", dirPath, "mode", dirSpec.Mode, "error", err)
				} else {
					logger.Debug("🔒 Set permissions", "path", dirPath, "mode", dirSpec.Mode)
				}
			}
		}
	}

	return nil
}

// getWorkenvPaths determines the workenv paths based on environment configuration.
func getWorkenvPaths(exePath string, logger hclog.Logger) *WorkenvPaths {
	if customWorkenv := os.Getenv("FLAVOR_WORKDIR"); customWorkenv != "" {
		logger.Info("📁 Using custom work environment from FLAVOR_WORKDIR", "path", customWorkenv)
		cacheDir := filepath.Dir(filepath.Dir(customWorkenv))
		return NewWorkenvPaths(cacheDir, exePath)
	}

	// Get cache directory (XDG_CACHE_HOME or fallback)
	cacheDir := os.Getenv("XDG_CACHE_HOME")
	if cacheDir == "" {
		homeDir, _ := os.UserHomeDir()
		cacheDir = filepath.Join(homeDir, ".cache")
	}
	cacheDir = filepath.Join(cacheDir, "flavor")
	return NewWorkenvPaths(cacheDir, exePath)
}

// 🌶️📦🖥️🪄
