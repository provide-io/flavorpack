//! Cryptographic operations for PSPF/2025

use crate::exceptions::{FlavorError, Result};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand::TryRng;
use rand::rngs::SysRng;

/// Generate an ephemeral Ed25519 key pair
///
/// # Errors
///
/// Returns an error when the system entropy source cannot be read. rand 0.10
/// renamed `OsRng` to `SysRng` and made that read fallible, so the failure is
/// reported rather than swallowed -- a key built from entropy that was never
/// delivered is worse than no key at all.
pub fn generate_ephemeral_keypair() -> Result<(SigningKey, VerifyingKey)> {
    let mut secret_key = [0u8; 32];
    SysRng
        .try_fill_bytes(&mut secret_key)
        .map_err(|e| FlavorError::Generic(format!("Failed to read system entropy: {e}")))?;
    let signing_key = SigningKey::from_bytes(&secret_key);
    let verifying_key = signing_key.verifying_key();
    Ok((signing_key, verifying_key))
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

#[cfg(test)]
mod tests {
    use super::{generate_ephemeral_keypair, sign_data, verify_signature};

    #[test]
    fn test_sign_and_verify_roundtrip() {
        let (signing_key, verifying_key) = generate_ephemeral_keypair().expect("keypair");
        let data = b"signed payload";

        let signature = sign_data(data, &signing_key);

        assert!(verify_signature(data, &signature, &verifying_key));
        assert!(!verify_signature(
            b"tampered payload",
            &signature,
            &verifying_key
        ));
    }

    #[test]
    fn test_verify_signature_rejects_invalid_length() {
        let (_, verifying_key) = generate_ephemeral_keypair().expect("keypair");
        assert!(!verify_signature(b"payload", &[1, 2, 3], &verifying_key));
    }
}
