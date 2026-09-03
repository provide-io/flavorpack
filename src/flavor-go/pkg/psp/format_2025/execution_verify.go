// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"errors"
	"fmt"
	"log/slog"
	"os"
	"strings"
)

// checkSigningKeyTrust reports whether the package's signing key is in the
// trusted store, and fails closed on an attestation fingerprint that does not
// describe the embedded key.
//
// An untrusted key is not fatal here: it warns, and EnforcePolicy decides what
// the operator policy makes of it.
func checkSigningKeyTrust(index *PSPFIndex, logger *slog.Logger) (bool, error) {
	hasPublicKey := false
	for _, b := range index.PublicKey {
		if b != 0 {
			hasPublicKey = true
			break
		}
	}

	attestationFP := strings.TrimRight(string(index.AttestationKeyFp[:]), "\x00")

	if !hasPublicKey {
		if attestationFP != "" {
			return false, errors.New("attestation key fingerprint is present but public key is missing")
		}
		return false, nil
	}

	fp, err := ComputeKeyFingerprint(index.PublicKey[:])
	if err != nil {
		logger.Warn("⚠️ Failed to derive signing key fingerprint", "error", err)
		return false, nil
	}

	if attestationFP != "" && attestationFP != fp {
		return false, errors.New("attestation key fingerprint does not match embedded public key")
	}

	trusted, err := IsKeyTrusted(fp, true)
	switch {
	case err != nil:
		logger.Warn("⚠️ Failed to check trusted key store", "error", err)
	case trusted == nil:
		logger.Warn("⚠️ No trusted-keys store found; requiring a trusted key will fail closed", "fingerprint", fp)
	case *trusted:
		return true, nil
	default:
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Package signing key is not in the trusted store\n")
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ Key fingerprint: %s\n", fp)
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ Use 'flavor trust add <key-file>' to trust this key\n")
		logger.Warn("⚠️ Package signing key not in trusted store", "fingerprint", fp)
	}

	return false, nil
}

// tolerateVerificationError decides what a check that could not complete means
// at this validation level: minimal and relaxed continue with a warning, and
// standard and strict stop. Returning nil means the caller carries on.
//
// The three integrity checks differ only in what they name, so subject is the
// caller's phrase for the thing it failed to verify.
func tolerateVerificationError(level ValidationLevel, subject string, err error, logger *slog.Logger) error {
	switch level {
	case ValidationMinimal, ValidationRelaxed:
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Failed to verify %s: %v\n", subject, err)
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ Continuing due to validation level: %v\n", level)
		logger.Warn("⚠️ Failed to verify "+subject+", continuing", "error", err, "level", level)
		return nil
	default: // ValidationStrict, ValidationStandard
		logger.Error("❌ Failed to verify "+subject, "error", err)
		return fmt.Errorf("failed to verify %s: %w", subject, err)
	}
}

// tolerateIntegrityFailure decides what a seal that verified cleanly and came
// back invalid means. It is separate from tolerateVerificationError because a
// package that fails its seal is a different event from one whose seal could
// not be read, and standard treats the two differently.
func tolerateIntegrityFailure(level ValidationLevel, logger *slog.Logger) error {
	switch level {
	case ValidationMinimal, ValidationRelaxed:
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Package integrity verification failed\n")
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ Package may be corrupted or tampered with\n")
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ Continuing due to validation level: %v\n", level)
		logger.Warn("⚠️ Package integrity verification failed, continuing", "level", level)
		return nil
	case ValidationStandard:
		_, _ = fmt.Fprintf(os.Stderr, "🚨 SECURITY WARNING: Package integrity verification failed\n")
		_, _ = fmt.Fprintf(os.Stderr, "🚨 Package may be corrupted or tampered with\n")
		_, _ = fmt.Fprintf(os.Stderr, "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)\n")
		logger.Warn("⚠️ Package integrity verification failed, continuing with standard validation")
		return nil
	default: // ValidationStrict
		logger.Error("❌ Package integrity verification failed")
		return errors.New("package integrity verification failed")
	}
}

// verifyPackageIntegrity runs the three integrity checks a launch depends on:
// the Ed25519 seal, the attestation SBOM digest, and the attestation policy
// hash. Each one's failure is referred to the validation level rather than
// decided here.
func verifyPackageIntegrity(reader *Reader, level ValidationLevel, logger *slog.Logger) error {
	if level == ValidationNone {
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ SECURITY WARNING: Skipping all integrity verification (FLAVOR_VALIDATION=none)\n")
		_, _ = fmt.Fprintf(os.Stderr, "⚠️ This is NOT RECOMMENDED for production use\n")
		logger.Warn("⚠️ VALIDATION DISABLED: Skipping integrity verification", "level", level)
		return nil
	}

	logger.Debug("🔍 Verifying package integrity", "level", level)
	valid, err := verifyIntegritySealFn(reader)
	switch {
	case err != nil:
		if tolerated := tolerateVerificationError(level, "integrity seal", err, logger); tolerated != nil {
			return tolerated
		}
	case !valid:
		if tolerated := tolerateIntegrityFailure(level, logger); tolerated != nil {
			return tolerated
		}
	default:
		logger.Debug("✅ Package integrity verified")
	}

	// Fail-closed: a digest present with the slot absent is an error.
	logger.Debug("🔍 Verifying attestation SBOM digest", "level", level)
	if err := reader.VerifyAttestationSbomDigest(); err != nil {
		if tolerated := tolerateVerificationError(level, "attestation SBOM digest", err, logger); tolerated != nil {
			return tolerated
		}
	} else {
		logger.Debug("✅ Attestation SBOM digest verified")
	}

	// Fail-closed: a hash present with no policy is an error.
	logger.Debug("🔍 Verifying attestation policy hash", "level", level)
	if err := reader.VerifyAttestationPolicyHash(); err != nil {
		if tolerated := tolerateVerificationError(level, "attestation policy hash", err, logger); tolerated != nil {
			return tolerated
		}
	} else {
		logger.Debug("✅ Attestation policy hash verified")
	}

	return nil
}

// enforcePackagePolicy merges the package's policy with the operator's and
// applies the result. Warnings are logged; a violation stops the launch.
func enforcePackagePolicy(metadata *Metadata, index *PSPFIndex, keyTrusted bool, logger *slog.Logger) error {
	opPolicy, err := LoadOperatorPolicy()
	if err != nil {
		logger.Error("❌ Failed to load operator policy", "error", err)
		return fmt.Errorf("failed to load operator policy: %w", err)
	}

	var pkgPolicy PackagePolicy
	if metadata.Policy != nil {
		pkgPolicy = *metadata.Policy
	}
	effective := MergePolicy(pkgPolicy, opPolicy)

	hasSBOM := false
	for _, slot := range metadata.Slots {
		if slot.Lifecycle == "attestation" {
			hasSBOM = true
			break
		}
	}

	buildTimestamp, err := uint64ToInt64Checked(index.BuildTimestamp, "build timestamp")
	if err != nil {
		logger.Error("❌ Invalid build timestamp", "error", err)
		return fmt.Errorf("invalid build timestamp: %w", err)
	}

	policyWarnings, enforceErr := EnforcePolicy(effective, buildTimestamp, hasSBOM, keyTrusted)
	for _, w := range policyWarnings {
		logger.Warn("⚠️  Policy warning", "message", w)
	}
	if enforceErr != nil {
		logger.Error("❌ Policy violation", "error", enforceErr)
		return fmt.Errorf("policy violation: %w", enforceErr)
	}

	logger.Debug("✅ Policy enforcement passed")
	return nil
}
