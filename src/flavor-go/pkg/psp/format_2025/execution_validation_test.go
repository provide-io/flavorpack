package format_2025

import (
	"crypto/ed25519"
	cryptorand "crypto/rand"
	"encoding/binary"
	"os"
	"strings"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// patchBundleIndexBytes reads the bundle, applies fn to the raw PSPFIndex bytes
// embedded in the trailer, and writes the modified bundle back.
func patchBundleIndexBytes(t *testing.T, bundlePath string, fn func(idxBytes []byte)) {
	t.Helper()

	data, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if len(data) < MagicTrailerSize {
		t.Fatalf("bundle too small: %d", len(data))
	}
	trailerStart := len(data) - MagicTrailerSize
	// Index bytes start at offset 4 (after start emoji), length IndexSize.
	idxBytes := data[trailerStart+4 : trailerStart+4+IndexSize]
	fn(idxBytes)
	if err := os.WriteFile(bundlePath, data, 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
}

// buildBundleWithFakeSignature creates a bundle and patches a non-zero but
// invalid IntegritySignature into the index, so VerifyIntegritySeal returns
// (false, ErrSignatureInvalid) - the "!valid" branch.
func buildBundleWithFakeSignature(t *testing.T) string {
	t.Helper()

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "sig-slot",
		Target: "{workenv}",
	}, 0, false)

	// Patch a non-zero public key (32 bytes at offset 64 in index) and a
	// non-zero fake signature (64 bytes at offset 128 in index), so
	// VerifyIntegritySeal finds a signature but can't verify it.
	patchBundleIndexBytes(t, bundle, func(idxBytes []byte) {
		// Public key is at bytes [64:96] in index
		for i := 64; i < 96; i++ {
			idxBytes[i] = 0x01
		}
		// IntegritySignature is at bytes [128:640] in index; first 64 bytes used
		for i := 128; i < 192; i++ {
			idxBytes[i] = 0x02
		}
	})

	return bundle
}

// buildBundleWithAttestationFPMismatch creates a bundle with a non-zero
// public key and an AttestationKeyFp that does NOT match the fingerprint
// derived from that public key.
func buildBundleWithAttestationFPMismatch(t *testing.T) string {
	t.Helper()

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "fp-slot",
		Target: "{workenv}",
	}, 0, false)

	// Generate a real ed25519 key so we have a valid public key.
	pub, _, err := ed25519.GenerateKey(cryptorand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey: %v", err)
	}

	patchBundleIndexBytes(t, bundle, func(idxBytes []byte) {
		// Set public key (bytes [64:96] in index)
		copy(idxBytes[64:96], pub)

		// Set AttestationKeyFp to something wrong (all 0x41 = 'A' bytes)
		// AttestationKeyFp is at offset 1376-1440 in index.
		for i := 1376; i < 1440; i++ {
			idxBytes[i] = 0x41
		}
	})

	return bundle
}

// buildBundleWithAttestationFPButNoPublicKey creates a bundle with an
// AttestationKeyFp set but zero public key (all zeros), so the "attestation
// fp present but public key is missing" branch (line 195) is hit.
func buildBundleWithAttestationFPButNoPublicKey(t *testing.T) string {
	t.Helper()

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "nokey-slot",
		Target: "{workenv}",
	}, 0, false)

	patchBundleIndexBytes(t, bundle, func(idxBytes []byte) {
		// Public key stays all-zero (no key).
		// AttestationKeyFp at bytes [1376:1440] — set to non-zero value.
		for i := 1376; i < 1440; i++ {
			idxBytes[i] = 0x42
		}
	})

	return bundle
}

// buildBundleWithSBOMDigestMismatch creates a bundle that has an
// AttestationSbomDigest set but no attestation slot, causing
// VerifyAttestationSbomDigest to return an error.
func buildBundleWithSBOMDigestMismatch(t *testing.T) string {
	t.Helper()

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "sbom-slot",
		Target: "{workenv}",
	}, 0, false)

	// AttestationSbomDigest is at bytes [1440:1504] in the packed index (64 bytes).
	// See index.go Pack(): copy(buf[1440:1504], idx.AttestationSbomDigest[:])
	patchBundleIndexBytes(t, bundle, func(idxBytes []byte) {
		for i := 1440; i < 1504; i++ {
			idxBytes[i] = 0x01
		}
	})

	return bundle
}

// buildBundleWithPolicyHashMismatch creates a bundle that has an
// AttestationPolicyHash set but no policy slot, causing
// VerifyAttestationPolicyHash to return an error.
func buildBundleWithPolicyHashMismatch(t *testing.T) string {
	t.Helper()

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "policy-slot",
		Target: "{workenv}",
	}, 0, false)

	// AttestationPolicyHash is at bytes [1504:1568] in the packed index (64 bytes).
	// See index.go Pack(): copy(buf[1504:1568], idx.AttestationPolicyHash[:])
	patchBundleIndexBytes(t, bundle, func(idxBytes []byte) {
		for i := 1504; i < 1568; i++ {
			idxBytes[i] = 0x01
		}
	})

	return bundle
}

// TestRunBundleWithCwdValidationMinimalIntegritySealError covers lines 211-214:
// ValidationMinimal + integrity seal error (ErrNoIntegritySeal) → continues with warning.
func TestRunBundleWithCwdValidationMinimalIntegritySealError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "minimal")
	t.Setenv(EnvWorkenvCache, "false")

	// Standard bundle without signature → ErrNoIntegritySeal
	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (expected continuation with warning)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdValidationRelaxedIntegritySealError covers the same
// ValidationRelaxed branch.
func TestRunBundleWithCwdValidationRelaxedIntegritySealError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "relaxed")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (expected continuation with warning)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdValidationMinimalInvalidSignature covers lines 211-214
// (the ValidationMinimal/Relaxed + err != nil → continue with warning path)
// using a bundle that has a non-zero but invalid signature, causing
// VerifyIntegritySeal to return an error (ErrSignatureInvalid).
func TestRunBundleWithCwdValidationMinimalInvalidSignature(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "minimal")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildBundleWithFakeSignature(t)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (expected continuation with warning)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdAttestationFPMismatch covers line 177-179:
// hasPublicKey + attestationFP != "" + fp mismatch → returns error.
func TestRunBundleWithCwdAttestationFPMismatch(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildBundleWithAttestationFPMismatch(t)

	logger := hclog.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error for attestation FP mismatch")
	}
	if !strings.Contains(err.Error(), "attestation key fingerprint does not match") {
		t.Fatalf("expected fingerprint mismatch error, got: %v", err)
	}
}

// TestRunBundleWithCwdAttestationFPWithNoPublicKey covers line 195-196:
// attestationFP != "" but hasPublicKey = false → returns error.
func TestRunBundleWithCwdAttestationFPWithNoPublicKey(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "none")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildBundleWithAttestationFPButNoPublicKey(t)

	logger := hclog.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error for attestation FP with missing public key")
	}
	if !strings.Contains(err.Error(), "attestation key fingerprint is present but public key is missing") {
		t.Fatalf("expected missing public key error, got: %v", err)
	}
}

// TestRunBundleWithCwdValidationMinimalSBOMError covers lines 242-246:
// ValidationMinimal + SBOM digest error → continues with warning.
func TestRunBundleWithCwdValidationMinimalSBOMError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "minimal")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildBundleWithSBOMDigestMismatch(t)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (expected continuation with SBOM warning)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdValidationRelaxedSBOMError also covers lines 242-246.
func TestRunBundleWithCwdValidationRelaxedSBOMError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "relaxed")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildBundleWithSBOMDigestMismatch(t)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdValidationMinimalPolicyHashError covers lines 258-262:
// ValidationMinimal + policy hash verification error → continues with warning.
func TestRunBundleWithCwdValidationMinimalPolicyHashError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "minimal")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildBundleWithPolicyHashMismatch(t)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v (expected continuation with policy hash warning)", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestRunBundleWithCwdValidationRelaxedPolicyHashError also covers lines 258-262.
func TestRunBundleWithCwdValidationRelaxedPolicyHashError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "relaxed")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildBundleWithPolicyHashMismatch(t)

	logger := hclog.NewNullLogger()
	cmd, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err != nil {
		t.Fatalf("runBundleWithCwd() error = %v", err)
	}
	if cmd == nil {
		t.Fatal("expected non-nil exec.Cmd")
	}
}

// TestPrepareBundlePathIncompleteWrite covers lines 96-100 of execution.go:
// the incomplete write path (bytesWritten != len(pspfData)).
// We inject a custom readPSPFFromResourceFn that returns known data, then
// inject a hasPSPFResourceFn that returns true, and mock the temp file write
// to report fewer bytes. Since os.File.Write reports the actual bytes written
// (not injectable directly), we instead inject data whose size is reported
// larger than what the OS will write by using a fake int from readPSPFFromResourceFn
// returning a []byte with a length trick — but that isn't possible without
// production code changes.
//
// Instead, we cover the error path by injecting a hasPSPFResourceFn that
// returns true and readPSPFFromResourceFn that returns an empty slice, causing
// a zero-byte write where len(pspfData) == 0, which means bytesWritten == 0 == len(pspfData)
// (no mismatch). So the incomplete write path requires a mismatch that can't
// be forced without an injectable tempFile. This path is not covered.
//
// We do cover the tmpFile.Close() failure path and the write error path using
// the existing injection approach from TestPrepareBundlePathPEResourceSuccess.
// These are already tested in execution_prepare_test.go. Skip this file entry.

// TestPrepareBundlePathCleanupRemovesFails ensures cleanup fn handles remove errors.
// This is a coverage supplement for the cleanup closure (lines 115-122).
func TestPrepareBundlePathCleanupRemovesFails(t *testing.T) {
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	})

	pspfData := []byte("fake-pspf-data")
	hasPSPFResourceFn = func(path string, logger hclog.Logger) bool { return true }
	readPSPFFromResourceFn = func(path string, logger hclog.Logger) ([]byte, error) {
		return pspfData, nil
	}

	logger := hclog.NewNullLogger()
	bundlePath, cleanup, err := prepareBundlePath("/fake/exe", logger)
	if err != nil {
		t.Fatalf("prepareBundlePath() error = %v", err)
	}
	if cleanup == nil {
		t.Fatal("expected cleanup function")
	}

	// Remove the file so the cleanup's os.Remove call will get an error — this
	// exercises the "Failed to remove temp file" debug log path.
	if err := os.Remove(bundlePath); err != nil {
		t.Fatalf("os.Remove: %v", err)
	}

	// Should not panic even though the file is already gone.
	cleanup()
}

// TestRunBundleWithCwdPrepareBundlePathError covers the prepareBundlePath error
// path at line 134-137 (when hasPSPFResourceFn returns true but read fails).
func TestRunBundleWithCwdPrepareBundlePathError(t *testing.T) {
	oldHas := hasPSPFResourceFn
	oldRead := readPSPFFromResourceFn
	t.Cleanup(func() {
		hasPSPFResourceFn = oldHas
		readPSPFFromResourceFn = oldRead
	})

	hasPSPFResourceFn = func(path string, logger hclog.Logger) bool { return true }
	readPSPFFromResourceFn = func(path string, logger hclog.Logger) ([]byte, error) {
		return nil, os.ErrNotExist
	}

	logger := hclog.NewNullLogger()
	_, err := runBundleWithCwd("/fake/exe", nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error when prepareBundlePath fails")
	}
}

// findAttestationPolicyHashOffset finds the offset of AttestationPolicyHash in the index.
// From index.go Pack(): copy(buf[1504:1568], idx.AttestationPolicyHash[:])
func findAttestationPolicyHashOffset() int {
	return 1504
}

// Verify our patch offset assumptions by checking a known bundle index.
func TestIndexPatchOffsets(t *testing.T) {
	t.Parallel()

	bundle := buildSingleSlotBundleForTests(t, []byte("x"), []byte("x"), nil, SlotMetadata{
		ID:     "chk",
		Target: "{workenv}",
	}, 0, false)

	data, err := os.ReadFile(bundle)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}

	trailerStart := len(data) - MagicTrailerSize
	idxBytes := data[trailerStart+4 : trailerStart+4+IndexSize]

	// Verify that IndexSize constant is consistent with what we think.
	if len(idxBytes) != IndexSize {
		t.Fatalf("idx bytes len = %d, want IndexSize = %d", len(idxBytes), IndexSize)
	}

	// Verify FormatVersion is at offset 0 (4 bytes, LE uint32).
	fv := binary.LittleEndian.Uint32(idxBytes[0:4])
	if fv != PSPFVersion {
		t.Fatalf("FormatVersion = 0x%x, want 0x%x", fv, PSPFVersion)
	}
}
