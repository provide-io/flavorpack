package pkg

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
	format_2025 "github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

// TestVerifyBundleWithLoggerValidSlot covers verification.go:57-59 — the slot
// read success path inside the metadata.Slots loop. We build a bundle with a
// valid slot and call VerifyBundleWithLogger directly (not via subprocess since
// the bundle is valid and no os.Exit is triggered).
func TestVerifyBundleWithLoggerValidSlot(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()

	// Write a small payload file (the slot source).
	slotFile := filepath.Join(dir, "payload.txt")
	if err := os.WriteFile(slotFile, []byte("hello slot"), 0o600); err != nil {
		t.Fatalf("WriteFile(slot): %v", err)
	}

	// Write a minimal launcher (shell script that accepts --version).
	launcherPath := filepath.Join(dir, "launcher.sh")
	if err := os.WriteFile(launcherPath, []byte("#!/bin/sh\nexit 0\n"), 0o700); err != nil {
		t.Fatalf("WriteFile(launcher): %v", err)
	}

	// Build a manifest with one slot.
	manifest := format_2025.BuildOptions{
		Package:   format_2025.PackageConfig{Name: "verify-slot-test", Version: "1.0.0"},
		Execution: format_2025.ExecutionConfig{Command: "/bin/true"},
		Slots: []format_2025.Slot{
			{ID: "main", Source: slotFile, Target: "payload.txt"},
		},
	}
	manifestJSON, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		t.Fatalf("MarshalIndent: %v", err)
	}
	manifestPath := filepath.Join(dir, "manifest.json")
	if err := os.WriteFile(manifestPath, manifestJSON, 0o600); err != nil {
		t.Fatalf("WriteFile(manifest): %v", err)
	}

	bundlePath := filepath.Join(dir, "bundle.psp")
	format_2025.BuildWithOptions(manifestPath, bundlePath, launcherPath, "", "", "")

	if _, err := os.Stat(bundlePath); err != nil {
		t.Fatalf("bundle not created: %v", err)
	}

	// Call VerifyBundleWithLogger — should succeed and hit line 57-59 in the slot loop.
	logger := hclog.NewNullLogger()
	VerifyBundleWithLogger(bundlePath, logger)
}
