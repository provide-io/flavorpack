package format_2025

// Verify the committed cross-version format-compatibility fixtures.
//
// These packages were built once, by an older toolchain, and are never rebuilt.
// Every other test in this package builds and verifies inside a single run, so
// both sides of the comparison move together and a format change stays
// invisible. These fixtures are the only thing that fails when a package built
// before a crypto, hashing, or layout change stops verifying after it.
//
// See tests/fixtures/format_compat/README.md.

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"testing"
)

const fixtureGeneration = "v1"

type pinnedFixture struct {
	Producer       string `json:"producer"`
	SHA256         string `json:"sha256"`
	Size           int64  `json:"size"`
	PublicKey      string `json:"public_key"`
	KeyFingerprint string `json:"key_fingerprint"`
	SlotCount      uint32 `json:"slot_count"`
}

type pinnedGeneration struct {
	Generation string `json:"generation"`
	KeySeed    string `json:"key_seed"`
	Package    struct {
		Name    string `json:"name"`
		Version string `json:"version"`
	} `json:"package"`
	Fixtures map[string]pinnedFixture `json:"fixtures"`
}

// repoRoot walks upward from the test's working directory to the checkout root,
// so the fixture path does not depend on how deep this package happens to sit.
func repoRoot(t *testing.T) string {
	t.Helper()

	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}

	for {
		if _, err := os.Stat(filepath.Join(dir, "VERSION")); err == nil {
			if _, err := os.Stat(filepath.Join(dir, "src", "flavor-go")); err == nil {
				return dir
			}
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("could not locate the repository root above the test directory")
		}
		dir = parent
	}
}

func fixtureDir(t *testing.T) string {
	t.Helper()
	return filepath.Join(repoRoot(t), "tests", "fixtures", "format_compat", fixtureGeneration)
}

// loadPinned reads expected.json and returns it with the fixture names sorted,
// so failures are reported in a stable order.
func loadPinned(t *testing.T) (pinnedGeneration, []string, string) {
	t.Helper()

	dir := fixtureDir(t)
	raw, err := os.ReadFile(filepath.Join(dir, "expected.json"))
	if err != nil {
		t.Fatalf("read expected.json: %v", err)
	}

	var pinned pinnedGeneration
	if err := json.Unmarshal(raw, &pinned); err != nil {
		t.Fatalf("parse expected.json: %v", err)
	}
	if len(pinned.Fixtures) == 0 {
		t.Fatal("expected.json lists no fixtures")
	}

	names := make([]string, 0, len(pinned.Fixtures))
	for name := range pinned.Fixtures {
		names = append(names, name)
	}
	sort.Strings(names)

	return pinned, names, dir
}

// openFixture returns a reader for one fixture, closed when the test ends.
func openFixture(t *testing.T, path string) *Reader {
	t.Helper()

	reader, err := NewReader(path)
	if err != nil {
		t.Fatalf("open reader: %v", err)
	}
	t.Cleanup(func() {
		if err := reader.Close(); err != nil {
			t.Errorf("close reader: %v", err)
		}
	})
	return reader
}

// TestFixtureBytesAreUnchanged pins each fixture's digest. Regenerating one
// silently converts this whole file into a tautology, so a rebuild has to be
// argued for in review.
func TestFixtureBytesAreUnchanged(t *testing.T) {
	t.Parallel()
	pinned, names, dir := loadPinned(t)

	for _, name := range names {
		want := pinned.Fixtures[name]
		data, err := os.ReadFile(filepath.Join(dir, name))
		if err != nil {
			t.Errorf("%s: read: %v", name, err)
			continue
		}
		if int64(len(data)) != want.Size {
			t.Errorf("%s: size is %d, pinned at %d", name, len(data), want.Size)
		}
		digest := sha256.Sum256(data)
		if got := hex.EncodeToString(digest[:]); got != want.SHA256 {
			t.Errorf("%s was regenerated (sha256 %s, pinned %s). That destroys the "+
				"cross-version guarantee: the fixture is only evidence while it "+
				"predates the code verifying it.", name, got, want.SHA256)
		}
	}
}

// TestOldPackagesStillVerify is the assertion the fixtures exist for: today's
// verifier accepts a package built by an older toolchain.
func TestOldPackagesStillVerify(t *testing.T) {
	t.Parallel()
	pinned, names, dir := loadPinned(t)

	for _, name := range names {
		want := pinned.Fixtures[name]
		reader := openFixture(t, filepath.Join(dir, name))

		if ok, err := reader.VerifyMagicTrailer(); err != nil || !ok {
			t.Errorf("%s: magic trailer no longer valid (ok=%v, err=%v)", name, ok, err)
		}

		index, err := reader.ReadIndex()
		if err != nil {
			t.Errorf("%s: index no longer reads: %v", name, err)
			continue
		}
		if index.SlotCount != want.SlotCount {
			t.Errorf("%s: slot count is %d, pinned at %d", name, index.SlotCount, want.SlotCount)
		}

		metadata, err := reader.ReadMetadata()
		if err != nil {
			t.Errorf("%s: metadata no longer reads: %v", name, err)
			continue
		}
		if metadata.Package.Name != pinned.Package.Name {
			t.Errorf("%s: package name is %q, pinned at %q", name, metadata.Package.Name, pinned.Package.Name)
		}
		if metadata.Package.Version != pinned.Package.Version {
			t.Errorf("%s: package version is %q, pinned at %q", name, metadata.Package.Version, pinned.Package.Version)
		}

		if err := reader.VerifyAllChecksums(); err != nil {
			t.Errorf("%s: checksums no longer match: %v", name, err)
		}

		// Read explicitly rather than relying on the launcher's verify command,
		// which does not check the seal.
		if ok, err := reader.VerifyIntegritySeal(); err != nil || !ok {
			t.Errorf("%s: Ed25519 seal no longer verifies (ok=%v, err=%v)", name, ok, err)
		}
	}
}

// TestSigningKeyMaterialIsStable pins the embedded key and its fingerprint.
// Both are derived from the committed seed, so drift here means key derivation
// or the digest behind the fingerprint changed underneath us.
func TestSigningKeyMaterialIsStable(t *testing.T) {
	t.Parallel()
	pinned, names, dir := loadPinned(t)

	for _, name := range names {
		want := pinned.Fixtures[name]
		reader := openFixture(t, filepath.Join(dir, name))

		index, err := reader.ReadIndex()
		if err != nil {
			t.Errorf("%s: read index: %v", name, err)
			continue
		}

		if got := hex.EncodeToString(index.PublicKey[:]); got != want.PublicKey {
			t.Errorf("%s: embedded public key is %s, pinned at %s", name, got, want.PublicKey)
		}

		fingerprint := string(bytes.TrimRight(index.AttestationKeyFp[:], "\x00"))
		if fingerprint != want.KeyFingerprint {
			t.Errorf("%s: key fingerprint is %s, pinned at %s", name, fingerprint, want.KeyFingerprint)
		}
	}
}

// TestPayloadSlotRoundTrips checks that slot 0 still decodes to the committed
// payload, byte for byte.
func TestPayloadSlotRoundTrips(t *testing.T) {
	t.Parallel()
	_, names, dir := loadPinned(t)

	payload, err := os.ReadFile(filepath.Join(dir, "inputs", "payload.txt"))
	if err != nil {
		t.Fatalf("read payload: %v", err)
	}

	for _, name := range names {
		reader := openFixture(t, filepath.Join(dir, name))
		if _, err := reader.ReadMetadata(); err != nil {
			t.Errorf("%s: read metadata: %v", name, err)
			continue
		}

		data, err := reader.ReadSlot(0)
		if err != nil {
			t.Errorf("%s: read slot 0: %v", name, err)
			continue
		}
		if !bytes.Equal(data, payload) {
			t.Errorf("%s: slot 0 no longer decodes to the payload", name)
		}
	}
}

// TestEveryProducerDerivesTheSameKey checks that deterministic key generation is
// deterministic across implementations, not merely within one.
func TestEveryProducerDerivesTheSameKey(t *testing.T) {
	t.Parallel()
	pinned, names, _ := loadPinned(t)

	first := pinned.Fixtures[names[0]].PublicKey
	for _, name := range names {
		if got := pinned.Fixtures[name].PublicKey; got != first {
			t.Errorf("%s derives %s from the seed, but %s derives %s", name, got, names[0], first)
		}
	}
}

// TestExecutionBlockOmittingPrimarySlotIsReadable reads the one metadata
// document every implementation has to agree on.
//
// primary_slot was required by Rust and optional here and in Python, so a
// package without it was ordinary to two implementations and unopenable to the
// third. The environment was worse: it is written under "env" by Rust and
// Python, and this implementation read "environment", so an environment set by
// either of them was dropped without a word. The fixture omits primary_slot and
// carries a non-empty env; see tests/fixtures/format_compat/execution/README.md.
func TestExecutionBlockOmittingPrimarySlotIsReadable(t *testing.T) {
	t.Parallel()

	path := filepath.Join(repoRoot(t), "tests", "fixtures", "format_compat", "execution", "omits-primary-slot.json")
	raw, err := os.ReadFile(path) //nolint:gosec // fixture path built from the repo root
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}

	// The fixture is only worth anything while it keeps omitting the field.
	var probe struct {
		Execution map[string]json.RawMessage `json:"execution"`
	}
	if err := json.Unmarshal(raw, &probe); err != nil {
		t.Fatalf("parse fixture: %v", err)
	}
	if _, present := probe.Execution["primary_slot"]; present {
		t.Fatal("the fixture must keep omitting primary_slot")
	}

	var metadata Metadata
	if err := json.Unmarshal(raw, &metadata); err != nil {
		t.Fatalf("metadata must parse without primary_slot: %v", err)
	}
	if metadata.Execution == nil {
		t.Fatal("execution block missing")
	}
	if metadata.Execution.PrimarySlot != 0 {
		t.Errorf("PrimarySlot = %d, want 0", metadata.Execution.PrimarySlot)
	}
	if metadata.Execution.Command != "true" {
		t.Errorf("Command = %q, want %q", metadata.Execution.Command, "true")
	}
	if got := metadata.Execution.Environment["MODE"]; got != "prod" {
		t.Errorf("Environment[\"MODE\"] = %q, want %q — the environment must be read from the \"env\" key", got, "prod")
	}
}
