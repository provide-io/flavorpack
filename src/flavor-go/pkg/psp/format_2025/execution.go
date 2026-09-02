package format_2025

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"log/slog"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

var (
	ErrExecutionFailed      = errors.New("command execution failed")
	ErrSlotExtractionFailed = errors.New("slot extraction failed")
	ErrMissingSlot          = errors.New("missing slot reference")
	ErrLockAcquisition      = errors.New("failed to acquire lock")
)

var tryAcquireLockFn = TryAcquireLock
var waitForExtractionFn = WaitForExtraction
var checkWorkenvValidityAfterWaitFn = checkWorkenvValidity
var chmodValidatedFn = chmodValidated
var hasPSPFResourceFn = HasPSPFResource
var readPSPFFromResourceFn = ReadPSPFFromResource
var verifyIntegritySealFn = (*Reader).VerifyIntegritySeal
var createTempFn = os.CreateTemp
var removeAllFn = os.RemoveAll
var runBundleReaderCloseFn = (*Reader).Close
var tmpFileWriteFn = func(f *os.File, d []byte) (int, error) { return f.Write(d) }
var tmpFileCloseFn = func(f *os.File) error { return f.Close() }

func removeFileQuietly(path, context string, logger *slog.Logger) {
	if err := os.Remove(path); err != nil {
		logging.Trace(logger, "Ignoring cleanup error", "context", context, "path", path, "error", err)
	}
}

func removeAllQuietly(path, context string, logger *slog.Logger) {
	if err := removeAllFn(path); err != nil {
		logging.Trace(logger, "Ignoring cleanup error", "context", context, "path", path, "error", err)
	}
}

func ensurePathWithinWorkenv(path, workenvDir, original string) error {
	cleanPath := filepath.Clean(path)
	cleanBase := filepath.Clean(workenvDir)
	if !strings.HasPrefix(cleanPath, cleanBase+string(os.PathSeparator)) && cleanPath != cleanBase {
		return fmt.Errorf("path %q escapes work environment directory", original)
	}
	return nil
}

// Utility functions: see execution_utils.go
// Cache functions: see execution_cache.go

// prepareBundlePath prepares the bundle path for reading.
// On Windows with PSPF embedded as a PE resource, it extracts the PSPF data
// to a temporary file and returns the path + cleanup function.
// Otherwise, it returns the original exePath with no cleanup.
func prepareBundlePath(exePath string, logger *slog.Logger) (string, func(), error) {
	logger.Debug("Checking bundle path preparation method", "exe", exePath)

	// Check if PSPF is embedded as a PE resource
	logging.Trace(logger, "Checking for PE resource embedding")
	if hasPSPFResourceFn(exePath, logger) {
		logger.Info("🪟 Detected PSPF embedded as PE resource, extracting to temp file")
		logger.Debug("Starting PE resource extraction workflow")

		// Read PSPF data from resource
		logging.Trace(logger, "Reading PSPF data from PE resource")
		pspfData, err := readPSPFFromResourceFn(exePath, logger)
		if err != nil {
			logger.Error("Failed to read PSPF from PE resource", "error", err)
			return "", nil, fmt.Errorf("failed to read PSPF from resource: %w", err)
		}
		logger.Debug("Successfully read PSPF from PE resource", "size", len(pspfData))

		// Create temporary file for PSPF data
		logging.Trace(logger, "Creating temporary file for extracted PSPF data")
		tmpFile, err := createTempFn("", "pspf-*.psp")
		if err != nil {
			logger.Error("Failed to create temp file for PSPF extraction", "error", err)
			return "", nil, fmt.Errorf("failed to create temp file: %w", err)
		}
		tmpPath := tmpFile.Name()
		logger.Debug("Created temp file", "path", tmpPath)

		// Write PSPF data to temp file
		logging.Trace(logger, "Writing PSPF data to temp file", "size", len(pspfData))
		bytesWritten, err := tmpFileWriteFn(tmpFile, pspfData)
		if err != nil {
			logger.Error("Failed to write PSPF data to temp file", "error", err, "path", tmpPath)
			_ = tmpFileCloseFn(tmpFile)
			logging.Trace(logger, "Cleaning up temp file after write failure", "path", tmpPath)
			_ = os.Remove(tmpPath)
			return "", nil, fmt.Errorf("failed to write PSPF to temp file: %w", err)
		}
		logger.Debug("Wrote PSPF data to temp file", "bytes", bytesWritten, "expected", len(pspfData))

		if bytesWritten != len(pspfData) {
			logger.Error("Incomplete write to temp file", "written", bytesWritten, "expected", len(pspfData))
			_ = tmpFileCloseFn(tmpFile)
			_ = os.Remove(tmpPath)
			return "", nil, fmt.Errorf("incomplete write: wrote %d bytes, expected %d", bytesWritten, len(pspfData))
		}

		logging.Trace(logger, "Closing temp file")
		if err := tmpFileCloseFn(tmpFile); err != nil {
			logger.Error("Failed to close temp file", "error", err, "path", tmpPath)
			logging.Trace(logger, "Cleaning up temp file after close failure", "path", tmpPath)
			_ = os.Remove(tmpPath)
			return "", nil, fmt.Errorf("failed to close temp file: %w", err)
		}
		logger.Debug("Temp file closed successfully", "path", tmpPath)

		logger.Debug("📝 Extracted PSPF to temp file", "path", tmpPath, "size", len(pspfData))

		// Return temp path with cleanup function
		cleanup := func() {
			logger.Debug("🧹 Cleaning up temp PSPF file", "path", tmpPath)
			if err := os.Remove(tmpPath); err != nil {
				logger.Debug("Failed to remove temp file (may have been already removed)", "path", tmpPath, "error", err)
			} else {
				logging.Trace(logger, "Successfully removed temp file", "path", tmpPath)
			}
		}
		return tmpPath, cleanup, nil
	}

	// No resource embedding - read from EOF (traditional approach)
	logger.Debug("📖 No PE resource detected, reading PSPF from EOF (appended to executable)")
	logging.Trace(logger, "Using direct executable path as bundle path", "path", exePath)
	return exePath, nil, nil
}

func runBundleWithCwd(exePath string, args []string, userCwd string, logger *slog.Logger) (*exec.Cmd, error) {
	// Check if PSPF is embedded as a PE resource (Windows + Go launcher)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		logger.Error("❌ Failed to prepare bundle path", "error", err)
		return nil, fmt.Errorf("failed to prepare bundle path: %w", err)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
	if err != nil {
		logger.Error("❌ Failed to create reader", "error", err)
		return nil, fmt.Errorf("failed to create reader: %w", err)
	}
	defer func() {
		if err := runBundleReaderCloseFn(reader); err != nil {
			logger.Error("Failed to close reader", "error", err)
		}
	}()

	// Read index for checksum validation
	index, err := reader.ReadIndex()
	if err != nil {
		logger.Error("❌ Failed to read index", "error", err)
		return nil, fmt.Errorf("failed to read index: %w", err)
	}

	// The attestation fingerprint, when present, must match the derived
	// public-key fingerprint. keyTrusted is an input to EnforcePolicy below.
	keyTrusted, err := checkSigningKeyTrust(index, logger)
	if err != nil {
		return nil, err
	}

	if err := verifyPackageIntegrity(reader, getValidationLevel(), logger); err != nil {
		return nil, err
	}

	metadata, err := reader.ReadMetadata()
	if err != nil {
		logger.Error("❌ Failed to read metadata", "error", err)
		return nil, fmt.Errorf("failed to read metadata: %w", err)
	}

	logger.Info("📦 Package", "name", metadata.Package.Name, "version", metadata.Package.Version)
	if metadata.Execution != nil {
		logger.Debug("🔧 Command", "command", metadata.Execution.Command)
	} else {
		logger.Debug("⚠️ No execution configuration present in metadata")
	}

	if err := enforcePackagePolicy(metadata, index, keyTrusted, logger); err != nil {
		return nil, err
	}

	paths, workenvDir, err := resolveWorkenvPaths(exePath, logger)
	if err != nil {
		return nil, err
	}

	// Forward slashes so the shell parser does not read Windows separators as
	// escape characters during command substitution.
	workenvDirForCmd := filepath.ToSlash(workenvDir)

	if err := createWorkenvDirectories(metadata, workenvDir, logger); err != nil {
		return nil, err
	}

	// Check if we should use cache
	useCache := os.Getenv(EnvWorkenvCache) != "false" && os.Getenv(EnvWorkenvCache) != "0"

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

	// Every branch below assigns it.
	var slotPaths map[int]string

	if workenvValid {
		logger.Info("✅ Work environment is valid, skipping persistent slot extraction")
		slotPaths = workenvSlotPaths(metadata, paths)
	} else {
		if err := checkDiskSpace(paths, metadata, logger); err != nil {
			return nil, err
		}

		acquiredLock, err := tryAcquireLockFn(paths, logger)
		if err != nil {
			logger.Error("❌ Failed to acquire extraction lock", "error", err)
			return nil, err
		}

		if acquiredLock {
			// Only a holder releases. ReleaseLock removes the lock file without
			// checking who owns it, so releasing one this process never took
			// deletes whichever process's lock is there.
			defer ReleaseLock(paths, logger)

			slotPaths, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logger)
			if err != nil {
				return nil, err
			}

			// Recorded for the next launch's cache check.
			if err := savePackageChecksum(paths, index.IndexChecksum, logger); err != nil {
				logger.Warn("⚠️ Failed to save package checksum", "error", err)
			}
		} else {
			// Another process holds the lock. Wait for its extraction and use
			// it: extracting into the same work environment alongside it is
			// what the lock exists to prevent.
			logger.Info("⏳ Another process is extracting, waiting...")
			if err := waitForExtractionFn(paths, 60, logger); err != nil {
				return nil, err
			}

			valid, err := checkWorkenvValidityAfterWaitFn(paths, index, metadata, logger)
			if err != nil {
				return nil, err
			}
			if !valid {
				return nil, errors.New("cache extraction by another process failed validation")
			}

			workenvValid = true
			slotPaths = workenvSlotPaths(metadata, paths)
		}
	}

	// Setup commands run once, against a freshly extracted work environment.
	if !workenvValid && len(metadata.SetupCommands) > 0 {
		if err := runSetupCommands(metadata, workenvDir, workenvDirForCmd, userCwd, slotPaths, logger); err != nil {
			return nil, err
		}
	}

	if metadata.Execution == nil {
		logger.Error("❌ No execution configuration found")
		return nil, errors.New("no execution configuration found")
	}

	// {slot:N} resolves to where a slot sits in the finished workenv. slotPaths
	// reports neither: after extraction it names a temporary directory that is
	// removed before this runs, and on the cached path every entry is the
	// workenv root. Derive them from the targets instead.
	commandSlotPaths := buildSlotPaths(metadata, workenvDirForCmd, logger)

	command, err := resolveCommandPlaceholders(metadata, commandSlotPaths, workenvDirForCmd, logger)
	if err != nil {
		return nil, err
	}

	cmd, cmdArgs, err := buildExecCommand(command, args, logger)
	if err != nil {
		return nil, err
	}

	originalCmd := os.Args[0]
	binaryName := filepath.Base(originalCmd)
	cmd.Args = append([]string{binaryName}, cmdArgs...)
	logger.Debug("🏷️ Attempted to set argv[0] (Go limitation: won't work)", "argv0", binaryName, "original", originalCmd, "fullArgs", cmd.Args)

	cmd.Env = buildCommandEnvironment(metadata, commandSlotPaths, workenvDir, originalCmd, binaryName, logger)

	cmd.Dir = userCwd
	logger.Debug("📂 Setting working directory", "path", userCwd)

	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	logger.Info("🚀 Executing command", "path", cmd.Path)
	logger.Debug("🎯 Command details", "args", cmd.Args[1:], "cwd", cmd.Dir)
	logger.Debug("📊 Final environment state", "total_vars", len(cmd.Env))

	logEnvironmentTrace(cmd.Env, logger)

	return cmd, nil
}
