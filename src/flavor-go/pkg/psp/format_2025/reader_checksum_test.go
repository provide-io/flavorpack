// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"crypto/sha256"
	"encoding/binary"
	"errors"
	"hash/adler32"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestReadMetadataArchiveChecksumMismatchViaBundle covers reader.go:197-199
// (checksum mismatch in ReadMetadataArchive).
// We build a valid bundle then set the MetadataChecksum in the index to a wrong value.
func TestReadMetadataArchiveChecksumMismatchViaBundle(t *testing.T) {
	t.Parallel()

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	// Read the bundle data
	data, err := os.ReadFile(bundle)
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}

	// Find the index in the trailer
	trailerStart := len(data) - MagicTrailerSize
	var index PSPFIndex
	if err := index.Unpack(data[trailerStart+4 : trailerStart+4+IndexSize]); err != nil {
		t.Fatalf("Unpack() error = %v", err)
	}

	// Corrupt the MetadataChecksum to a wrong value
	wrongHash := sha256.Sum256([]byte("wrong-checksum-that-never-matches"))
	index.MetadataChecksum = wrongHash

	// Recompute the index adler32 checksum
	index.IndexChecksum = 0
	indexData := index.Pack()
	binary.LittleEndian.PutUint32(indexData[12:16], 0)
	cs := adler32.Checksum(indexData)
	index.IndexChecksum = cs
	indexData = index.Pack()

	// Write back the corrupted index
	copy(data[trailerStart+4:trailerStart+4+IndexSize], indexData)

	// Write corrupted bundle to a new file
	corruptPath := bundle + ".corrupt"
	if err := os.WriteFile(corruptPath, data, 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}
	t.Cleanup(func() { _ = os.Remove(corruptPath) })

	reader, _ := NewReaderWithLogger(corruptPath, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadMetadataArchive()
	if err == nil {
		t.Fatal("expected ErrChecksumMismatch from ReadMetadataArchive with corrupted checksum")
	}
}

// TestReadMetadataArchiveFileReadFails covers reader.go:197-199
// (file.Read for metadata archive fails → error returned).
func TestReadMetadataArchiveFileReadFails(t *testing.T) {
	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	old := fileReadFn
	t.Cleanup(func() { fileReadFn = old })
	fileReadFn = func(_ *os.File, _ []byte) (int, error) {
		return 0, errors.New("injected file.Read failure for metadata archive")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ReadMetadataArchive()
	if err == nil {
		t.Fatal("expected error from ReadMetadataArchive when file.Read fails")
	}
}
