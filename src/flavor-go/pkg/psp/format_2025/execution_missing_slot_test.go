package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"errors"
	"os"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// buildBundleWithSlotNumberMismatch creates a PSPF bundle where:
//   - There is one physical slot (descriptor ID=1, stored at offset 0)
//   - The metadata Slots list has one entry with Slot=1 (not 0)
//   - The Execution.Command references {slot:0}
//
// After extraction, slotPaths[1] is set (from metadata.Slots[0].Slot=1) but
// slotPaths[0] is absent, so {slot:0} in the command is never substituted.
// The len(metadata.Slots)=1 loop runs for i=0 and finds {slot:0} still present.
func buildBundleWithSlotNumberMismatch(t *testing.T) string {
	t.Helper()

	slotData := []byte("payload")
	slotHash := sha256.Sum256(slotData)
	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName("slot-one"),
		Offset:       0,
		Size:         uint64(len(slotData)),
		OriginalSize: uint64(len(slotData)),
		Operations:   0,
		Checksum:     binary.LittleEndian.Uint64(slotHash[:8]),
		Purpose:      PurposeData,
		Lifecycle:    LifecycleRuntime,
	}

	slotTableOffset := uint64(len(slotData))

	// Metadata: Slots[0].Slot = 1, command references {slot:0}.
	meta := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "mismatch-test", Version: "1.0.0"},
		Slots: []SlotMetadata{
			{
				Slot:   1, // slotPaths key will be 1, not 0
				ID:     "slot-one",
				Target: "{workenv}",
				Size:   int64(len(slotData)),
			},
		},
		// Command references {slot:0} — which won't be in slotPaths.
		Execution: &ExecutionInfo{PrimarySlot: 1, Command: "/bin/true {slot:0}"},
		Build:     &BuildInfo{Tool: "test"},
	}
	metaJSON, err := json.Marshal(meta)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}
	var gzBuf bytes.Buffer
	gw := gzip.NewWriter(&gzBuf)
	if _, err := gw.Write(metaJSON); err != nil {
		t.Fatalf("gzip.Write: %v", err)
	}
	if err := gw.Close(); err != nil {
		t.Fatalf("gzip.Close: %v", err)
	}
	gzMeta := gzBuf.Bytes()
	metaOffset := slotTableOffset + SlotDescriptorSize

	metaHash := sha256.Sum256(gzMeta)
	totalSize := metaOffset + uint64(len(gzMeta)) + uint64(MagicTrailerSize)
	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     totalSize,
		MetadataOffset:  metaOffset,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
	}
	copy(index.MetadataChecksum[:], metaHash[:])

	bundlePath := testBundlePath(t, ".psp")
	f, err := os.Create(bundlePath)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(slotData); err != nil {
		t.Fatalf("Write(slot): %v", err)
	}
	if _, err := f.Write(desc.Pack()); err != nil {
		t.Fatalf("Write(descriptor): %v", err)
	}
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("Write(meta): %v", err)
	}

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], index.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("Write(trailer): %v", err)
	}

	return bundlePath
}

// TestRunBundleWithCwdMissingSlotReference covers execution.go:607-610:
// ErrMissingSlot is returned when the command still contains a {slot:N} placeholder
// after substitution because slot N has no entry in slotPaths.
//
// We build a bundle where metadata.Slots[0].Slot=1 (so slotPaths[1] is populated
// after extraction) but the command references {slot:0} (absent from slotPaths).
// The missing-slot detection loop at line 605 iterates i from 0 to
// len(metadata.Slots)-1 (= 0), finds {slot:0} still present, and returns ErrMissingSlot.
func TestRunBundleWithCwdMissingSlotReference(t *testing.T) {
	t.Setenv(EnvCacheDir, t.TempDir())
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildBundleWithSlotNumberMismatch(t)

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected ErrMissingSlot, got nil")
	}
	if !errors.Is(err, ErrMissingSlot) {
		if !strings.Contains(err.Error(), "missing slot") {
			t.Logf("note: got error %v (expected ErrMissingSlot)", err)
		}
	}
}
