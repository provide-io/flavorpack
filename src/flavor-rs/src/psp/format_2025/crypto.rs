//! Cryptographic operations for PSPF/2025

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand::rngs::OsRng;

/// Generate an ephemeral Ed25519 key pair
pub fn generate_ephemeral_keypair() -> (SigningKey, VerifyingKey) {
    use rand::RngCore;
    let mut secret_key = [0u8; 32];
    OsRng.fill_bytes(&mut secret_key);
    let signing_key = SigningKey::from_bytes(&secret_key);
    let verifying_key = signing_key.verifying_key();
    (signing_key, verifying_key)
}

/// Sign data with a signing key
pub fn sign_data(data: &[u8], signing_key: &SigningKey) -> Vec<u8> {
    let signature = signing_key.sign(data);
    signature.to_bytes().to_vec()
}

/// Verify a signature
pub fn verify_signature(data: &[u8], signature: &[u8], verifying_key: &VerifyingKey) -> bool {
    if let Ok(sig) = Signature::from_slice(signature) {
        verifying_key.verify(data, &sig).is_ok()
    } else {
        false
    }
}
