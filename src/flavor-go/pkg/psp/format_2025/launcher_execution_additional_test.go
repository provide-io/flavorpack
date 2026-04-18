// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func newExecutionSlotsExtractionContext(t *testing.T, bundle string) (*Reader, *PSPFIndex, *Metadata, *slog.Logger) {
	t.Helper()

	logger := logging.NewNullLogger()
	reader, err := NewReaderWithLogger(bundle, logger)
	if err != nil {
		t.Fatalf("NewReaderWithLogger() error = %v", err)
	}
	t.Cleanup(func() {
		if err := reader.Close(); err != nil {
			t.Fatalf("Close() error = %v", err)
		}
	})

	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}
	readMetadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata() error = %v", err)
	}

	return reader, index, readMetadata, logger
}

func TestExtractAndMergeSlotsToWorkenvMergesSlotZeroDirectoriesAndMarksExtractionComplete(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)

	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
	}

	slotOneTar := buildTarArchiveWithDirAndFile(t, "shared", "slot-one.txt", 0o644, []byte("slot-one"))
	slotZeroTar := buildTarArchiveWithDirAndFile(t, "shared", "slot-zero.txt", 0o644, []byte("slot-zero"))

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "slot-one", Target: "{workenv}"},
			storedData:   gzipDataForExecutionTests(t, slotOneTar),
			originalData: slotOneTar,
			operations:   []uint8{OP_TAR, OP_GZIP},
			permissions:  0o755,
		},
		{
			meta:         SlotMetadata{ID: "slot-zero", Target: "{workenv}"},
			storedData:   gzipDataForExecutionTests(t, slotZeroTar),
			originalData: slotZeroTar,
			operations:   []uint8{OP_TAR, OP_GZIP},
			permissions:  0o755,
		},
	}, metadata)

	reader, index, readMetadata, logger := newExecutionSlotsExtractionContext(t, bundle)
	paths := NewWorkenvPaths(cacheRoot, bundle)

	if err := os.MkdirAll(filepath.Join(paths.Workenv(), "shared"), 0o755); err != nil {
		t.Fatalf("MkdirAll(preexisting shared dir) error = %v", err)
	}
	if err := os.WriteFile(filepath.Join(paths.Workenv(), "shared", "preexisting.txt"), []byte("keep"), 0o644); err != nil {
		t.Fatalf("WriteFile(preexisting file) error = %v", err)
	}

	slotPaths, err := extractAndMergeSlotsToWorkenv(reader, readMetadata, paths, index, logger)
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv() error = %v", err)
	}
	if len(slotPaths) != 2 {
		t.Fatalf("slot path count = %d, want 2", len(slotPaths))
	}

	for _, name := range []string{"preexisting.txt", "slot-one.txt", "slot-zero.txt"} {
		got, err := os.ReadFile(filepath.Join(paths.Workenv(), "shared", name))
		if err != nil {
			t.Fatalf("ReadFile(shared/%s) error = %v", name, err)
		}
		if name == "preexisting.txt" && string(got) != "keep" {
			t.Fatalf("shared/%s = %q, want %q", name, string(got), "keep")
		}
		if name == "slot-one.txt" && string(got) != "slot-one" {
			t.Fatalf("shared/%s = %q, want %q", name, string(got), "slot-one")
		}
		if name == "slot-zero.txt" && string(got) != "slot-zero" {
			t.Fatalf("shared/%s = %q, want %q", name, string(got), "slot-zero")
		}
	}

	if !IsExtractionComplete(paths) {
		t.Fatal("expected extraction completion marker to be written")
	}
	if _, err := os.Stat(paths.CompleteFile()); err != nil {
		t.Fatalf("expected completion marker file to exist: %v", err)
	}
	if _, err := os.Stat(filepath.Join(paths.Metadata(), "package", "psp.json")); err != nil {
		t.Fatalf("expected package metadata to be written: %v", err)
	}
	tempDirs, err := paths.ListTempExtractions()
	if err != nil {
		t.Fatalf("ListTempExtractions() error = %v", err)
	}
	if len(tempDirs) != 0 {
		t.Fatalf("expected temp extraction cleanup, found %v", tempDirs)
	}
}

func TestExtractAndMergeSlotsToWorkenvMergesHigherSlotDirectoriesIntoWorkenvRoot(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)

	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
	}

	slotZeroPayload := []byte("config=true")
	slotOneTar := buildTarArchiveWithDirAndFile(t, "assets", "logo.txt", 0o644, []byte("logo"))

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "config-slot", Target: "config.txt"},
			storedData:   slotZeroPayload,
			originalData: slotZeroPayload,
			permissions:  0o644,
		},
		{
			meta:         SlotMetadata{ID: "assets-slot", Target: "{workenv}"},
			storedData:   gzipDataForExecutionTests(t, slotOneTar),
			originalData: slotOneTar,
			operations:   []uint8{OP_TAR, OP_GZIP},
			permissions:  0o755,
		},
	}, metadata)

	reader, index, readMetadata, logger := newExecutionSlotsExtractionContext(t, bundle)
	paths := NewWorkenvPaths(cacheRoot, bundle)

	if err := os.MkdirAll(filepath.Join(paths.Workenv(), "assets"), 0o755); err != nil {
		t.Fatalf("MkdirAll(assets dir) error = %v", err)
	}
	if err := os.WriteFile(filepath.Join(paths.Workenv(), "assets", "existing.txt"), []byte("existing"), 0o644); err != nil {
		t.Fatalf("WriteFile(existing asset) error = %v", err)
	}

	if _, err := extractAndMergeSlotsToWorkenv(reader, readMetadata, paths, index, logger); err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv() error = %v", err)
	}

	if got, err := os.ReadFile(filepath.Join(paths.Workenv(), "assets", "existing.txt")); err != nil || string(got) != "existing" {
		t.Fatalf("expected preexisting asset to remain, err=%v content=%q", err, string(got))
	}
	if got, err := os.ReadFile(filepath.Join(paths.Workenv(), "assets", "logo.txt")); err != nil || string(got) != "logo" {
		t.Fatalf("expected slot N directory merge into workenv root, err=%v content=%q", err, string(got))
	}
	if got, err := os.ReadFile(filepath.Join(paths.Workenv(), "config.txt")); err != nil || string(got) != "config=true" {
		t.Fatalf("expected slot 0 regular file to be moved to workenv root, err=%v content=%q", err, string(got))
	}
	if !IsExtractionComplete(paths) {
		t.Fatal("expected extraction completion marker to be written")
	}
}

func TestExtractAndMergeSlotsToWorkenvReportsCopyFailureWhenDestinationIsDirectory(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)

	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
	}

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:         SlotMetadata{ID: "plain-file", Target: "plain.txt"},
			storedData:   []byte("payload"),
			originalData: []byte("payload"),
			permissions:  0o644,
		},
	}, metadata)

	reader, index, readMetadata, logger := newExecutionSlotsExtractionContext(t, bundle)
	paths := NewWorkenvPaths(cacheRoot, bundle)

	if err := os.MkdirAll(filepath.Join(paths.Workenv(), "plain.txt"), 0o755); err != nil {
		t.Fatalf("MkdirAll(conflicting destination) error = %v", err)
	}

	_, err := extractAndMergeSlotsToWorkenv(reader, readMetadata, paths, index, logger)
	if err == nil {
		t.Fatal("expected extractAndMergeSlotsToWorkenv() to fail when destination path is a directory")
	}
	if !strings.Contains(err.Error(), "failed to copy file") {
		t.Fatalf("expected copy fallback failure, got %v", err)
	}
	if IsExtractionComplete(paths) {
		t.Fatal("did not expect completion marker after failed extraction")
	}
	tempDirs, listErr := paths.ListTempExtractions()
	if listErr != nil {
		t.Fatalf("ListTempExtractions() error = %v", listErr)
	}
	if len(tempDirs) != 0 {
		t.Fatalf("expected temp extraction cleanup after failure, found %v", tempDirs)
	}
}
