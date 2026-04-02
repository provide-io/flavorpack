package format_2025

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/hashicorp/go-hclog"
)

func TestResolveExecutableAndLookPathInEnv(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	dir := t.TempDir()
	executable := filepath.Join(dir, "tool")
	if err := os.WriteFile(executable, []byte("#!/bin/sh\n"), 0o700); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	if got := resolveExecutable(executable, logger); got != executable {
		t.Fatalf("resolveExecutable() = %q, want %q", got, executable)
	}

	if got := resolveExecutable("/definitely/not/here/tool", logger); got != "tool" {
		t.Fatalf("resolveExecutable() basename fallback = %q, want tool", got)
	}

	resolved, err := lookPathInEnv("tool", []string{"PATH=" + dir})
	if err != nil {
		t.Fatalf("lookPathInEnv() error = %v", err)
	}
	if resolved != executable {
		t.Fatalf("lookPathInEnv() = %q, want %q", resolved, executable)
	}

	if _, err := lookPathInEnv("tool", []string{"HOME=/tmp"}); err == nil {
		t.Fatal("expected PATH lookup error")
	}
}

func TestResolveExecutableUsesPathAndLookPathInEnvSupportsEmptyPathEntry(t *testing.T) {
	logger := hclog.NewNullLogger()
	dir := t.TempDir()
	tool := filepath.Join(dir, "tool")
	if err := os.WriteFile(tool, []byte("#!/bin/sh\n"), 0o700); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	t.Setenv("PATH", dir)
	// Windows exec.LookPath requires a PATHEXT extension; extensionless "tool" is Unix-only.
	if runtime.GOOS != "windows" {
		if got := resolveExecutable("/missing/tool", logger); got != tool {
			t.Fatalf("resolveExecutable() PATH resolution = %q, want %q", got, tool)
		}
	}

	wd := t.TempDir()
	localTool := filepath.Join(wd, "local-tool")
	if err := os.WriteFile(localTool, []byte("#!/bin/sh\n"), 0o700); err != nil {
		t.Fatalf("WriteFile(local tool) error = %v", err)
	}

	oldWd, err := os.Getwd()
	if err != nil {
		t.Fatalf("Getwd() error = %v", err)
	}
	if err := os.Chdir(wd); err != nil {
		t.Fatalf("Chdir() error = %v", err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(oldWd); err != nil {
			t.Errorf("restore cwd error = %v", err)
		}
	})

	resolved, err := lookPathInEnv("local-tool", []string{"PATH=" + string(os.PathListSeparator) + "/nowhere"})
	if err != nil {
		t.Fatalf("lookPathInEnv() error = %v", err)
	}
	if resolved != filepath.Join(".", "local-tool") && resolved != "local-tool" {
		t.Fatalf("lookPathInEnv() with empty PATH entry = %q, want local tool path", resolved)
	}
}

func TestLookPathInEnvNotFoundInPath(t *testing.T) {
	// PATH is present but the binary doesn't exist in any listed directory —
	// covers the "executable not found in PATH" return at the end of the function.
	_, err := lookPathInEnv("no-such-exe-xyz-12345", []string{"PATH=/nonexistent/abc:/also/nonexistent"})
	if err == nil {
		t.Fatal("expected not-found error from lookPathInEnv")
	}
}
