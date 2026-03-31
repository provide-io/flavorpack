package format_2025

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/hashicorp/go-hclog"
)

// checkDiskSpace verifies there's enough disk space for extraction
func checkDiskSpace(paths *WorkenvPaths, metadata *Metadata, logger hclog.Logger) error {
	// Calculate total size needed (compressed size * DiskSpaceMultiplier for safety)
	var totalSizeNeeded int64
	for _, slot := range metadata.Slots {
		totalSizeNeeded += slot.Size * DiskSpaceMultiplier
	}

	// Get available disk space
	workenvPath := paths.Workenv()
	available, err := getAvailableDiskSpace(workenvPath)
	if err != nil {
		logger.Warn("⚠️ Could not check disk space", "error", err)
		return nil // Don't fail if we can't check
	}

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
	case ValidationStandard:
		fmt.Fprintf(os.Stderr, "🚨 SECURITY WARNING: Package checksum mismatch! cached=%s, current=%s\n", storedChecksum, currentChecksumStr)
		fmt.Fprintf(os.Stderr, "🚨 Cache may be compromised or package has changed\n")
		fmt.Fprintf(os.Stderr, "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)\n")
		logger.Warn("⚠️ Package checksum mismatch, continuing with standard validation", "cached", storedChecksum, "current", currentChecksumStr)
		return false, nil
	default: // ValidationStrict
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

	// Open file with explicit sync to ensure write is flushed before exec
	file, err := os.OpenFile(checksumPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
	if err != nil {
		logger.Debug("⚠️ Failed to open checksum file", "error", err)
		return err
	}
	defer file.Close()

	if _, err := file.WriteString(checksumStr); err != nil {
		logger.Debug("⚠️ Failed to write package checksum", "error", err)
		return err
	}

	// Explicitly sync to disk before syscall.Exec replaces process
	if err := file.Sync(); err != nil {
		logger.Debug("⚠️ Failed to sync checksum file", "error", err)
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

	// Check that workenv directory exists and is not empty
	workenvDir := paths.Workenv()
	entries, err := os.ReadDir(workenvDir)
	if err != nil {
		logger.Debug("🔍 Workenv directory does not exist or cannot be read")
		return false, nil
	}
	if len(entries) == 0 {
		logger.Debug("🔍 Workenv directory is empty")
		return false, nil
	}

	// Check package checksum
	return validatePackageChecksum(paths, index.IndexChecksum, logger)
}
