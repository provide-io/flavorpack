package format_2025

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/hashicorp/go-hclog"
	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)


func isEnvTrue(key string) bool {
	val := os.Getenv(key)
	if val == "" {
		return false
	}

	valLower := strings.ToLower(val)
	if valLower == "on" || valLower == "yes" {
		return true
	}

	result, err := strconv.ParseBool(val)
	return err == nil && result
}

// LaunchWithLogLevel launches with explicit log level control
func LaunchWithLogLevel(exePath string, args []string, cliLogLevel, cliLogSource string) {
	// Determine log level and source
	var logLevel string
	var logSource string
	
	if cliLogLevel != "" {
		logLevel = cliLogLevel
		logSource = cliLogSource
	} else if envLevel := os.Getenv("FLAVOR_LAUNCHER_LOG_LEVEL"); envLevel != "" {
		logLevel = envLevel
		logSource = "FLAVOR_LAUNCHER_LOG_LEVEL"
	} else if envLevel := os.Getenv("FLAVOR_LOG_LEVEL"); envLevel != "" {
		logLevel = envLevel
		logSource = "FLAVOR_LOG_LEVEL"
	} else {
		logLevel = "info"
		logSource = "default"
	}

	// Parse JSON format from log level (e.g., "json:debug" or just "debug")
	jsonFormat := false
	actualLevel := logLevel
	if strings.HasPrefix(logLevel, "json") {
		jsonFormat = true
		parts := strings.Split(logLevel, ":")
		if len(parts) > 1 {
			actualLevel = parts[1]
		} else {
			actualLevel = "info"
		}
	}

	// Configure logger with JSON if requested
	var output io.Writer = os.Stderr
	
	// Support log file output
	if logPath := os.Getenv("FLAVOR_LOG_PATH"); logPath != "" {
		if file, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644); err == nil {
			output = file
		}
	}
	
	// Add 🐹 prefix to non-JSON output
	if !jsonFormat {
		output = logging.NewPrefixWriter("🐹 ", output)
	}
	
	loggerOpts := &hclog.LoggerOptions{
		Name:       "flavor-go-launcher",
		Level:      hclog.LevelFromString(actualLevel),
		JSONFormat: jsonFormat,
		Output:     output,
		TimeFormat: "2006-01-02T15:04:05Z", // UTC ISO format without timezone  
		TimeFn: func() time.Time {
			return time.Now().UTC() // Force UTC time
		},
	}

	logger := hclog.New(loggerOpts)

	// Log startup messages
	logger.Info("🐹🐹🐹 Hello from Flavor's PSPF Launcher 🐹🐹🐹")
	logger.Debug("Log level", "level", actualLevel, "source", logSource)
	logger.Info("PSPF Go Launcher starting...")
	logger.Debug("📖 Reading PSPF bundle")

	envVars := os.Environ()
	logger.Debug("🔧 Environment variables received from parent process", "count", len(envVars))

	if logger.IsTrace() {
		for _, env := range envVars {
			parts := strings.SplitN(env, "=", 2)
			if len(parts) == 2 {
				logger.Trace("📝 Environment variable", "key", parts[0], "value", parts[1])
			}
		}
	}

	userCwd, err := os.Getwd()
	if err != nil {
		logger.Error("❌ Failed to get current directory", "error", err)
		os.Exit(1)
	}
	logger.Debug("📁 User working directory", "path", userCwd)

	if isEnvTrue("FLAVOR_LAUNCHER_CLI") {
		logger.Debug("💻 Running in CLI mode")
		if len(args) < 1 {
			// Default to info command when no args provided
			showBundleInfo(exePath, logger)
			return
		}

		switch args[0] {
		case "info":
			showBundleInfo(exePath, logger)
		case "verify":
			verifyBundle(exePath, logger)
		case "metadata":
			showMetadata(exePath, logger)
		case "extract":
			if len(args) < 3 {
				fmt.Fprintf(os.Stderr, "Error: extract requires slot index and output directory\n")
				fmt.Fprintf(os.Stderr, "Usage: extract <slot_index> <output_dir>\n")
				os.Exit(1)
			}
			extractSlot(exePath, args[1], args[2], logger)
		case "run":
			// Run with remaining arguments
			if err := execBundle(exePath, args[1:], userCwd, logger); err != nil {
				fmt.Fprintf(os.Stderr, "Error: %v\n", err)
				os.Exit(1)
			}
			// If we reach here, exec failed
			os.Exit(1)
		default:
			fmt.Fprintf(os.Stderr, "Error: Unknown command '%s'\n", args[0])
			fmt.Fprintf(os.Stderr, "Available commands: info, verify, metadata, extract, run\n")
			os.Exit(1)
		}
		return
	}

	if err := execBundle(exePath, args, userCwd, logger); err != nil {
		logger.Error("❌ Failed to exec command", "error", err)
		os.Exit(1)
	}
	// If we reach here, exec failed (shouldn't happen on Unix)
	os.Exit(1)
}

// Launch is the backward-compatible entry point
func Launch(exePath string, args []string) {
	LaunchWithLogLevel(exePath, args, "", "")
}

// execBundle prepares and executes a bundle
func execBundle(exePath string, args []string, userCwd string, logger hclog.Logger) error {
	// Check execution mode
	execMode := os.Getenv("FLAVOR_EXEC_MODE")
	useSpawn := strings.ToLower(execMode) == "spawn"
	
	if useSpawn {
		logger.Debug("👶 Using spawn mode (child process)")
		return spawnBundle(exePath, args, userCwd, logger)
	}
	
	logger.Debug("🔄 Using exec mode (process replacement)")
	return execBundleReplace(exePath, args, userCwd, logger)
}

// execBundleReplace prepares and executes a bundle using syscall.Exec (process replacement)
func execBundleReplace(exePath string, args []string, userCwd string, logger hclog.Logger) error {
	// Prepare the command (do all extraction and setup)
	var cmd *exec.Cmd
	cmd, err := runBundleWithCwd(exePath, args, userCwd, logger)
	if err != nil {
		return err
	}

	// Convert exec.Cmd to syscall.Exec arguments
	binary := cmd.Path
	argv := cmd.Args
	if argv == nil || len(argv) == 0 {
		argv = []string{binary}
	}
	
	// Convert environment to []string format
	envv := cmd.Env
	if envv == nil {
		envv = os.Environ()
	}

	logger.Info("🔄 Replacing process via exec", "binary", binary, "args", argv[1:])
	
	// This replaces the current process and never returns on success
	err = syscall.Exec(binary, argv, envv)
	if err != nil {
		return fmt.Errorf("syscall.Exec failed: %w", err)
	}
	
	// This should never be reached
	return errors.New("syscall.Exec returned unexpectedly")
}

// Note: Signal handling and cleanup functions removed - not compatible with syscall.Exec
// When using exec, the process is replaced entirely so there's no parent process
// to handle signals or perform cleanup. The new process handles its own signals.

func showBundleInfo(exePath string, logger hclog.Logger) {
	reader, err := NewReader(exePath)
	if err != nil {
		logger.Error("❌ Failed to create reader", "error", err)
		os.Exit(1)
	}
	defer func() {
		if err := reader.Close(); err != nil {
			logger.Error("Failed to close reader", "error", err)
		}
	}()

	index, err := reader.ReadIndex()
	if err != nil {
		logger.Error("❌ Failed to read index", "error", err)
		os.Exit(1)
	}

	metadata, err := reader.ReadMetadata()
	if err != nil {
		logger.Error("❌ Failed to read metadata", "error", err)
		os.Exit(1)
	}

	launcherType := detectLauncherType(exePath)
	builderType := detectBuilderType(metadata)

	totalSize := int64(0)
	encodingTypes := make(map[string]int)

	for _, slot := range metadata.Slots {
		totalSize += slot.Size
		if slot.Encoding != "" && slot.Encoding != "none" {
			encodingTypes[slot.Encoding]++
		}
	}

	encodingInfo := "none"
	if len(encodingTypes) > 0 {
		var types []string
		for t := range encodingTypes {
			types = append(types, t)
		}
		encodingInfo = strings.Join(types, ", ")
	}

	verifyStatus := "✓"
	_, err = reader.VerifyMagic()
	if err != nil {
		verifyStatus = "✗"
	}

	fmt.Printf("%s v%s [PSPF/%s]\n",
		metadata.Package.Name,
		metadata.Package.Version,
		strings.TrimPrefix(metadata.Format, "PSPF/"))

	fmt.Printf("Built with: %s | Launcher: %s | Size: %.1fMB\n",
		builderType,
		launcherType,
		float64(index.PackageSize)/(1024*1024))

	fmt.Printf("Slots: %d (%s) | Verified: %s\n",
		len(metadata.Slots),
		encodingInfo,
		verifyStatus)

	fmt.Printf("\nRun with: %s\n", metadata.Execution.Command)
	fmt.Printf("CLI Mode: Use 'run' to execute, 'extract' to unpack\n")
}

func extractSlot(exePath, slotStr, outputDir string, logger hclog.Logger) {
	slotIndex, err := strconv.Atoi(slotStr)
	if err != nil {
		logger.Error("Invalid slot index", "slot", slotStr)
		os.Exit(1)
	}

	reader, err := NewReader(exePath)
	if err != nil {
		logger.Error("❌ Failed to create reader", "error", err)
		os.Exit(1)
	}
	defer func() {
		if err := reader.Close(); err != nil {
			logger.Error("Failed to close reader", "error", err)
		}
	}()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		logger.Error("❌ Failed to read metadata", "error", err)
		os.Exit(1)
	}

	if slotIndex < 0 || slotIndex >= len(metadata.Slots) {
		logger.Error("Slot index out of range")
		os.Exit(1)
	}

	slot := metadata.Slots[slotIndex]
	outputPath, err := reader.ExtractSlot(slotIndex, outputDir)
	if err != nil {
		logger.Error("❌ Failed to extract slot", "error", err)
		os.Exit(1)
	}

	fmt.Printf("Extracted slot %d (%s) to %s\n", slotIndex, slot.ID, outputPath)
}

func detectLauncherType(exePath string) string {
	if strings.Contains(os.Args[0], "test-cli.pspf") || strings.Contains(exePath, "test-cli.pspf") {
		return "go"
	}
	if strings.Contains(os.Args[0], "rust-go.pspf") || strings.Contains(exePath, "rust-go.pspf") {
		return "go"
	}
	if strings.Contains(os.Args[0], "go-rust.pspf") || strings.Contains(exePath, "go-rust.pspf") {
		return "rust"
	}
	if strings.Contains(os.Args[0], "rust-rust.pspf") || strings.Contains(exePath, "rust-rust.pspf") {
		return "rust"
	}

	data, err := os.ReadFile(exePath)
	if err != nil {
		return "unknown"
	}

	size := len(data)
	if size > 65536 {
		size = 65536
	}
	header := data[:size]
	headerStr := string(header)

	if strings.Contains(headerStr, "go.buildid") || strings.Contains(headerStr, "runtime.main") {
		return "go"
	}

	if strings.Contains(headerStr, "rust_panic") || strings.Contains(headerStr, "_ZN") {
		return "rust"
	}

	if strings.HasPrefix(headerStr, "#!/usr/bin/env python") || strings.HasPrefix(headerStr, "#!/usr/bin/python") {
		return "python"
	}

	if strings.HasPrefix(headerStr, "#!/usr/bin/env node") || strings.HasPrefix(headerStr, "#!/usr/bin/node") {
		return "node"
	}

	return "unknown"
}

func showMetadata(exePath string, logger hclog.Logger) {
	reader, err := NewReader(exePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: Failed to create reader: %v\n", err)
		os.Exit(1)
	}
	defer func() {
		if err := reader.Close(); err != nil {
			logger.Debug("Failed to close reader", "error", err)
		}
	}()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: Failed to read metadata: %v\n", err)
		os.Exit(1)
	}

	// Output raw JSON metadata
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(metadata); err != nil {
		fmt.Fprintf(os.Stderr, "Error: Failed to encode metadata: %v\n", err)
		os.Exit(1)
	}
}

func verifyBundle(exePath string, logger hclog.Logger) {
	reader, err := NewReader(exePath)
	if err != nil {
		logger.Error("❌ Failed to create reader", "error", err)
		os.Exit(1)
	}
	defer func() {
		if err := reader.Close(); err != nil {
			logger.Error("Failed to close reader", "error", err)
		}
	}()

	fmt.Println("Verifying bundle integrity...")

	errors := []string{}

	_, err = reader.VerifyMagic()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Magic verification failed: %v", err))
	} else {
		fmt.Println("✓ Magic sequence valid")
	}

	_, err = reader.ReadIndex()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Index verification failed: %v", err))
	} else {
		fmt.Println("✓ Index checksum valid")
	}

	metadata, err := reader.ReadMetadata()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Metadata verification failed: %v", err))
	} else {
		fmt.Println("✓ Metadata checksum valid")

		for i, slot := range metadata.Slots {
			_, err := reader.ReadSlot(i)
			if err != nil {
				errors = append(errors, fmt.Sprintf("Slot %d (%s) read failed: %v", i, slot.ID, err))
			} else {
				fmt.Printf("✓ Slot %d (%s) checksum valid\n", i, slot.ID)
			}
		}
	}

	if len(errors) == 0 {
		fmt.Println("\n✓ Bundle verification passed")
	} else {
		fmt.Println("\n✗ Bundle verification failed:")
		for _, err := range errors {
			fmt.Printf("  - %s\n", err)
		}
		os.Exit(1)
	}
}

func detectBuilderType(metadata *Metadata) string {
	if metadata.Build != nil && metadata.Build.Tool != "" {
		return metadata.Build.Tool
	}
	return "unknown/flavor-builder"
}

// spawnBundle executes the bundle as a child process (doesn't replace current process)
func spawnBundle(exePath string, args []string, userCwd string, logger hclog.Logger) error {
	// Prepare the command (do all extraction and setup)
	cmd, err := runBundleWithCwd(exePath, args, userCwd, logger)
	if err != nil {
		return fmt.Errorf("failed to prepare command: %w", err)
	}
	
	// Connect stdio
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	
	logger.Info("🚀 Spawning child process", "command", cmd.Path, "args", cmd.Args[1:])
	
	// Start and wait for the process
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start process: %w", err)
	}
	
	// Track volatile paths for cleanup
	// TODO: Get volatile paths from execution context
	
	if err := cmd.Wait(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			// Return the exit code
			if status, ok := exitErr.Sys().(syscall.WaitStatus); ok {
				// Clean up volatile paths before exit
				// TODO: Implement volatile cleanup
				os.Exit(status.ExitStatus())
			}
		}
		return fmt.Errorf("process failed: %w", err)
	}
	
	// Clean up volatile paths on success
	// TODO: Implement volatile cleanup
	
	return nil
}
