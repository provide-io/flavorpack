package format_2025

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"log/slog"
)

var osRenameFn = os.Rename
var jsonMarshalIndentFn = json.MarshalIndent
var osReadDirFn = os.ReadDir
var mkdirAllParentFn = os.MkdirAll
var fixShebangsFn = fixShebangs
var osRemoveAllFn = os.RemoveAll
var saveIndexMetadataFn = saveIndexMetadata
var markExtractionCompleteFn = MarkExtractionComplete

// extractAndMergeSlotsToWorkenv extracts slots to temporary directory and merges them to final workenv location
// It handles the complex slot merging logic where slot_N_* directories need to be merged (not replaced)
// extractAndMergeSlotsToWorkenv stages every slot in a temporary directory and
// then merges it into the work environment.
//
// Staging first is what makes a failed extraction leave no half-built work
// environment behind: nothing reaches the real directory until every slot has
// been written successfully.
func extractAndMergeSlotsToWorkenv(
	reader *Reader,
	metadata *Metadata,
	paths *WorkenvPaths,
	index *PSPFIndex,
	logger *slog.Logger,
) (map[int]string, error) {
	workenvDir := paths.Workenv()

	tempExtractDir := paths.TempExtraction(os.Getpid())
	if err := os.MkdirAll(tempExtractDir, os.FileMode(DirPerms)); err != nil {
		logger.Error("❌ Failed to create temp extraction directory", "error", err)
		return nil, fmt.Errorf("failed to create temp extraction directory: %w", err)
	}
	logger.Info("📁 Created temporary extraction directory", "path", tempExtractDir)

	// Every failure below leaves the staging directory behind otherwise, and it
	// is named after this process, so nothing else will clean it up.
	staged := false
	defer func() {
		if !staged {
			_ = os.RemoveAll(tempExtractDir)
		}
	}()

	slotPaths, err := extractSlotsToTemp(reader, metadata, tempExtractDir, logger)
	if err != nil {
		return nil, err
	}

	if err := writePackageMetadataFile(metadata, paths, logger); err != nil {
		return nil, err
	}

	if err := mergeTempIntoWorkenv(tempExtractDir, workenvDir, logger); err != nil {
		return nil, err
	}
	staged = true

	// Scripts carry the interpreter path from wherever they were built.
	binDir := filepath.Join(workenvDir, "bin")
	if _, err := os.Stat(binDir); err == nil {
		logger.Info("🔧 Fixing shebangs in scripts...")
		if err := fixShebangsFn(binDir, tempExtractDir, workenvDir, logger); err != nil {
			logger.Warn("⚠️ Failed to fix some shebangs", "error", err)
		}
	}

	if err := osRemoveAllFn(tempExtractDir); err != nil {
		logger.Debug("⚠️ Failed to remove temp directory", "error", err)
	}

	// None of the following is required for the package to run.
	if err := saveIndexMetadataFn(paths, index, logger); err != nil {
		logger.Debug("⚠️ Failed to save index metadata", "error", err)
	}
	if err := markExtractionCompleteFn(paths, logger); err != nil {
		logger.Debug("⚠️ Failed to mark extraction complete", "error", err)
	}

	return slotPaths, nil
}
