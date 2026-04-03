package format_2025

import (
	"strings"
	"testing"
)

// TestReadSlotGzipNewReaderFails covers reader_slots.go:96-98:
// when a slot has OP_GZIP in its operations but the stored data is not
// valid gzip, gzip.NewReader returns an error.
func TestReadSlotGzipNewReaderFails(t *testing.T) {
	t.Parallel()

	// Store non-gzip bytes with OP_GZIP operation set.
	// The checksum is computed from the stored bytes so it will pass validation,
	// but gzip.NewReader will fail on the invalid gzip header.
	notGzip := []byte("this is definitely not gzip data at all")
	bundle := buildSingleSlotBundleForTests(t, notGzip, notGzip, []uint8{OP_GZIP}, SlotMetadata{
		ID:     "bad-gzip",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error from ReadSlot when gzip data is invalid, got nil")
	}
	if !strings.Contains(err.Error(), "gzip") {
		t.Logf("note: got error %v (expected 'gzip' in message)", err)
	}
}
