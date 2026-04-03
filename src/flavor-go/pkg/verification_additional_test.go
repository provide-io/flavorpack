//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package pkg

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

// gzipBytes compresses data with gzip.
func gzipBytes(t *testing.T, data []byte) []byte {
	t.Helper()
	var buf bytes.Buffer
	gz := gzip.NewWriter(&buf)
	if _, err := gz.Write(data); err != nil {
		t.Fatalf("gzip write: %v", err)
	}
	if err := gz.Close(); err != nil {
		t.Fatalf("gzip close: %v", err)
	}
	return buf.Bytes()
}

// buildBundleWithCorruptSlot creates a PSPF bundle that has a valid magic trailer
// and valid index, valid metadata, but a slot with a corrupted checksum.
func buildBundleWithCorruptSlot(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()
	path := filepath.Join(dir, "corrupt-slot.pspf")
	f, err := os.Create(path)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	defer func() { _ = f.Close() }()

	// Write slot data.
	slotData := []byte("slot content")
	if _, err := f.Write(slotData); err != nil {
		t.Fatalf("write slot: %v", err)
	}
	slotSize := uint64(len(slotData))

	// Build a slot descriptor with corrupted checksum.
	slotHash := sha256.Sum256(slotData)
	checksum := binary.LittleEndian.Uint64(slotHash[:8])
	checksum ^= 0xFF // corrupt

	desc := format_2025.SlotDescriptor{
		ID:           1,
		NameHash:     format_2025.HashName("test-slot"),
		Offset:       0,
		Size:         slotSize,
		OriginalSize: slotSize,
		Operations:   0,
		Checksum:     checksum,
	}
	slotTableOffset := uint64(len(slotData))
	if _, err := f.Write(desc.Pack()); err != nil {
		t.Fatalf("write slot descriptor: %v", err)
	}

	// Write metadata.
	metadata := format_2025.Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package: format_2025.PackageInfo{
			Name:    "test-corrupt",
			Version: "1.0.0",
		},
		Slots: []format_2025.SlotMetadata{
			{ID: "test-slot", Target: "{workenv}/file.txt"},
		},
	}
	metaJSON, err := json.Marshal(metadata)
	if err != nil {
		t.Fatalf("Marshal: %v", err)
	}
	gzMeta := gzipBytes(t, metaJSON)
	metaOffset := uint64(len(slotData)) + uint64(format_2025.SlotDescriptorSize)
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}

	// Build index.
	idx := format_2025.PSPFIndex{
		FormatVersion:   format_2025.PSPFVersion,
		PackageSize:     uint64(len(slotData)) + uint64(format_2025.SlotDescriptorSize) + uint64(len(gzMeta)) + uint64(format_2025.MagicTrailerSize),
		MetadataOffset:  metaOffset,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   uint64(format_2025.SlotDescriptorSize),
		SlotCount:       1,
	}
	idx.MetadataChecksum = sha256.Sum256(gzMeta)

	trailer := make([]byte, format_2025.MagicTrailerSize)
	copy(trailer[0:4], format_2025.PackageEmojiBytes)
	copy(trailer[4:4+format_2025.IndexSize], idx.Pack())
	copy(trailer[4+format_2025.IndexSize:], format_2025.MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	return path
}

// buildBundleWithBadMetadata creates a PSPF bundle that has a valid magic trailer
// and valid index, but non-gzip (corrupt) metadata — so ReadMetadata fails.
func buildBundleWithBadMetadata(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()
	path := filepath.Join(dir, "bad-metadata.pspf")

	// Write plain (non-gzip) JSON as metadata.
	plainMeta := []byte(`{"package":{"name":"bad"},"slots":[]}`)
	metaHash := sha256.Sum256(plainMeta)

	idx := format_2025.PSPFIndex{
		FormatVersion:   format_2025.PSPFVersion,
		PackageSize:     uint64(len(plainMeta) + format_2025.MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(plainMeta)),
		SlotTableOffset: uint64(len(plainMeta)),
		SlotTableSize:   0,
		SlotCount:       0,
	}
	idx.MetadataChecksum = metaHash

	var bundle bytes.Buffer
	bundle.Write(plainMeta)
	trailer := make([]byte, format_2025.MagicTrailerSize)
	copy(trailer[0:4], format_2025.PackageEmojiBytes)
	copy(trailer[4:4+format_2025.IndexSize], idx.Pack())
	copy(trailer[4+format_2025.IndexSize:], format_2025.MagicWandEmojiBytes)
	bundle.Write(trailer)

	if err := os.WriteFile(path, bundle.Bytes(), 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	return path
}

// TestVerifyBundleWithLoggerSlotFailure tests that VerifyBundleWithLogger properly
// handles a corrupt slot — runs via subprocess to avoid os.Exit killing the test.
func TestVerifyBundleWithLoggerSlotFailure(t *testing.T) {
	bundlePath := buildBundleWithCorruptSlot(t)

	cmd := exec.Command(os.Args[0], "-test.run=TestVerifyBundleAdditionalHelper", "--", "corrupt-slot", bundlePath)
	cmd.Env = append(os.Environ(),
		"FLAVORPACK_VERIFY_ADDITIONAL_HELPER=1",
		"FLAVORPACK_VERIFY_ADDITIONAL_MODE=corrupt-slot",
	)
	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatalf("expected process to exit with error for corrupt slot bundle\noutput: %s", out)
	}
}

// TestVerifyBundleWithLoggerMetadataFailure tests that VerifyBundleWithLogger properly
// handles a bundle with corrupt metadata — runs via subprocess to avoid os.Exit.
func TestVerifyBundleWithLoggerMetadataFailure(t *testing.T) {
	bundlePath := buildBundleWithBadMetadata(t)

	cmd := exec.Command(os.Args[0], "-test.run=TestVerifyBundleAdditionalHelper", "--", "bad-metadata", bundlePath)
	cmd.Env = append(os.Environ(),
		"FLAVORPACK_VERIFY_ADDITIONAL_HELPER=1",
		"FLAVORPACK_VERIFY_ADDITIONAL_MODE=bad-metadata",
	)
	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatalf("expected process to exit with error for bad-metadata bundle\noutput: %s", out)
	}
}

// TestVerifyBundleAdditionalHelper is the subprocess helper for the additional
// verification tests.
func TestVerifyBundleAdditionalHelper(t *testing.T) {
	if os.Getenv("FLAVORPACK_VERIFY_ADDITIONAL_HELPER") != "1" {
		t.Skip("helper process")
	}

	args := os.Args
	if len(args) < 3 {
		t.Fatal("missing helper arguments")
	}
	path := args[len(args)-1]

	VerifyBundle(path)
}
