package format_2025

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"

	"github.com/hashicorp/go-hclog"
)

// showBundleInfo displays bundle information in human-readable format
func showBundleInfo(exePath string, logger hclog.Logger) {
	// Prepare bundle path (may extract from PE resources on Windows)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		logger.Error("❌ Failed to prepare bundle path", "error", err)
		os.Exit(1)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
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
	codecTypes := make(map[string]int)

	for _, slot := range metadata.Slots {
		totalSize += slot.Size
		if slot.Operations != "" && slot.Operations != "none" {
			codecTypes[slot.Operations]++
		}
	}

	codecInfo := "none"
	if len(codecTypes) > 0 {
		var types []string
		for t := range codecTypes {
			types = append(types, t)
		}
		codecInfo = strings.Join(types, ", ")
	}

	verifyStatus := "✓"
	_, err = reader.VerifyMagicTrailer()
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
		codecInfo,
		verifyStatus)

	fmt.Printf("\nRun with: %s\n", metadata.Execution.Command)
	fmt.Printf("CLI Mode: Use 'run' to execute, 'extract' to unpack\n")
}

// extractSlot extracts a specific slot to an output directory
func extractSlot(exePath, slotStr, outputDir string, logger hclog.Logger) {
	slotIndex, err := strconv.Atoi(slotStr)
	if err != nil {
		logger.Error("Invalid slot index", "slot", slotStr)
		os.Exit(1)
	}

	// Prepare bundle path (may extract from PE resources on Windows)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		logger.Error("❌ Failed to prepare bundle path", "error", err)
		os.Exit(1)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
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

// detectLauncherType attempts to determine the launcher implementation language
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

// showMetadata outputs the raw JSON metadata
func showMetadata(exePath string, logger hclog.Logger) {
	// Prepare bundle path (may extract from PE resources on Windows)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: Failed to prepare bundle path: %v\n", err)
		os.Exit(1)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
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

// verifyBundle performs integrity verification on the bundle
func verifyBundle(exePath string, logger hclog.Logger) {
	// Prepare bundle path (may extract from PE resources on Windows)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		logger.Error("❌ Failed to prepare bundle path", "error", err)
		os.Exit(1)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
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

	_, err = reader.VerifyMagicTrailer()
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

// detectBuilderType determines the builder implementation from metadata
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

	// Note: Volatile path cleanup would require passing metadata and workenvDir
	// from runBundleWithCwd. This is a future enhancement.

	if err := cmd.Wait(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			// Child process exited with non-zero code
			exitCode := exitErr.ExitCode()
			logger.Info("⏹️ Process exited with error", "code", exitCode)
			logger.Debug("Calling os.Exit to propagate child exit code", "code", exitCode)
			os.Exit(exitCode)
			// Should never reach here - os.Exit terminates the process
			logger.Error("🚨 CRITICAL: os.Exit returned unexpectedly", "code", exitCode)
		}
		// Type assertion failed - this is unexpected
		logger.Error("Failed to extract exit code from exec.ExitError", "error", err)
		return fmt.Errorf("process failed: %w", err)
	}

	// Child process exited successfully with code 0
	logger.Info("⏹️ Process exited successfully", "code", 0)
	logger.Debug("Calling os.Exit(0) to terminate launcher with success")
	os.Exit(0)

	// This should never be reached (os.Exit terminates the process)
	logger.Error("🚨 CRITICAL: os.Exit(0) returned unexpectedly - this should be impossible")
	return fmt.Errorf("unreachable code executed: os.Exit(0) returned")
}
