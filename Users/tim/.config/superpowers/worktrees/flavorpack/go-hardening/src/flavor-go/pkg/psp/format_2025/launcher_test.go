package format_2025

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestLaunchWithLogLevelInfoOnBuiltBundle(t *testing.T) {
	dir := t.TempDir()
	launcherPath := filepath.Join(dir, "launcher.sh")
	if err := os.WriteFile(launcherPath, []byte("#!/bin/sh\nexit 0\n"), 0o700); err != nil {
		t.Fatalf("WriteFile(launcher) error = %v", err)
	}

	manifestPath := filepath.Join(dir, "manifest.json")
	manifest := BuildOptions{
		Package: PackageConfig{
			Name:    "demo",
			Version: "1.0.0",
		},
		Execution: ExecutionConfig{
			Command: "/bin/true",
		},
	}
	manifestJSON, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		t.Fatalf("MarshalIndent() error = %v", err)
	}
	if err := os.WriteFile(manifestPath, manifestJSON, 0o600); err != nil {
		t.Fatalf("WriteFile(manifest) error = %v", err)
	}

	outputPath := filepath.Join(dir, "bundle.psp")
	BuildWithOptions(manifestPath, outputPath, launcherPath, "", "", "")

	if _, err := os.Stat(outputPath); err != nil {
		t.Fatalf("expected built bundle to exist: %v", err)
	}

	t.Setenv("FLAVOR_LAUNCHER_CLI", "1")
	LaunchWithLogLevel(outputPath, []string{"info"}, "trace", "test")
}
