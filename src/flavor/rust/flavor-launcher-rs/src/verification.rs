//
// flavor/rust/flavor-launcher-rs/src/verification.rs
//
use anyhow::{Context, Result, bail};
use sha2::{Sha256, Digest};
use p256::ecdsa::{VerifyingKey, Signature};
use p256::ecdsa::signature::Verifier;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};

// Trusted public key fingerprints (SHA-256 hashes of DER-encoded public keys)
// In production, these would be compiled in from a secure source
const TRUSTED_KEY_FINGERPRINTS: &[[u8; 32]] = &[
    // Add trusted fingerprints here during build process
    // For testing, we'll accept a well-known test key
    [
        0x2e, 0x6a, 0xb3, 0x35, 0x72, 0x8b, 0x83, 0x9e,
        0x8f, 0x5a, 0x4e, 0x12, 0x3c, 0x58, 0x73, 0x88,
        0x7c, 0x6a, 0xac, 0xb5, 0x35, 0x5b, 0x84, 0x92,
        0x58, 0x5c, 0xb3, 0x98, 0xe2, 0x80, 0xd3, 0x40
    ],
];

pub fn verify_package_signature(
    file: &mut File,
    flavor_data_offset: i64,
    public_key_offset: u64,
    public_key_size: u64,
    signature_offset: u64,
    signature_size: u64,
    max_data_end: u64,
) -> Result<()> {
    // Read public key
    file.seek(SeekFrom::Start((flavor_data_offset as u64) + public_key_offset))?;
    let mut public_key_pem = vec![0u8; public_key_size as usize];
    file.read_exact(&mut public_key_pem)?;
    
    // Parse public key
    let public_key_str = std::str::from_utf8(&public_key_pem)
        .context("Invalid UTF-8 in public key")?;
    let verifying_key = VerifyingKey::from_public_key_pem(public_key_str)
        .context("Failed to parse public key PEM")?;
    
    // Compute fingerprint of the public key
    let public_key_der = verifying_key.to_encoded_point(false);
    let mut hasher = Sha256::new();
    hasher.update(public_key_der.as_bytes());
    let fingerprint = hasher.finalize();
    
    // Check if this key is trusted
    let mut trusted = false;
    for trusted_fp in TRUSTED_KEY_FINGERPRINTS {
        if &fingerprint[..] == trusted_fp {
            trusted = true;
            break;
        }
    }
    
    // For development/testing, also check for empty fingerprint list or env var
    if TRUSTED_KEY_FINGERPRINTS.is_empty() || std::env::var("FLAVOR_SKIP_KEY_VERIFICATION").is_ok() {
        log::warn!("Key fingerprint verification disabled - accepting any key");
        trusted = true;
    }
    
    if !trusted {
        log::error!("Untrusted public key fingerprint: {}", hex::encode(&fingerprint));
        bail!("Package signed with untrusted key");
    }
    
    log::info!("Public key fingerprint verified: {}", hex::encode(&fingerprint));
    
    // Read signature
    file.seek(SeekFrom::Start((flavor_data_offset as u64) + signature_offset))?;
    let mut signature_bytes = vec![0u8; signature_size as usize];
    file.read_exact(&mut signature_bytes)?;
    
    let signature = Signature::from_der(&signature_bytes)
        .context("Failed to parse ECDSA signature")?;
    
    // Compute hash of all data up to (but not including) the signature
    file.seek(SeekFrom::Start(flavor_data_offset as u64))?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 8192];
    let mut bytes_read = 0u64;
    
    while bytes_read < max_data_end {
        let to_read = std::cmp::min(buffer.len(), (max_data_end - bytes_read) as usize);
        let n = file.read(&mut buffer[..to_read])?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
        bytes_read += n as u64;
    }
    
    let data_hash = hasher.finalize();
    log::debug!("Data hash: {}", hex::encode(&data_hash));
    
    // Verify signature
    verifying_key.verify(&data_hash, &signature)
        .context("Signature verification failed")?;
    
    log::info!("Package signature verified successfully");
    Ok(())
}

// Helper function to compute fingerprint of a public key file (for build tools)
pub fn compute_key_fingerprint(public_key_pem: &str) -> Result<[u8; 32]> {
    let verifying_key = VerifyingKey::from_public_key_pem(public_key_pem)
        .context("Failed to parse public key PEM")?;
    
    let public_key_der = verifying_key.to_encoded_point(false);
    let mut hasher = Sha256::new();
    hasher.update(public_key_der.as_bytes());
    let fingerprint = hasher.finalize();
    
    Ok(fingerprint.into())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_compute_fingerprint() {
        // Test with a sample public key
        let test_key = r#"-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE7Z8l0KQmBsNr7Pm1XqxqPE8F4Ohe
SQou2h7hEq0gp4x8tW2MXLmfpL0G7Xb3PJV4roM8z3cVDdx2jK1hT3XZEQ==
-----END PUBLIC KEY-----"#;
        
        let fingerprint = compute_key_fingerprint(test_key).unwrap();
        println!("Test key fingerprint: {}", hex::encode(&fingerprint));
        assert_eq!(fingerprint.len(), 32);
    }
}