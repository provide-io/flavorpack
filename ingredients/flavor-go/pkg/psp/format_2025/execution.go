package format_2025

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"

	"github.com/hashicorp/go-hclog"
)

var (
	ErrExecutionFailed      = errors.New("command execution failed")
	ErrSlotExtractionFailed = errors.New("slot extraction failed")
	ErrMissingSlot          = errors.New("missing slot reference")
	ErrLockAcquisition      = errors.New("failed to acquire lock")
)

// copyFile copies a single file from src to dst
func copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destFile.Close()

	if _, err := io.Copy(destFile, sourceFile); err != nil {
		return err
	}

	// Copy file permissions
	sourceInfo, err := os.Stat(src)
	if err != nil {
		return err
	}
	return os.Chmod(dst, sourceInfo.Mode())
}

// copyDirAll recursively copies a directory tree
func copyDirAll(src, dst string) error {
	sourceInfo, err := os.Stat(src)
	if err != nil {
		return err
	}

	if err := os.MkdirAll(dst, sourceInfo.Mode()); err != nil {
		return err
	}

	entries, err := os.ReadDir(src)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())

		if entry.IsDir() {
			if err := copyDirAll(srcPath, dstPath); err != nil {
				return err
			}
		} else {
			if err := copyFile(srcPath, dstPath); err != nil {
				return err
			}
		}
	}
	return nil
}

// fixShebangs fixes shebang paths in scripts after atomic move
func fixShebangs(binDir, oldPrefix, newPrefix string, logger hclog.Logger) error {
	if _, err := os.Stat(binDir); os.IsNotExist(err) {
		return nil
	}

	entries, err := os.ReadDir(binDir)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		scriptPath := filepath.Join(binDir, entry.Name())

		// Read first few bytes to check for shebang
		file, err := os.Open(scriptPath)
		if err != nil {
			continue
		}

		header := make([]byte, 2)
		if _, err := file.Read(header); err != nil {
			file.Close()
			continue
		}
		file.Close()

		if string(header) != "#!" {
			continue
		}

		// Read entire file
		content, err := os.ReadFile(scriptPath)
		if err != nil {
			continue
		}

		// Find end of first line
		lines := strings.SplitN(string(content), "\n", 2)
		if len(lines) < 1 {
			continue
		}

		firstLine := lines[0]
		if strings.Contains(firstLine, oldPrefix) {
			// Replace old prefix with new prefix in shebang
			newFirstLine := strings.ReplaceAll(firstLine, oldPrefix, newPrefix)

			// Reconstruct content
			var newContent string
			if len(lines) > 1 {
				newContent = newFirstLine + "\n" + lines[1]
			} else {
				newContent = newFirstLine + "\n"
			}

			// Write back the modified content
			if err := os.WriteFile(scriptPath, []byte(newContent), entry.Type().Perm()); err != nil {
				logger.Debug("Failed to fix shebang", "script", entry.Name(), "error", err)
			} else {
				logger.Debug("Fixed shebang", "script", entry.Name())
			}
		}
	}

	return nil
}

// checkDiskSpace verifies there's enough disk space for extraction
func checkDiskSpace(paths *WorkenvPaths, metadata *Metadata, logger hclog.Logger) error {
	// Calculate total size needed (compressed size * DiskSpaceMultiplier for safety)
	var totalSizeNeeded int64
	for _, slot := range metadata.Slots {
		totalSizeNeeded += slot.Size * DiskSpaceMultiplier
	}

	// Get available disk space
	var stat syscall.Statfs_t
	workenvPath := paths.Workenv()
	if err := syscall.Statfs(workenvPath, &stat); err != nil {
		logger.Warn("⚠️ Could not check disk space", "error", err)
		return nil // Don't fail if we can't check
	}

	available := int64(stat.Bavail) * int64(stat.Bsize)

	// Convert to human-readable sizes
	neededGB := float64(totalSizeNeeded) / (1024 * 1024 * 1024)
	availableGB := float64(available) / (1024 * 1024 * 1024)

	logger.Debug("💾 Disk space check", "needed_gb", fmt.Sprintf("%.2f", neededGB), "available_gb", fmt.Sprintf("%.2f", availableGB))

	if available < totalSizeNeeded {
		logger.Error("❌ Insufficient disk space",
			"needed_gb", fmt.Sprintf("%.2f", neededGB),
			"available_gb", fmt.Sprintf("%.2f", availableGB))
		return fmt.Errorf("insufficient disk space: need %.2f GB, have %.2f GB", neededGB, availableGB)
	}

	logger.Debug("✅ Sufficient disk space available")
	return nil
}

// validatePackageChecksum checks if the cached package checksum matches the current package
func validatePackageChecksum(paths *WorkenvPaths, currentChecksum uint32, logger hclog.Logger) (bool, error) {
	checksumPath := paths.ChecksumFile()

	// Read stored checksum
	data, err := os.ReadFile(checksumPath)
	if err != nil {
		if os.IsNotExist(err) {
			logger.Debug("🔍 No cached checksum found")
		} else {
			logger.Debug("⚠️ Failed to read cached checksum", "error", err)
		}
		return false, nil // No checksum file is not an error, just means cache is invalid
	}

	storedChecksum := strings.TrimSpace(string(data))
	currentChecksumStr := fmt.Sprintf("%08x", currentChecksum)

	if storedChecksum == currentChecksumStr {
		logger.Debug("✅ Package checksum matches cached version", "checksum", currentChecksumStr)
		return true, nil
	}

	// Checksum mismatch - this is a potential security issue
	validationLevel := getValidationLevel()
	switch validationLevel {
	case ValidationNone, ValidationMinimal:
		logger.Warn("⚠️ SECURITY WARNING: Package checksum mismatch!", "cached", storedChecksum, "current", currentChecksumStr)
		logger.Warn("⚠️ Cache may be compromised or package has changed")
		logger.Warn("⚠️ Continuing due to validation level", "level", validationLevel)
		return false, nil
	case ValidationRelaxed:
		logger.Warn("⚠️ SECURITY WARNING: Package checksum mismatch!", "cached", storedChecksum, "current", currentChecksumStr)
		logger.Warn("⚠️ Cache may be compromised or package has changed")
		logger.Warn("⚠️ Continuing due to relaxed validation")
		return false, nil
	default: // ValidationStrict, ValidationStandard
		logger.Error("🚨 CRITICAL: Package checksum mismatch!", "cached", storedChecksum, "current", currentChecksumStr)
		logger.Error("🚨 Cache may be compromised or package has changed")
		logger.Error("🚨 Refusing to continue. Set FLAVOR_VALIDATION=relaxed to bypass (NOT RECOMMENDED)")
		return false, fmt.Errorf("package checksum mismatch: cached=%s, current=%s", storedChecksum, currentChecksumStr)
	}
}

// savePackageChecksum saves the package checksum to the cache
func savePackageChecksum(paths *WorkenvPaths, checksum uint32, logger hclog.Logger) error {
	instanceDir := paths.Instance()
	if err := os.MkdirAll(instanceDir, os.FileMode(DirPerms)); err != nil {
		return fmt.Errorf("failed to create instance directory: %w", err)
	}

	checksumPath := paths.ChecksumFile()
	checksumStr := fmt.Sprintf("%08x", checksum)

	if err := os.WriteFile(checksumPath, []byte(checksumStr), 0644); err != nil {
		logger.Debug("⚠️ Failed to save package checksum", "error", err)
		return err
	}

	logger.Debug("💾 Saved package checksum", "checksum", checksumStr)
	return nil
}

// IndexMetadata represents the serializable subset of PSPFIndex for JSON export
type IndexMetadata struct {
	FormatVersion    uint32 `json:"format_version"`
	PackageSize      uint64 `json:"package_size"`
	LauncherSize     uint64 `json:"launcher_size"`
	MetadataOffset   uint64 `json:"metadata_offset"`
	MetadataSize     uint64 `json:"metadata_size"`
	SlotTableOffset  uint64 `json:"slot_table_offset"`
	SlotTableSize    uint64 `json:"slot_table_size"`
	SlotCount        uint32 `json:"slot_count"`
	Flags            uint32 `json:"flags"`
	IndexChecksum    string `json:"index_checksum"`
	MetadataChecksum string `json:"metadata_checksum"`
	BuildTimestamp   uint64 `json:"build_timestamp"`
	PageSize         uint32 `json:"page_size"`
	Capabilities     uint64 `json:"capabilities"`
	Requirements     uint64 `json:"requirements"`
}

// saveIndexMetadata saves index metadata to JSON file for inspection
func saveIndexMetadata(paths *WorkenvPaths, index *PSPFIndex, logger hclog.Logger) error {
	instanceDir := paths.Instance()
	if err := os.MkdirAll(instanceDir, os.FileMode(DirPerms)); err != nil {
		return fmt.Errorf("failed to create instance directory: %w", err)
	}

	// Create a serializable version of the index
	indexMetadata := IndexMetadata{
		FormatVersion:    index.FormatVersion,
		PackageSize:      index.PackageSize,
		LauncherSize:     index.LauncherSize,
		MetadataOffset:   index.MetadataOffset,
		MetadataSize:     index.MetadataSize,
		SlotTableOffset:  index.SlotTableOffset,
		SlotTableSize:    index.SlotTableSize,
		SlotCount:        index.SlotCount,
		Flags:            index.Flags,
		IndexChecksum:    fmt.Sprintf("%08x", index.IndexChecksum),
		MetadataChecksum: fmt.Sprintf("%x", index.MetadataChecksum),
		BuildTimestamp:   index.BuildTimestamp,
		PageSize:         index.PageSize,
		Capabilities:     index.Capabilities,
		Requirements:     index.Requirements,
	}

	indexPath := paths.IndexMetadataFile()
	jsonData, err := json.MarshalIndent(indexMetadata, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal index metadata: %w", err)
	}

	if err := os.WriteFile(indexPath, jsonData, 0644); err != nil {
		logger.Debug("⚠️ Failed to save index metadata", "error", err)
		return err
	}

	logger.Debug("💾 Saved index metadata", "path", indexPath)
	return nil
}

// checkWorkenvValidity checks if the work environment is valid using checksums
func checkWorkenvValidity(paths *WorkenvPaths, index *PSPFIndex, metadata *Metadata, logger hclog.Logger) (bool, error) {
	// First check if extraction is complete
	completePath := paths.CompleteFile()
	if _, err := os.Stat(completePath); err != nil {
		logger.Debug("🔍 No extraction completion marker found")
		return false, nil
	}

	// Check package checksum
	return validatePackageChecksum(paths, index.IndexChecksum, logger)
}

func runBundleWithCwd(exePath string, args []string, userCwd string, logger hclog.Logger) (*exec.Cmd, error) {
	reader, err := NewReaderWithLogger(exePath, logger)
	if err != nil {
		logger.Error("❌ Failed to create reader", "error", err)
		return nil, fmt.Errorf("failed to create reader: %w", err)
	}
	defer func() {
		if err := reader.Close(); err != nil {
			logger.Error("Failed to close reader", "error", err)
		}
	}()

	// Read index for checksum validation
	index, err := reader.ReadIndex()
	if err != nil {
		logger.Error("❌ Failed to read index", "error", err)
		return nil, fmt.Errorf("failed to read index: %w", err)
	}

	validationLevel := getValidationLevel()

	switch validationLevel {
	case ValidationNone:
		fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Skipping all integrity verification (FLAVOR_VALIDATION=none)\n")
		fmt.Fprintf(os.Stderr, "⚠️ This is NOT RECOMMENDED for production use\n")
		logger.Warn("⚠️ INSECURE MODE: Skipping integrity verification", "level", validationLevel)
	default:
		logger.Debug("🔍 Verifying package integrity", "level", validationLevel)
		valid, err := reader.VerifyIntegritySeal()
		if err != nil {
			switch validationLevel {
			case ValidationMinimal, ValidationRelaxed:
				fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Failed to verify integrity seal: %v\n", err)
				fmt.Fprintf(os.Stderr, "⚠️ Continuing due to validation level: %v\n", validationLevel)
				logger.Warn("⚠️ Failed to verify integrity seal, continuing", "error", err, "level", validationLevel)
			default: // ValidationStrict, ValidationStandard
				logger.Error("❌ Failed to verify integrity seal", "error", err)
				return nil, fmt.Errorf("failed to verify integrity seal: %w", err)
			}
		} else if !valid {
			switch validationLevel {
			case ValidationMinimal, ValidationRelaxed:
				fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Package integrity verification failed\n")
				fmt.Fprintf(os.Stderr, "⚠️ Package may be corrupted or tampered with\n")
				fmt.Fprintf(os.Stderr, "⚠️ Continuing due to validation level: %v\n", validationLevel)
				logger.Warn("⚠️ Package integrity verification failed, continuing", "level", validationLevel)
			default: // ValidationStrict, ValidationStandard
				if validationLevel == ValidationStandard {
					fmt.Fprintf(os.Stderr, "🚨 SECURITY WARNING: Package integrity verification failed\n")
					fmt.Fprintf(os.Stderr, "🚨 Package may be corrupted or tampered with\n")
					fmt.Fprintf(os.Stderr, "🚨 Set FLAVOR_VALIDATION=relaxed to bypass (NOT RECOMMENDED)\n")
				}
				logger.Error("❌ Package integrity verification failed")
				return nil, errors.New("package integrity verification failed")
			}
		} else {
			logger.Debug("✅ Package integrity verified")
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

	// Create WorkenvPaths structure
	var paths *WorkenvPaths
	if customWorkenv := os.Getenv("FLAVOR_WORKDIR"); customWorkenv != "" {
		// Use custom workenv path from environment variable
		logger.Info("📁 Using custom work environment from FLAVOR_WORKDIR", "path", customWorkenv)
		// Extract cache dir from custom workenv (go up two levels)
		cacheDir := filepath.Dir(filepath.Dir(customWorkenv))
		paths = NewWorkenvPaths(cacheDir, exePath)
	} else {
		// Get cache directory (XDG_CACHE_HOME or fallback)
		cacheDir := os.Getenv("XDG_CACHE_HOME")
		if cacheDir == "" {
			homeDir, _ := os.UserHomeDir()
			cacheDir = filepath.Join(homeDir, ".cache")
		}
		cacheDir = filepath.Join(cacheDir, "flavor")
		paths = NewWorkenvPaths(cacheDir, exePath)
	}

	workenvDir := paths.Workenv()
	if err := os.MkdirAll(workenvDir, os.FileMode(DirPerms)); err != nil {
		logger.Error("❌ Failed to create work environment directory", "error", err)
		return nil, fmt.Errorf("failed to create work environment directory: %w", err)
	}
	logger.Info("📁 Work environment", "path", workenvDir)

	// Setup workenv directories if specified
	if metadata.Workenv != nil && metadata.Workenv.Directories != nil {
		for _, dirSpec := range metadata.Workenv.Directories {
			// Substitute {workenv} placeholder in the path
			dirPath := strings.ReplaceAll(dirSpec.Path, "{workenv}", workenvDir)
			logger.Debug("📁 Creating directory", "path", dirPath)
			if err := os.MkdirAll(dirPath, os.FileMode(DirPerms)); err != nil {
				logger.Error("❌ Failed to create directory", "path", dirPath, "error", err)
				return nil, fmt.Errorf("failed to create directory %s: %w", dirPath, err)
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
	}

	// Check if we should use cache
	useCache := os.Getenv("FLAVOR_WORKENV_CACHE") != "false" && os.Getenv("FLAVOR_WORKENV_CACHE") != "0"

	workenvValid := false
	if useCache {
		logger.Debug("🔍 Checking cache validity")
		valid, err := checkWorkenvValidity(paths, index, metadata, logger)
		if err != nil {
			// Critical checksum mismatch error
			return nil, err
		}
		workenvValid = valid
		if workenvValid {
			logger.Info("✅ Cache is valid, skipping extraction")
		} else {
			logger.Info("❌ Cache invalid, will extract")
		}
	} else {
		logger.Info("📦 FLAVOR_WORKENV_CACHE=false, forcing fresh extraction")
	}

	slotPaths := make(map[int]string)

	if !workenvValid {
		// Check disk space before extraction
		if err := checkDiskSpace(paths, metadata, logger); err != nil {
			return nil, err
		}

		// Acquire lock before extraction
		acquiredLock, err := TryAcquireLock(paths, logger)
		if err != nil {
			logger.Error("❌ Failed to acquire extraction lock", "error", err)
			return nil, err
		}
		if !acquiredLock {
			// Another process is extracting, wait for it
			logger.Info("⏳ Another process is extracting, waiting...")
			if err := WaitForExtraction(paths, 60, logger); err != nil {
				return nil, err
			}
			// Re-check validity after waiting
			valid, err := checkWorkenvValidity(paths, index, metadata, logger)
			if err != nil {
				return nil, err
			}
			if !valid {
				return nil, fmt.Errorf("cache extraction by another process failed validation")
			}
			workenvValid = true
		}
		defer ReleaseLock(paths, logger)

		// Create temporary extraction directory
		tempExtractDir := paths.TempExtraction(os.Getpid())
		if err := os.MkdirAll(tempExtractDir, os.FileMode(DirPerms)); err != nil {
			logger.Error("❌ Failed to create temp extraction directory", "error", err)
			return nil, fmt.Errorf("failed to create temp extraction directory: %w", err)
		}
		logger.Info("📁 Created temporary extraction directory", "path", tempExtractDir)

		// Extract to temporary directory
		logger.Info("📤 Extracting slots to temp directory", "count", len(metadata.Slots))

		// Progress reporting to stderr
		for i, slot := range metadata.Slots {
			logger.Debug("📦 Extracting slot", "index", i, "id", slot.ID, "size", slot.Size)

			// Write progress to stderr
			fmt.Fprintf(os.Stderr, "[%d/%d] Extracting %s...\n", i+1, len(metadata.Slots), slot.ID)
			slotPath, err := reader.ExtractSlot(i, tempExtractDir)
			if err != nil {
				logger.Error("❌ Failed to extract slot, cleaning up", "error", err)
				os.RemoveAll(tempExtractDir)
				return nil, fmt.Errorf("%w: %v", ErrSlotExtractionFailed, err)
			}
			logger.Debug("✅ Extracted slot", "path", slotPath)
			slotPaths[slot.Slot] = slotPath
		}

		// Write metadata to package metadata directory directly in cache (not in temp)
		// Use hidden .{workenv}.pspf/package/ structure as a sibling to workenv
		packageMetadataDir := filepath.Join(paths.Metadata(), "package")
		if err := os.MkdirAll(packageMetadataDir, os.FileMode(DirPerms)); err != nil {
			logger.Error("❌ Failed to create package metadata directory", "error", err)
			os.RemoveAll(tempExtractDir)
			return nil, fmt.Errorf("failed to create package metadata directory: %w", err)
		}
		metadataFile := filepath.Join(packageMetadataDir, "psp.json")
		metadataJSON, err := json.MarshalIndent(metadata, "", "  ")
		if err != nil {
			logger.Error("❌ Failed to marshal metadata", "error", err)
			os.RemoveAll(tempExtractDir)
			return nil, fmt.Errorf("failed to marshal metadata: %w", err)
		}
		if err := os.WriteFile(metadataFile, metadataJSON, 0644); err != nil {
			logger.Error("❌ Failed to write metadata", "error", err)
			os.RemoveAll(tempExtractDir)
			return nil, fmt.Errorf("failed to write metadata: %w", err)
		}
		logger.Debug("📝 Wrote metadata to cache location", "path", metadataFile)

		// Atomically move extracted content from temp to final location
		logger.Info("🔄 Moving extracted content to final location...")

		// List all top-level items in temp directory
		entries, err := os.ReadDir(tempExtractDir)
		if err != nil {
			logger.Error("❌ Failed to read temp directory", "error", err)
			os.RemoveAll(tempExtractDir)
			return nil, fmt.Errorf("failed to read temp directory: %w", err)
		}

		for _, entry := range entries {
			fileName := entry.Name()
			source := filepath.Join(tempExtractDir, fileName)
			dest := filepath.Join(workenvDir, fileName)

			// Remove destination if it exists (for overwrite)
			if _, err := os.Stat(dest); err == nil {
				if entry.IsDir() {
					os.RemoveAll(dest)
				} else {
					os.Remove(dest)
				}
			}

			// Move from temp to final location
			logger.Debug("Moving", "from", source, "to", dest)
			if err := os.Rename(source, dest); err != nil {
				// If rename fails (e.g., cross-filesystem), fall back to copy
				logger.Warn("Rename failed, falling back to copy", "error", err)
				if entry.IsDir() {
					// Recursive copy for directories
					if err := copyDirAll(source, dest); err != nil {
						logger.Error("❌ Failed to copy directory", "error", err)
						os.RemoveAll(tempExtractDir)
						return nil, fmt.Errorf("failed to copy directory: %w", err)
					}
					os.RemoveAll(source)
				} else {
					if err := copyFile(source, dest); err != nil {
						logger.Error("❌ Failed to copy file", "error", err)
						os.RemoveAll(tempExtractDir)
						return nil, fmt.Errorf("failed to copy file: %w", err)
					}
					os.Remove(source)
				}
			}
		}

		// Fix shebangs in bin directory
		binDir := filepath.Join(workenvDir, "bin")
		if _, err := os.Stat(binDir); err == nil {
			logger.Info("🔧 Fixing shebangs in scripts...")
			if err := fixShebangs(binDir, tempExtractDir, workenvDir, logger); err != nil {
				logger.Warn("⚠️ Failed to fix some shebangs", "error", err)
			}
		}

		// Remove the now-empty temp directory
		if err := os.RemoveAll(tempExtractDir); err != nil {
			logger.Debug("⚠️ Failed to remove temp directory", "error", err)
		}

		// Save index metadata for inspection
		if err := saveIndexMetadata(paths, index, logger); err != nil {
			logger.Debug("⚠️ Failed to save index metadata", "error", err)
		}

		// Mark extraction as complete
		if err := MarkExtractionComplete(paths, logger); err != nil {
			logger.Debug("⚠️ Failed to mark extraction complete", "error", err)
		}

		// Save package checksum for future cache validation
		if err := savePackageChecksum(paths, index.IndexChecksum, logger); err != nil {
			logger.Debug("⚠️ Failed to save package checksum", "error", err)
		}
	} else {
		logger.Info("✅ Work environment is valid, skipping persistent slot extraction")
		for i, slot := range metadata.Slots {
			if slot.Lifecycle == "volatile" {
				logger.Debug("📦 Extracting volatile slot", "index", i, "id", slot.ID)
				slotPath, err := reader.ExtractSlot(i, workenvDir)
				if err != nil {
					logger.Error("❌ Failed to extract slot", "error", fmt.Errorf("%w: %v", ErrSlotExtractionFailed, err))
					return nil, fmt.Errorf("%w: %v", ErrSlotExtractionFailed, err)
				}
				slotPaths[slot.Slot] = slotPath
			} else {
				slotPaths[slot.Slot] = workenvDir
			}
		}
	}

	// Run setup commands if cache is invalid
	if !workenvValid && len(metadata.SetupCommands) > 0 {
		logger.Info("🔧 Running setup commands", "count", len(metadata.SetupCommands))
		metadataDir := filepath.Join(workenvDir, "metadata")
		if err := os.MkdirAll(metadataDir, os.FileMode(DirPerms)); err != nil {
			logger.Error("❌ Failed to create metadata directory", "error", err)
			return nil, fmt.Errorf("failed to create metadata directory: %w", err)
		}

		for i, setupCmdInterface := range metadata.SetupCommands {
			logger.Debug("🔧 Processing setup command", "index", i)
			var cmdToRun string
			var cmdArgs []string

			switch cmd := setupCmdInterface.(type) {
			case string:
				cmdToRun = cmd
			case map[string]interface{}:
				cmdType, _ := cmd["type"].(string)
				command, _ := cmd["command"].(string)

				command = strings.ReplaceAll(command, "{workenv}", workenvDir)
				command = strings.ReplaceAll(command, "{package_name}", metadata.Package.Name)
				command = strings.ReplaceAll(command, "{version}", metadata.Package.Version)

				if cmdType == "enumerate_and_execute" {
					if enumerate, ok := cmd["enumerate"].(map[string]interface{}); ok {
						path, _ := enumerate["path"].(string)
						pattern, _ := enumerate["pattern"].(string)

						path = strings.ReplaceAll(path, "{workenv}", workenvDir)

						matches, err := filepath.Glob(filepath.Join(path, pattern))
						if err != nil {
							logger.Warn("⚠️ Failed to enumerate files", "error", err)
						}

						parts := strings.Fields(command)
						if len(parts) > 0 && len(matches) > 0 {
							cmdArgs = append(parts[1:], matches...)
							cmdToRun = parts[0]
						} else {
							cmdToRun = command
						}
					}
				} else if cmdType == "write_file" {
					path, _ := cmd["path"].(string)
					content, _ := cmd["content"].(string)

					path = strings.ReplaceAll(path, "{workenv}", workenvDir)
					path = strings.ReplaceAll(path, "{package_name}", metadata.Package.Name)
					path = strings.ReplaceAll(path, "{version}", metadata.Package.Version)

					content = strings.ReplaceAll(content, "{workenv}", workenvDir)
					content = strings.ReplaceAll(content, "{package_name}", metadata.Package.Name)
					content = strings.ReplaceAll(content, "{version}", metadata.Package.Version)

					mode := os.FileMode(0644)
					if modeFloat, ok := cmd["mode"].(float64); ok {
						mode = os.FileMode(int(modeFloat))
					}

					if err := os.WriteFile(path, []byte(content+"\n"), mode); err != nil {
						logger.Error("❌ Failed to write file", "path", path, "error", err)
						return nil, fmt.Errorf("failed to write file %s: %w", path, err)
					}

					continue
				} else {
					cmdToRun = command
				}
			default:
				logger.Warn("⚠️ Unknown setup command type", "type", fmt.Sprintf("%T", setupCmdInterface))
				continue
			}

			if cmdToRun != "" {
				if len(cmdArgs) == 0 {
					cmdToRun = strings.ReplaceAll(cmdToRun, "{workenv}", workenvDir)
					cmdToRun = strings.ReplaceAll(cmdToRun, "{package_name}", metadata.Package.Name)
					cmdToRun = strings.ReplaceAll(cmdToRun, "{version}", metadata.Package.Version)
				}

				var setupExec *exec.Cmd
				if len(cmdArgs) > 0 {
					setupExec = exec.Command(cmdToRun, cmdArgs...)
				} else {
					parts := strings.Fields(cmdToRun)
					if len(parts) == 0 {
						continue
					}
					setupExec = exec.Command(parts[0], parts[1:]...)
				}

				setupExec.Dir = userCwd

				setupExec.Env = os.Environ()
				setupExec.Env = append(setupExec.Env, fmt.Sprintf("FLAVOR_WORKENV=%s", workenvDir))

				for i, env := range setupExec.Env {
					if strings.HasPrefix(env, "PATH=") {
						setupExec.Env[i] = fmt.Sprintf("PATH=%s/bin:%s", workenvDir, strings.TrimPrefix(env, "PATH="))
						break
					}
				}

				logger.Debug("🏃 Running setup command", "command", cmdToRun, "args", cmdArgs, "cwd", userCwd)
				if output, err := setupExec.CombinedOutput(); err != nil {
					logger.Error("❌ Setup command failed", "command", cmdToRun, "output", string(output))
					return nil, fmt.Errorf("setup command %s failed: %w", cmdToRun, err)
				}
			}
		}

		// Clean up lifecycle-based slots after setup
		logger.Info("🧹 Cleaning up lifecycle slots...")
		cleanupLifecycleSlots(workenvDir, metadata, slotPaths, logger)
	}

	if metadata.Execution == nil {
		logger.Error("❌ No execution configuration found")
		return nil, errors.New("no execution configuration found")
	}

	command := metadata.Execution.Command
	for idx, path := range slotPaths {
		placeholder := fmt.Sprintf("{slot:%d}", idx)
		command = strings.ReplaceAll(command, placeholder, path)
	}
	command = strings.ReplaceAll(command, "{workenv}", workenvDir)
	command = strings.ReplaceAll(command, "{package_name}", metadata.Package.Name)
	command = strings.ReplaceAll(command, "{version}", metadata.Package.Version)

	if strings.Contains(command, "{slot:") {
		for i := 0; i < len(metadata.Slots); i++ {
			placeholder := fmt.Sprintf("{slot:%d}", i)
			if strings.Contains(command, placeholder) {
				logger.Error("❌ Missing slot reference", "slot", i, "error", ErrMissingSlot)
				return nil, fmt.Errorf("%w: slot %d", ErrMissingSlot, i)
			}
		}
	}

	parts := strings.Fields(command)
	if len(parts) == 0 {
		logger.Error("Empty command")
		return nil, errors.New("empty command")
	}

	cmdArgs := parts[1:]
	if len(args) > 0 {
		cmdArgs = append(cmdArgs, args...)
	}

	cmd := exec.Command(parts[0], cmdArgs...)

	originalCmd := os.Args[0]
	binaryName := filepath.Base(originalCmd)

	cmd.Args = append([]string{binaryName}, cmdArgs...)
	logger.Debug("🏷️ Attempted to set argv[0] (Go limitation: won't work)", "argv0", binaryName, "original", originalCmd, "fullArgs", cmd.Args)

	parentEnv := os.Environ()
	logger.Debug("🌍 Inheriting parent environment", "vars_count", len(parentEnv))
	cmd.Env = parentEnv
	cmd.Env = append(cmd.Env, fmt.Sprintf("FLAVOR_WORKENV=%s", workenvDir))
	logger.Debug("➕ Added FLAVOR_WORKENV", "path", workenvDir)

	cmd.Env = append(cmd.Env,
		fmt.Sprintf("FLAVOR_ORIGINAL_COMMAND=%s", originalCmd),
		fmt.Sprintf("FLAVOR_COMMAND_NAME=%s", binaryName))
	logger.Debug("🏷️ Added command name environment variables",
		"FLAVOR_ORIGINAL_COMMAND", originalCmd,
		"FLAVOR_COMMAND_NAME", binaryName)

	pathFound := false
	for i, env := range cmd.Env {
		if strings.HasPrefix(env, "PATH=") {
			cmd.Env[i] = fmt.Sprintf("PATH=%s/bin:%s", workenvDir, strings.TrimPrefix(env, "PATH="))
			pathFound = true
			break
		}
	}
	if !pathFound {
		cmd.Env = append(cmd.Env, fmt.Sprintf("PATH=%s/bin", workenvDir))
	}

	if metadata.Runtime != nil && metadata.Runtime.Env != nil {
		logger.Debug("🔄 Processing runtime.env configuration")
		cmd.Env = processRuntimeEnv(cmd.Env, metadata.Runtime.Env, logger)
	}

	if metadata.Execution.Environment != nil {
		logger.Debug("➕ Adding package-defined environment variables", "count", len(metadata.Execution.Environment))
		for k, v := range metadata.Execution.Environment {
			for idx, path := range slotPaths {
				placeholder := fmt.Sprintf("{slot:%d}", idx)
				v = strings.ReplaceAll(v, placeholder, path)
			}
			cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
			logger.Trace("➕ Added package env var", "key", k, "value", v)
		}
	}

	cmd.Dir = userCwd
	logger.Debug("📂 Setting working directory", "path", userCwd)

	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	logger.Info("🚀 Executing command", "path", cmd.Path)
	logger.Debug("🎯 Command details", "args", cmd.Args[1:], "cwd", cmd.Dir)
	logger.Debug("📊 Final environment state", "total_vars", len(cmd.Env))

	if logger.IsTrace() {
		logger.Trace("🌍 Environment variables being passed to subprocess:")
		for _, env := range cmd.Env {
			parts := strings.SplitN(env, "=", 2)
			if len(parts) == 2 {
				logger.Trace("  →", "key", parts[0], "value", parts[1])
			}
		}
	}

	return cmd, nil
}

// cleanupLifecycleSlots removes slots based on their lifecycle after setup
func cleanupLifecycleSlots(workenvDir string, metadata *Metadata, slotPaths map[int]string, logger hclog.Logger) {
	for i, slot := range metadata.Slots {
		// Clean up init lifecycle slots - they're only needed during setup
		if slot.Lifecycle == "init" {
			slotPath := filepath.Join(workenvDir, slot.ID)
			if err := os.RemoveAll(slotPath); err != nil {
				logger.Debug("⚠️ Failed to remove init slot", "slot", slot.ID, "path", slotPath, "error", err)
			} else {
				logger.Debug("✅ Removed init slot", "slot", slot.ID, "path", slotPath)
			}
			// Remove from slotPaths map so it's not used in execution
			delete(slotPaths, i)
		}
	}
}
