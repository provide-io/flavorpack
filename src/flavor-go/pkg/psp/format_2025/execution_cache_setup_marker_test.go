// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"testing"
)

// setupMarkerFixture builds a workenv that extracted cleanly and whose checksum
// matches -- everything the validity check looked at before setup completion was
// considered.
func setupMarkerFixture(t *testing.T) (*WorkenvPaths, *PSPFIndex, *Metadata, *slog.Logger) {
	t.Helper()

	paths := NewWorkenvPaths(t.TempDir(), "demo.psp")
	if err := os.MkdirAll(paths.Workenv(), 0o700); err != nil {
		t.Fatalf("MkdirAll(workenv) error = %v", err)
	}
	if err := os.MkdirAll(filepath.Dir(paths.CompleteFile()), 0o700); err != nil {
		t.Fatalf("MkdirAll(complete dir) error = %v", err)
	}
	if err := os.WriteFile(paths.CompleteFile(), []byte("done"), 0o600); err != nil {
		t.Fatalf("WriteFile(complete) error = %v", err)
	}
	if err := os.WriteFile(paths.ChecksumFile(), []byte("12345678"), 0o600); err != nil {
		t.Fatalf("WriteFile(checksum) error = %v", err)
	}
	if err := os.WriteFile(filepath.Join(paths.Workenv(), "payload.txt"), []byte("x"), 0o600); err != nil {
		t.Fatalf("WriteFile(payload) error = %v", err)
	}

	metadata := &Metadata{
		Package: PackageInfo{Name: "demo", Version: "1.0.0"},
		CacheValidation: &CacheValidationInfo{
			CheckFile:       "{workenv}/metadata/installed",
			ExpectedContent: "{package_name}-{version}",
		},
	}
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	return paths, &PSPFIndex{IndexChecksum: 0x12345678}, metadata, logger
}

func writeSetupMarker(t *testing.T, paths *WorkenvPaths, content string) {
	t.Helper()
	marker := filepath.Join(paths.Workenv(), "metadata", "installed")
	if err := os.MkdirAll(filepath.Dir(marker), 0o700); err != nil {
		t.Fatalf("MkdirAll(metadata) error = %v", err)
	}
	if err := os.WriteFile(marker, []byte(content), 0o600); err != nil {
		t.Fatalf("WriteFile(marker) error = %v", err)
	}
}

// TestExtractedButUnfinishedWorkenvIsNotReused covers the shape that broke in
// the field: setup was interrupted, so the marker was never written, but the
// extraction marker and the package checksum both survived. Every later run
// reused the half-built workenv and died at exec with "no such file or
// directory".
func TestExtractedButUnfinishedWorkenvIsNotReused(t *testing.T) {
	paths, index, metadata, logger := setupMarkerFixture(t)

	valid, err := checkWorkenvValidity(paths, index, metadata, logger)
	if err != nil {
		t.Fatalf("checkWorkenvValidity() error = %v", err)
	}
	if valid {
		t.Fatal("a workenv with no setup marker must be rebuilt, not reused")
	}

	writeSetupMarker(t, paths, "demo-1.0.0")

	valid, err = checkWorkenvValidity(paths, index, metadata, logger)
	if err != nil {
		t.Fatalf("checkWorkenvValidity() error = %v", err)
	}
	if !valid {
		t.Fatal("a workenv whose setup completed is reusable")
	}
}

// TestSetupMarkerFromAnotherVersionIsRejected: a marker left by a different
// version is not evidence for this one.
func TestSetupMarkerFromAnotherVersionIsRejected(t *testing.T) {
	paths, index, metadata, logger := setupMarkerFixture(t)
	writeSetupMarker(t, paths, "demo-0.9.0")

	valid, err := checkWorkenvValidity(paths, index, metadata, logger)
	if err != nil {
		t.Fatalf("checkWorkenvValidity() error = %v", err)
	}
	if valid {
		t.Fatal("a marker naming another version must not validate this one")
	}
}

// TestManifestWithoutCacheValidationIsUnaffected: packages that declare no
// cache_validation keep working exactly as before.
func TestManifestWithoutCacheValidationIsUnaffected(t *testing.T) {
	paths, index, metadata, logger := setupMarkerFixture(t)
	metadata.CacheValidation = nil

	valid, err := checkWorkenvValidity(paths, index, metadata, logger)
	if err != nil {
		t.Fatalf("checkWorkenvValidity() error = %v", err)
	}
	if !valid {
		t.Fatal("a manifest without cache_validation must validate as before")
	}
}
