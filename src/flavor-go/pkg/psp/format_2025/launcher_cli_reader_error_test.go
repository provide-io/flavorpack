package format_2025

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestShowMetadataNewReaderError covers lines 205-208 in launcher_cli.go:
// when NewReaderWithLogger fails (non-existent bundle file), showMetadata
// calls osExitFn(1). prepareBundlePath succeeds (returns path as-is),
// then NewReaderWithLogger fails when the file doesn't exist.
func TestShowMetadataNewReaderError(t *testing.T) {
	// Non-existent path so prepareBundlePath returns it directly,
	// but NewReaderWithLogger fails to open it.
	nonExistent := filepath.Join(t.TempDir(), "nonexistent.psp")
	logger := hclog.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		showMetadata(nonExistent, logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in showMetadata")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 when NewReaderWithLogger fails, got %d", exitCode)
	}
}

// TestShowMetadataReadMetadataError covers lines 216-219 in launcher_cli.go:
// when ReadMetadata fails (bundle has bad metadata), showMetadata calls osExitFn(1).
// We corrupt the gzip metadata archive in the bundle at the known metadata offset.
func TestShowMetadataReadMetadataError(t *testing.T) {
	// Build a valid bundle.
	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "meta-error-slot",
		Target: "{workenv}",
	}, 0, false)

	// Read the bundle and find the metadata offset from the index in the trailer.
	data, err := os.ReadFile(bundle)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if len(data) < MagicTrailerSize {
		t.Fatalf("bundle too small: %d bytes", len(data))
	}

	// Index starts at trailerStart+4 (after start emoji bytes).
	trailerStart := len(data) - MagicTrailerSize
	idxBytes := data[trailerStart+4 : trailerStart+4+IndexSize]
	var idx PSPFIndex
	if err := idx.Unpack(idxBytes); err != nil {
		t.Fatalf("idx.Unpack: %v", err)
	}

	// Corrupt the first 10 bytes of the metadata archive (at MetadataOffset)
	// to make gzip.NewReader fail.
	metaOff := int(idx.MetadataOffset)
	if metaOff+10 < len(data)-MagicTrailerSize {
		for i := metaOff; i < metaOff+10; i++ {
			data[i] = 0xff
		}
	}
	if err := os.WriteFile(bundle, data, 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	logger := hclog.NewNullLogger()
	exitCode, panicked := withStubbedExit(func() {
		showMetadata(bundle, logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in showMetadata")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 when ReadMetadata fails, got %d", exitCode)
	}
}

// TestShowBundleInfoNewReaderError covers lines 27-30 in launcher_cli.go:
// when NewReaderWithLogger fails, showBundleInfo calls osExitFn(1).
func TestShowBundleInfoNewReaderError(t *testing.T) {
	nonExistent := filepath.Join(t.TempDir(), "nonexistent.psp")
	logger := hclog.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		showBundleInfo(nonExistent, logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in showBundleInfo")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 when NewReaderWithLogger fails in showBundleInfo, got %d", exitCode)
	}
}

// TestExtractSlotNewReaderError covers lines 115-118 in launcher_cli.go:
// when NewReaderWithLogger fails, extractSlot calls osExitFn(1).
func TestExtractSlotNewReaderError(t *testing.T) {
	nonExistent := filepath.Join(t.TempDir(), "nonexistent.psp")
	logger := hclog.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		extractSlot(nonExistent, "0", t.TempDir(), logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in extractSlot")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 when NewReaderWithLogger fails in extractSlot, got %d", exitCode)
	}
}

// TestVerifyBundleNewReaderError covers lines 243-246 in launcher_cli.go:
// when NewReaderWithLogger fails, verifyBundle calls osExitFn(1).
func TestVerifyBundleNewReaderError(t *testing.T) {
	nonExistent := filepath.Join(t.TempDir(), "nonexistent.psp")
	logger := hclog.NewNullLogger()

	exitCode, panicked := withStubbedExit(func() {
		verifyBundle(nonExistent, logger)
	})
	if panicked {
		t.Fatal("unexpected non-exit panic in verifyBundle")
	}
	if exitCode != 1 {
		t.Fatalf("expected exit code 1 when NewReaderWithLogger fails in verifyBundle, got %d", exitCode)
	}
}
