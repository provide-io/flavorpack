package format_2025

import (
	"crypto/sha256"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
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
	}, hclog.NewNullLogger())

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
	}, hclog.NewNullLogger())

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

	processor := NewSlotProcessor(nil, hclog.NewNullLogger())
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
			processor := NewSlotProcessor([]Slot{tc.slot}, hclog.NewNullLogger())
			if err := processor.ProcessSlots(); err == nil {
				t.Fatalf("ProcessSlots() succeeded unexpectedly for %s", tc.name)
			}
		})
	}
}
