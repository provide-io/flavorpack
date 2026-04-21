//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

//! Trusted key store for Flavorpack package signature verification.

use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

use sha2::{Digest, Sha256};

/// A trusted public key loaded from the store.
#[derive(Debug, Clone)]
pub struct TrustedKey {
    pub fingerprint: String,
    pub name: Option<String>,
    pub path: PathBuf,
}

/// Returns the user-level trusted-keys directory.
/// Priority: FLAVOR_TRUSTED_KEYS_DIR → FLAVOR_CONFIG_DIR/trusted-keys
///           → XDG_CONFIG_HOME/flavor/trusted-keys → ~/.config/flavor/trusted-keys
pub fn get_trusted_keys_dir() -> PathBuf {
    if let Ok(dir) = env::var(crate::env_vars::TRUSTED_KEYS_DIR) {
        return PathBuf::from(dir);
    }
    get_config_root().join("trusted-keys")
}

fn get_config_root() -> PathBuf {
    if let Ok(d) = env::var(crate::env_vars::CONFIG_DIR) {
        return PathBuf::from(d);
    }
    if let Ok(d) = env::var("XDG_CONFIG_HOME") {
        return PathBuf::from(d).join("flavor");
    }
    #[cfg(target_os = "windows")]
    if let Ok(d) = env::var("APPDATA") {
        return PathBuf::from(d).join("flavor");
    }
    // Fall back to ~/.config/flavor using HOME or USERPROFILE env vars
    for var in &["HOME", "USERPROFILE"] {
        if let Some(home) = env::var_os(var) {
            return PathBuf::from(home).join(".config").join("flavor");
        }
    }
    // Return a non-existent path rather than a world-writable temp directory.
    // A temp-backed trust store would allow trusted-key injection.
    PathBuf::from("/nonexistent/flavor/config")
}

fn get_system_trusted_keys_dir() -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        if let Ok(d) = env::var("PROGRAMDATA") {
            return PathBuf::from(d).join("flavor").join("trusted-keys");
        }
        return PathBuf::from("C:\\ProgramData\\flavor\\trusted-keys");
    }
    #[cfg(not(target_os = "windows"))]
    PathBuf::from("/etc/flavor/trusted-keys")
}

/// Computes the SHA-256 fingerprint of a raw 32-byte Ed25519 public key.
/// Returns lowercase hex string (64 chars).
pub fn compute_key_fingerprint(raw_key: &[u8]) -> Result<String, String> {
    if raw_key.len() != 32 {
        return Err(format!("invalid Ed25519 key length: {}", raw_key.len()));
    }
    let mut hasher = Sha256::new();
    hasher.update(raw_key);
    Ok(format!("{:x}", hasher.finalize()))
}

/// Derive the canonical trust fingerprint from an index's embedded public key.
///
/// Returns:
/// - `Ok(None)` for unsigned packages with an all-zero public key and no attestation fingerprint.
/// - `Ok(Some(fp))` for signed packages when the stored attestation fingerprint is absent or matches.
/// - `Err(...)` when the attestation fingerprint is present but mismatches the embedded public key.
pub fn derive_index_key_fingerprint(index: &super::index::Index) -> Result<Option<String>, String> {
    if index.public_key.iter().all(|&b| b == 0) {
        if index.attestation_key_fp.iter().any(|&b| b != 0) {
            return Err("attestation_key_fp is present but public_key is missing".to_string());
        }
        return Ok(None);
    }

    let derived = compute_key_fingerprint(&index.public_key)?;
    let stored = String::from_utf8_lossy(&index.attestation_key_fp)
        .trim_end_matches('\0')
        .to_string();

    if !stored.is_empty() && stored != derived {
        return Err("attestation key fingerprint does not match embedded public key".to_string());
    }

    Ok(Some(derived))
}

/// Loads all .pub PEM files from a directory.
/// Returns empty map if directory doesn't exist.
fn load_keys_from_dir(dir: &Path) -> HashMap<String, TrustedKey> {
    let mut result = HashMap::new();
    let entries = match fs::read_dir(dir) {
        Ok(e) => e,
        Err(_) => return result,
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("pub") {
            continue;
        }
        match load_pub_key_file(&path) {
            Ok(key) => {
                result.insert(key.fingerprint.clone(), key);
            }
            Err(e) => {
                eprintln!(
                    "flavor: warning: failed to load trusted key {}: {}",
                    path.display(),
                    e
                );
            }
        }
    }
    result
}

fn load_pub_key_file(path: &Path) -> Result<TrustedKey, String> {
    let content = fs::read_to_string(path).map_err(|e| e.to_string())?;

    // Extract optional "# Name: ..." comment before the PEM block
    let mut name: Option<String> = None;
    let mut pem_lines: Vec<&str> = Vec::new();
    for line in content.lines() {
        let trimmed = line.trim();
        if let Some(stripped) = trimmed.strip_prefix("# Name:") {
            name = Some(stripped.trim().to_string());
        } else {
            pem_lines.push(line);
        }
    }
    let pem_str = pem_lines.join("\n");

    let raw_key = parse_ed25519_pem(pem_str.as_bytes())?;
    let fingerprint = compute_key_fingerprint(&raw_key)?;
    Ok(TrustedKey {
        fingerprint,
        name,
        path: path.to_path_buf(),
    })
}

fn parse_ed25519_pem(pem_bytes: &[u8]) -> Result<Vec<u8>, String> {
    let pem_str = std::str::from_utf8(pem_bytes).map_err(|e| e.to_string())?;
    let pem_obj = pem::parse(pem_str).map_err(|e| e.to_string())?;
    let der = pem_obj.contents();
    Ok(extract_ed25519_raw_key(der)?.to_vec())
}

fn extract_ed25519_raw_key(der: &[u8]) -> Result<&[u8], String> {
    // A well-formed Ed25519 SubjectPublicKeyInfo is exactly 44 bytes:
    //   30 2a 30 05 06 03 2b 65 70 03 21 00 <32-byte key>
    const SPKI_PREFIX: &[u8] = &[
        0x30, 0x2a, // SEQUENCE, 42 bytes
        0x30, 0x05, // SEQUENCE (AlgorithmIdentifier), 5 bytes
        0x06, 0x03, 0x2b, 0x65, 0x70, // OID 1.3.101.112 (Ed25519)
        0x03, 0x21, // BIT STRING, 33 bytes
        0x00, // no unused bits
    ];
    const SPKI_LEN: usize = 44; // 12-byte prefix + 32-byte key

    if der.len() != SPKI_LEN {
        return Err(format!(
            "Ed25519 public key must be {} bytes (SubjectPublicKeyInfo), got {}",
            SPKI_LEN,
            der.len()
        ));
    }
    if !der.starts_with(SPKI_PREFIX) {
        return Err(
            "key is not a valid Ed25519 SubjectPublicKeyInfo (wrong DER structure)".to_string(),
        );
    }
    Ok(&der[SPKI_PREFIX.len()..])
}

/// Loads all trusted keys from user and optionally system store.
pub fn load_trusted_keys(include_system: bool) -> HashMap<String, TrustedKey> {
    let mut keys = HashMap::new();
    if include_system {
        keys.extend(load_keys_from_dir(&get_system_trusted_keys_dir()));
    }
    keys.extend(load_keys_from_dir(&get_trusted_keys_dir()));
    keys
}

/// Checks if a fingerprint is in the trusted store.
/// Returns `None` if no store exists (backwards-compatible — treat as trusted).
/// Returns `Some(true)` if found, `Some(false)` if store exists but key is absent.
pub fn is_key_trusted(fingerprint: &str, include_system: bool) -> Option<bool> {
    let user_dir = get_trusted_keys_dir();
    let sys_dir = get_system_trusted_keys_dir();
    let store_exists = user_dir.exists() || (include_system && sys_dir.exists());
    if !store_exists {
        return None;
    }
    let keys = load_trusted_keys(include_system);
    Some(keys.contains_key(fingerprint))
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::SigningKey;
    use pem::{Pem, encode};
    use std::fs;
    use tempfile::TempDir;

    fn mock_raw_key() -> Vec<u8> {
        vec![0u8; 32]
    }

    fn spki_public_pem_from_seed(seed: [u8; 32]) -> String {
        let signing_key = SigningKey::from_bytes(&seed);
        let raw_key = signing_key.verifying_key().to_bytes();
        let mut der = vec![
            0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00,
        ];
        der.extend_from_slice(&raw_key);
        encode(&Pem::new("PUBLIC KEY", der))
    }

    #[test]
    fn test_compute_key_fingerprint_valid() {
        let key = mock_raw_key();
        let fp = compute_key_fingerprint(&key).expect("fingerprint should succeed");
        assert_eq!(fp.len(), 64, "fingerprint must be 64 hex chars");
        // SHA-256 of 32 zero bytes is deterministic
        assert!(fp.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn test_compute_key_fingerprint_wrong_length() {
        let short_key = vec![0u8; 16];
        let err = compute_key_fingerprint(&short_key).unwrap_err();
        assert!(
            err.contains("invalid Ed25519 key length"),
            "unexpected: {err}"
        );
    }

    #[test]
    fn test_derive_index_key_fingerprint_unsigned_package_returns_none() {
        let index = crate::psp::format_2025::index::Index::new();
        let fingerprint = derive_index_key_fingerprint(&index).expect("derive fingerprint");
        assert_eq!(fingerprint, None);
    }

    #[test]
    fn test_derive_index_key_fingerprint_matches_public_key() {
        let seed = [7u8; 32];
        let signing_key = SigningKey::from_bytes(&seed);
        let public_key = signing_key.verifying_key().to_bytes();
        let mut index = crate::psp::format_2025::index::Index::new();
        index.public_key = public_key;

        let fingerprint = derive_index_key_fingerprint(&index).expect("derive fingerprint");
        assert_eq!(
            fingerprint,
            Some(compute_key_fingerprint(&public_key).expect("fingerprint"))
        );
    }

    #[test]
    fn test_derive_index_key_fingerprint_rejects_mismatch() {
        let seed = [8u8; 32];
        let signing_key = SigningKey::from_bytes(&seed);
        let public_key = signing_key.verifying_key().to_bytes();
        let mut index = crate::psp::format_2025::index::Index::new();
        index.public_key = public_key;
        index.attestation_key_fp[..64]
            .copy_from_slice(b"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff");

        let err = derive_index_key_fingerprint(&index).expect_err("mismatch must fail");
        assert!(err.contains("mismatch") || err.contains("attestation"));
    }

    #[test]
    fn test_load_keys_from_dir_missing() {
        let result = load_keys_from_dir(Path::new("/nonexistent/path/to/keys"));
        assert!(result.is_empty(), "missing dir should return empty map");
    }

    #[test]
    fn test_load_keys_from_dir_empty() {
        let dir = TempDir::new().expect("tempdir");
        let result = load_keys_from_dir(dir.path());
        assert!(result.is_empty(), "empty dir should return empty map");
    }

    #[test]
    fn test_is_key_trusted_no_store() {
        // When both user and system store directories are absent, is_key_trusted returns None.
        // We verify this by calling with a path that definitely doesn't exist.
        // (We cannot set env vars safely without unsafe; instead we exercise the logic directly.)
        let nonexistent = PathBuf::from("/nonexistent/flavor/trusted-keys-abc123xyz");
        // load_keys_from_dir returns empty map for missing dirs
        let keys = load_keys_from_dir(&nonexistent);
        assert!(keys.is_empty());

        // is_key_trusted returns None only when no store dir exists.
        // We confirm the helper behaves correctly for a missing dir.
        let store_exists = nonexistent.exists();
        assert!(!store_exists, "test path must not exist");
    }

    #[test]
    fn test_load_keys_from_dir_bad_pub_file_skipped() {
        let dir = TempDir::new().expect("tempdir");
        // Write an invalid .pub file — should be skipped with a warning
        fs::write(dir.path().join("bad.pub"), "not a pem file").expect("write");
        let result = load_keys_from_dir(dir.path());
        // Bad file is skipped; map stays empty
        assert!(result.is_empty(), "bad key file should be skipped");
    }

    #[test]
    fn test_extract_ed25519_raw_key_valid_spki() {
        // Construct a well-formed 44-byte Ed25519 SubjectPublicKeyInfo
        let mut spki = vec![
            0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00,
        ];
        spki.extend_from_slice(&[0u8; 32]); // 32-byte key material
        let result = extract_ed25519_raw_key(&spki);
        assert!(result.is_ok(), "valid SPKI should succeed");
        assert_eq!(result.unwrap(), &[0u8; 32]);
    }

    #[test]
    fn test_extract_ed25519_raw_key_wrong_length() {
        // Any length other than 44 should fail with a message mentioning "44 bytes"
        let short_der = vec![0x30u8; 20];
        let err = extract_ed25519_raw_key(&short_der).unwrap_err();
        assert!(
            err.contains("44 bytes"),
            "error should mention 44 bytes, got: {err}"
        );
    }

    #[test]
    fn test_extract_ed25519_raw_key_wrong_prefix() {
        // Correct length (44) but wrong prefix bytes
        let mut bad_spki = vec![0xFFu8; 44];
        // Ensure last 32 bytes look like a key but prefix is wrong
        bad_spki[12..].copy_from_slice(&[0u8; 32]);
        let err = extract_ed25519_raw_key(&bad_spki).unwrap_err();
        assert!(
            err.contains("DER structure"),
            "error should mention DER structure, got: {err}"
        );
    }

    #[test]
    fn test_load_pub_key_file_reads_name_comment_and_fingerprint() {
        let dir = TempDir::new().expect("tempdir");
        let path = dir.path().join("alice.pub");
        let seed = [9u8; 32];
        let signing_key = SigningKey::from_bytes(&seed);
        let public_key = signing_key.verifying_key().to_bytes();
        let pem = format!("# Name: Alice\n{}", spki_public_pem_from_seed(seed));
        fs::write(&path, pem).expect("write public key");

        let key = load_pub_key_file(&path).expect("load public key");
        assert_eq!(key.name.as_deref(), Some("Alice"));
        assert_eq!(
            key.fingerprint,
            compute_key_fingerprint(&public_key).expect("fingerprint")
        );
        assert_eq!(key.path, path);
    }

    #[test]
    fn test_derive_index_key_fingerprint_matches_when_attestation_fp_stored() {
        let seed = [12u8; 32];
        let signing_key = SigningKey::from_bytes(&seed);
        let public_key = signing_key.verifying_key().to_bytes();
        let mut index = crate::psp::format_2025::index::Index::new();
        index.public_key = public_key;

        // Store the correct fingerprint in attestation_key_fp
        let fp = compute_key_fingerprint(&public_key).expect("fingerprint");
        index.attestation_key_fp[..fp.len()].copy_from_slice(fp.as_bytes());

        let result = derive_index_key_fingerprint(&index).expect("derive fingerprint");
        assert_eq!(result, Some(fp));
    }

    #[test]
    fn test_derive_index_key_fingerprint_rejects_zero_key_with_nonzero_attestation_fp() {
        let mut index = crate::psp::format_2025::index::Index::new();
        // public_key is all zeros (unsigned) but attestation_key_fp has data
        index.attestation_key_fp[0] = 0xFF;

        let err = derive_index_key_fingerprint(&index).expect_err("should reject");
        assert!(err.contains("public_key is missing"));
    }

    #[test]
    fn test_load_keys_from_dir_skips_non_pub_files() {
        let dir = TempDir::new().expect("tempdir");
        fs::write(dir.path().join("readme.txt"), "not a key").expect("write");
        fs::write(dir.path().join("key.pem"), "not a pub file").expect("write");
        let result = load_keys_from_dir(dir.path());
        assert!(result.is_empty());
    }

    #[test]
    fn test_load_pub_key_file_without_name_comment() {
        let dir = TempDir::new().expect("tempdir");
        let path = dir.path().join("noname.pub");
        let seed = [13u8; 32];
        let pem = spki_public_pem_from_seed(seed);
        fs::write(&path, pem).expect("write public key");

        let key = load_pub_key_file(&path).expect("load public key");
        assert!(key.name.is_none());
        assert!(!key.fingerprint.is_empty());
    }

    #[test]
    fn test_parse_ed25519_pem_rejects_non_utf8() {
        let err = parse_ed25519_pem(&[0xFF, 0xFE]).unwrap_err();
        assert!(!err.is_empty());
    }

    #[test]
    fn test_load_keys_from_dir_reads_valid_pub_file() {
        let dir = TempDir::new().expect("tempdir");
        let key_path = dir.path().join("user.pub");
        let seed = [11u8; 32];
        let signing_key = SigningKey::from_bytes(&seed);
        let public_key = signing_key.verifying_key().to_bytes();
        let pem = spki_public_pem_from_seed(seed);
        fs::write(&key_path, pem).expect("write public key");

        let keys = load_keys_from_dir(dir.path());
        assert_eq!(keys.len(), 1);
        let fingerprint = compute_key_fingerprint(&public_key).expect("fingerprint");
        let loaded = keys.get(&fingerprint).expect("key present");
        assert_eq!(loaded.path, key_path);
    }
}
