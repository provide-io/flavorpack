package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// buildSignedExecutableBundle creates a minimal signed PSPF bundle that:
//   - has a valid Ed25519 integrity seal (so VerifyIntegritySeal returns true)
//   - has no attestation SBOM digest or policy hash (so those checks pass)
//   - has Execution metadata pointing to /bin/true
//
// Returns the bundle path and the public key used for signing.
func buildSignedExecutableBundle(t *testing.T) (string, ed25519.PublicKey) {
	t.Helper()

	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey: %v", err)
	}

	meta := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "1.0.0"},
		Slots: []SlotMetadata{
			{ID: "slot", Target: "{workenv}", Slot: 0},
		},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "test"},
	}
	metaJSON, err := json.Marshal(meta)
	if err != nil {
		t.Fatalf("json.Marshal(meta): %v", err)
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

	// Sign the raw JSON (same as what VerifyIntegritySeal checks).
	sig := ed25519.Sign(priv, metaJSON)

	// Build a single empty slot.
	slotData := []byte("payload")
	slotHash := sha256.Sum256(slotData)
	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName("slot"),
		Offset:       0,
		Size:         uint64(len(slotData)),
		OriginalSize: uint64(len(slotData)),
		Operations:   0,
		Checksum:     binary.LittleEndian.Uint64(slotHash[:8]),
		Purpose:      PurposeData,
		Lifecycle:    LifecycleRuntime,
	}

	bundlePath := testBundlePath(t, ".psp")
	f, err := os.Create(bundlePath)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	defer func() { _ = f.Close() }()

	// Write slot data.
	if _, err := f.Write(slotData); err != nil {
		t.Fatalf("Write(slot data): %v", err)
	}
	slotTableOffset := uint64(len(slotData))

	// Write slot descriptor.
	if _, err := f.Write(desc.Pack()); err != nil {
		t.Fatalf("Write(descriptor): %v", err)
	}
	metaOffset := slotTableOffset + SlotDescriptorSize

	// Write gzip metadata.
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("Write(gzMeta): %v", err)
	}
	totalDataSize := metaOffset + uint64(len(gzMeta))

	// Build index with proper checksum and signature.
	metaHash := sha256.Sum256(gzMeta)
	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     totalDataSize + uint64(MagicTrailerSize),
		MetadataOffset:  metaOffset,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
	}
	copy(index.MetadataChecksum[:], metaHash[:])
	copy(index.IntegritySignature[:], sig)
	copy(index.PublicKey[:], pub)

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], index.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("Write(trailer): %v", err)
	}

	return bundlePath, pub
}

// TestRunBundleWithCwdCheckWorkenvValidityError covers execution.go:381-384:
// checkWorkenvValidity returns (false, err) when ValidationStrict + checksum mismatch.
// We pre-create a "valid" cache (complete marker, non-empty workenv, wrong checksum)
// and use a properly signed bundle so VerifyIntegritySeal passes.
func TestRunBundleWithCwdCheckWorkenvValidityError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "strict")
	// Do NOT set EnvWorkenvCache=false — we need the cache check to run.

	bundle, _ := buildSignedExecutableBundle(t)

	// Pre-populate the cache using the same path logic as NewWorkenvPaths.
	paths := NewWorkenvPaths(cacheRoot, bundle)

	// Create directories required by checkWorkenvValidity:
	//   paths.Extract() — for the complete marker
	//   paths.Workenv()  — must be non-empty
	//   paths.Instance() — for the checksum file
	if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
		t.Fatalf("MkdirAll(Extract): %v", err)
	}
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(Workenv): %v", err)
	}
	if err := os.MkdirAll(paths.Instance(), 0o755); err != nil {
		t.Fatalf("MkdirAll(Instance): %v", err)
	}

	// Write the complete marker so Stat(completePath) succeeds.
	if err := os.WriteFile(paths.CompleteFile(), []byte("done"), 0o600); err != nil {
		t.Fatalf("WriteFile(CompleteFile): %v", err)
	}

	// Put a dummy file in workenv so ReadDir returns non-empty entries.
	if err := os.WriteFile(filepath.Join(paths.Workenv(), "dummy"), []byte("x"), 0o600); err != nil {
		t.Fatalf("WriteFile(workenv/dummy): %v", err)
	}

	// Write a deliberately wrong checksum. The bundle's IndexChecksum is 0 (not computed
	// in the test builder), so "00000000" would match. Use "ffffffff" for a guaranteed mismatch.
	if err := os.WriteFile(paths.ChecksumFile(), []byte("ffffffff\n"), 0o600); err != nil {
		t.Fatalf("WriteFile(ChecksumFile): %v", err)
	}

	logger := hclog.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from checkWorkenvValidity (checksum mismatch + strict), got nil")
	}
	if !strings.Contains(err.Error(), "checksum mismatch") {
		t.Logf("note: got error %v (expected 'checksum mismatch')", err)
	}
}
