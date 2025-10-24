//! PSPF/2025 package verifier

use super::constants::MAGIC_WAND_EMOJI_BYTES;
use crate::api::VerifyResult;
use crate::exceptions::{FlavorError, Result};
use adler::Adler32;
use ed25519_dalek::{Signature, Verifier as _, VerifyingKey};
use flate2::read::GzDecoder;
use log::{debug, info};
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

/// Verify a PSPF/2025 package
pub fn verify(package_path: &Path) -> Result<VerifyResult> {
    info!("Verifying PSPF/2025 package: {package_path:?}");

    let mut file = File::open(package_path)?;
    let file_size = file.metadata()?.len();

    // Read the index
    let mut reader = super::reader::Reader::new(package_path)?;
    let index = reader.read_index()?.clone();
    let metadata = reader.read_metadata()?.clone();

    // Verify index checksum
    let index_checksum_valid = verify_index_checksum(&index);
    debug!(
        "Index checksum: {}",
        if index_checksum_valid {
            "✅ VALID"
        } else {
            "❌ INVALID"
        }
    );

    // Verify metadata checksum
    let metadata_checksum_valid = verify_metadata_checksum(&mut file, &index)?;
    debug!(
        "Metadata checksum: {}",
        if metadata_checksum_valid {
            "✅ VALID"
        } else {
            "❌ INVALID"
        }
    );

    // Verify package size
    let size_valid = index.package_size == file_size;
    debug!(
        "Package size: {}",
        if size_valid {
            "✅ VALID"
        } else {
            "❌ INVALID"
        }
    );

    // Verify integrity seal (Ed25519 signature)
    let integrity_seal_valid = verify_integrity_seal(&mut file, &index)?;
    debug!(
        "Integrity seal: {}",
        if integrity_seal_valid {
            "✅ VALID"
        } else {
            "❌ NOT VERIFIED"
        }
    );

    // Verify trailing magic (8 bytes: 📦🪄)
    let trailing_magic_valid = verify_trailing_magic(&mut file)?;
    debug!(
        "Trailing magic: {}",
        if trailing_magic_valid {
            "✅ VALID"
        } else {
            "❌ INVALID"
        }
    );

    // Overall signature validity
    debug!(
        "🔍 Verification results: index_checksum={}, metadata_checksum={}, size={}, integrity_seal={}, trailing_magic={}",
        index_checksum_valid,
        metadata_checksum_valid,
        size_valid,
        integrity_seal_valid,
        trailing_magic_valid
    );
    let signature_valid = index_checksum_valid
        && metadata_checksum_valid
        && size_valid
        && integrity_seal_valid
        && trailing_magic_valid;

    Ok(VerifyResult {
        format: "PSPF/2025".to_string(),
        version: format!("0x{:08x}", super::constants::FORMAT_VERSION),
        signature_valid,
        slot_count: metadata.slots.len(),
        package_name: metadata.package.name.clone(),
        package_version: metadata.package.version.clone(),
    })
}

/// Verify the index checksum
fn verify_index_checksum(index: &super::index::Index) -> bool {
    // Get the index bytes using the pack method
    let mut index_bytes = index.pack();

    // Zero out the checksum field (offset 4-8 in 8192-byte header)
    index_bytes[4..8].copy_from_slice(&[0u8; 4]);

    // Calculate Adler32 checksum
    let mut adler = Adler32::new();
    adler.write_slice(&index_bytes);
    let calculated = adler.checksum();

    calculated == index.index_checksum
}

/// Verify the metadata checksum
fn verify_metadata_checksum(file: &mut File, index: &super::index::Index) -> Result<bool> {
    // Read metadata bytes
    file.seek(SeekFrom::Start(index.metadata_offset))?;
    let mut metadata_bytes = vec![0u8; index.metadata_size as usize];
    file.read_exact(&mut metadata_bytes)?;

    // Calculate SHA256 (metadata checksum is full 32-byte SHA-256 hash)
    let mut hasher = Sha256::new();
    hasher.update(&metadata_bytes);
    let calculated: [u8; 32] = hasher.finalize().into();

    // Compare with expected checksum
    Ok(calculated == index.metadata_checksum)
}

/// Verify the trailing magic (4 bytes: 🪄 at the very end)
fn verify_trailing_magic(file: &mut File) -> Result<bool> {
    // Seek to end minus 4 bytes (magic wand emoji)
    file.seek(SeekFrom::End(-4))?;

    // Read the last 4 bytes
    let mut magic = [0u8; 4];
    file.read_exact(&mut magic)?;

    // Check if it matches the magic wand emoji
    Ok(magic == MAGIC_WAND_EMOJI_BYTES)
}

/// Verify the integrity seal (Ed25519 signature)
fn verify_integrity_seal(file: &mut File, index: &super::index::Index) -> Result<bool> {
    // Read metadata
    file.seek(SeekFrom::Start(index.metadata_offset))?;
    let mut metadata_bytes = vec![0u8; index.metadata_size as usize];
    file.read_exact(&mut metadata_bytes)?;

    // Decompress metadata if needed
    let json_bytes = if true {
        // Always gzip for now
        let gz = GzDecoder::new(&metadata_bytes[..]);
        let mut json_data = Vec::new();
        gz.take(1024 * 1024).read_to_end(&mut json_data)?;
        json_data
    } else {
        metadata_bytes.clone()
    };

    // Get signature from index
    let sig_bytes = &index.integrity_signature;

    // Get public key from index
    let public_key_bytes = &index.public_key;

    // Check if signature is present (not all zeros)
    if sig_bytes.iter().all(|&b| b == 0) {
        debug!("No signature present in package");
        return Ok(false);
    }

    // Check if public key is present (not all zeros)
    if public_key_bytes.iter().all(|&b| b == 0) {
        debug!("No public key present in package");
        return Ok(false);
    }

    // Parse signature (Ed25519 signatures are 64 bytes, stored at beginning of 512-byte field)
    let sig_array: [u8; 64] = sig_bytes[..64]
        .try_into()
        .map_err(|_| FlavorError::Generic("Invalid signature size".to_string()))?;
    let signature = Signature::from_bytes(&sig_array);

    // Parse public key
    let key_array: [u8; 32] = public_key_bytes[..]
        .try_into()
        .map_err(|_| FlavorError::Generic("Invalid public key size".to_string()))?;
    let public_key = VerifyingKey::from_bytes(&key_array)
        .map_err(|e| FlavorError::Generic(format!("Invalid public key: {e}")))?;

    // Verify signature over JSON metadata
    let valid = public_key.verify(&json_bytes, &signature).is_ok();

    if valid {
        debug!("✅ Signature verification successful");
    } else {
        debug!("❌ Signature verification failed");
    }

    Ok(valid)
}
