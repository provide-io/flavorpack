package format_2025

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// generateTestKeyPEM creates a fresh Ed25519 key pair and returns the raw public key bytes
// and a PEM-encoded SubjectPublicKeyInfo block suitable for writing to a .pub file.
func generateTestKeyPEM(t *testing.T) (rawPub []byte, pemBlock []byte) {
	t.Helper()
	pub, _, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("failed to generate Ed25519 key: %v", err)
	}
	der, err := x509.MarshalPKIXPublicKey(pub)
	if err != nil {
		t.Fatalf("failed to marshal public key: %v", err)
	}
	block := pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: der})
	return []byte(pub), block
}

// TestComputeKeyFingerprint verifies that the fingerprint of known key bytes is stable and correct.
func TestComputeKeyFingerprint(t *testing.T) {
	// Use a deterministic 32-byte key for reproducibility
	key := make([]byte, 32)
	for i := range key {
		key[i] = byte(i)
	}

	fp, err := ComputeKeyFingerprint(key)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(fp) != 64 {
		t.Errorf("fingerprint length: got %d, want 64", len(fp))
	}

	// Same key → same fingerprint (deterministic)
	fp2, err := ComputeKeyFingerprint(key)
	if err != nil {
		t.Fatalf("unexpected error on second call: %v", err)
	}
	if fp != fp2 {
		t.Errorf("fingerprint not deterministic: %s != %s", fp, fp2)
	}
}

// TestComputeKeyFingerprint_WrongSize ensures an error is returned for wrong-size input.
func TestComputeKeyFingerprint_WrongSize(t *testing.T) {
	_, err := ComputeKeyFingerprint([]byte{1, 2, 3})
	if err == nil {
		t.Error("expected error for wrong key size, got nil")
	}
}

// TestLoadTrustedKeys_EmptyDir returns an empty map (not error) for an existing but empty dir.
func TestLoadTrustedKeys_EmptyDir(t *testing.T) {
	dir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, dir)

	keys, err := LoadTrustedKeys(false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(keys) != 0 {
		t.Errorf("expected empty map, got %d entries", len(keys))
	}
}

// TestLoadTrustedKeys_MissingDir returns an empty map (not error) when dir does not exist.
func TestLoadTrustedKeys_MissingDir(t *testing.T) {
	t.Setenv(EnvTrustedKeysDir, "/nonexistent/path/that/does/not/exist/trusted-keys")

	keys, err := LoadTrustedKeys(false)
	if err != nil {
		t.Fatalf("unexpected error for missing dir: %v", err)
	}
	if len(keys) != 0 {
		t.Errorf("expected empty map, got %d entries", len(keys))
	}
}

// TestLoadTrustedKeys_ValidKey loads a single .pub file correctly.
func TestLoadTrustedKeys_ValidKey(t *testing.T) {
	dir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, dir)

	rawPub, pemBlock := generateTestKeyPEM(t)

	// Write a .pub file with a Name comment
	content := fmt.Sprintf("# Name: Test Signing Key\n%s", string(pemBlock))
	if err := os.WriteFile(filepath.Join(dir, "test-key.pub"), []byte(content), 0600); err != nil {
		t.Fatalf("failed to write test key file: %v", err)
	}

	keys, err := LoadTrustedKeys(false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(keys) != 1 {
		t.Fatalf("expected 1 key, got %d", len(keys))
	}

	expectedFP, err := ComputeKeyFingerprint(rawPub)
	if err != nil {
		t.Fatalf("failed to compute expected fingerprint: %v", err)
	}

	tk, ok := keys[expectedFP]
	if !ok {
		t.Fatalf("key with fingerprint %s not found in map", expectedFP)
	}
	if tk.Name != "Test Signing Key" {
		t.Errorf("key name: got %q, want %q", tk.Name, "Test Signing Key")
	}
	if tk.Fingerprint != expectedFP {
		t.Errorf("key fingerprint mismatch: got %s, want %s", tk.Fingerprint, expectedFP)
	}
}

// TestIsKeyTrusted_NoStore returns nil when no trusted-keys directory exists.
func TestIsKeyTrusted_NoStore(t *testing.T) {
	t.Setenv(EnvTrustedKeysDir, "/nonexistent/path/flavor/trusted-keys")
	// Disable system config lookup
	t.Setenv(EnvConfigDir, "/nonexistent/path/flavor/config")

	result, err := IsKeyTrusted("abc123", false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != nil {
		t.Errorf("expected nil (no store), got %v", *result)
	}
}

// TestIsKeyTrusted_Match returns true when the fingerprint is found in the store.
func TestIsKeyTrusted_Match(t *testing.T) {
	dir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, dir)

	rawPub, pemBlock := generateTestKeyPEM(t)
	if err := os.WriteFile(filepath.Join(dir, "mykey.pub"), pemBlock, 0600); err != nil {
		t.Fatalf("failed to write key file: %v", err)
	}

	fp, err := ComputeKeyFingerprint(rawPub)
	if err != nil {
		t.Fatalf("compute fingerprint: %v", err)
	}

	result, err := IsKeyTrusted(fp, false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil result (store exists)")
	}
	if !*result {
		t.Error("expected true (key is trusted), got false")
	}
}

// TestLoadTrustedKeys_WithSystemDir exercises the includeSystem=true path.
func TestLoadTrustedKeys_WithSystemDir(t *testing.T) {
	dir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, dir)

	// Non-existent system dir is not an error.
	keys, err := LoadTrustedKeys(true)
	if err != nil {
		t.Fatalf("unexpected error with includeSystem=true: %v", err)
	}
	if len(keys) != 0 {
		t.Errorf("expected empty map, got %d entries", len(keys))
	}
}

// TestLoadKeysFromDir_SkipsInvalidPubFile exercises the warning-and-continue path in loadKeysFromDir.
func TestLoadKeysFromDir_SkipsInvalidPubFile(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "bad.pub"), []byte("not a pem block"), 0o600); err != nil {
		t.Fatalf("write bad.pub: %v", err)
	}

	keys := make(map[string]TrustedKey)
	found, err := loadKeysFromDir(dir, keys)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !found {
		t.Error("expected found=true for existing dir")
	}
	if len(keys) != 0 {
		t.Errorf("expected 0 keys after skipping invalid file, got %d", len(keys))
	}
}

// TestLoadKeyFromFile_NoPEMBlock covers the nil-block error path.
func TestLoadKeyFromFile_NoPEMBlock(t *testing.T) {
	f := filepath.Join(t.TempDir(), "noblock.pub")
	if err := os.WriteFile(f, []byte("not a pem block\n"), 0o600); err != nil {
		t.Fatalf("write: %v", err)
	}
	if _, err := loadKeyFromFile(f); err == nil {
		t.Fatal("expected error for file with no PEM block")
	}
}

// TestIsKeyTrusted_NoMatch returns false when the store exists but the fingerprint is absent.
func TestIsKeyTrusted_NoMatch(t *testing.T) {
	dir := t.TempDir()
	t.Setenv(EnvTrustedKeysDir, dir)

	// Write a key so the dir is non-empty (store "exists" in a meaningful way)
	_, pemBlock := generateTestKeyPEM(t)
	if err := os.WriteFile(filepath.Join(dir, "other-key.pub"), pemBlock, 0600); err != nil {
		t.Fatalf("failed to write key file: %v", err)
	}

	result, err := IsKeyTrusted("deadbeef000000000000000000000000deadbeef000000000000000000000000", false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil result (store exists)")
	}
	if *result {
		t.Error("expected false (key not in store), got true")
	}
}
