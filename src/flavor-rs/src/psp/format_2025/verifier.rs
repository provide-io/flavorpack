//! PSPF/2025 package verifier

use super::constants::{LifecycleAttestation, MAGIC_WAND_EMOJI_BYTES};
use crate::api::VerifyResult;
use crate::exceptions::{FlavorError, Result};
use adler::Adler32;
use ed25519_dalek::{Signature, Verifier as _, VerifyingKey};
use flate2::read::GzDecoder;
use hex;
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

    let slot_checksums_valid = verify_slot_checksums(&mut reader)?;
    debug!(
        "Slot checksums: {}",
        if slot_checksums_valid {
            "✅ VALID"
        } else {
            "❌ INVALID"
        }
    );

    // Verify attestation SBOM digest (fail-closed)
    verify_attestation_sbom_digest(&mut reader)?;
    debug!("Attestation SBOM digest: ✅ VERIFIED (or absent)");

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
        "🔍 Verification results: index_checksum={}, metadata_checksum={}, size={}, integrity_seal={}, slot_checksums={}, trailing_magic={}",
        index_checksum_valid,
        metadata_checksum_valid,
        size_valid,
        integrity_seal_valid,
        slot_checksums_valid,
        trailing_magic_valid
    );
    let valid = index_checksum_valid
        && metadata_checksum_valid
        && size_valid
        && integrity_seal_valid
        && slot_checksums_valid
        && trailing_magic_valid;

    Ok(VerifyResult {
        format: "PSPF/2025".to_string(),
        version: format!("0x{:08x}", super::constants::FORMAT_VERSION),
        valid,
        checksums_valid: slot_checksums_valid,
        signature_valid: integrity_seal_valid,
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

fn verify_slot_checksums(reader: &mut super::reader::Reader) -> Result<bool> {
    let descriptors = reader.read_slot_descriptors()?;

    for descriptor in &descriptors {
        let slot_data = reader.read_slot(descriptor)?;
        if !verify_slot_checksum(descriptor, &slot_data) {
            return Ok(false);
        }
    }

    Ok(true)
}

fn verify_slot_checksum(
    descriptor: &crate::psp::format_2025::slots::SlotDescriptor,
    slot_data: &[u8],
) -> bool {
    let checksum = Sha256::digest(slot_data);
    let mut checksum_bytes = [0u8; 8];
    checksum_bytes.copy_from_slice(&checksum[..8]);
    let actual = u64::from_le_bytes(checksum_bytes);
    actual == descriptor.checksum
}

/// Verify the attestation SBOM digest stored in the index against the attestation slot.
///
/// Semantics (fail-closed):
/// - digest present + slot present  → compute SHA-256 of raw slot bytes, compare; mismatch = error
/// - digest present + slot absent   → error (digest present but no slot to satisfy it)
/// - digest absent  + slot absent   → OK (backwards-compatible: no attestation)
/// - digest absent  + slot present  → OK (digest not bound, treat as no-op)
fn verify_attestation_sbom_digest(reader: &mut super::reader::Reader) -> Result<()> {
    let index = reader.read_index()?.clone();

    // Check whether the stored digest field is non-zero.
    let digest_field = &index.attestation_sbom_digest;
    let digest_present = digest_field.iter().any(|&b| b != 0);

    // Find the attestation slot (lifecycle == LifecycleAttestation).
    let descriptors = reader.read_slot_descriptors()?;
    let attestation_desc = descriptors
        .iter()
        .find(|d| d.lifecycle == LifecycleAttestation);

    if !digest_present {
        // No digest bound — nothing to verify (backwards-compatible).
        return Ok(());
    }

    // Digest is present; the attestation slot must also be present.
    let desc = attestation_desc.ok_or_else(|| {
        FlavorError::Generic(format!(
            "attestation SBOM digest is set but no attestation slot (lifecycle={}) found",
            LifecycleAttestation
        ))
    })?;

    // Read the raw (as-stored) bytes of the attestation slot.
    let slot_bytes = reader.read_slot(desc)?;

    // The per-slot checksum was already verified by verify_slot_checksums(); the
    // verification here is over the same bytes so we know they are intact.

    // Compute SHA-256 of the raw slot bytes.
    let slot_hash = Sha256::digest(&slot_bytes);
    let computed_hex = hex::encode(slot_hash);

    // Strip trailing null bytes from the stored field and interpret as ASCII hex.
    let stored_hex = String::from_utf8_lossy(digest_field)
        .trim_end_matches('\0')
        .to_string();

    if computed_hex != stored_hex {
        return Err(FlavorError::Generic(format!(
            "attestation SBOM digest mismatch: stored {:?}, computed {:?}",
            stored_hex, computed_hex
        )));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::psp::format_2025::slots::SlotDescriptor;

    #[test]
    fn test_verify_slot_checksum_detects_tampering() {
        let payload = b"expected payload";
        let mut descriptor = SlotDescriptor::new(1);
        let checksum = Sha256::digest(payload);
        descriptor.checksum = u64::from_le_bytes(checksum[..8].try_into().expect("checksum slice"));

        assert!(verify_slot_checksum(&descriptor, payload));
        assert!(!verify_slot_checksum(&descriptor, b"tampered payload"));
    }

    // ─── Attestation SBOM digest unit tests ───────────────────────────────────

    /// Build a minimal Reader backed by a temp file that contains exactly one
    /// attestation slot (lifecycle=11) with the provided content.
    fn build_attestation_reader(
        slot_content: &[u8],
        digest_hex: Option<&str>,
    ) -> (super::super::reader::Reader, tempfile::TempPath) {
        use crate::psp::format_2025::constants::{
            HEADER_SIZE, LifecycleAttestation, MAGIC_TRAILER_SIZE, PSPF_VERSION,
        };
        use crate::psp::format_2025::index::Index;
        use crate::psp::format_2025::slots::SlotDescriptor;
        use flate2::Compression;
        use flate2::write::GzEncoder;
        use sha2::{Digest as _, Sha256};
        use std::io::Write;
        use tempfile::NamedTempFile;

        let mut file = NamedTempFile::new().expect("temp file");
        let mut offset: u64 = 0;

        // ── Write slot data ──────────────────────────────────────────────────
        file.write_all(slot_content).expect("write slot");
        let slot_size = slot_content.len() as u64;

        // Build slot descriptor
        let checksum_raw = Sha256::digest(slot_content);
        let checksum = u64::from_le_bytes(checksum_raw[..8].try_into().expect("checksum slice"));
        let mut desc = SlotDescriptor::new(1);
        desc.offset = offset;
        desc.size = slot_size;
        desc.original_size = slot_size;
        desc.lifecycle = LifecycleAttestation;
        desc.checksum = checksum;
        offset += slot_size;

        // ── Write slot table ─────────────────────────────────────────────────
        let slot_table_offset = offset;
        file.write_all(&desc.pack()).expect("write descriptor");
        offset += 64;

        // ── Write gzip metadata ──────────────────────────────────────────────
        let meta_json = br#"{"package":{"name":"test","version":"0.0.1"},"slots":[]}"#;
        let mut gz_buf = Vec::new();
        {
            let mut enc = GzEncoder::new(&mut gz_buf, Compression::default());
            enc.write_all(meta_json).expect("gz write");
            enc.finish().expect("gz finish");
        }
        let meta_offset = offset;
        let meta_size = gz_buf.len() as u64;
        file.write_all(&gz_buf).expect("write metadata");
        offset += meta_size;

        let trailer_offset = offset;

        // ── Build index ──────────────────────────────────────────────────────
        let mut index = Index::new();
        index.format_version = PSPF_VERSION;
        index.package_size = trailer_offset + MAGIC_TRAILER_SIZE as u64;
        index.slot_table_offset = slot_table_offset;
        index.slot_table_size = 64;
        index.slot_count = 1;
        index.metadata_offset = meta_offset;
        index.metadata_size = meta_size;

        let meta_hash: [u8; 32] = Sha256::digest(&gz_buf).into();
        index.metadata_checksum = meta_hash;

        if let Some(hex) = digest_hex {
            let bytes = hex.as_bytes();
            let len = bytes.len().min(64);
            index.attestation_sbom_digest[..len].copy_from_slice(&bytes[..len]);
        }

        // ── Write MagicTrailer ───────────────────────────────────────────────
        let idx_bytes = index.pack();
        let mut trailer = vec![0u8; MAGIC_TRAILER_SIZE];
        trailer[..4].copy_from_slice(&[0xF0, 0x9F, 0x93, 0xA6]); // 📦
        trailer[4..4 + HEADER_SIZE].copy_from_slice(&idx_bytes);
        trailer[4 + HEADER_SIZE..].copy_from_slice(&[0xF0, 0x9F, 0xAA, 0x84]); // 🪄
        file.write_all(&trailer).expect("write trailer");
        file.flush().expect("flush");

        let path = file.into_temp_path();
        let reader = super::super::reader::Reader::new(path.as_ref()).expect("create reader");
        (reader, path)
    }

    #[test]
    fn test_attestation_sbom_digest_match() {
        let content = b"sbom+provenance data";
        let hash = Sha256::digest(content);
        let hex = hex::encode(hash);
        let (mut reader, _path) = build_attestation_reader(content, Some(&hex));
        verify_attestation_sbom_digest(&mut reader).expect("should pass for matching digest");
    }

    #[test]
    fn test_attestation_sbom_digest_mismatch() {
        let content = b"original sbom content";
        let wrong_hex = hex::encode(Sha256::digest(b"")); // SHA-256 of empty
        let (mut reader, _path) = build_attestation_reader(content, Some(&wrong_hex));
        let err = verify_attestation_sbom_digest(&mut reader)
            .expect_err("should fail for mismatched digest");
        assert!(
            err.to_string().contains("mismatch"),
            "error should mention mismatch: {err}"
        );
    }

    #[test]
    fn test_attestation_sbom_digest_absent_skipped() {
        let content = b"some attestation content";
        // Pass None → digest field stays all-zero → verification is skipped.
        let (mut reader, _path) = build_attestation_reader(content, None);
        verify_attestation_sbom_digest(&mut reader)
            .expect("should skip verification when digest absent");
    }
}
