package format_2025

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestVerifyIntegritySealIoReadAllFails covers reader_verify.go:85-87
// (io.ReadAll failure for gzip data → error returned from VerifyIntegritySeal).
func TestVerifyIntegritySealIoReadAllFails(t *testing.T) {
	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	old := ioReadAllFn
	t.Cleanup(func() { ioReadAllFn = old })
	ioReadAllFn = func(_ io.Reader) ([]byte, error) {
		return nil, errors.New("injected io.ReadAll failure")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.VerifyIntegritySeal()
	if err == nil {
		t.Fatal("expected error from VerifyIntegritySeal when io.ReadAll fails")
	}
}

// TestVerifyAttestationSbomDigestSeekFails covers reader_verify.go:168-170
// (file.Seek for attestation slot data fails → error returned).
func TestVerifyAttestationSbomDigestSeekFails(t *testing.T) {

	slotContent := []byte("fake-sbom-content")
	digest := sha256.Sum256(slotContent)
	bundle := buildAttestationBundle(t, slotContent, hex.EncodeToString(digest[:]))

	old := fileSeekFn
	t.Cleanup(func() { fileSeekFn = old })
	fileSeekFn = func(_ *os.File, _ int64, _ int) (int64, error) {
		return 0, errors.New("injected seek failure in attestation verification")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	err := reader.VerifyAttestationSbomDigest()
	if err == nil {
		t.Fatal("expected error from VerifyAttestationSbomDigest when fileSeekFn fails")
	}
}

// TestVerifyAttestationPolicyHashJsonUnmarshalFails covers reader_verify.go:230-232
// (json.Unmarshal failure → error from VerifyAttestationPolicyHash).
func TestVerifyAttestationPolicyHashJsonUnmarshalFails(t *testing.T) {

	// Build a bundle with a policy and compute its canonical hash.
	policy := &PackagePolicy{
		Platforms: []string{"linux_amd64"},
	}
	policyJSON, err := json.Marshal(policy)
	if err != nil {
		t.Fatalf("json.Marshal(policy) error = %v", err)
	}
	// Compute canonical hash the same way the verifier does.
	var policyMap map[string]interface{}
	if err := json.Unmarshal(policyJSON, &policyMap); err != nil {
		t.Fatalf("json.Unmarshal error = %v", err)
	}
	canonical, _ := json.Marshal(policyMap)
	hashBytes := sha256.Sum256(canonical)
	hashHex := hex.EncodeToString(hashBytes[:])

	bundle := buildPolicyHashBundle(t, policy, hashHex)

	old := jsonUnmarshalFn
	t.Cleanup(func() { jsonUnmarshalFn = old })
	jsonUnmarshalFn = func(_ []byte, _ interface{}) error {
		return errors.New("injected json.Unmarshal failure")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	err = reader.VerifyAttestationPolicyHash()
	if err == nil {
		t.Fatal("expected error from VerifyAttestationPolicyHash when json.Unmarshal fails")
	}
}
