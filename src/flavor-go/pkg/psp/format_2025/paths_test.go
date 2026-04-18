// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

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

func TestWorkenvPathsMetadataAndDerivedLocations(t *testing.T) {
	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, "/tmp/demo.pspf")

	if got := paths.Metadata(); got != filepath.Join(cacheDir, "workenv", ".demo.pspf") {
		t.Fatalf("Metadata() = %q", got)
	}
	if got := paths.PackageMetadata(); got != filepath.Join(cacheDir, "workenv", ".demo.pspf", "package") {
		t.Fatalf("PackageMetadata() = %q", got)
	}
	if got := paths.Log(); got != filepath.Join(cacheDir, "workenv", ".demo.pspf", "instance", "log") {
		t.Fatalf("Log() = %q", got)
	}
	if got := paths.PSPMetadataFile(); got != filepath.Join(cacheDir, "workenv", ".demo.pspf", "package", "psp.json") {
		t.Fatalf("PSPMetadataFile() = %q", got)
	}
	if got := paths.LockFile(); got != filepath.Join(cacheDir, "workenv", ".demo.pspf", "instance", "extract", "lock") {
		t.Fatalf("LockFile() = %q", got)
	}
	if got := paths.CompleteFile(); got != filepath.Join(cacheDir, "workenv", ".demo.pspf", "instance", "extract", "complete") {
		t.Fatalf("CompleteFile() = %q", got)
	}
	if got := paths.ChecksumFile(); got != filepath.Join(cacheDir, "workenv", ".demo.pspf", "instance", "package.checksum") {
		t.Fatalf("ChecksumFile() = %q", got)
	}
	if got := paths.IndexMetadataFile(); got != filepath.Join(cacheDir, "workenv", ".demo.pspf", "instance", "index.json") {
		t.Fatalf("IndexMetadataFile() = %q", got)
	}
}

func mustMkdirAllPSP(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatalf("failed to create %q: %v", path, err)
	}
}
