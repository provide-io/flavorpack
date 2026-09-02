// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// slotDirIndex reports the slot number a "slot_N_*" directory carries, or -1
// for anything else.
func slotDirIndex(entry os.DirEntry) int {
	if !entry.IsDir() {
		return -1
	}
	n := -1
	if _, err := fmt.Sscanf(entry.Name(), "slot_%d_", &n); err != nil {
		return -1
	}
	return n
}

// sortSlotDirectoriesFirst orders extracted entries so slot directories are
// merged before anything else, highest slot number first.
//
// Later slots are meant to be overwritten by earlier ones, so they have to land
// first; regular files come last and win outright.
func sortSlotDirectoriesFirst(entries []os.DirEntry) {
	sort.SliceStable(entries, func(i, j int) bool {
		slotI, slotJ := slotDirIndex(entries[i]), slotDirIndex(entries[j])
		switch {
		case slotI >= 0 && slotJ >= 0:
			return slotI > slotJ
		case slotI >= 0:
			return true
		case slotJ >= 0:
			return false
		default:
			return false
		}
	})
}

// moveIntoWorkenv moves one extracted item to its place in the work
// environment.
//
// Directories are merged rather than replaced, so a later slot's tree does not
// erase an earlier one's. Files are renamed where the filesystem allows it and
// copied when it does not -- the temp directory and the work environment can
// sit on different filesystems.
//
// replaceExisting clears the destination first. Slot contents merge into a
// shared root and are expected to land on each other, so they replace. A
// top-level entry does not: a destination already occupied there is a conflict
// the build should hear about, and clearing it first would turn a directory in
// the way into a silent success.
func moveIntoWorkenv(source, dest string, isDir, replaceExisting bool, what string, logger *slog.Logger) error {
	// "file" / "directory", or "slot file" / "slot directory".
	noun := "file"
	if isDir {
		noun = "directory"
	}
	if what != "" {
		noun = what + " " + noun
	}

	if isDir {
		if err := copyDirAll(source, dest); err != nil {
			logger.Error("❌ Failed to copy "+noun, "error", err)
			return fmt.Errorf("failed to copy %s: %w", noun, err)
		}
		_ = os.RemoveAll(source)
		return nil
	}

	if replaceExisting {
		_ = os.Remove(dest)
	}
	if err := osRenameFn(source, dest); err == nil {
		return nil
	}

	logger.Warn("Rename failed, falling back to copy", "source", source, "dest", dest)
	if err := copyFile(source, dest); err != nil {
		logger.Error("❌ Failed to copy "+noun, "error", err)
		return fmt.Errorf("failed to copy %s: %w", noun, err)
	}
	_ = os.Remove(source)
	return nil
}

// mergeSlotDirectory empties one "slot_N_*" directory into the work environment
// root, which is where a slot whose target is {workenv} belongs.
func mergeSlotDirectory(source, workenvDir string, logger *slog.Logger) error {
	slotEntries, err := os.ReadDir(source)
	if err != nil {
		logger.Error("❌ Failed to read slot directory", "error", err, "path", source)
		return fmt.Errorf("failed to read slot directory: %w", err)
	}

	for _, slotEntry := range slotEntries {
		slotSource := filepath.Join(source, slotEntry.Name())
		slotDest := filepath.Join(workenvDir, slotEntry.Name())
		logger.Debug("Moving slot content", "from", slotSource, "to", slotDest)

		if err := moveIntoWorkenv(slotSource, slotDest, slotEntry.IsDir(), true, "slot", logger); err != nil {
			return err
		}
	}

	_ = os.RemoveAll(source) // now empty
	return nil
}

// mergeExtractedEntry places one top-level extracted entry.
func mergeExtractedEntry(entry os.DirEntry, tempExtractDir, workenvDir string, logger *slog.Logger) error {
	fileName := entry.Name()
	source := filepath.Join(tempExtractDir, fileName)

	// Every slot_N_* directory merges to the root the same way, slot 0 included.
	if entry.IsDir() && strings.HasPrefix(fileName, "slot_") {
		logger.Debug("🎯 Moving slot contents to workenv root", "slotDir", fileName)
		return mergeSlotDirectory(source, workenvDir, logger)
	}

	dest := filepath.Join(workenvDir, fileName)
	logger.Debug("Moving", "from", source, "to", dest)

	if !entry.IsDir() {
		if err := mkdirAllParentFn(filepath.Dir(dest), os.FileMode(DirPerms)); err != nil {
			logger.Error("❌ Failed to create parent directory for file", "dest", dest, "error", err)
			return fmt.Errorf("failed to create parent directory for file: %w", err)
		}
	}

	return moveIntoWorkenv(source, dest, entry.IsDir(), false, "", logger)
}

// mergeTempIntoWorkenv moves everything extracted into the work environment.
func mergeTempIntoWorkenv(tempExtractDir, workenvDir string, logger *slog.Logger) error {
	logger.Info("🔄 Moving extracted content to final location...")

	entries, err := osReadDirFn(tempExtractDir)
	if err != nil {
		logger.Error("❌ Failed to read temp directory", "error", err)
		return fmt.Errorf("failed to read temp directory: %w", err)
	}

	sortSlotDirectoriesFirst(entries)

	for _, entry := range entries {
		if err := mergeExtractedEntry(entry, tempExtractDir, workenvDir, logger); err != nil {
			return err
		}
	}

	return nil
}

// extractSlotsToTemp writes every slot into a staging directory, reporting
// progress on stderr as it goes.
func extractSlotsToTemp(
	reader *Reader,
	metadata *Metadata,
	tempExtractDir string,
	logger *slog.Logger,
) (map[int]string, error) {
	logger.Info("📤 Extracting slots to temp directory", "count", len(metadata.Slots))

	slotPaths := make(map[int]string, len(metadata.Slots))
	for i, slot := range metadata.Slots {
		logger.Debug("📦 Extracting slot", "index", i, "id", slot.ID, "size", slot.Size)
		_, _ = fmt.Fprintf(os.Stderr, "[%d/%d] Extracting %s...\n", i+1, len(metadata.Slots), slot.ID)

		slotPath, err := reader.ExtractSlot(i, tempExtractDir)
		if err != nil {
			logger.Error("❌ Failed to extract slot", "error", err)
			return nil, fmt.Errorf("%w: %v", ErrSlotExtractionFailed, err)
		}
		logger.Debug("✅ Extracted slot", "path", slotPath)
		slotPaths[slot.Slot] = slotPath
	}

	return slotPaths, nil
}

// writePackageMetadataFile records the metadata document beside the work
// environment, where an inspection can read it without opening the package.
func writePackageMetadataFile(metadata *Metadata, paths *WorkenvPaths, logger *slog.Logger) error {
	packageMetadataDir := filepath.Join(paths.Metadata(), "package")
	if err := os.MkdirAll(packageMetadataDir, os.FileMode(DirPerms)); err != nil {
		logger.Error("❌ Failed to create package metadata directory", "error", err)
		return fmt.Errorf("failed to create package metadata directory: %w", err)
	}

	metadataJSON, err := jsonMarshalIndentFn(metadata, "", "  ")
	if err != nil {
		logger.Error("❌ Failed to marshal metadata", "error", err)
		return fmt.Errorf("failed to marshal metadata: %w", err)
	}

	metadataFile := filepath.Join(packageMetadataDir, "psp.json")
	if err := os.WriteFile(metadataFile, metadataJSON, FilePerms); err != nil {
		logger.Error("❌ Failed to write metadata", "error", err)
		return fmt.Errorf("failed to write metadata: %w", err)
	}

	logger.Debug("📝 Wrote metadata to cache location", "path", metadataFile)
	return nil
}
