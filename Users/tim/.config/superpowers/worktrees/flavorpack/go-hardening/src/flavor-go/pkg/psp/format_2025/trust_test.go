package format_2025

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"os"
	"path/filepath"
	"testing"
)

func TestLoadKeyFromFileAndTrustedKeyLookup(t *testing.T) {
	publicKey, _, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}

	publicDER, err := x509.MarshalPKIXPublicKey(publicKey)
	if err != nil {
		t.Fatalf("MarshalPKIXPublicKey() error = %v", err)
	}

	dir := t.TempDir()
	path := filepath.Join(dir, "demo.pub")
	content := []byte("# Name: Demo Key\n" + string(pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: publicDER})))
	if err := os.WriteFile(path, content, 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	key, err := loadKeyFromFile(path)
	if err != nil {
		t.Fatalf("loadKeyFromFile() error = %v", err)
	}
	wantFP, err := ComputeKeyFingerprint(publicKey)
	if err != nil {
		t.Fatalf("ComputeKeyFingerprint() error = %v", err)
	}
	if key.Fingerprint != wantFP {
		t.Fatalf("fingerprint mismatch: got %q want %q", key.Fingerprint, wantFP)
	}
	if key.Name != "Demo Key" {
		t.Fatalf("expected name to round-trip, got %q", key.Name)
	}

	t.Setenv(EnvTrustedKeysDir, dir)
	keys, err := LoadTrustedKeys(false)
	if err != nil {
		t.Fatalf("LoadTrustedKeys() error = %v", err)
	}
	if _, ok := keys[wantFP]; !ok {
		t.Fatalf("expected fingerprint %q in trusted store", wantFP)
	}

	trusted, err := IsKeyTrusted(wantFP, false)
	if err != nil {
		t.Fatalf("IsKeyTrusted() error = %v", err)
	}
	if trusted == nil || !*trusted {
		t.Fatalf("expected key to be trusted, got %#v", trusted)
	}
}

func TestLoadKeyFromFileErrors(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	path := filepath.Join(dir, "broken.pub")
	if err := os.WriteFile(path, []byte("broken"), 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	if _, err := loadKeyFromFile(path); err == nil {
		t.Fatal("expected error for invalid trusted key file")
	}
}

func TestIsKeyTrustedWithoutStore(t *testing.T) {
	t.Setenv(EnvTrustedKeysDir, "")
	trusted, err := IsKeyTrusted("missing", true)
	if err != nil {
		t.Fatalf("IsKeyTrusted() error = %v", err)
	}
	if trusted != nil {
		t.Fatalf("expected nil trust result when store is absent, got %#v", trusted)
	}
}
