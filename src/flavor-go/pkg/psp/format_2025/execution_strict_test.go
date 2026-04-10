package format_2025

import (
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// buildSignedBundleWithSBOMDigestMismatch creates a properly signed bundle
// (so the integrity seal check passes) but with a non-zero AttestationSbomDigest
// and no attestation slot, causing VerifyAttestationSbomDigest to return an error.
// This is needed to reach lines 247-249 in execution.go for Standard/Strict validation.
func buildSignedBundleWithSBOMDigestMismatch(t *testing.T) string {
	t.Helper()

	// Build a signed bundle via doBuild so VerifyIntegritySeal returns (true, nil).
	bundle := buildSignedBundleForPolicyTests(t, BuildOptions{})

	// Patch the AttestationSbomDigest field to non-zero so VerifyAttestationSbomDigest fails.
	// AttestationSbomDigest is at bytes [1440:1504] in the packed index (64 bytes).
	patchBundleIndexBytes(t, bundle, func(idxBytes []byte) {
		for i := 1440; i < 1504; i++ {
			idxBytes[i] = 0x01
		}
	})

	return bundle
}

// buildSignedBundleWithPolicyHashMismatch creates a properly signed bundle
// (so the integrity seal check passes) but with a non-zero AttestationPolicyHash
// and no policy slot, causing VerifyAttestationPolicyHash to return an error.
// This is needed to reach lines 263-265 in execution.go for Standard/Strict validation.
func buildSignedBundleWithPolicyHashMismatch(t *testing.T) string {
	t.Helper()

	bundle := buildSignedBundleForPolicyTests(t, BuildOptions{})

	// Patch the AttestationPolicyHash field to non-zero so VerifyAttestationPolicyHash fails.
	// AttestationPolicyHash is at bytes [1504:1568] in the packed index (64 bytes).
	patchBundleIndexBytes(t, bundle, func(idxBytes []byte) {
		for i := 1504; i < 1568; i++ {
			idxBytes[i] = 0x01
		}
	})

	return bundle
}

// TestRunBundleWithCwdValidationStandardSBOMError covers lines 247-249 in execution.go:
// ValidationStandard (default case) with SBOM digest error → returns error.
// The bundle has a valid integrity seal (so the seal check passes) but an
// invalid SBOM digest (non-zero but no attestation slot), so the SBOM check fails.
func TestRunBundleWithCwdValidationStandardSBOMError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "standard")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildSignedBundleWithSBOMDigestMismatch(t)

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd with ValidationStandard and SBOM digest error")
	}
}

// TestRunBundleWithCwdValidationStrictSBOMError covers lines 247-249 in execution.go:
// ValidationStrict + SBOM digest error → returns error.
func TestRunBundleWithCwdValidationStrictSBOMError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "strict")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildSignedBundleWithSBOMDigestMismatch(t)

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd with ValidationStrict and SBOM digest error")
	}
}

// TestRunBundleWithCwdValidationStandardPolicyHashError covers lines 263-265 in execution.go:
// ValidationStandard + policy hash error → returns error.
func TestRunBundleWithCwdValidationStandardPolicyHashError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "standard")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildSignedBundleWithPolicyHashMismatch(t)

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd with ValidationStandard and policy hash error")
	}
}

// TestRunBundleWithCwdValidationStrictPolicyHashError covers lines 263-265 in execution.go:
// ValidationStrict + policy hash error → returns error.
func TestRunBundleWithCwdValidationStrictPolicyHashError(t *testing.T) {
	cacheRoot := t.TempDir()
	t.Setenv(EnvCacheDir, cacheRoot)
	t.Setenv(EnvValidation, "strict")
	t.Setenv(EnvWorkenvCache, "false")

	bundle := buildSignedBundleWithPolicyHashMismatch(t)

	logger := logging.NewNullLogger()
	_, err := runBundleWithCwd(bundle, nil, t.TempDir(), logger)
	if err == nil {
		t.Fatal("expected error from runBundleWithCwd with ValidationStrict and policy hash error")
	}
}
