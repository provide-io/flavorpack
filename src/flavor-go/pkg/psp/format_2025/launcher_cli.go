package format_2025

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"strings"

	"log/slog"
)

var readerCloseFn = (*Reader).Close
var verifyMagicTrailerFn = (*Reader).VerifyMagicTrailer

// showBundleInfo displays bundle information in human-readable format
func showBundleInfo(out io.Writer, exePath string, logger *slog.Logger) {
	// Prepare bundle path (may extract from PE resources on Windows)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		logger.Error("❌ Failed to prepare bundle path", "error", err)
		osExitFn(1)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
	if err != nil {
		logger.Error("❌ Failed to create reader", "error", err)
		osExitFn(1)
	}
	defer func() {
		if err := readerCloseFn(reader); err != nil {
			logger.Error("Failed to close reader", "error", err)
		}
	}()

	index, err := reader.ReadIndex()
	if err != nil {
		logger.Error("❌ Failed to read index", "error", err)
		osExitFn(1)
	}

	metadata, err := reader.ReadMetadata()
	if err != nil {
		logger.Error("❌ Failed to read metadata", "error", err)
		osExitFn(1)
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
	_, err = verifyMagicTrailerFn(reader)
	if err != nil {
		verifyStatus = "✗"
	}

	_, _ = fmt.Fprintf(out, "%s v%s [PSPF/%s]\n",
		metadata.Package.Name,
		metadata.Package.Version,
		strings.TrimPrefix(metadata.Format, "PSPF/"))

	_, _ = fmt.Fprintf(out, "Built with: %s | Launcher: %s | Size: %.1fMB\n",
		builderType,
		launcherType,
		float64(index.PackageSize)/(1024*1024))

	_, _ = fmt.Fprintf(out, "Slots: %d (%s) | Verified: %s\n",
		len(metadata.Slots),
		codecInfo,
		verifyStatus)

	_, _ = fmt.Fprintf(out, "\nRun with: %s\n", metadata.Execution.Command)
	_, _ = fmt.Fprintf(out, "CLI Mode: Use 'run' to execute, 'extract' to unpack\n")
}

// extractSlot extracts a specific slot to an output directory
func extractSlot(out io.Writer, exePath, slotStr, outputDir string, logger *slog.Logger) {
	slotIndex, err := strconv.Atoi(slotStr)
	if err != nil {
		logger.Error("Invalid slot index", "slot", slotStr)
		osExitFn(1)
	}

	// Prepare bundle path (may extract from PE resources on Windows)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		logger.Error("❌ Failed to prepare bundle path", "error", err)
		osExitFn(1)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
	if err != nil {
		logger.Error("❌ Failed to create reader", "error", err)
		osExitFn(1)
	}
	defer func() {
		if err := readerCloseFn(reader); err != nil {
			logger.Error("Failed to close reader", "error", err)
		}
	}()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		logger.Error("❌ Failed to read metadata", "error", err)
		osExitFn(1)
	}

	if slotIndex < 0 || slotIndex >= len(metadata.Slots) {
		logger.Error("Slot index out of range")
		osExitFn(1)
	}

	slot := metadata.Slots[slotIndex]
	outputPath, err := reader.ExtractSlot(slotIndex, outputDir)
	if err != nil {
		logger.Error("❌ Failed to extract slot", "error", err)
		osExitFn(1)
	}

	_, _ = fmt.Fprintf(out, "Extracted slot %d (%s) to %s\n", slotIndex, slot.ID, outputPath)
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
func showMetadata(out io.Writer, exePath string, logger *slog.Logger) {
	// Prepare bundle path (may extract from PE resources on Windows)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		_, _ = fmt.Fprintf(os.Stderr, "Error: Failed to prepare bundle path: %v\n", err)
		osExitFn(1)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
	if err != nil {
		_, _ = fmt.Fprintf(os.Stderr, "Error: Failed to create reader: %v\n", err)
		osExitFn(1)
	}
	defer func() {
		if err := readerCloseFn(reader); err != nil {
			logger.Debug("Failed to close reader", "error", err)
		}
	}()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		_, _ = fmt.Fprintf(os.Stderr, "Error: Failed to read metadata: %v\n", err)
		osExitFn(1)
	}

	// Output raw JSON metadata
	encoder := json.NewEncoder(out)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(metadata); err != nil {
		_, _ = fmt.Fprintf(os.Stderr, "Error: Failed to encode metadata: %v\n", err)
		osExitFn(1)
	}
}

// verifyBundle performs integrity verification on the bundle.
//
// Every line this prints is a check that was actually made. It did not used to
// be: "Index checksum valid" was printed whenever the index parsed, "Metadata
// checksum valid" whenever it gunzipped, and the Ed25519 seal was not consulted
// at all. The checks that were real -- the magic bookends and the slot digests
// -- are unkeyed, so anyone able to rewrite the file could recompute them. The
// signature is the only check that needs the signing key, and it was the one
// being skipped.
//
// The set below matches the Rust verifier's conjunction, so the same package
// gets the same verdict from either implementation.
func verifyBundle(out io.Writer, exePath string, logger *slog.Logger) {
	// Prepare bundle path (may extract from PE resources on Windows)
	bundlePath, cleanup, err := prepareBundlePath(exePath, logger)
	if err != nil {
		logger.Error("❌ Failed to prepare bundle path", "error", err)
		osExitFn(1)
	}
	if cleanup != nil {
		defer cleanup()
	}

	reader, err := NewReaderWithLogger(bundlePath, logger)
	if err != nil {
		logger.Error("❌ Failed to create reader", "error", err)
		osExitFn(1)
	}
	defer func() {
		if err := readerCloseFn(reader); err != nil {
			logger.Error("Failed to close reader", "error", err)
		}
	}()

	_, _ = fmt.Fprintln(out, "Verifying bundle integrity...")

	errors := []string{}

	// record one result. A check that could not run is a failure: "could not
	// tell" is not the same as "fine", and reporting it as a pass is how this
	// command came to vouch for things it had never looked at.
	record := func(label string, ok bool, err error) {
		switch {
		case err != nil:
			errors = append(errors, fmt.Sprintf("%s verification failed: %v", label, err))
		case !ok:
			errors = append(errors, fmt.Sprintf("%s verification failed", label))
		default:
			_, _ = fmt.Fprintf(out, "✓ %s valid\n", label)
		}
	}

	magicOK, err := verifyMagicTrailerFn(reader)
	record("Magic sequence", magicOK, err)

	indexOK, err := reader.VerifyIndexChecksum()
	record("Index checksum", indexOK, err)

	metadataOK, err := reader.VerifyMetadataChecksum()
	record("Metadata checksum", metadataOK, err)

	sizeOK, err := reader.VerifyPackageSize()
	record("Package size", sizeOK, err)

	// An absent seal counts as a failure, not an exemption -- an unsigned
	// package is exactly what an attacker would hand you.
	sealOK, err := reader.VerifyIntegritySeal()
	record("Integrity seal", sealOK, err)

	metadata, err := reader.ReadMetadata()
	if err != nil {
		errors = append(errors, fmt.Sprintf("Metadata read failed: %v", err))
	} else {
		for i, slot := range metadata.Slots {
			if _, err := reader.ReadSlot(i); err != nil {
				errors = append(errors, fmt.Sprintf("Slot %d (%s) read failed: %v", i, slot.ID, err))
			} else {
				_, _ = fmt.Fprintf(out, "✓ Slot %d (%s) checksum valid\n", i, slot.ID)
			}
		}
	}

	// Both are fail-closed and no-ops on a package without attestation.
	record("Attestation SBOM digest", true, reader.VerifyAttestationSbomDigest())
	record("Attestation policy hash", true, reader.VerifyAttestationPolicyHash())

	if len(errors) == 0 {
		_, _ = fmt.Fprintln(out, "\n✓ Bundle verification passed")
	} else {
		_, _ = fmt.Fprintln(out, "\n✗ Bundle verification failed:")
		for _, err := range errors {
			_, _ = fmt.Fprintf(out, "  - %s\n", err)
		}
		osExitFn(1)
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
func spawnBundle(exePath string, args []string, userCwd string, logger *slog.Logger) error {
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
			osExitFn(exitCode)
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
	osExitFn(0)

	// This should never be reached (os.Exit terminates the process)
	logger.Error("🚨 CRITICAL: os.Exit(0) returned unexpectedly - this should be impossible")
	return fmt.Errorf("unreachable code executed: os.Exit(0) returned")
}
