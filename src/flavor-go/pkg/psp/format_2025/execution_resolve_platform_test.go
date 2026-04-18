// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestResolveExecutableWindowsFallbackPython3(t *testing.T) {
	// Simulate Windows platform
	oldGOOS := currentGOOS
	t.Cleanup(func() { currentGOOS = oldGOOS })
	currentGOOS = "windows"

	// Create a temp dir with python.exe to simulate Windows PATH
	tmpDir := t.TempDir()
	pythonExe := filepath.Join(tmpDir, "python.exe")
	if err := os.WriteFile(pythonExe, []byte("fake"), 0o755); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	t.Setenv("PATH", tmpDir)

	logger := logging.NewNullLogger()
	// exec.LookPath won't find "python3" on most systems, so it falls into the Windows fallback
	// We mock PATH to have python.exe but not python3
	got := resolveExecutable("python3", logger)
	if got != pythonExe {
		t.Fatalf("resolveExecutable(python3) on windows = %q, want %q", got, pythonExe)
	}
}

func TestResolveExecutableWindowsFallbackSh(t *testing.T) {
	oldGOOS := currentGOOS
	t.Cleanup(func() { currentGOOS = oldGOOS })
	currentGOOS = "windows"

	tmpDir := t.TempDir()
	bashExe := filepath.Join(tmpDir, "bash.exe")
	if err := os.WriteFile(bashExe, []byte("fake"), 0o755); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	t.Setenv("PATH", tmpDir)

	logger := logging.NewNullLogger()
	got := resolveExecutable("sh", logger)
	if got != bashExe {
		t.Fatalf("resolveExecutable(sh) on windows = %q, want %q", got, bashExe)
	}
}

func TestResolveExecutableWindowsFallbackNotFound(t *testing.T) {
	oldGOOS := currentGOOS
	t.Cleanup(func() { currentGOOS = oldGOOS })
	currentGOOS = "windows"

	// Empty PATH so no fallback found either
	t.Setenv("PATH", t.TempDir()) // dir exists but no executables

	logger := logging.NewNullLogger()
	// "python3" not found, fallback "python.exe" not found either → returns "python3" as-is
	got := resolveExecutable("python3", logger)
	if got != "python3" {
		t.Fatalf("resolveExecutable(python3) windows no fallback = %q, want %q", got, "python3")
	}
}

func TestResolveExecutableWindowsUnknownName(t *testing.T) {
	oldGOOS := currentGOOS
	t.Cleanup(func() { currentGOOS = oldGOOS })
	currentGOOS = "windows"

	t.Setenv("PATH", t.TempDir())

	logger := logging.NewNullLogger()
	// "curl" has no Windows fallback, goes to return-basename path
	got := resolveExecutable("curl", logger)
	if got != "curl" {
		t.Fatalf("resolveExecutable(curl) windows = %q, want %q", got, "curl")
	}
}
