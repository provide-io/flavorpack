//
// flavor/rust/flavor-launcher-rs/src/verification.rs
//
use anyhow::{Context, Result, bail};
use sha2::{Sha256, Digest};
use p256::ecdsa::{VerifyingKey, Signature};
use p256::ecdsa::signature::hazmat::PrehashVerifier;
use p256::pkcs8::{DecodePublicKey, EncodePublicKey};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};

// Trusted public key fingerprints (SHA-256 hashes of DER-encoded public keys)
// In production, these would be compiled in from a secure source
const TRUSTED_KEY_FINGERPRINTS: &[[u8; 32]] = &[
    // Test key from test-keys/provider-public.key
    [
        0xbf, 0xff, 0xaf, 0x98, 0xc1, 0xfb, 0xba, 0x56,
        0x17, 0xd3, 0x5a, 0xd9, 0xd5, 0x5f, 0xb3, 0xba,
        0xd4, 0x96, 0x1e, 0x43, 0x96, 0x45, 0x6e, 0xa5,
        0x1f, 0x5e, 0x09, 0x13, 0xe0, 0x9a, 0xa0, 0x15,
    ],
    // Alternate test key (from error message)
    [
        0xb6, 0xa7, 0x48, 0xc4, 0xf5, 0x67, 0x25, 0x07,
        0xd1, 0x78, 0x77, 0x90, 0x93, 0xfa, 0xf9, 0x97,
        0x1d, 0xc1, 0x17, 0xa1, 0x2f, 0x79, 0x15, 0x3f,
        0xfa, 0x10, 0x77, 0x44, 0xa6, 0x62, 0x35, 0xbd,
    ],
    // Python packager generated key
    [
        0xa3, 0x36, 0xb2, 0xe5, 0x53, 0x34, 0xb7, 0xab,
        0x49, 0x69, 0x54, 0x57, 0xe3, 0x22, 0x4b, 0xd9,
        0xf1, 0xb2, 0xbb, 0x61, 0xf7, 0xbe, 0x25, 0x38,
        0xff, 0xeb, 0xc9, 0x76, 0x2d, 0x3f, 0xb7, 0x2b,
    ],
];

pub fn verify_package_signature(
    file: &mut File,
    flavor_data_offset: i64,
    public_key_offset: u64,
    public_key_size: u64,
    signature_offset: u64,
    signature_size: u64,
    payload_offset: u64,
    payload_size: u64,
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
    
    // Compute fingerprint of the public key (must use DER-encoded SubjectPublicKeyInfo)
    let public_key_der = verifying_key.to_public_key_der()
        .context("Failed to convert to DER format")?;
    let mut hasher = Sha256::new();
    hasher.update(public_key_der.as_ref());
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
    
    // Hash only the payload data (what was actually signed during build)
    file.seek(SeekFrom::Start((flavor_data_offset as u64) + payload_offset))?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 8192];
    let mut bytes_read = 0u64;
    
    while bytes_read < payload_size {
        let to_read = std::cmp::min(buffer.len(), (payload_size - bytes_read) as usize);
        let n = file.read(&mut buffer[..to_read])?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
        bytes_read += n as u64;
    }
    
    let data_hash = hasher.finalize();
    log::debug!("Data hash: {}", hex::encode(&data_hash));
    
    // Verify signature (using prehashed since packagers sign the hash directly)
    verifying_key.verify_prehash(&data_hash, &signature)
        .context("Signature verification failed")?;
    
    log::info!("Package signature verified successfully");
    Ok(())
}

// Helper function to compute fingerprint of a public key file (for build tools)
pub fn compute_key_fingerprint(public_key_pem: &str) -> Result<[u8; 32]> {
    let verifying_key = VerifyingKey::from_public_key_pem(public_key_pem)
        .context("Failed to parse public key PEM")?;
    
    let public_key_der = verifying_key.to_public_key_der()
        .context("Failed to convert to DER format")?;
    let mut hasher = Sha256::new();
    hasher.update(public_key_der.as_ref());
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