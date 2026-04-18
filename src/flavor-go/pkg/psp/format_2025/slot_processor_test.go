// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"crypto/sha256"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestSlotProcessorProcessSlotsSelfReferentialDefaults(t *testing.T) {
	processor := NewSlotProcessor([]Slot{
		{
			ID:        "launcher",
			Source:    SelfRefMarker,
			Target:    "bin/launcher",
			Purpose:   "runtime",
			Lifecycle: "startup",
		},
	}, logging.NewNullLogger())

	if err := processor.ProcessSlots(); err != nil {
		t.Fatalf("ProcessSlots() error = %v", err)
	}

	descriptors := processor.GetDescriptors()
	metadata := processor.GetMetadata()
	slotData := processor.GetSlotData()

	if len(descriptors) != 1 || len(metadata) != 1 || len(slotData) != 1 {
		t.Fatalf("unexpected processed lengths: descriptors=%d metadata=%d data=%d", len(descriptors), len(metadata), len(slotData))
	}

	if metadata[0].SelfRef == nil || !*metadata[0].SelfRef {
		t.Fatalf("expected self-ref metadata marker, got %#v", metadata[0].SelfRef)
	}
	if metadata[0].Permissions != fmt.Sprintf("%04o", FilePerms) {
		t.Fatalf("expected default permissions, got %q", metadata[0].Permissions)
	}
	if metadata[0].Resolution != "build" {
		t.Fatalf("expected default resolution 'build', got %q", metadata[0].Resolution)
	}
	if descriptors[0].Size != 0 || descriptors[0].OriginalSize != 0 || descriptors[0].Checksum != 0 {
		t.Fatalf("expected empty self-ref descriptor, got %#v", descriptors[0])
	}
	if len(slotData[0]) != 0 {
		t.Fatalf("expected empty slot payload for self-ref slot, got %d bytes", len(slotData[0]))
	}
}

func TestSlotProcessorProcessSlotsRegularFile(t *testing.T) {
	t.Parallel()

	tmpDir := t.TempDir()
	slotPath := filepath.Join(tmpDir, "payload.txt")
	payload := []byte("payload-data")
	if err := os.WriteFile(slotPath, payload, 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	processor := NewSlotProcessor([]Slot{
		{
			ID:          "payload",
			Source:      slotPath,
			Target:      "app/payload.txt",
			Purpose:     "tool",
			Lifecycle:   "cache",
			Operations:  "tar.gz",
			Permissions: "0755",
			Resolution:  "runtime",
		},
	}, logging.NewNullLogger())

	if err := processor.ProcessSlots(); err != nil {
		t.Fatalf("ProcessSlots() error = %v", err)
	}

	meta := processor.GetMetadata()[0]
	desc := processor.GetDescriptors()[0]
	data := processor.GetSlotData()[0]

	if meta.Size != int64(len(payload)) {
		t.Fatalf("expected metadata size %d, got %d", len(payload), meta.Size)
	}
	if meta.Checksum == "" || meta.Checksum[:7] != "sha256:" {
		t.Fatalf("expected sha256 metadata checksum, got %q", meta.Checksum)
	}
	if meta.Operations != "tar.gz" {
		t.Fatalf("expected metadata operations to round-trip, got %q", meta.Operations)
	}
	if desc.NameHash != HashName("app/payload.txt") {
		t.Fatalf("unexpected name hash: got %d", desc.NameHash)
	}
	if desc.Size != uint64(len(payload)) || desc.OriginalSize != uint64(len(payload)) {
		t.Fatalf("unexpected descriptor sizes: %#v", desc)
	}
	if desc.Operations != PackOperations([]uint8{OP_TAR, OP_GZIP}) {
		t.Fatalf("unexpected packed operations: %#v", desc.Operations)
	}
	if got := uint16(desc.PermissionsHigh)<<8 | uint16(desc.Permissions); got != 0o755 {
		t.Fatalf("unexpected descriptor permissions: %04o", got)
	}

	sum := sha256.Sum256(payload)
	expectedChecksum := computeSlotChecksum(payload)
	if desc.Checksum != expectedChecksum {
		t.Fatalf("unexpected checksum: got %x want %x (sha256=%x)", desc.Checksum, expectedChecksum, sum)
	}
	if string(data) != string(payload) {
		t.Fatalf("expected slot data to match file contents")
	}
}

func TestSlotProcessorProcessSlotsGzipAndTarOperations(t *testing.T) {
	t.Parallel()

	tmpDir := t.TempDir()
	slotPath := filepath.Join(tmpDir, "payload.bin")
	payload := []byte("raw-payload-data")
	if err := os.WriteFile(slotPath, payload, 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	for _, ops := range []string{"gzip", "tar"} {
		ops := ops
		t.Run(ops, func(t *testing.T) {
			processor := NewSlotProcessor([]Slot{
				{
					ID:         "payload",
					Source:     slotPath,
					Target:     "app/payload.bin",
					Purpose:    "payload",
					Lifecycle:  "runtime",
					Operations: ops,
				},
			}, logging.NewNullLogger())

			if err := processor.ProcessSlots(); err != nil {
				t.Fatalf("ProcessSlots() with %q error = %v", ops, err)
			}
			desc := processor.GetDescriptors()[0]
			var want uint64
			switch ops {
			case "gzip":
				want = PackOperations([]uint8{OP_GZIP})
			case "tar":
				want = PackOperations([]uint8{OP_TAR})
			}
			if desc.Operations != want {
				t.Fatalf("operations = %d, want %d", desc.Operations, want)
			}
		})
	}
}

func TestSlotProcessorLoadSlotDataResolvesWorkenvPlaceholder(t *testing.T) {
	tmpDir := t.TempDir()
	slotPath := filepath.Join(tmpDir, "nested", "payload.txt")
	if err := os.MkdirAll(filepath.Dir(slotPath), 0o755); err != nil {
		t.Fatalf("MkdirAll() error = %v", err)
	}
	if err := os.WriteFile(slotPath, []byte("via-workenv"), 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	t.Setenv(EnvWorkenvBase, tmpDir)

	processor := NewSlotProcessor(nil, logging.NewNullLogger())
	rawData, err := processor.loadSlotData(&Slot{
		Source:     "{workenv}/nested/payload.txt",
		Operations: "raw",
	})
	if err != nil {
		t.Fatalf("loadSlotData() error = %v", err)
	}
	if string(rawData) != "via-workenv" {
		t.Fatalf("unexpected slot contents: %q", string(rawData))
	}
}

func TestSlotProcessorProcessSlotsRejectsInvalidInput(t *testing.T) {
	t.Parallel()

	index := 1
	cases := []struct {
		name string
		slot Slot
	}{
		{
			name: "missing-id",
			slot: Slot{Source: "file", Target: "out"},
		},
		{
			name: "missing-source",
			slot: Slot{ID: "payload", Target: "out"},
		},
		{
			name: "missing-target",
			slot: Slot{ID: "payload", Source: "file"},
		},
		{
			name: "slot-mismatch",
			slot: Slot{Slot: &index, ID: "payload", Source: "file", Target: "out"},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			processor := NewSlotProcessor([]Slot{tc.slot}, logging.NewNullLogger())
			if err := processor.ProcessSlots(); err == nil {
				t.Fatalf("ProcessSlots() succeeded unexpectedly for %s", tc.name)
			}
		})
	}
}

// ---------------------------------------------------------------------------
// mapLifecycleToUint8 — exhaustive case coverage
// ---------------------------------------------------------------------------

func TestSlotProcessorLoadSlotDataFallsBackToGetwd(t *testing.T) {
	// When EnvWorkenvBase is unset, loadSlotData falls back to os.Getwd()
	// to resolve {workenv} placeholders. Write a file relative to cwd.
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("os.Getwd() error = %v", err)
	}

	// Write a temp file into the cwd-relative tmpDir so the resolved path lands there.
	tmpDir := t.TempDir()
	payload := []byte("fallback-workenv")
	slotPath := filepath.Join(tmpDir, "payload.txt")
	if err := os.WriteFile(slotPath, payload, 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	// Make the source relative to cwd using an absolute {workenv} stand-in.
	// Since cwd is absolute, use the tmpDir directly as the workenv substitute.
	_ = cwd // used implicitly via os.Getwd() fallback below

	t.Setenv(EnvWorkenvBase, "")
	// Temporarily change cwd to tmpDir so the fallback resolves to tmpDir.
	orig, _ := os.Getwd()
	if err := os.Chdir(tmpDir); err != nil {
		t.Fatalf("Chdir() error = %v", err)
	}
	t.Cleanup(func() { _ = os.Chdir(orig) })

	processor := NewSlotProcessor(nil, logging.NewNullLogger())
	rawData, err := processor.loadSlotData(&Slot{
		Source:     "{workenv}/payload.txt",
		Operations: "raw",
	})
	if err != nil {
		t.Fatalf("loadSlotData() error = %v", err)
	}
	if string(rawData) != string(payload) {
		t.Fatalf("unexpected slot contents: %q", string(rawData))
	}
}

func TestMapLifecycleToUint8_AllCases(t *testing.T) {
	cases := []struct {
		input    string
		expected uint8
	}{
		{"init", 0},
		{"startup", 1},
		{"runtime", 2},
		{"shutdown", 3},
		{"cache", 4},
		{"temporary", 5},
		{"lazy", 6},
		{"eager", 7},
		{"dev", 8},
		{"config", 9},
		{"platform", 10},
		{"unknown-default", 2},
	}
	for _, tc := range cases {
		got := mapLifecycleToUint8(tc.input)
		if got != tc.expected {
			t.Errorf("mapLifecycleToUint8(%q) = %d, want %d", tc.input, got, tc.expected)
		}
	}
}

// ---------------------------------------------------------------------------
// mapPurposeToUint8 — all purpose values
// ---------------------------------------------------------------------------

func TestMapPurposeToUint8_AllCases(t *testing.T) {
	cases := []struct {
		input    string
		expected uint8
	}{
		{"payload", 0},
		{"runtime", 1},
		{"tool", 2},
		{"unknown-default", 0},
	}
	for _, tc := range cases {
		got := mapPurposeToUint8(tc.input)
		if got != tc.expected {
			t.Errorf("mapPurposeToUint8(%q) = %d, want %d", tc.input, got, tc.expected)
		}
	}
}

// ---------------------------------------------------------------------------
// parsePermissions — valid, empty, and invalid inputs
// ---------------------------------------------------------------------------

func TestParsePermissions_ValidOctal(t *testing.T) {
	if got := parsePermissions("0755"); got != 0o755 {
		t.Errorf("parsePermissions(%q) = %04o, want %04o", "0755", got, 0o755)
	}
}

func TestParsePermissions_EmptyStringFallsBackToDefault(t *testing.T) {
	if got := parsePermissions(""); got != uint16(FilePerms) {
		t.Errorf("parsePermissions(%q) = %04o, want %04o (FilePerms)", "", got, uint16(FilePerms))
	}
}

func TestParsePermissions_InvalidStringFallsBackToDefault(t *testing.T) {
	if got := parsePermissions("notoctal"); got != uint16(FilePerms) {
		t.Errorf("parsePermissions(%q) = %04o, want %04o (FilePerms)", "notoctal", got, uint16(FilePerms))
	}
}
