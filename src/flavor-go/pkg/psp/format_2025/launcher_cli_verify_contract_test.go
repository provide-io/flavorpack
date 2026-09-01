package format_2025

// What `verify` actually verifies.
//
// The command printed "✓ Index checksum valid", "✓ Metadata checksum valid"
// and "✓ Bundle verification passed" for a package whose Ed25519 seal was
// never checked, whose index Adler-32 was never computed, and whose metadata
// SHA-256 was never compared. Only the magic bookends and the slot checksums
// were real, and both of those are unkeyed -- anyone who can rewrite the file
// can recompute them.
//
// Each test below tampers with exactly one thing and asserts the command says
// no. They fail against the implementation that shipped before this file.

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"hash/adler32"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// A committed seed, so a failure is reproducible rather than a new key each run.
var verifyTestSeed = bytes.Repeat([]byte{0x2a}, ed25519.SeedSize)

// sealIndex fills in the two fields a real builder computes last: the Ed25519
// signature over the raw metadata JSON, and the Adler-32 over the index itself.
//
// The checksum has to be computed over the packed bytes with its own field
// zeroed, which is the order the builder uses -- get it backwards and the
// index never validates.
func sealIndex(index *PSPFIndex, metaJSON []byte, priv ed25519.PrivateKey) {
	copy(index.IntegritySignature[:], ed25519.Sign(priv, metaJSON))
	copy(index.PublicKey[:], priv.Public().(ed25519.PublicKey))
	index.IndexChecksum = 0
	packed := index.Pack()
	binary.LittleEndian.PutUint32(packed[4:8], 0)
	index.IndexChecksum = adler32.Checksum(packed)
}

// buildSealedBundle writes a bundle that passes every check a verifier can make.
// Each test then breaks one thing.
func buildSealedBundle(t *testing.T) (path string, index *PSPFIndex, metaJSON []byte, priv ed25519.PrivateKey) {
	t.Helper()

	priv = ed25519.NewKeyFromSeed(verifyTestSeed)

	slotData := []byte("sealed payload")
	slotHash := sha256.Sum256(slotData)
	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName("payload"),
		Offset:       0,
		Size:         uint64(len(slotData)),
		OriginalSize: uint64(len(slotData)),
		Checksum:     binary.LittleEndian.Uint64(slotHash[:8]),
		Purpose:      PurposeData,
		Lifecycle:    LifecycleRuntime,
	}

	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "sealed", Version: "1.0.0"},
		Slots:         []SlotMetadata{{ID: "payload", Target: "{workenv}/payload", Slot: 0}},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "verify-test"},
	}
	var err error
	metaJSON, err = json.Marshal(metadata)
	if err != nil {
		t.Fatalf("Marshal(metadata): %v", err)
	}
	gzMeta := gzipData(t, metaJSON)

	slotTableOffset := uint64(len(slotData))
	metadataOffset := slotTableOffset + SlotDescriptorSize

	index = &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(slotData) + SlotDescriptorSize + len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  metadataOffset,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
	}
	metaHash := sha256.Sum256(gzMeta)
	copy(index.MetadataChecksum[:], metaHash[:])
	sealIndex(index, metaJSON, priv)

	path = testBundlePath(t, ".psp")
	body := append(append(append([]byte{}, slotData...), desc.Pack()...), gzMeta...)
	if err := os.WriteFile(path, append(body, packTrailer(index)...), 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	return path, index, metaJSON, priv
}

// packTrailer wraps an index in the 📦 / 🪄 bookends.
func packTrailer(index *PSPFIndex) []byte {
	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], index.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	return trailer
}

// rewriteTrailer swaps in a modified index, leaving the rest of the file alone.
func rewriteTrailer(t *testing.T, path string, index *PSPFIndex) {
	t.Helper()

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	copy(data[len(data)-MagicTrailerSize:], packTrailer(index))
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
}

// runVerify returns the exit code verifyBundle asked for, and what it printed.
func runVerify(t *testing.T, path string) (code int, output string) {
	t.Helper()

	oldExit := osExitFn
	code = 0
	osExitFn = func(c int) { code = c; panic(launcherExitCode{code: c}) }
	t.Cleanup(func() { osExitFn = oldExit })

	output = captureCLIOutput(func(out io.Writer) {
		defer func() { _ = recover() }()
		verifyBundle(out, path, logging.NewNullLogger())
	})
	return code, output
}

func TestVerifyAcceptsASealedBundle(t *testing.T) {
	path, _, _, _ := buildSealedBundle(t)

	code, output := runVerify(t, path)
	if code != 0 {
		t.Fatalf("exit code = %d, want 0; output:\n%s", code, output)
	}
	if !strings.Contains(output, "Bundle verification passed") {
		t.Fatalf("output = %q", output)
	}
}

// The one #35 was filed for: an attacker who rewrites a package recomputes
// every unkeyed checksum trivially. The signature is the only check that needs
// the signing key, and it was the only one not being made.
func TestVerifyRejectsATamperedSignature(t *testing.T) {
	path, index, metaJSON, priv := buildSealedBundle(t)

	index.IntegritySignature[0] ^= 0xFF
	// Re-seal everything *except* the signature, so the only thing wrong with
	// this package is the one thing that used to go unchecked.
	copy(index.PublicKey[:], priv.Public().(ed25519.PublicKey))
	index.IndexChecksum = 0
	packed := index.Pack()
	binary.LittleEndian.PutUint32(packed[4:8], 0)
	index.IndexChecksum = adler32.Checksum(packed)
	rewriteTrailer(t, path, index)
	_ = metaJSON

	code, output := runVerify(t, path)
	if code != 1 {
		t.Fatalf("a package with a broken seal verified: exit = %d; output:\n%s", code, output)
	}
}

// Parity with Rust, whose verify_integrity_seal returns false when the
// signature field is all zeros, making the package invalid overall.
func TestVerifyRejectsAnUnsignedBundle(t *testing.T) {
	path, index, metaJSON, priv := buildSealedBundle(t)

	index.IntegritySignature = [512]byte{}
	sealIndexKeepingSignature(index, metaJSON, priv)
	rewriteTrailer(t, path, index)

	code, output := runVerify(t, path)
	if code != 1 {
		t.Fatalf("an unsigned package verified: exit = %d; output:\n%s", code, output)
	}
}

// sealIndexKeepingSignature recomputes only the index checksum, leaving
// whatever the caller put in the signature field.
func sealIndexKeepingSignature(index *PSPFIndex, _ []byte, priv ed25519.PrivateKey) {
	copy(index.PublicKey[:], priv.Public().(ed25519.PublicKey))
	index.IndexChecksum = 0
	packed := index.Pack()
	binary.LittleEndian.PutUint32(packed[4:8], 0)
	index.IndexChecksum = adler32.Checksum(packed)
}

// "✓ Index checksum valid" was printed whenever the index merely parsed.
func TestVerifyRejectsACorruptIndexChecksum(t *testing.T) {
	path, index, _, _ := buildSealedBundle(t)

	index.IndexChecksum ^= 0xFFFF
	rewriteTrailer(t, path, index)

	code, output := runVerify(t, path)
	if code != 1 {
		t.Fatalf("a package with a bad index checksum verified: exit = %d; output:\n%s", code, output)
	}
}

// "✓ Metadata checksum valid" was printed whenever the metadata gunzipped and
// parsed, without ever comparing it to index.MetadataChecksum.
func TestVerifyRejectsTamperedMetadata(t *testing.T) {
	path, index, _, priv := buildSealedBundle(t)

	// Swap in different metadata, re-sign it and fix the index checksum, but
	// leave MetadataChecksum describing the original bytes.
	altered := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "altered", Version: "9.9.9"},
		Slots:         []SlotMetadata{{ID: "payload", Target: "{workenv}/payload", Slot: 0}},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/false"},
		Build:         &BuildInfo{Tool: "verify-test"},
	}
	alteredJSON, err := json.Marshal(altered)
	if err != nil {
		t.Fatalf("Marshal(altered): %v", err)
	}
	alteredGz := gzipData(t, alteredJSON)

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	head := data[:index.MetadataOffset]
	rebuilt := append(append([]byte{}, head...), alteredGz...)

	index.MetadataSize = uint64(len(alteredGz))
	index.PackageSize = uint64(len(rebuilt) + MagicTrailerSize)
	sealIndex(index, alteredJSON, priv)

	if err := os.WriteFile(path, append(rebuilt, packTrailer(index)...), 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	code, output := runVerify(t, path)
	if code != 1 {
		t.Fatalf("a package whose metadata does not match its recorded digest verified: exit = %d; output:\n%s", code, output)
	}
}

// The committed format-compatibility fixtures are real packages, signed by the
// Go, Rust and Python builders. If the tightened checks rejected any of them,
// the new conjunction would be wrong rather than the old one being too loose.
func TestVerifyAcceptsEveryCommittedFixture(t *testing.T) {
	_, names, dir := loadPinned(t)

	for _, name := range names {
		code, output := runVerify(t, filepath.Join(dir, name))
		if code != 0 {
			t.Errorf("%s no longer verifies: exit = %d; output:\n%s", name, code, output)
			continue
		}
		for _, want := range []string{
			"Magic sequence valid",
			"Index checksum valid",
			"Metadata checksum valid",
			"Package size valid",
			"Integrity seal valid",
			"Bundle verification passed",
		} {
			if !strings.Contains(output, want) {
				t.Errorf("%s: output missing %q:\n%s", name, want, output)
			}
		}
	}
}
