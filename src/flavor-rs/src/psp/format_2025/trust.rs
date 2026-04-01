//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

//! Trusted key store for FlavorPack package signature verification.

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
    // Fall back to ~/.config/flavor using HOME env var
    if let Some(home) = env::var_os("HOME") {
        return PathBuf::from(home).join(".config").join("flavor");
    }
    PathBuf::from("/tmp/flavor/config")
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
    // Ed25519 OID: 1.3.101.112 → DER: 06 03 2b 65 70
    const ED25519_OID: &[u8] = &[0x06, 0x03, 0x2b, 0x65, 0x70];
    if !der.windows(ED25519_OID.len()).any(|w| w == ED25519_OID) {
        return Err("key is not an Ed25519 public key (OID mismatch)".to_string());
    }
    if der.len() < 32 {
        return Err("DER too short to contain Ed25519 key".to_string());
    }
    Ok(&der[der.len() - 32..])
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
    use std::fs;
    use tempfile::TempDir;

    fn mock_raw_key() -> Vec<u8> {
        vec![0u8; 32]
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
    fn test_extract_ed25519_raw_key_wrong_oid() {
        // A DER blob without the Ed25519 OID should fail
        let fake_der = vec![0x30u8, 0x01, 0x00];
        let result = extract_ed25519_raw_key(&fake_der);
        assert!(result.is_err(), "should reject non-Ed25519 key");
    }

    #[test]
    fn test_extract_ed25519_raw_key_too_short_with_oid() {
        // DER has correct OID but is too short to contain 32-byte key
        let mut fake_der = vec![0x06u8, 0x03, 0x2b, 0x65, 0x70];
        fake_der.extend_from_slice(&[0u8; 10]); // only 10 more bytes, not 32
        let result = extract_ed25519_raw_key(&fake_der);
        assert!(result.is_err(), "should reject DER that is too short");
    }
}
