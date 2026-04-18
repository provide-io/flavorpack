// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"strings"
	"testing"
)

// TestReadSlotReadIndexError covers reader_slots.go:21-23:
// when ReadIndex fails (non-existent bundle file), ReadSlot propagates the error.
func TestReadSlotReadIndexError(t *testing.T) {
	t.Parallel()

	// NewReader is lazy — it doesn't open the file yet.
	reader, err := NewReader("/nonexistent/bundle-that-does-not-exist.pspf")
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// ReadSlot calls ReadIndex, which will fail when trying to open the non-existent file.
	_, err = reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error from ReadSlot when file does not exist, got nil")
	}
	if !strings.Contains(err.Error(), "no such file") && !strings.Contains(err.Error(), "cannot find") {
		t.Logf("note: got error %v", err)
	}
}

// TestExtractSlotReadIndexError covers reader_slots.go:173-175:
// when the first ReadIndex in ExtractSlot fails, the error is propagated.
func TestExtractSlotReadIndexError(t *testing.T) {
	t.Parallel()

	reader, err := NewReader("/nonexistent/bundle-extract-test.pspf")
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when file does not exist, got nil")
	}
}

// TestReadSlotAfterFileClose covers reader_slots.go:31-33 (Seek error after file close).
// When the underlying file is closed, r.file.Seek() returns an error.
func TestReadSlotAfterFileClose(t *testing.T) {
	t.Parallel()

	// Build a valid bundle with one slot.
	data := []byte("slot payload data")
	bundle := buildSingleSlotBundleForTests(t, data, data, nil, SlotMetadata{
		ID:     "test-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	// Note: do NOT defer reader.Close() — we close it manually below.

	// First, prime the index cache so ReadIndex (line 20-23) succeeds.
	if _, err := reader.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	// Close the underlying file so subsequent Seek/Read calls fail.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("file.Close(): %v", err)
	}

	// ReadSlot should now fail at the Seek for the slot table entry (line 31-33).
	_, err = reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error from ReadSlot when file is closed, got nil")
	}
}

// TestExtractSlotAfterFileClose covers reader_slots.go:173-175 and 179-181:
// when the file is closed between ReadIndex and the slot table Seek in ExtractSlot.
func TestExtractSlotAfterFileClose(t *testing.T) {
	t.Parallel()

	data := []byte("extract payload")
	bundle := buildSingleSlotBundleForTests(t, data, data, nil, SlotMetadata{
		ID:     "extract-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}

	// Prime the index cache.
	if _, err := reader.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	// Close the file so ExtractSlot's ReadSlot (line 166) fails,
	// and then the slot descriptor Seek (line 179) also fails.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("file.Close(): %v", err)
	}

	destDir := t.TempDir()
	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error from ExtractSlot when file is closed, got nil")
	}
}
