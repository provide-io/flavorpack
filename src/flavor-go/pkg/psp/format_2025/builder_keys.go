// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"crypto/ed25519"
	cryptorand "crypto/rand"
	"crypto/sha256"
	"fmt"
	"log/slog"
	"os"
)

// resolveSigningKeys produces the Ed25519 pair this build signs with, in
// descending order of preference: a key pair on disk, a deterministic pair
// derived from a seed, or a random ephemeral pair.
//
// Failures call buildExitFn rather than returning, matching the rest of the
// builder: a build that cannot sign does not produce a package.
func resolveSigningKeys(
	privateKeyPath string,
	publicKeyPath string,
	keySeed string,
	logger *slog.Logger,
) (ed25519.PublicKey, ed25519.PrivateKey) {
	switch {
	case privateKeyPath != "":
		logger.Debug("🔐 Loading keys from files", "private", privateKeyPath, "public", publicKeyPath)
		privateKey, publicKey, err := loadKeysFromFiles(privateKeyPath, publicKeyPath)
		if err != nil {
			logger.Error("❌ Failed to load keys", "error", err)
			buildExitFn(1)
		}
		logger.Info("🔑 Using provided keys")
		return publicKey, privateKey

	case keySeed != "":
		logger.Debug("🔐 Generating deterministic key pair from seed")

		actualSeed := keySeed
		if keySeed == "env" {
			actualSeed = os.Getenv(EnvKeySeed)
			if actualSeed == "" {
				logger.Error("❌ FLAVOR_KEY_SEED environment variable not set")
				buildExitFn(1)
			}
		}

		seed := sha256.Sum256([]byte(actualSeed))
		privateKey := ed25519.NewKeyFromSeed(seed[:])
		logger.Info("🔑 Using seed-based key generation", "seed_hash", fmt.Sprintf("%x", seed[:8]))
		return privateKey.Public().(ed25519.PublicKey), privateKey

	default:
		logger.Debug("🔐 Generating random ephemeral key pair")
		publicKey, privateKey, err := ed25519GenerateKeyFn(cryptorand.Reader)
		if err != nil {
			logger.Error("❌ Failed to generate ephemeral keys", "error", err)
			buildExitFn(1)
		}
		logger.Debug("🎲 Using random key generation")
		return publicKey, privateKey
	}
}

// recordSigningKeyInIndex stores the public key and its fingerprint, which is
// what a launcher checks the package's attestation against.
func recordSigningKeyInIndex(index *PSPFIndex, publicKey ed25519.PublicKey, logger *slog.Logger) {
	copy(index.PublicKey[:], publicKey[:32])

	fingerprint, err := ComputeKeyFingerprint(publicKey)
	if err != nil {
		logger.Error("❌ Failed to compute signing key fingerprint", "error", err)
		buildExitFn(1)
		return
	}
	copy(index.AttestationKeyFp[:], fingerprint)
}
