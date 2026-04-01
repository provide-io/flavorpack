package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"io"
	"os"
	"path/filepath"
	"testing"
)

func TestWriteMetadata(t *testing.T) {
	t.Parallel()

	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}

	metadata := &Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
		Slots:         []SlotMetadata{},
	}

	var buf bytes.Buffer
	n, signature, err := writeMetadata(&buf, metadata, privateKey, publicKey)
	if err != nil {
		t.Fatalf("writeMetadata() error = %v", err)
	}
	if n == 0 {
		t.Fatal("expected compressed metadata to be written")
	}
	if len(signature) != ed25519.SignatureSize {
		t.Fatalf("unexpected signature size %d", len(signature))
	}

	reader, err := gzip.NewReader(bytes.NewReader(buf.Bytes()))
	if err != nil {
		t.Fatalf("gzip.NewReader() error = %v", err)
	}
	defer reader.Close()

	decompressed, err := io.ReadAll(reader)
	if err != nil {
		t.Fatalf("ReadAll() error = %v", err)
	}
	if !bytes.Contains(decompressed, []byte(`"name": "demo"`)) {
		t.Fatalf("unexpected metadata JSON %q", string(decompressed))
	}
}

func TestLoadKeysFromFiles(t *testing.T) {
	t.Parallel()

	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}

	privateDER, err := x509.MarshalPKCS8PrivateKey(privateKey)
	if err != nil {
		t.Fatalf("MarshalPKCS8PrivateKey() error = %v", err)
	}
	publicDER, err := x509.MarshalPKIXPublicKey(publicKey)
	if err != nil {
		t.Fatalf("MarshalPKIXPublicKey() error = %v", err)
	}

	dir := t.TempDir()
	privatePath := filepath.Join(dir, "private.pem")
	publicPath := filepath.Join(dir, "public.pem")

	if err := os.WriteFile(privatePath, pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privateDER}), 0o600); err != nil {
		t.Fatalf("WriteFile(private) error = %v", err)
	}
	if err := os.WriteFile(publicPath, pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: publicDER}), 0o600); err != nil {
		t.Fatalf("WriteFile(public) error = %v", err)
	}

	gotPrivate, gotPublic, err := loadKeysFromFiles(privatePath, publicPath)
	if err != nil {
		t.Fatalf("loadKeysFromFiles() error = %v", err)
	}
	if !bytes.Equal(gotPrivate, privateKey) {
		t.Fatalf("private key mismatch")
	}
	if !bytes.Equal(gotPublic, publicKey) {
		t.Fatalf("public key mismatch")
	}

	derivedPrivate, derivedPublic, err := loadKeysFromFiles(privatePath, "")
	if err != nil {
		t.Fatalf("loadKeysFromFiles() derived error = %v", err)
	}
	if !bytes.Equal(derivedPrivate, privateKey) {
		t.Fatalf("derived private key mismatch")
	}
	if !bytes.Equal(derivedPublic, publicKey) {
		t.Fatalf("derived public key mismatch")
	}
}

func TestLoadKeysFromFilesErrors(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	privatePath := filepath.Join(dir, "private.pem")
	publicPath := filepath.Join(dir, "public.pem")

	if err := os.WriteFile(privatePath, []byte("not a key"), 0o600); err != nil {
		t.Fatalf("WriteFile(private) error = %v", err)
	}

	if _, _, err := loadKeysFromFiles(privatePath, publicPath); err == nil {
		t.Fatal("expected error for missing public key and invalid private key")
	}
}
