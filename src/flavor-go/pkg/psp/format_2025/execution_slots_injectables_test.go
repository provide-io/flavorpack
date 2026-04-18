// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"errors"
	"log/slog"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestExtractAndMergeJsonMarshalFails covers execution_slots.go:66-70
// (json.MarshalIndent failure → error returned).
func TestExtractAndMergeJsonMarshalFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	oldFn := jsonMarshalIndentFn
	t.Cleanup(func() { jsonMarshalIndentFn = oldFn })
	jsonMarshalIndentFn = func(_ interface{}, _, _ string) ([]byte, error) {
		return nil, errors.New("injected json marshal failure")
	}

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd when json.MarshalIndent fails")
	}
}

// TestExtractAndMergeReadDirFails covers execution_slots.go:83-87
// (os.ReadDir failure → error returned).
func TestExtractAndMergeReadDirFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	oldFn := osReadDirFn
	t.Cleanup(func() { osReadDirFn = oldFn })
	osReadDirFn = func(_ string) ([]os.DirEntry, error) {
		return nil, errors.New("injected ReadDir failure")
	}

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd when os.ReadDir fails")
	}
}

// TestExtractAndMergeMkdirAllParentFails covers execution_slots.go:250-254
// (mkdirAllParentFn fails for parent directory of a file move → error returned).
// This requires the slot to be a non-tar file (single file slot) so that
// the file path (mkdirAllParentFn) branch in the move loop is taken.
func TestExtractAndMergeMkdirAllParentFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	// Build a bundle with a file slot that targets a flat filename (non-workenv root, no subdir)
	// so that it ends up as a regular file entry (not a directory) in the temp directory move loop.
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "file.txt"},
			storedData: []byte("hello world"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	oldFn := mkdirAllParentFn
	t.Cleanup(func() { mkdirAllParentFn = oldFn })
	mkdirAllParentFn = func(_ string, _ os.FileMode) error {
		return errors.New("injected MkdirAll failure for file parent directory")
	}

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd when mkdirAllParentFn fails")
	}
}

// TestExtractAndMergeFixShebangsFails covers execution_slots.go:254-256
// (fixShebangs failure → warns but continues).
func TestExtractAndMergeFixShebangsFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	// Build a bundle and inject fixShebangsFn to fail. The slot needs to produce a
	// bin/ directory in the workenv so the fixShebangs call is attempted.
	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
		Workenv: &WorkenvInfo{
			Directories: []DirectorySpec{
				{Path: "{workenv}/bin", Mode: "0755"},
			},
		},
	})

	oldFn := fixShebangsFn
	t.Cleanup(func() { fixShebangsFn = oldFn })
	fixShebangsFn = func(_, _, _ string, _ *slog.Logger) error {
		return errors.New("injected fixShebangs failure")
	}

	// fixShebangs failure is warned but not fatal
	logger := logging.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (fixShebangs failure should be non-fatal)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}
}

// TestExtractAndMergeRemoveAllFails covers execution_slots.go:260-262
// (os.RemoveAll failure for temp dir → logs debug, continues).
func TestExtractAndMergeRemoveAllFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	oldFn := osRemoveAllFn
	t.Cleanup(func() { osRemoveAllFn = oldFn })
	osRemoveAllFn = func(_ string) error {
		return errors.New("injected RemoveAll failure")
	}

	// RemoveAll failure is non-fatal
	logger := logging.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (RemoveAll failure should be non-fatal)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}
}

// TestExtractAndMergeSaveIndexMetadataFails covers execution_slots.go:265-267
// (saveIndexMetadata failure → logs debug, continues).
func TestExtractAndMergeSaveIndexMetadataFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	oldFn := saveIndexMetadataFn
	t.Cleanup(func() { saveIndexMetadataFn = oldFn })
	saveIndexMetadataFn = func(_ *WorkenvPaths, _ *PSPFIndex, _ *slog.Logger) error {
		return errors.New("injected saveIndexMetadata failure")
	}

	// saveIndexMetadata failure is non-fatal
	logger := logging.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (saveIndexMetadata failure should be non-fatal)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}
}

// TestExtractAndMergeMarkExtractionCompleteFails covers execution_slots.go:270-272
// (MarkExtractionComplete failure → logs debug, continues).
func TestExtractAndMergeMarkExtractionCompleteFails(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvWorkenvCache, "false")
	t.Setenv(EnvValidation, "none")

	bundle := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{
		{
			meta:       SlotMetadata{ID: "main", Target: "{workenv}"},
			storedData: []byte("hello"),
		},
	}, Metadata{
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	})

	oldFn := markExtractionCompleteFn
	t.Cleanup(func() { markExtractionCompleteFn = oldFn })
	markExtractionCompleteFn = func(_ *WorkenvPaths, _ *slog.Logger) error {
		return errors.New("injected MarkExtractionComplete failure")
	}

	// MarkExtractionComplete failure is non-fatal
	logger := logging.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (MarkExtractionComplete failure should be non-fatal)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil cmd")
	}
}
