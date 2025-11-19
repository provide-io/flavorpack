package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"os"
)

func writeMetadata(w io.Writer, metadata *Metadata, privateKey, publicKey []byte) (int, []byte, error) {
	// Create JSON metadata
	metadataJSON, err := json.MarshalIndent(metadata, "", "  ")
	if err != nil {
		return 0, nil, err
	}

	// Sign the uncompressed JSON with Ed25519
	signature := ed25519.Sign(privateKey, metadataJSON)

	// Compress the JSON with gzip
	var buf bytes.Buffer
	gw := gzip.NewWriter(&buf)
	if _, err := gw.Write(metadataJSON); err != nil {
		return 0, nil, err
	}
	if err := gw.Close(); err != nil {
		return 0, nil, fmt.Errorf("failed to close gzip writer: %w", err)
	}

	// Write compressed metadata
	n, err := w.Write(buf.Bytes())
	return n, signature, err
}

// loadKeysFromFiles loads Ed25519 keys from PEM files
func loadKeysFromFiles(privateKeyPath, publicKeyPath string) (ed25519.PrivateKey, ed25519.PublicKey, error) {
	// Load private key
	privateKeyData, err := os.ReadFile(privateKeyPath)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to read private key: %w", err)
	}

	block, _ := pem.Decode(privateKeyData)
	if block == nil {
		return nil, nil, fmt.Errorf("failed to decode private key PEM")
	}

	var privateKey ed25519.PrivateKey

	// Try to parse as PKCS8 first (standard format)
	if key, err := x509.ParsePKCS8PrivateKey(block.Bytes); err == nil {
		var ok bool
		privateKey, ok = key.(ed25519.PrivateKey)
		if !ok {
			return nil, nil, fmt.Errorf("private key is not Ed25519")
		}
	} else if len(block.Bytes) == ed25519.PrivateKeySize {
		// Try raw Ed25519 format
		privateKey = ed25519.PrivateKey(block.Bytes)
	} else {
		return nil, nil, fmt.Errorf("unable to parse private key: %w", err)
	}

	// Derive or load public key
	var publicKey ed25519.PublicKey
	if publicKeyPath != "" {
		// Load public key from file
		publicKeyData, err := os.ReadFile(publicKeyPath)
		if err != nil {
			return nil, nil, fmt.Errorf("failed to read public key: %w", err)
		}

		block, _ := pem.Decode(publicKeyData)
		if block == nil {
			return nil, nil, fmt.Errorf("failed to decode public key PEM")
		}

		// Try to parse as PKIX first
		if key, err := x509.ParsePKIXPublicKey(block.Bytes); err == nil {
			var ok bool
			publicKey, ok = key.(ed25519.PublicKey)
			if !ok {
				return nil, nil, fmt.Errorf("public key is not Ed25519")
			}
		} else if len(block.Bytes) == ed25519.PublicKeySize {
			// Try raw Ed25519 format
			publicKey = ed25519.PublicKey(block.Bytes)
		} else {
			return nil, nil, fmt.Errorf("unable to parse public key: %w", err)
		}
	} else {
		// Derive public key from private key
		publicKey = privateKey.Public().(ed25519.PublicKey)
	}

	return privateKey, publicKey, nil
}

func generateEmojiMagic(launcherType string) []byte {
	// Package and magic wand emojis (8 bytes total per PSPF/2025 spec)
	// Using byte representation to avoid having literal emoji in binary
	// 📦 = 0xF0 0x9F 0x93 0xA6 (UTF-8)
	// 🪄 = 0xF0 0x9F 0xAA 0x84 (UTF-8)
	return []byte{0xF0, 0x9F, 0x93, 0xA6, 0xF0, 0x9F, 0xAA, 0x84}
}
