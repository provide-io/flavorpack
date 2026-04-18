// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"errors"
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
	defer func() { _ = reader.Close() }()

	decompressed, err := io.ReadAll(reader)
	if err != nil {
		t.Fatalf("ReadAll() error = %v", err)
	}
	if !bytes.Contains(decompressed, []byte(`"name": "demo"`)) {
		t.Fatalf("unexpected metadata JSON %q", string(decompressed))
	}
}

func TestWriteMetadataReturnsWriterError(t *testing.T) {
	t.Parallel()

	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}

	metadata := &Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "demo", Version: "1.0.0"},
	}

	_, _, err = writeMetadata(errorWriter{}, metadata, privateKey, publicKey)
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("forced write failure")) {
		t.Fatalf("writeMetadata() error = %v, want forced write failure", err)
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

func TestLoadKeysFromFilesSupportsRawPEM(t *testing.T) {
	t.Parallel()

	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}

	dir := t.TempDir()
	privatePath := filepath.Join(dir, "private.pem")
	publicPath := filepath.Join(dir, "public.pem")

	if err := os.WriteFile(privatePath, pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privateKey}), 0o600); err != nil {
		t.Fatalf("WriteFile(private) error = %v", err)
	}
	if err := os.WriteFile(publicPath, pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: publicKey}), 0o600); err != nil {
		t.Fatalf("WriteFile(public) error = %v", err)
	}

	gotPrivate, gotPublic, err := loadKeysFromFiles(privatePath, publicPath)
	if err != nil {
		t.Fatalf("loadKeysFromFiles() error = %v", err)
	}
	if !bytes.Equal(gotPrivate, privateKey) {
		t.Fatalf("raw private key mismatch")
	}
	if !bytes.Equal(gotPublic, publicKey) {
		t.Fatalf("raw public key mismatch")
	}
}

func TestLoadKeysFromFilesRejectsMalformedPEM(t *testing.T) {
	t.Parallel()

	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}

	tests := []struct {
		name        string
		privatePEM  []byte
		publicPEM   []byte
		wantErrText string
	}{
		{
			name: "invalid private key",
			privatePEM: pem.EncodeToMemory(&pem.Block{
				Type:  "PRIVATE KEY",
				Bytes: []byte{0x01, 0x02, 0x03},
			}),
			wantErrText: "unable to parse private key",
		},
		{
			name: "invalid public key",
			publicPEM: pem.EncodeToMemory(&pem.Block{
				Type:  "PUBLIC KEY",
				Bytes: []byte{0x04, 0x05, 0x06},
			}),
			wantErrText: "unable to parse public key",
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			dir := t.TempDir()
			privatePath := filepath.Join(dir, "private.pem")
			publicPath := filepath.Join(dir, "public.pem")

			validPrivate := pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privateKey})
			validPublic := pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: publicKey})

			privateBytes := validPrivate
			if tt.privatePEM != nil {
				privateBytes = tt.privatePEM
			}
			publicBytes := validPublic
			if tt.publicPEM != nil {
				publicBytes = tt.publicPEM
			}

			if err := os.WriteFile(privatePath, privateBytes, 0o600); err != nil {
				t.Fatalf("WriteFile(private) error = %v", err)
			}
			if err := os.WriteFile(publicPath, publicBytes, 0o600); err != nil {
				t.Fatalf("WriteFile(public) error = %v", err)
			}

			_, _, err := loadKeysFromFiles(privatePath, publicPath)
			if err == nil || !bytes.Contains([]byte(err.Error()), []byte(tt.wantErrText)) {
				t.Fatalf("loadKeysFromFiles() error = %v, want substring %q", err, tt.wantErrText)
			}
		})
	}
}

func TestLoadKeysFromFilesReturnsReadErrors(t *testing.T) {
	t.Parallel()

	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}

	tests := []struct {
		name             string
		writePrivateKey  bool
		writePublicKey   bool
		wantErrSubstring string
	}{
		{name: "missing private key file", writePublicKey: true, wantErrSubstring: "failed to read private key"},
		{name: "missing public key file", writePrivateKey: true, wantErrSubstring: "failed to read public key"},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			dir := t.TempDir()
			privatePath := filepath.Join(dir, "private.pem")
			publicPath := filepath.Join(dir, "public.pem")

			if tt.writePrivateKey {
				privateDER, err := x509.MarshalPKCS8PrivateKey(privateKey)
				if err != nil {
					t.Fatalf("MarshalPKCS8PrivateKey() error = %v", err)
				}
				if err := os.WriteFile(privatePath, pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privateDER}), 0o600); err != nil {
					t.Fatalf("WriteFile(private) error = %v", err)
				}
			}
			if tt.writePublicKey {
				publicDER, err := x509.MarshalPKIXPublicKey(publicKey)
				if err != nil {
					t.Fatalf("MarshalPKIXPublicKey() error = %v", err)
				}
				if err := os.WriteFile(publicPath, pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: publicDER}), 0o600); err != nil {
					t.Fatalf("WriteFile(public) error = %v", err)
				}
			}

			_, _, err := loadKeysFromFiles(privatePath, publicPath)
			if err == nil || !bytes.Contains([]byte(err.Error()), []byte(tt.wantErrSubstring)) {
				t.Fatalf("loadKeysFromFiles() error = %v, want substring %q", err, tt.wantErrSubstring)
			}
		})
	}
}

type errorWriter struct{}

func (errorWriter) Write([]byte) (int, error) {
	return 0, errors.New("forced write failure")
}
