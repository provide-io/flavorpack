package format_2025

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/hashicorp/go-hclog"
)

// extractAndMergeSlotsToWorkenv extracts slots to temporary directory and merges them to final workenv location
// It handles the complex slot merging logic where slot_N_* directories need to be merged (not replaced)
func extractAndMergeSlotsToWorkenv(
	reader *Reader,
	metadata *Metadata,
	paths *WorkenvPaths,
	index *PSPFIndex,
	logger hclog.Logger,
) (map[int]string, error) {
	slotPaths := make(map[int]string)
	workenvDir := paths.Workenv()

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

	// Process slots in reverse order (highest index first) so earlier slots don't get overwritten
	// This ensures slot_N_* directories are merged before slot_0_* and regular files
	sort.SliceStable(entries, func(i, j int) bool {
		nameI := entries[i].Name()
		nameJ := entries[j].Name()

		// Extract slot numbers for slot_N_* directories
		var slotI, slotJ int = -1, -1
		if _, err := fmt.Sscanf(nameI, "slot_%d_", &slotI); err == nil && entries[i].IsDir() {
			// nameI is a slot directory
		} else {
			slotI = -1
		}
		if _, err := fmt.Sscanf(nameJ, "slot_%d_", &slotJ); err == nil && entries[j].IsDir() {
			// nameJ is a slot directory
		} else {
			slotJ = -1
		}

		// Both are slot directories - sort by slot number in reverse (higher first)
		if slotI >= 0 && slotJ >= 0 {
			return slotI > slotJ
		}
		// Only one is a slot directory - slot directories come first
		if slotI >= 0 {
			return true
		}
		if slotJ >= 0 {
			return false
		}
		// Neither are slot directories - keep original order
		return false
	})

	for _, entry := range entries {
		fileName := entry.Name()
		source := filepath.Join(tempExtractDir, fileName)

		// Special handling for slot 0 - move contents to workenv root
		if strings.HasPrefix(fileName, "slot_0_") && entry.IsDir() {
			logger.Debug("🎯 Moving slot 0 contents to workenv root", "slotDir", fileName)
			// Read contents of slot 0 directory
			slotEntries, err := os.ReadDir(source)
			if err != nil {
				logger.Error("❌ Failed to read slot 0 directory", "error", err)
				os.RemoveAll(tempExtractDir)
				return nil, fmt.Errorf("failed to read slot 0 directory: %w", err)
			}

			// Move each item from slot 0 directory to workenv root
			for _, slotEntry := range slotEntries {
				slotSource := filepath.Join(source, slotEntry.Name())
				slotDest := filepath.Join(workenvDir, slotEntry.Name())

				logger.Debug("Moving slot 0 content", "from", slotSource, "to", slotDest)

				// For directories, merge instead of replacing
				if slotEntry.IsDir() {
					// Always use copyDirAll which merges directories
					if err := copyDirAll(slotSource, slotDest); err != nil {
						logger.Error("❌ Failed to copy slot 0 directory", "error", err)
						os.RemoveAll(tempExtractDir)
						return nil, fmt.Errorf("failed to copy slot 0 directory: %w", err)
					}
					os.RemoveAll(slotSource)
				} else {
					// For files, remove destination and move
					os.Remove(slotDest) // Remove existing file if any
					if err := os.Rename(slotSource, slotDest); err != nil {
						// If rename fails (e.g., cross-filesystem), fall back to copy
						logger.Warn("Rename failed, falling back to copy", "error", err)
						if err := copyFile(slotSource, slotDest); err != nil {
							logger.Error("❌ Failed to copy slot 0 file", "error", err)
							os.RemoveAll(tempExtractDir)
							return nil, fmt.Errorf("failed to copy slot 0 file: %w", err)
						}
						os.Remove(slotSource)
					}
				}
			}
			// Remove empty slot 0 directory
			os.RemoveAll(source)
		} else if strings.HasPrefix(fileName, "slot_") && entry.IsDir() {
			// Handle other slot_N_* directories (where target was {workenv}) - merge to root
			logger.Debug("🎯 Moving slot contents to workenv root", "slotDir", fileName)
			// Read contents of slot directory
			slotEntries, err := os.ReadDir(source)
			if err != nil {
				logger.Error("❌ Failed to read slot directory", "error", err)
				os.RemoveAll(tempExtractDir)
				return nil, fmt.Errorf("failed to read slot directory: %w", err)
			}

			// Move each item from slot directory to workenv root
			for _, slotEntry := range slotEntries {
				slotSource := filepath.Join(source, slotEntry.Name())
				slotDest := filepath.Join(workenvDir, slotEntry.Name())

				logger.Debug("Moving slot content", "from", slotSource, "to", slotDest)

				// For directories, merge instead of replacing
				if slotEntry.IsDir() {
					// Always use copyDirAll which merges directories
					if err := copyDirAll(slotSource, slotDest); err != nil {
						logger.Error("❌ Failed to copy slot directory", "error", err)
						os.RemoveAll(tempExtractDir)
						return nil, fmt.Errorf("failed to copy slot directory: %w", err)
					}
					os.RemoveAll(slotSource)
				} else {
					// For files, remove destination and move
					os.Remove(slotDest) // Remove existing file if any
					if err := os.Rename(slotSource, slotDest); err != nil {
						// If rename fails (e.g., cross-filesystem), fall back to copy
						logger.Warn("Rename failed, falling back to copy", "error", err)
						if err := copyFile(slotSource, slotDest); err != nil {
							logger.Error("❌ Failed to copy slot file", "error", err)
							os.RemoveAll(tempExtractDir)
							return nil, fmt.Errorf("failed to copy slot file: %w", err)
						}
						os.Remove(slotSource)
					}
				}
			}
			// Remove empty slot directory
			os.RemoveAll(source)
		} else {
			// Regular handling for other files/directories
			dest := filepath.Join(workenvDir, fileName)

			logger.Debug("Moving", "from", source, "to", dest)

			if entry.IsDir() {
				// For directories, always merge using copyDirAll (handles existing destinations)
				if err := copyDirAll(source, dest); err != nil {
					logger.Error("❌ Failed to copy directory", "error", err)
					os.RemoveAll(tempExtractDir)
					return nil, fmt.Errorf("failed to copy directory: %w", err)
				}
				os.RemoveAll(source)
			} else {
				// For files, try rename first, then copy
				if err := os.Rename(source, dest); err != nil {
					// If rename fails (e.g., cross-filesystem or destination exists), fall back to copy
					logger.Warn("Rename failed, falling back to copy", "error", err)
					if err := copyFile(source, dest); err != nil {
						logger.Error("❌ Failed to copy file", "error", err)
						os.RemoveAll(tempExtractDir)
						return nil, fmt.Errorf("failed to copy file: %w", err)
					}
					os.Remove(source)
				}
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

	return slotPaths, nil
}
