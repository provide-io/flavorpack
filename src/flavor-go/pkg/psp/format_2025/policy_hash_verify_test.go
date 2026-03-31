package format_2025

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"testing"
)

// buildPolicyHashBundle constructs a minimal PSPF bundle where the metadata
// optionally includes a "policy" key and the index AttestationPolicyHash field
// is set to hashHex (pass "" to leave zero-filled).
func buildPolicyHashBundle(t *testing.T, policy *PackagePolicy, hashHex string) string {
	t.Helper()

	f, err := os.CreateTemp(t.TempDir(), "pspf-policy-*.bin")
	if err != nil {
		t.Fatalf("create temp file: %v", err)
	}
	defer f.Close()

	// Build metadata JSON with optional policy field.
	type minimalMeta struct {
		Package struct {
			Name    string `json:"name"`
			Version string `json:"version"`
		} `json:"package"`
		Slots  []interface{}  `json:"slots"`
		Policy *PackagePolicy `json:"policy,omitempty"`
	}
	var meta minimalMeta
	meta.Package.Name = "test"
	meta.Package.Version = "0.0.1"
	meta.Slots = []interface{}{}
	meta.Policy = policy

	metaJSON, err := json.Marshal(meta)
	if err != nil {
		t.Fatalf("marshal metadata: %v", err)
	}

	// Write the bundle using the same layout as buildAttestationBundle (no slot).
	var offset uint64

	// Write minimal gzip-compressed metadata.
	gzMeta := gzipData(t, metaJSON)
	metaOffset := offset
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}
	offset += uint64(len(gzMeta))

	// MagicTrailer follows.
	trailerOffset := offset

	// Build index (no slots).
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     trailerOffset + uint64(MagicTrailerSize),
		SlotTableOffset: trailerOffset, // empty slot table
		SlotTableSize:   0,
		SlotCount:       0,
		MetadataOffset:  metaOffset,
		MetadataSize:    uint64(len(gzMeta)),
	}

	mh := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], mh[:])

	if hashHex != "" {
		copy(idx.AttestationPolicyHash[:], []byte(hashHex))
	}

	// Write MagicTrailer.
	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write MagicTrailer: %v", err)
	}

	return f.Name()
}

// TestVerifyAttestationPolicyHash_ZeroField_Skip checks that when
// AttestationPolicyHash is all-zero, verification is skipped regardless of
// whether a policy is present.
func TestVerifyAttestationPolicyHash_ZeroField_Skip(t *testing.T) {
	// No policy, zero hash — should be a no-op.
	bundlePath := buildPolicyHashBundle(t, nil, "")
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	if err := reader.VerifyAttestationPolicyHash(); err != nil {
		t.Errorf("expected nil for zero policy hash, got: %v", err)
	}
}

// TestVerifyAttestationPolicyHash_Match checks that a correctly computed hash
// passes verification.
func TestVerifyAttestationPolicyHash_Match(t *testing.T) {
	policy := &PackagePolicy{
		Platforms:  []string{"linux_amd64"},
		RefuseRoot: true,
	}

	// Compute canonical JSON the same way the method does.
	canonical, err := json.Marshal(policy)
	if err != nil {
		t.Fatalf("marshal policy: %v", err)
	}
	h := sha256.Sum256(canonical)
	correctHex := hex.EncodeToString(h[:])

	bundlePath := buildPolicyHashBundle(t, policy, correctHex)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	if err := reader.VerifyAttestationPolicyHash(); err != nil {
		t.Errorf("expected no error for matching policy hash, got: %v", err)
	}
}

// TestVerifyAttestationPolicyHash_Mismatch checks that a wrong hash causes failure.
func TestVerifyAttestationPolicyHash_Mismatch(t *testing.T) {
	policy := &PackagePolicy{
		Platforms:  []string{"linux_amd64"},
		RefuseRoot: true,
	}
	wrongHex := hex.EncodeToString(sha256.New().Sum(nil)) // SHA-256 of empty string

	bundlePath := buildPolicyHashBundle(t, policy, wrongHex)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	if err := reader.VerifyAttestationPolicyHash(); err == nil {
		t.Error("expected error for mismatched policy hash, got nil")
	}
}

// TestVerifyAttestationPolicyHash_HashPresentNoPolicyFails checks the
// fail-closed case: hash is set but metadata has no policy key.
func TestVerifyAttestationPolicyHash_HashPresentNoPolicyFails(t *testing.T) {
	fakeHash := hex.EncodeToString(sha256.New().Sum(nil)) // non-zero

	// Pass nil policy → "policy" key absent from metadata JSON.
	bundlePath := buildPolicyHashBundle(t, nil, fakeHash)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	if err := reader.VerifyAttestationPolicyHash(); err == nil {
		t.Error("expected error when hash is set but metadata has no policy, got nil")
	}
}
