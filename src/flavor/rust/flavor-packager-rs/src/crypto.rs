//
// flavor/rust/flavor-packager-rs/src/crypto.rs
//
use anyhow::{Context, Result};
use p256::{
    ecdsa::{
        signature::{Signer, Verifier, hazmat::PrehashSigner},
        Signature, SigningKey, VerifyingKey,
    },
    pkcs8::{DecodePrivateKey, DecodePublicKey, EncodePrivateKey, EncodePublicKey},
    SecretKey,
};
use rand::rngs::OsRng;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

pub fn generate_key_pair() -> Result<(SigningKey, VerifyingKey)> {
    let secret_key = SecretKey::random(&mut OsRng);
    let signing_key = SigningKey::from(secret_key);
    let verifying_key = *signing_key.verifying_key();
    
    Ok((signing_key, verifying_key))
}

pub fn save_private_key<P: AsRef<Path>>(key: &SigningKey, path: P) -> Result<()> {
    let pem = key.to_pkcs8_pem(p256::pkcs8::LineEnding::LF)
        .context("Failed to encode private key as PEM")?;
    
    fs::write(&path, pem.as_bytes())
        .with_context(|| format!("Failed to write private key to {:?}", path.as_ref()))?;
    
    log::info!("Private key saved to: {:?}", path.as_ref());
    Ok(())
}

pub fn save_public_key<P: AsRef<Path>>(key: &VerifyingKey, path: P) -> Result<()> {
    let pem = key.to_public_key_pem(p256::pkcs8::LineEnding::LF)
        .context("Failed to encode public key as PEM")?;
    
    fs::write(&path, pem.as_bytes())
        .with_context(|| format!("Failed to write public key to {:?}", path.as_ref()))?;
    
    log::info!("Public key saved to: {:?}", path.as_ref());
    Ok(())
}

pub fn load_private_key<P: AsRef<Path>>(path: P) -> Result<SigningKey> {
    let pem_data = fs::read_to_string(&path)
        .with_context(|| format!("Failed to read private key from {:?}", path.as_ref()))?;
    
    SigningKey::from_pkcs8_pem(&pem_data)
        .with_context(|| format!("Failed to parse private key from {:?}", path.as_ref()))
}

pub fn load_public_key<P: AsRef<Path>>(path: P) -> Result<VerifyingKey> {
    let pem_data = fs::read_to_string(&path)
        .with_context(|| format!("Failed to read public key from {:?}", path.as_ref()))?;
    
    VerifyingKey::from_public_key_pem(&pem_data)
        .with_context(|| format!("Failed to parse public key from {:?}", path.as_ref()))
}

pub fn sign_data(signing_key: &SigningKey, data: &[u8]) -> Result<Vec<u8>> {
    // Hash the data first (ECDSA typically signs hashes, not raw data)
    let mut hasher = Sha256::new();
    hasher.update(data);
    let hash = hasher.finalize();
    
    // Sign the hash
    let signature: Signature = signing_key.sign(&hash);
    
    // Convert to DER format (ASN.1)
    Ok(signature.to_der().as_bytes().to_vec())
}

pub fn sign_hash(signing_key: &SigningKey, hash: &[u8]) -> Result<Vec<u8>> {
    // Sign the pre-computed hash directly (for compatibility with Go packager)
    // Use sign_prehash to avoid double hashing
    let signature: Signature = signing_key.sign_prehash(hash)
        .context("Failed to sign prehashed data")?;
    
    // Convert to DER format (ASN.1)
    Ok(signature.to_der().as_bytes().to_vec())
}

pub fn verify_signature(
    verifying_key: &VerifyingKey, 
    data: &[u8], 
    signature_bytes: &[u8]
) -> Result<bool> {
    // Hash the data
    let mut hasher = Sha256::new();
    hasher.update(data);
    let hash = hasher.finalize();
    
    // Parse signature from DER format
    let signature = Signature::from_der(signature_bytes)
        .context("Failed to parse signature")?;
    
    // Verify the signature
    match verifying_key.verify(&hash, &signature) {
        Ok(()) => Ok(true),
        Err(_) => Ok(false),
    }
}


// 📦🍜📄🪄
