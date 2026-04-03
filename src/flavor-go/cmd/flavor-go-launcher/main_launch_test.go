package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

// buildTestBundle creates a minimal valid PSPF bundle and returns its path.
func buildTestBundle(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()

	launcherPath := filepath.Join(dir, "launcher.sh")
	if err := os.WriteFile(launcherPath, []byte("#!/bin/sh\nexit 0\n"), 0o700); err != nil {
		t.Fatalf("WriteFile(launcher): %v", err)
	}

	manifest := format_2025.BuildOptions{
		Package: format_2025.PackageConfig{
			Name:    "launcher-test",
			Version: "0.0.1",
		},
		Execution: format_2025.ExecutionConfig{
			Command: "/bin/true",
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

	outputPath := filepath.Join(dir, "test.psp")
	format_2025.BuildWithOptions(manifestPath, outputPath, launcherPath, "", "", "")
	if _, err := os.Stat(outputPath); err != nil {
		t.Fatalf("expected bundle to exist: %v", err)
	}
	return outputPath
}

// TestLauncherMainLaunchFnIsCalled covers the launchFn call at main.go:32 by
// overriding launchFn with a no-op that records whether it was called.
// This allows in-process testing without os.Exit terminating the test.
func TestLauncherMainLaunchFnIsCalled(t *testing.T) {
	t.Parallel()

	bundlePath := buildTestBundle(t)

	called := false
	var capturedExePath string

	oldLaunchFn := launchFn
	t.Cleanup(func() { launchFn = oldLaunchFn })
	launchFn = func(exePath string, args []string, cliLogLevel, cliLogSource string) {
		called = true
		capturedExePath = exePath
	}

	oldExeFn := executablePathFn
	t.Cleanup(func() { executablePathFn = oldExeFn })
	executablePathFn = func() (string, error) {
		return bundlePath, nil
	}

	os.Args = []string{bundlePath}
	main()

	if !called {
		t.Fatal("expected launchFn to be called, but it was not")
	}
	if capturedExePath != bundlePath {
		t.Fatalf("expected exePath=%q, got %q", bundlePath, capturedExePath)
	}
}
