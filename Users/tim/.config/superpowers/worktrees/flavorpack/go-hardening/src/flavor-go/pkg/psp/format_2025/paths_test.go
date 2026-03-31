package format_2025

import (
	"os"
	"path/filepath"
	"testing"
)

func TestWorkenvPathsStructureAndExistence(t *testing.T) {
	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, "/tmp/demo.pspf")

	if got := paths.Name(); got != "demo" {
		t.Fatalf("expected workenv name demo, got %q", got)
	}

	if paths.WorkenvExists() {
		t.Fatalf("expected workenv to be absent before creation")
	}
	if paths.MetadataExists() {
		t.Fatalf("expected metadata to be absent before creation")
	}

	mustMkdirAllPSP(t, paths.Workenv())
	mustMkdirAllPSP(t, paths.Metadata())

	if !paths.WorkenvExists() {
		t.Fatalf("expected workenv existence check to succeed")
	}
	if !paths.MetadataExists() {
		t.Fatalf("expected metadata existence check to succeed")
	}
}

func TestWorkenvPathsListTempExtractions(t *testing.T) {
	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, "/tmp/demo.psp")

	dirs, err := paths.ListTempExtractions()
	if err != nil {
		t.Fatalf("ListTempExtractions returned error: %v", err)
	}
	if len(dirs) != 0 {
		t.Fatalf("expected no temp extractions, got %d", len(dirs))
	}

	first := paths.TempExtraction(111)
	second := paths.TempExtraction(222)
	mustMkdirAllPSP(t, first)
	mustMkdirAllPSP(t, second)
	if err := os.WriteFile(filepath.Join(paths.Tmp(), "not-a-dir"), []byte("x"), 0o644); err != nil {
		t.Fatalf("failed to create non-directory entry: %v", err)
	}

	dirs, err = paths.ListTempExtractions()
	if err != nil {
		t.Fatalf("ListTempExtractions returned error after setup: %v", err)
	}
	if len(dirs) != 2 {
		t.Fatalf("expected 2 temp extraction dirs, got %d (%v)", len(dirs), dirs)
	}
}

func mustMkdirAllPSP(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatalf("failed to create %q: %v", path, err)
	}
}
