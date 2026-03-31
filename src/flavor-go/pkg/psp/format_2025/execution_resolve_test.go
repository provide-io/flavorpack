package format_2025

import (
	"os"
	"path/filepath"
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
