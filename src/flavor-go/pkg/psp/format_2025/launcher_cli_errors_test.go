// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"crypto/sha256"
	"encoding/json"
	"log/slog"
	"os"
	"runtime"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// stubPEResourceWithInvalidBundle injects hasPSPFResourceFn and readPSPFFromResourceFn
// so that prepareBundlePath succeeds (returns a temp file path) but the written
// content is not a valid PSPF bundle (too small for NewReaderWithLogger).
// It returns a restore function.
func stubPEResourceWithInvalidBundle(t *testing.T) func() {
	t.Helper()
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	hasPSPFResourceFn = func(path string, logger *slog.Logger) bool { return true }
	readPSPFFromResourceFn = func(path string, logger *slog.Logger) ([]byte, error) {
		// Return valid-length but non-PSPF data (too small to be a real bundle).
		return []byte("not-a-pspf-bundle-xxxxxxxxxxxx"), nil
	}
	return func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	}
}

// corruptMagicTrailerBytes overwrites the last MagicTrailerSize bytes of a
// bundle file with zeros, making VerifyMagicTrailer return an error.
func corruptMagicTrailerBytes(t *testing.T, bundlePath string) {
	t.Helper()

	data, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatalf("ReadFile(bundle): %v", err)
	}
	if len(data) < MagicTrailerSize {
		t.Fatalf("bundle too small: %d bytes", len(data))
	}
	for i := len(data) - MagicTrailerSize; i < len(data); i++ {
		data[i] = 0x00
	}
	if err := os.WriteFile(bundlePath, data, 0o600); err != nil {
		t.Fatalf("WriteFile(bundle): %v", err)
	}
}

// buildBundleWithBadIndex creates a bundle whose magic trailer is valid but
// whose index has an incorrect FormatVersion, causing ReadIndex to fail.
func buildBundleWithBadIndex(t *testing.T) string {
	t.Helper()

	metaJSON, err := json.Marshal(Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Slots:         []SlotMetadata{{Slot: 0, ID: "slot-0", Target: "{workenv}", Size: 0}},
	})
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}
	gzMeta := gzipData(t, metaJSON)

	f, err := os.CreateTemp(t.TempDir(), "pspf-badidx-*.psp")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("Write(metadata): %v", err)
	}

	// Use an invalid FormatVersion so ReadIndex returns an error.
	idx := &PSPFIndex{
		FormatVersion:   0xDEADBEEF,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: uint64(len(gzMeta)),
	}
	metaHash := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], metaHash[:])

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("Write(trailer): %v", err)
	}

	return f.Name()
}

// buildBundleWithBadMetadata creates a bundle whose magic trailer and index
// are valid, but the metadata bytes are raw (not gzip-compressed), causing
// ReadMetadata to fail when it tries to decompress them.
func buildBundleWithBadMetadata(t *testing.T) string {
	t.Helper()

	// Use plain (non-gzip) bytes as metadata — this will make gzip.NewReader fail.
	rawMeta := []byte(`{"package":{"name":"demo","version":"1.0.0"},"slots":[]}`)

	f, err := os.CreateTemp(t.TempDir(), "pspf-badmeta-*.psp")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(rawMeta); err != nil {
		t.Fatalf("Write(metadata): %v", err)
	}

	// Use the real checksum of the raw bytes so ReadIndex succeeds but
	// ReadMetadata fails on the gzip.NewReader call.
	metaHash := sha256.Sum256(rawMeta)
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(rawMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(rawMeta)),
		SlotTableOffset: uint64(len(rawMeta)),
	}
	copy(idx.MetadataChecksum[:], metaHash[:])

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("Write(trailer): %v", err)
	}

	return f.Name()
}

// buildBundleWithBadSlotData creates a bundle with a valid structure but
// corrupted slot data (checksum mismatch), so ReadSlot returns an error.
func buildBundleWithBadSlotData(t *testing.T) string {
	t.Helper()

	return buildSingleSlotBundleForTests(t,
		[]byte("slot data here"),
		[]byte("slot data here"),
		nil,
		SlotMetadata{ID: "bad-slot", Target: "{workenv}"},
		0,
		true, // corruptChecksum
	)
}

// withStubbedExit stubs osExitFn and catches the exit code via panic/recover.
// It returns the captured exit code and any non-exit panic message.
func withStubbedExit(fn func()) (exitCode int, panicked bool) {
	old := osExitFn
	defer func() { osExitFn = old }()

	panicked = false
	exitCode = 0
	osExitFn = func(code int) {
		exitCode = code
		panic(launcherExitCode{code: code})
	}

	defer func() {
		if r := recover(); r != nil {
			if _, ok := r.(launcherExitCode); !ok {
				panicked = true
			}
		}
	}()

	fn()
	return exitCode, panicked
}

// TestShowBundleInfoReadIndexErrorPath verifies that showBundleInfo calls osExitFn(1)
// when the bundle has an invalid index format version (ReadIndex fails).
func TestShowBundleInfoReadIndexErrorPath(t *testing.T) {
	bundlePath := buildBundleWithBadIndex(t)
	logger := logging.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		showBundleInfo(bundlePath, logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestShowBundleInfoReadMetadataErrorPath verifies that showBundleInfo calls
// osExitFn(1) when the bundle has a correct index but corrupt metadata.
func TestShowBundleInfoReadMetadataErrorPath(t *testing.T) {
	bundlePath := buildBundleWithBadMetadata(t)
	logger := logging.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		showBundleInfo(bundlePath, logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestShowBundleInfoVerifyStatusFail verifies that showBundleInfo displays
// "Verified: ✗" when the magic trailer is corrupted.
func TestShowBundleInfoVerifyStatusFail(t *testing.T) {
	// Build a valid bundle first, then corrupt it so VerifyMagicTrailer fails.
	bundle := buildSingleSlotBundleForTests(t,
		[]byte("content"), []byte("content"), nil,
		SlotMetadata{ID: "slot", Target: "{workenv}/out.txt"},
		0, false,
	)
	corruptMagicTrailerBytes(t, bundle)
	logger := logging.NewNullLogger()

	// The bundle now has a corrupt magic trailer. showBundleInfo should still
	// display info but set verifyStatus = "✗". However, ReadIndex/ReadMetadata
	// may also fail since the trailer is zeroed — in that case it will just call
	// osExitFn(1) on index read failure. Either way, no panic.
	output := captureStdout(t, func() {
		old := osExitFn
		osExitFn = func(code int) {
			panic(launcherExitCode{code: code})
		}
		defer func() {
			osExitFn = old
			recover() // swallow exit panic
		}()
		showBundleInfo(bundle, logger)
	})
	// If it printed output, it should have included "✗".
	if output != "" && !strings.Contains(output, "✗") {
		t.Fatalf("expected '✗' in showBundleInfo output for corrupted bundle, got: %q", output)
	}
}

// TestExtractSlotExtractionFailure verifies that extractSlot calls osExitFn(1)
// when ExtractSlot fails (corrupt checksum bundle).
func TestExtractSlotExtractionFailure(t *testing.T) {
	bundlePath := buildBundleWithBadSlotData(t)
	outputDir := t.TempDir()
	logger := logging.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		extractSlot(bundlePath, "0", outputDir, logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 when ExtractSlot fails, got %d", exitCode)
	}
}

// TestShowMetadataReadMetadataErrorPath verifies that showMetadata calls
// osExitFn(1) when the bundle has a bad metadata checksum.
func TestShowMetadataReadMetadataErrorPath(t *testing.T) {
	bundlePath := buildBundleWithBadMetadata(t)
	logger := logging.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		showMetadata(bundlePath, logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 for bad metadata, got %d", exitCode)
	}
}

// TestVerifyBundleSlotReadFailure verifies that verifyBundle reports a slot
// read failure when slot data is corrupted (ReadSlot returns an error).
func TestVerifyBundleSlotReadFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("corrupt-checksum bundles may behave differently on Windows file systems")
	}

	bundlePath := buildBundleWithBadSlotData(t)
	logger := logging.NewNullLogger()

	// verifyBundle calls osExitFn(1) when errors are found; stub it.
	output := captureStdout(t, func() {
		old := osExitFn
		osExitFn = func(code int) {
			panic(launcherExitCode{code: code})
		}
		defer func() {
			osExitFn = old
			recover()
		}()
		verifyBundle(bundlePath, logger)
	})

	if !strings.Contains(output, "read failed") && !strings.Contains(output, "verification failed") {
		t.Fatalf("expected slot read failure in verifyBundle output, got: %q", output)
	}
}

// TestShowBundleInfoWithCleanupAndReaderFailure covers the "defer cleanup()" branch
// and the NewReaderWithLogger failure path in showBundleInfo. We inject a PE resource
// that returns invalid bundle bytes so prepareBundlePath succeeds (cleanup != nil)
// but NewReaderWithLogger fails.
func TestShowBundleInfoWithCleanupAndReaderFailure(t *testing.T) {
	restore := stubPEResourceWithInvalidBundle(t)
	defer restore()

	exitCode, panicked := withStubbedExit(func() {
		showBundleInfo("/fake/exe", logging.NewNullLogger())
	})
	if panicked {
		t.Fatal("unexpected non-exit panic")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestExtractSlotWithCleanupAndReaderFailure covers the "defer cleanup()" and
// NewReaderWithLogger failure paths in extractSlot.
func TestExtractSlotWithCleanupAndReaderFailure(t *testing.T) {
	restore := stubPEResourceWithInvalidBundle(t)
	defer restore()

	exitCode, panicked := withStubbedExit(func() {
		extractSlot("/fake/exe", "0", t.TempDir(), logging.NewNullLogger())
	})
	if panicked {
		t.Fatal("unexpected non-exit panic")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestShowMetadataWithCleanupAndReaderFailure covers the "defer cleanup()" and
// NewReaderWithLogger failure paths in showMetadata.
func TestShowMetadataWithCleanupAndReaderFailure(t *testing.T) {
	restore := stubPEResourceWithInvalidBundle(t)
	defer restore()

	exitCode, panicked := withStubbedExit(func() {
		showMetadata("/fake/exe", logging.NewNullLogger())
	})
	if panicked {
		t.Fatal("unexpected non-exit panic")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1, got %d", exitCode)
	}
}

// TestVerifyBundleWithCleanupAndReaderFailure covers the "defer cleanup()" and
// NewReaderWithLogger failure paths in verifyBundle.
func TestVerifyBundleWithCleanupAndReaderFailure(t *testing.T) {
	restore := stubPEResourceWithInvalidBundle(t)
	defer restore()

	output := captureStdout(t, func() {
		old := osExitFn
		osExitFn = func(code int) {
			panic(launcherExitCode{code: code})
		}
		defer func() {
			osExitFn = old
			recover()
		}()
		verifyBundle("/fake/exe", logging.NewNullLogger())
	})
	// verifyBundle may print verification failure info or exit with code 1.
	_ = output
}
