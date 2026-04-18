// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"archive/tar"
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// buildSlotsBundleForSlotsTest creates a minimal PSPF bundle with a single raw (non-tar)
// slot whose target is "{workenv}". When ExtractSlot is called, it writes the slot
// contents to tempDir/slot_0_<id> as a regular file.
func buildSlotsBundleForSlotsTest(t *testing.T, slotID string, slotContents []byte) (bundlePath string, metadata *Metadata) {
	t.Helper()

	slotMeta := SlotMetadata{
		Slot:   0,
		ID:     slotID,
		Target: "{workenv}",
		Size:   int64(len(slotContents)),
	}

	md := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "0.0.1"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
		Slots:         []SlotMetadata{slotMeta},
	}

	spec := multiSlotBundleSpec{
		meta:         slotMeta,
		storedData:   slotContents,
		originalData: slotContents,
	}
	path := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{spec}, md)
	return path, &md
}

// buildSlotsBundleWithTarForSlotsTest creates a PSPF bundle with a single slot whose
// payload is a valid tar archive and target is "{workenv}". ExtractSlot will extract
// the tar entries directly into tempDir (not into a slot_0_* subdir).
func buildSlotsBundleWithTarForSlotsTest(t *testing.T, tarFileName string, tarFileContent []byte) (bundlePath string, metadata *Metadata) {
	t.Helper()

	// Build a minimal tar archive with one regular file.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	hdr := &tar.Header{
		Name: tarFileName,
		Mode: 0o644,
		Size: int64(len(tarFileContent)),
	}
	if err := tw.WriteHeader(hdr); err != nil {
		t.Fatalf("tw.WriteHeader: %v", err)
	}
	if _, err := tw.Write(tarFileContent); err != nil {
		t.Fatalf("tw.Write: %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("tw.Close: %v", err)
	}
	tarData := buf.Bytes()

	slotMeta := SlotMetadata{
		Slot:   0,
		ID:     "tarslot",
		Target: "{workenv}",
		Size:   int64(len(tarData)),
	}
	md := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "0.0.1"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
		Slots:         []SlotMetadata{slotMeta},
	}
	spec := multiSlotBundleSpec{
		meta:         slotMeta,
		storedData:   tarData,
		originalData: tarData,
	}
	path := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{spec}, md)
	return path, &md
}

// TestExtractAndMergeSlotsToWorkenv_HappyPath verifies the main path for a single
// non-tar slot with "{workenv}" target.  ExtractSlot writes tempDir/slot_0_<id> as
// a file; the function then copies it to workenvDir/<id>.
func TestExtractAndMergeSlotsToWorkenv_HappyPath(t *testing.T) {
	t.Parallel()

	slotContents := []byte("hello workenv")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "payload", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	slotPaths, err := extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	// Slot 0 should be recorded in slotPaths
	if _, ok := slotPaths[0]; !ok {
		t.Fatalf("slotPaths missing entry for slot 0: %v", slotPaths)
	}

	// The slot file (slot_0_payload) should have been moved/copied to workenvDir
	// as "slot_0_payload" (regular file, not in a slot_0_ directory)
	workenvDir := paths.Workenv()
	entries, err := os.ReadDir(workenvDir)
	if err != nil {
		t.Fatalf("ReadDir(workenv): %v", err)
	}
	if len(entries) == 0 {
		t.Fatal("expected at least one file in workenv after extraction")
	}

	// Metadata psp.json should exist
	metaFile := filepath.Join(paths.Metadata(), "package", "psp.json")
	if _, err := os.Stat(metaFile); err != nil {
		t.Fatalf("metadata psp.json missing: %v", err)
	}

	// Completion marker should exist
	if _, err := os.Stat(paths.CompleteFile()); err != nil {
		t.Fatalf("complete file missing: %v", err)
	}
}

// TestExtractAndMergeSlotsToWorkenv_TarSlot verifies that tar slot contents are
// extracted directly into the workenv (not placed in a slot_0_* subdir).
func TestExtractAndMergeSlotsToWorkenv_TarSlot(t *testing.T) {
	t.Parallel()

	bundlePath, _ := buildSlotsBundleWithTarForSlotsTest(t, "hello.txt", []byte("tar content"))

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	// hello.txt should be directly in workenv (tar extract to root)
	destFile := filepath.Join(paths.Workenv(), "hello.txt")
	got, err := os.ReadFile(destFile)
	if err != nil {
		t.Fatalf("ReadFile(hello.txt): %v", err)
	}
	if string(got) != "tar content" {
		t.Fatalf("expected %q, got %q", "tar content", string(got))
	}
}

// TestExtractAndMergeSlotsToWorkenv_Slot0Directory verifies the slot_0_* DIRECTORY
// branch (line 125 in execution_slots.go). We pre-create a slot_0_pre/ directory
// in the temp extraction path before the function is called. The function finds
// both the pre-created directory AND the real extracted file and handles both.
func TestExtractAndMergeSlotsToWorkenv_Slot0Directory(t *testing.T) {
	// Not parallel: uses os.Getpid() path injection.

	slotContents := []byte("real slot data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "myslot", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create the temp extraction directory with a slot_0_pre/ subdirectory
	// containing a file. When extractAndMergeSlotsToWorkenv runs, it will call
	// os.MkdirAll (no-op since dir exists), then ExtractSlot (adds slot_0_myslot
	// file), and then processes ALL entries including our pre-created slot_0_pre/.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	slotDir := filepath.Join(tempExtractDir, "slot_0_pre")
	if err := os.MkdirAll(slotDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot_0_pre): %v", err)
	}
	injectedFile := filepath.Join(slotDir, "injected.txt")
	if err := os.WriteFile(injectedFile, []byte("from slot_0_dir"), 0o644); err != nil {
		t.Fatalf("WriteFile(injected.txt): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	// injected.txt should have been merged from slot_0_pre/ into workenv root
	destFile := filepath.Join(paths.Workenv(), "injected.txt")
	got, err := os.ReadFile(destFile)
	if err != nil {
		t.Fatalf("ReadFile(injected.txt): %v", err)
	}
	if string(got) != "from slot_0_dir" {
		t.Fatalf("expected %q, got %q", "from slot_0_dir", string(got))
	}
}

// TestExtractAndMergeSlotsToWorkenv_SlotNDirectory verifies the slot_N_* DIRECTORY
// branch (line 168). We pre-create a slot_2_extra/ directory in the temp extraction
// path. The function processes it via the generic slot_* directory path.
func TestExtractAndMergeSlotsToWorkenv_SlotNDirectory(t *testing.T) {
	// Not parallel: uses os.Getpid() path injection.

	slotContents := []byte("base slot data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "base", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create a slot_2_extra/ directory in the temp extraction path.
	// This exercises the "slot_N_* directory" branch (not slot_0_*).
	tempExtractDir := paths.TempExtraction(os.Getpid())
	slotDir := filepath.Join(tempExtractDir, "slot_2_extra")
	if err := os.MkdirAll(slotDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot_2_extra): %v", err)
	}
	injectedFile := filepath.Join(slotDir, "extra.txt")
	if err := os.WriteFile(injectedFile, []byte("from slot_N_dir"), 0o644); err != nil {
		t.Fatalf("WriteFile(extra.txt): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	// extra.txt should have been merged from slot_2_extra/ into workenv root
	destFile := filepath.Join(paths.Workenv(), "extra.txt")
	got, err := os.ReadFile(destFile)
	if err != nil {
		t.Fatalf("ReadFile(extra.txt): %v", err)
	}
	if string(got) != "from slot_N_dir" {
		t.Fatalf("expected %q, got %q", "from slot_N_dir", string(got))
	}
}

// TestExtractAndMergeSlotsToWorkenv_DirectoryInTempRoot verifies the "regular
// directory" branch (line 218) where an extracted directory (not named slot_*) is
// merged into the workenv.
func TestExtractAndMergeSlotsToWorkenv_DirectoryInTempRoot(t *testing.T) {
	// Not parallel: uses os.Getpid() path injection.

	slotContents := []byte("slot content")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "myid", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create a plain (non-slot_*) directory in the temp extraction path.
	// This exercises the "regular directory" else branch.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	regularDir := filepath.Join(tempExtractDir, "lib")
	if err := os.MkdirAll(regularDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(lib): %v", err)
	}
	if err := os.WriteFile(filepath.Join(regularDir, "mylib.so"), []byte("lib data"), 0o644); err != nil {
		t.Fatalf("WriteFile(mylib.so): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	// lib/mylib.so should appear in workenv
	destFile := filepath.Join(paths.Workenv(), "lib", "mylib.so")
	got, err := os.ReadFile(destFile)
	if err != nil {
		t.Fatalf("ReadFile(lib/mylib.so): %v", err)
	}
	if string(got) != "lib data" {
		t.Fatalf("expected %q, got %q", "lib data", string(got))
	}
}

// TestExtractAndMergeSlotsToWorkenv_BinDirShebangFix verifies that when a bin/
// directory exists in the workenv after extraction, fixShebangs is invoked without
// error (the function continues even when fixShebangs returns a warning).
func TestExtractAndMergeSlotsToWorkenv_BinDirShebangFix(t *testing.T) {
	t.Parallel()

	// Use a tar slot that places a file directly in the workenv, then also pre-create
	// a bin directory via the tar structure.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	files := []struct {
		name    string
		content string
		mode    int64
	}{
		{"bin/myapp", "#!/usr/bin/env python3\nprint('hello')\n", 0o755},
		{"lib/data.txt", "some data", 0o644},
	}
	for _, f := range files {
		hdr := &tar.Header{Name: f.name, Mode: f.mode, Size: int64(len(f.content))}
		if err := tw.WriteHeader(hdr); err != nil {
			t.Fatalf("WriteHeader: %v", err)
		}
		if _, err := tw.Write([]byte(f.content)); err != nil {
			t.Fatalf("Write: %v", err)
		}
	}
	// Also add a bin/ dir entry
	if err := tw.WriteHeader(&tar.Header{Typeflag: tar.TypeDir, Name: "bin/", Mode: 0o755}); err != nil {
		t.Fatalf("WriteHeader(bin/): %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	tarData := buf.Bytes()

	slotMeta := SlotMetadata{Slot: 0, ID: "binslot", Target: "{workenv}", Size: int64(len(tarData))}
	md := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "0.0.1"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
		Slots:         []SlotMetadata{slotMeta},
	}
	spec := multiSlotBundleSpec{meta: slotMeta, storedData: tarData, originalData: tarData}
	bundlePath := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{spec}, md)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	// bin/myapp should be present in workenv
	destFile := filepath.Join(paths.Workenv(), "bin", "myapp")
	if _, err := os.Stat(destFile); err != nil {
		t.Fatalf("expected bin/myapp in workenv: %v", err)
	}
}

// TestExtractAndMergeSlotsToWorkenv_ExtractSlotFailure verifies that when ExtractSlot
// fails (e.g., the bundle is malformed/corrupt for that slot), the function returns
// a wrapped ErrSlotExtractionFailed and cleans up the temp dir.
func TestExtractAndMergeSlotsToWorkenv_ExtractSlotFailure(t *testing.T) {
	t.Parallel()

	// Build a bundle with a slot that has a corrupted checksum so ExtractSlot fails.
	slotContents := []byte("data")
	slotMeta := SlotMetadata{Slot: 0, ID: "corrupt", Target: "{workenv}", Size: int64(len(slotContents))}
	md := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "0.0.1"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
		Slots:         []SlotMetadata{slotMeta},
	}
	// Use corruptChecksum=true via buildSingleSlotBundleForTests
	bundlePath := buildSingleSlotBundleForTests(t, slotContents, nil, nil, slotMeta, 0, true)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Use the metadata we already built (it will match the bundle structure).
	_ = md // metadata is embedded in the bundle; read it back
	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error from corrupted slot, got nil")
	}
	// Should be wrapped ErrSlotExtractionFailed
	if !isSlotExtractionFailed(err) {
		t.Fatalf("expected ErrSlotExtractionFailed, got: %v", err)
	}
}

// TestExtractAndMergeSlotsToWorkenv_Slot0DirWithSubdir verifies the slot_0_ directory
// branch when the slot directory itself contains a subdirectory (exercises the
// copyDirAll path for subdirectories within slot_0_*).
func TestExtractAndMergeSlotsToWorkenv_Slot0DirWithSubdir(t *testing.T) {
	// Not parallel: uses os.Getpid() path injection.

	slotContents := []byte("plain slot")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "myslot2", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create slot_0_bundle/ containing a subdirectory — exercises copyDirAll
	// inside the slot_0_* directory handling branch.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	slotDir := filepath.Join(tempExtractDir, "slot_0_bundle")
	subDir := filepath.Join(slotDir, "share", "docs")
	if err := os.MkdirAll(subDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(share/docs): %v", err)
	}
	if err := os.WriteFile(filepath.Join(subDir, "readme.txt"), []byte("docs"), 0o644); err != nil {
		t.Fatalf("WriteFile(readme.txt): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	// share/docs/readme.txt should appear in workenv
	destFile := filepath.Join(paths.Workenv(), "share", "docs", "readme.txt")
	got, err := os.ReadFile(destFile)
	if err != nil {
		t.Fatalf("ReadFile(share/docs/readme.txt): %v", err)
	}
	if string(got) != "docs" {
		t.Fatalf("expected %q, got %q", "docs", string(got))
	}
}

// TestExtractAndMergeSlotsToWorkenv_SlotNDirWithSubdir verifies the slot_N_*
// directory branch with a subdirectory inside it, exercising copyDirAll.
func TestExtractAndMergeSlotsToWorkenv_SlotNDirWithSubdir(t *testing.T) {
	// Not parallel: uses os.Getpid() path injection.

	slotContents := []byte("slot n content")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "slotN", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create slot_3_overlay/ with a subdirectory to exercise copyDirAll in
	// the slot_N_* branch.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	slotDir := filepath.Join(tempExtractDir, "slot_3_overlay")
	subDir := filepath.Join(slotDir, "etc")
	if err := os.MkdirAll(subDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(etc): %v", err)
	}
	if err := os.WriteFile(filepath.Join(subDir, "config.cfg"), []byte("cfg"), 0o644); err != nil {
		t.Fatalf("WriteFile(config.cfg): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	// etc/config.cfg should appear in workenv
	destFile := filepath.Join(paths.Workenv(), "etc", "config.cfg")
	got, err := os.ReadFile(destFile)
	if err != nil {
		t.Fatalf("ReadFile(etc/config.cfg): %v", err)
	}
	if string(got) != "cfg" {
		t.Fatalf("expected %q, got %q", "cfg", string(got))
	}
}

// TestExtractAndMergeSlotsToWorkenv_MultipleSlots verifies that multiple slots are
// correctly extracted and merged, and that slotPaths contains entries for all slots.
func TestExtractAndMergeSlotsToWorkenv_MultipleSlots(t *testing.T) {
	t.Parallel()

	slotA := []byte("content A")
	slotB := []byte("content B")

	metaA := SlotMetadata{Slot: 0, ID: "slotA", Target: "{workenv}", Size: int64(len(slotA))}
	metaB := SlotMetadata{Slot: 1, ID: "slotB", Target: "{workenv}", Size: int64(len(slotB))}
	md := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "multi", Version: "1.0.0"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
		Slots:         []SlotMetadata{metaA, metaB},
	}
	specs := []multiSlotBundleSpec{
		{meta: metaA, storedData: slotA, originalData: slotA},
		{meta: metaB, storedData: slotB, originalData: slotB},
	}
	bundlePath := buildMultiSlotBundleForTests(t, specs, md)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	slotPaths, err := extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}

	if len(slotPaths) != 2 {
		t.Fatalf("expected slotPaths len=2, got %d: %v", len(slotPaths), slotPaths)
	}
}

// TestExtractAndMergeSlotsToWorkenv_Slot0DirReadFailure verifies that when reading a
// slot_0_* directory fails (no read permission), the function returns an error.
func TestExtractAndMergeSlotsToWorkenv_Slot0DirReadFailure(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}
	// Not parallel: uses os.Getpid() path injection.

	slotContents := []byte("data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "testslot", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create slot_0_noaccess/ with no read permission so ReadDir inside it fails.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	slotDir := filepath.Join(tempExtractDir, "slot_0_noaccess")
	if err := os.MkdirAll(slotDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot_0_noaccess): %v", err)
	}
	// Populate the directory so it's non-empty, then remove read permission.
	if err := os.WriteFile(filepath.Join(slotDir, "secret.txt"), []byte("x"), 0o000); err != nil {
		t.Fatalf("WriteFile(secret.txt): %v", err)
	}
	if err := os.Chmod(slotDir, 0o000); err != nil {
		t.Fatalf("Chmod(slot_0_noaccess): %v", err)
	}
	// Restore permissions for cleanup.
	t.Cleanup(func() { _ = os.Chmod(slotDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when slot_0_* directory is unreadable, got nil")
	}
}

// TestExtractAndMergeSlotsToWorkenv_SlotNDirReadFailure verifies that when reading a
// slot_N_* directory (non-zero) fails, the function returns an error.
func TestExtractAndMergeSlotsToWorkenv_SlotNDirReadFailure(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}
	// Not parallel: uses os.Getpid() path injection.

	slotContents := []byte("data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "base", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create slot_5_noaccess/ with no read permission.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	slotDir := filepath.Join(tempExtractDir, "slot_5_noaccess")
	if err := os.MkdirAll(slotDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot_5_noaccess): %v", err)
	}
	if err := os.WriteFile(filepath.Join(slotDir, "secret.txt"), []byte("x"), 0o000); err != nil {
		t.Fatalf("WriteFile(secret.txt): %v", err)
	}
	if err := os.Chmod(slotDir, 0o000); err != nil {
		t.Fatalf("Chmod(slot_5_noaccess): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(slotDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when slot_N_* directory is unreadable, got nil")
	}
}

// TestExtractAndMergeSlotsToWorkenv_MetadataWriteFailure verifies that when the
// package metadata JSON cannot be written (parent dir is a file), an error is returned.
// This exercises the WriteFile failure branch (lines 68-72).
func TestExtractAndMergeSlotsToWorkenv_MetadataWriteFailure(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}
	t.Parallel()

	slotContents := []byte("data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "wfail", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create the package metadata directory as a READ-ONLY directory so
	// writing psp.json into it fails.
	packageMetadataDir := filepath.Join(paths.Metadata(), "package")
	if err := os.MkdirAll(packageMetadataDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(package metadata dir): %v", err)
	}
	if err := os.Chmod(packageMetadataDir, 0o444); err != nil {
		t.Fatalf("Chmod(package metadata dir): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(packageMetadataDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when metadata psp.json write fails, got nil")
	}
}

// isSlotExtractionFailed checks whether the error chain contains ErrSlotExtractionFailed.
func isSlotExtractionFailed(err error) bool {
	if err == nil {
		return false
	}
	return bytes.Contains([]byte(err.Error()), []byte("slot extraction failed")) ||
		bytes.Contains([]byte(err.Error()), []byte(ErrSlotExtractionFailed.Error()))
}
