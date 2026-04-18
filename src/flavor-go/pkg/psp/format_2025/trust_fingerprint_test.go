// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"errors"
	"os"
	"testing"
)

// TestLoadKeyFromFileComputeFingerprintFails covers trust.go:106-108
// (computeKeyFingerprintFn returns error → error from loadKeyFromFile).
// ComputeKeyFingerprint always succeeds for a real Ed25519 key (32 bytes),
// so we inject computeKeyFingerprintFn to simulate a failure.
func TestLoadKeyFromFileComputeFingerprintFails(t *testing.T) {

	// Build a temp dir with a valid Ed25519 public key PEM file
	_, pemBlock := generateTestKeyPEM(t)
	keyPath := t.TempDir() + "/key.pub"
	if err := os.WriteFile(keyPath, pemBlock, 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	old := computeKeyFingerprintFn
	t.Cleanup(func() { computeKeyFingerprintFn = old })
	computeKeyFingerprintFn = func(_ []byte) (string, error) {
		return "", errors.New("injected fingerprint computation failure")
	}

	_, err := loadKeyFromFile(keyPath)
	if err == nil {
		t.Fatal("expected error from loadKeyFromFile when computeKeyFingerprintFn fails")
	}
}
