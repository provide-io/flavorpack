package format_2025

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/hashicorp/go-hclog"
	"github.com/provide-io/flavor/go/flavor/pkg/utils/shellparse"
)

var (
	ErrExecutionFailed      = errors.New("command execution failed")
	ErrSlotExtractionFailed = errors.New("slot extraction failed")
	ErrMissingSlot          = errors.New("missing slot reference")
	ErrLockAcquisition      = errors.New("failed to acquire lock")
)

// Utility functions: see execution_utils.go
// Cache functions: see execution_cache.go

// prepareBundlePath prepares the bundle path for reading.
// On Windows with PSPF embedded as a PE resource, it extracts the PSPF data
// to a temporary file and returns the path + cleanup function.
// Otherwise, it returns the original exePath with no cleanup.
func prepareBundlePath(exePath string, logger hclog.Logger) (string, func(), error) {
	logger.Debug("Checking bundle path preparation method", "exe", exePath)

	// Check if PSPF is embedded as a PE resource
	logger.Trace("Checking for PE resource embedding")
	if HasPSPFResource(exePath, logger) {
		logger.Info("🪟 Detected PSPF embedded as PE resource, extracting to temp file")
		logger.Debug("Starting PE resource extraction workflow")

		// Read PSPF data from resource
		logger.Trace("Reading PSPF data from PE resource")
		pspfData, err := ReadPSPFFromResource(exePath, logger)
		if err != nil {
			logger.Error("Failed to read PSPF from PE resource", "error", err)
			return "", nil, fmt.Errorf("failed to read PSPF from resource: %w", err)
		}
		logger.Debug("Successfully read PSPF from PE resource", "size", len(pspfData))

		// Create temporary file for PSPF data
		logger.Trace("Creating temporary file for extracted PSPF data")
		tmpFile, err := os.CreateTemp("", "pspf-*.psp")
		if err != nil {
			logger.Error("Failed to create temp file for PSPF extraction", "error", err)
			return "", nil, fmt.Errorf("failed to create temp file: %w", err)
		}
		tmpPath := tmpFile.Name()
		logger.Debug("Created temp file", "path", tmpPath)

		// Write PSPF data to temp file
		logger.Trace("Writing PSPF data to temp file", "size", len(pspfData))
		bytesWritten, err := tmpFile.Write(pspfData)
		if err != nil {
			logger.Error("Failed to write PSPF data to temp file", "error", err, "path", tmpPath)
			tmpFile.Close()
			logger.Trace("Cleaning up temp file after write failure", "path", tmpPath)
			os.Remove(tmpPath)
			return "", nil, fmt.Errorf("failed to write PSPF to temp file: %w", err)
		}
		logger.Debug("Wrote PSPF data to temp file", "bytes", bytesWritten, "expected", len(pspfData))

		if bytesWritten != len(pspfData) {
			logger.Error("Incomplete write to temp file", "written", bytesWritten, "expected", len(pspfData))
			tmpFile.Close()
			os.Remove(tmpPath)
			return "", nil, fmt.Errorf("incomplete write: wrote %d bytes, expected %d", bytesWritten, len(pspfData))
		}

		logger.Trace("Closing temp file")
		if err := tmpFile.Close(); err != nil {
			logger.Error("Failed to close temp file", "error", err, "path", tmpPath)
			logger.Trace("Cleaning up temp file after close failure", "path", tmpPath)
			os.Remove(tmpPath)
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
				logger.Trace("Successfully removed temp file", "path", tmpPath)
			}
		}
		return tmpPath, cleanup, nil
	}

	// No resource embedding - read from EOF (traditional approach)
	logger.Debug("📖 No PE resource detected, reading PSPF from EOF (appended to executable)")
	logger.Trace("Using direct executable path as bundle path", "path", exePath)
	return exePath, nil, nil
}

func runBundleWithCwd(exePath string, args []string, userCwd string, logger hclog.Logger) (*exec.Cmd, error) {
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
		logger.Warn("⚠️ VALIDATION DISABLED: Skipping integrity verification", "level", validationLevel)
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
			case ValidationStandard:
				fmt.Fprintf(os.Stderr, "🚨 SECURITY WARNING: Package integrity verification failed\n")
				fmt.Fprintf(os.Stderr, "🚨 Package may be corrupted or tampered with\n")
				fmt.Fprintf(os.Stderr, "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)\n")
				logger.Warn("⚠️ Package integrity verification failed, continuing with standard validation")
			default: // ValidationStrict
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

	// Convert to forward slashes for command string substitution on Windows
	// This prevents backslashes from being treated as escape characters by the shell parser
	workenvDirForCmd := filepath.ToSlash(workenvDir)
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

		// Extract and merge slots to workenv
		slotPaths, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logger)
		if err != nil {
			return nil, err
		}

		// Save package checksum for future cache validation
		if err := savePackageChecksum(paths, index.IndexChecksum, logger); err != nil {
			logger.Warn("⚠️ Failed to save package checksum", "error", err)
		}
	} else {
		logger.Info("✅ Work environment is valid, skipping persistent slot extraction")
		for i, slot := range metadata.Slots {
			if slot.Lifecycle == "volatile" {
				logger.Debug("📦 Extracting volatile slot", "index", i, "id", slot.ID)
				slotPath, err := reader.ExtractSlot(i, paths.Workenv())
				if err != nil {
					logger.Error("❌ Failed to extract slot", "error", fmt.Errorf("%w: %v", ErrSlotExtractionFailed, err))
					return nil, fmt.Errorf("%w: %v", ErrSlotExtractionFailed, err)
				}
				slotPaths[slot.Slot] = slotPath
			} else {
				slotPaths[slot.Slot] = paths.Workenv()
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

				command = strings.ReplaceAll(command, "{workenv}", workenvDirForCmd)
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

					content = strings.ReplaceAll(content, "{workenv}", workenvDirForCmd)
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
					cmdToRun = strings.ReplaceAll(cmdToRun, "{workenv}", workenvDirForCmd)
					cmdToRun = strings.ReplaceAll(cmdToRun, "{package_name}", metadata.Package.Name)
					cmdToRun = strings.ReplaceAll(cmdToRun, "{version}", metadata.Package.Version)
				}

				var setupExec *exec.Cmd
				if len(cmdArgs) > 0 {
					// Resolve executable for cross-platform compatibility
					resolvedCmd := resolveExecutable(cmdToRun, logger)
					setupExec = exec.Command(resolvedCmd, cmdArgs...)
				} else {
					// Use shell-aware parser to handle quoted arguments
					parts, err := shellparse.Split(cmdToRun)
					if err != nil {
						logger.Error("❌ Failed to parse setup command", "command", cmdToRun, "error", err)
						return nil, fmt.Errorf("failed to parse setup command %q: %w", cmdToRun, err)
					}
					if len(parts) == 0 {
						continue
					}
					// Resolve executable for cross-platform compatibility
					resolvedExec := resolveExecutable(parts[0], logger)
					setupExec = exec.Command(resolvedExec, parts[1:]...)
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
		// Convert slot paths to forward slashes for command string on Windows
		command = strings.ReplaceAll(command, placeholder, filepath.ToSlash(path))
	}
	command = strings.ReplaceAll(command, "{workenv}", workenvDirForCmd)
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

	// Use shell-aware parser to handle quoted arguments
	parts, err := shellparse.Split(command)
	if err != nil {
		logger.Error("❌ Failed to parse command", "command", command, "error", err)
		return nil, fmt.Errorf("failed to parse command %q: %w", command, err)
	}
	if len(parts) == 0 {
		logger.Error("Empty command")
		return nil, errors.New("empty command")
	}

	cmdArgs := parts[1:]
	if len(args) > 0 {
		cmdArgs = append(cmdArgs, args...)
	}

	// Resolve executable for cross-platform compatibility
	resolvedExec := resolveExecutable(parts[0], logger)
	cmd := exec.Command(resolvedExec, cmdArgs...)

	originalCmd := os.Args[0]
	binaryName := filepath.Base(originalCmd)

	cmd.Args = append([]string{binaryName}, cmdArgs...)
	logger.Debug("🏷️ Attempted to set argv[0] (Go limitation: won't work)", "argv0", binaryName, "original", originalCmd, "fullArgs", cmd.Args)

	// Setup environment variables in proper layering order
	parentEnv := os.Environ()
	logger.Debug("🌍 Inheriting parent environment", "vars_count", len(parentEnv))
	cmd.Env = parentEnv

	// Set FLAVOR_CACHE BEFORE workenv environment (which overwrites HOME)
	cmd.Env = setFlavorCacheBeforeWorkenv(cmd.Env, logger)

	// Add FLAVOR_* variables
	cmd.Env = append(cmd.Env, fmt.Sprintf("FLAVOR_WORKENV=%s", workenvDir))
	logger.Debug("➕ Added FLAVOR_WORKENV", "path", workenvDir)

	cmd.Env = append(cmd.Env,
		fmt.Sprintf("FLAVOR_ORIGINAL_COMMAND=%s", originalCmd),
		fmt.Sprintf("FLAVOR_COMMAND_NAME=%s", binaryName))
	logger.Debug("🏷️ Added command name environment variables",
		"FLAVOR_ORIGINAL_COMMAND", originalCmd,
		"FLAVOR_COMMAND_NAME", binaryName)

	// Prepend workenv/bin to PATH
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

	// Process runtime.env configuration
	if metadata.Runtime != nil && metadata.Runtime.Env != nil {
		logger.Debug("🔄 Processing runtime.env configuration")
		cmd.Env = processRuntimeEnv(cmd.Env, metadata.Runtime.Env, logger)
	}

	// Add package-defined environment variables
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

	logEnvironmentTrace(cmd.Env, logger)

	return cmd, nil
}
