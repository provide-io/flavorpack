//! Key management for PSPF/2025 packages

use crate::api::BuildOptions;
use crate::exceptions::{FlavorError, Result};
use ed25519_dalek::{SigningKey, VerifyingKey};
use log::{debug, info, warn};
use pem::parse;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

/// Load signing keys from PEM files or generate from seed
pub fn load_or_generate_keys(options: &BuildOptions) -> Result<(SigningKey, VerifyingKey)> {
    // Try key seed first
    if let Some(ref seed) = options.key_seed {
        info!("🔑 Using seed-based key generation");
        let (signing_key, verifying_key) = generate_keys_from_seed(seed);
        return Ok((signing_key, verifying_key));
    }

    // Try loading from files
    if let Some(ref private_path) = options.private_key_path {
        let public_path = options.public_key_path.as_ref().ok_or_else(|| {
            FlavorError::BuildError(
                "Public key path required when private key provided".to_string(),
            )
        })?;

        info!("🔑 Loading keys from files");
        return load_keys_from_files(private_path, public_path);
    }

    // Generate ephemeral keys
    warn!("⚠️ No keys provided, generating ephemeral keys (not recommended for production)");
    use rand::RngCore;
    use rand::rngs::OsRng;
    let mut secret_key = [0u8; 32];
    OsRng.fill_bytes(&mut secret_key);
    let signing_key = SigningKey::from_bytes(&secret_key);
    let verifying_key = signing_key.verifying_key();
    Ok((signing_key, verifying_key))
}

/// Load signing keys from PEM files
fn load_keys_from_files(
    private_key_path: &Path,
    public_key_path: &Path,
) -> Result<(SigningKey, VerifyingKey)> {
    // Load and parse private key
    let private_pem = fs::read_to_string(private_key_path)
        .map_err(|e| FlavorError::BuildError(format!("Failed to read private key: {}", e)))?;

    let private_parsed = parse(&private_pem)
        .map_err(|e| FlavorError::BuildError(format!("Failed to parse private key PEM: {}", e)))?;

    // Extract the key bytes - handle both PKCS#8 and raw Ed25519 formats
    let private_bytes = if private_parsed.tag() == "PRIVATE KEY" {
        // PKCS#8 format - skip the header
        let contents = private_parsed.contents();
        if contents.len() >= 34 && contents[0..2] == [0x30, 0x2e] {
            // Standard PKCS#8 Ed25519 key
            &contents[16..48]
        } else if contents.len() == 32 {
            // Raw 32-byte key
            contents
        } else {
            return Err(FlavorError::BuildError(
                "Invalid private key format".to_string(),
            ));
        }
    } else if private_parsed.tag() == "ED25519 PRIVATE KEY" {
        // Raw Ed25519 key
        private_parsed.contents()
    } else {
        return Err(FlavorError::BuildError(format!(
            "Unsupported private key type: {}",
            private_parsed.tag()
        )));
    };

    // Create signing key from bytes
    let signing_key = SigningKey::from_bytes(
        private_bytes
            .try_into()
            .map_err(|_| FlavorError::BuildError("Invalid private key length".to_string()))?,
    );

    // Load and parse public key
    let public_pem = fs::read_to_string(public_key_path)
        .map_err(|e| FlavorError::BuildError(format!("Failed to read public key: {}", e)))?;

    let public_parsed = parse(&public_pem)
        .map_err(|e| FlavorError::BuildError(format!("Failed to parse public key PEM: {}", e)))?;

    // Extract the key bytes - handle both PKCS#8 and raw Ed25519 formats
    let public_bytes = if public_parsed.tag() == "PUBLIC KEY" {
        // PKCS#8 format - skip the header
        let contents = public_parsed.contents();
        if contents.len() >= 44 && contents[0..2] == [0x30, 0x2a] {
            // Standard PKCS#8 Ed25519 public key
            &contents[12..44]
        } else if contents.len() == 32 {
            // Raw 32-byte key
            contents
        } else {
            return Err(FlavorError::BuildError(
                "Invalid public key format".to_string(),
            ));
        }
    } else if public_parsed.tag() == "ED25519 PUBLIC KEY" {
        // Raw Ed25519 key
        public_parsed.contents()
    } else {
        return Err(FlavorError::BuildError(format!(
            "Unsupported public key type: {}",
            public_parsed.tag()
        )));
    };

    // Create verifying key from bytes
    let verifying_key = VerifyingKey::from_bytes(
        public_bytes
            .try_into()
            .map_err(|_| FlavorError::BuildError("Invalid public key length".to_string()))?,
    )
    .map_err(|e| FlavorError::BuildError(format!("Invalid public key: {}", e)))?;

    debug!("✅ Loaded keys from files");
    Ok((signing_key, verifying_key))
}

/// Generate deterministic keys from a seed string
pub fn generate_keys_from_seed(seed: &str) -> (SigningKey, VerifyingKey) {
    // Hash the seed to get 32 bytes
    let mut hasher = Sha256::new();
    hasher.update(seed.as_bytes());
    let seed_hash = hasher.finalize();
    let seed_bytes: [u8; 32] = seed_hash.into();

    // Create signing key from seed bytes
    let signing_key = SigningKey::from_bytes(&seed_bytes);
    let verifying_key = signing_key.verifying_key();

    // Log seed hash for debugging (not the actual seed)
    let mut seed_hasher = Sha256::new();
    seed_hasher.update(seed_bytes);
    let seed_hash = seed_hasher.finalize();
    info!(
        "🔑 Using seed-based key generation: seed_hash={:x}",
        &seed_hash[0..8]
            .iter()
            .fold(0u64, |acc, &b| (acc << 8) | b as u64)
    );

    (signing_key, verifying_key)
}
