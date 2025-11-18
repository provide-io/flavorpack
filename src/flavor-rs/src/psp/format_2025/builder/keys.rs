//! Key management for PSPF package building

use crate::exceptions::{FlavorError, Result};
use ed25519_dalek::{SigningKey, VerifyingKey};
use log::{debug, info};
use pem::parse;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::Read;
use std::path::Path;

/// Load Ed25519 keys from PEM files
pub fn load_keys_from_files(
    private_key_path: &Path,
    public_key_path: Option<&Path>,
) -> Result<(SigningKey, VerifyingKey)> {
    // Load private key
    let mut private_key_data = Vec::new();
    File::open(private_key_path)?.read_to_end(&mut private_key_data)?;

    let pem = parse(&private_key_data)
        .map_err(|e| FlavorError::Generic(format!("Failed to parse private key PEM: {e}")))?;

    // Try to parse as raw Ed25519 (32 bytes) or PKCS8
    let signing_key = if pem.contents().len() == 32 {
        let key_array: [u8; 32] = pem.contents().try_into().map_err(|_| {
            FlavorError::Generic("Private key must be exactly 32 bytes".to_string())
        })?;
        SigningKey::from_bytes(&key_array)
    } else {
        // Try PKCS8 format
        let key_bytes = if pem.contents().len() > 32 {
            // Assume PKCS8 and extract the actual key bytes (last 32 bytes typically)
            &pem.contents()[pem.contents().len() - 32..]
        } else {
            return Err(FlavorError::Generic("Invalid private key size".to_string()));
        };
        SigningKey::from_bytes(
            key_bytes
                .try_into()
                .map_err(|_| FlavorError::Generic("Invalid key size".to_string()))?,
        )
    };

    // Get or derive public key
    let verifying_key = if let Some(public_path) = public_key_path {
        // Load public key from file
        let mut public_key_data = Vec::new();
        File::open(public_path)?.read_to_end(&mut public_key_data)?;

        let pem = parse(&public_key_data)
            .map_err(|e| FlavorError::Generic(format!("Failed to parse public key PEM: {e}")))?;

        let key_array: [u8; 32] = pem.contents().try_into().map_err(|_| {
            FlavorError::Generic("Public key must be exactly 32 bytes".to_string())
        })?;
        VerifyingKey::from_bytes(&key_array)
            .map_err(|e| FlavorError::Generic(format!("Invalid public key: {e}")))?
    } else {
        // Derive from private key
        signing_key.verifying_key()
    };

    Ok((signing_key, verifying_key))
}

/// Generate deterministic Ed25519 keys from a seed string
pub fn generate_keys_from_seed(seed: &str) -> Result<(SigningKey, VerifyingKey)> {
    info!("🔑 Using seed-based key generation");

    // Hash the seed to get 32 bytes
    let mut hasher = Sha256::new();
    hasher.update(seed.as_bytes());
    let seed_hash = hasher.finalize();

    // Create signing key from seed
    let signing_key = SigningKey::from_bytes(&seed_hash.into());
    let verifying_key = signing_key.verifying_key();

    // Log the key fingerprint for debugging (first 8 bytes of public key hex)
    let pub_hex = hex::encode(verifying_key.as_bytes());
    debug!("Generated key with fingerprint: {}", &pub_hex[..16]);

    Ok((signing_key, verifying_key))
}