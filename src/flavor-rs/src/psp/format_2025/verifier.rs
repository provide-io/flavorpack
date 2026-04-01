//! PSPF/2025 package verifier

use super::constants::{LifecycleAttestation, MAGIC_WAND_EMOJI_BYTES};
use crate::api::VerifyResult;
use crate::exceptions::{FlavorError, Result};
use adler2::Adler32;
use ed25519_dalek::{Signature, Verifier as _, VerifyingKey};
use flate2::read::GzDecoder;
use hex;
use log::{debug, info, trace};
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

    // Verify attestation policy hash (fail-closed)
    verify_attestation_policy_hash(&mut reader)?;
    debug!("Attestation policy hash: ✅ VERIFIED (or absent)");

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

    // Decompress gzip metadata
    let gz = GzDecoder::new(&metadata_bytes[..]);
    let mut json_bytes = Vec::new();
    gz.take(1024 * 1024).read_to_end(&mut json_bytes)?;

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

    // Hash slots incrementally via read_at() so that verification is correct
    // regardless of file size. StreamBackend.read_slot() truncates to
    // DEFAULT_CHUNK_SIZE (64 KB), which would produce a wrong checksum for
    // multi-megabyte slots; reading in chunks avoids loading everything at once.
    const CHUNK: u64 = 256 * 1024; // 256 KB per read

    for (i, descriptor) in descriptors.iter().enumerate() {
        let mut hasher = Sha256::new();
        let mut remaining = descriptor.size;
        let mut offset = descriptor.offset;
        let mut first_chunk_preview: Option<Vec<u8>> = None;

        while remaining > 0 {
            let to_read = remaining.min(CHUNK) as usize;
            let chunk = reader.backend_mut().read_at(offset, to_read)?;
            if chunk.is_empty() {
                return Err(FlavorError::Generic(format!(
                    "Backend returned empty read for slot {} at offset {:#x} (remaining {})",
                    i, offset, remaining
                )));
            }
            if first_chunk_preview.is_none() {
                first_chunk_preview = Some(chunk[..16.min(chunk.len())].to_vec());
            }
            let actually_read = chunk.len() as u64;
            hasher.update(&chunk);
            offset += actually_read;
            remaining -= actually_read;
        }

        let checksum = hasher.finalize();
        let mut checksum_bytes = [0u8; 8];
        checksum_bytes.copy_from_slice(&checksum[..8]);
        let actual = u64::from_le_bytes(checksum_bytes);
        let expected = descriptor.checksum;

        if actual != expected {
            let desc_offset = descriptor.offset;
            let desc_size = descriptor.size;
            debug!(
                "❌ Slot {} checksum mismatch: offset={:#x} size={} expected={:#018x} actual={:#018x}",
                i, desc_offset, desc_size, expected, actual
            );
            if let Some(ref preview) = first_chunk_preview {
                trace!("  First 16 bytes: {:02x?}", preview);
            }
            return Ok(false);
        }

        trace!("✅ Slot {} checksum ok: {:#018x}", i, actual);
    }

    Ok(true)
}

#[cfg(test)]
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

/// Verify the attestation policy hash stored in the index against the package-declared policy.
///
/// Semantics (fail-closed):
/// - hash present + policy present  → serialise policy to canonical JSON, hash it; mismatch = error
/// - hash present + policy absent   → error (hash present but no policy to verify against)
/// - hash absent  + policy absent   → OK (backwards-compatible: no policy hash bound)
/// - hash absent  + policy present  → OK (hash not bound yet, treat as no-op)
fn verify_attestation_policy_hash(reader: &mut super::reader::Reader) -> Result<()> {
    let index = reader.read_index()?.clone();

    // Check whether the stored hash field is non-zero.
    let hash_field = &index.attestation_policy_hash;
    let hash_present = hash_field.iter().any(|&b| b != 0);

    if !hash_present {
        // No hash bound — nothing to verify (backwards-compatible).
        return Ok(());
    }

    // Hash is present; a policy must exist in the metadata.
    let metadata = reader.read_metadata()?.clone();

    let policy_value = metadata.policy.ok_or_else(|| {
        FlavorError::Generic(
            "attestation_policy_hash is set but package has no policy in metadata".to_string(),
        )
    })?;

    // Serialise the policy value to canonical JSON.
    // serde_json::to_string produces compact JSON; key ordering for objects is
    // insertion-order (i.e. the order in the source JSON), which matches the
    // builder that uses the same serde_json serialiser.
    let canonical =
        serde_json::to_string(&policy_value).map_err(|e| FlavorError::Generic(e.to_string()))?;

    let computed_hash = Sha256::digest(canonical.as_bytes());
    let computed_hex = hex::encode(computed_hash);

    // Strip trailing null bytes from the stored field and interpret as ASCII hex.
    let stored_hex = String::from_utf8_lossy(hash_field)
        .trim_end_matches('\0')
        .to_string();

    if computed_hex != stored_hex {
        return Err(FlavorError::Generic(format!(
            "attestation_policy_hash mismatch: stored {:?}, computed {:?}",
            stored_hex, computed_hex
        )));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::psp::format_2025::slots::SlotDescriptor;
    use proptest::prelude::*;

    #[test]
    fn test_verify_slot_checksum_detects_tampering() {
        let payload = b"expected payload";
        let mut descriptor = SlotDescriptor::new(1);
        let checksum = Sha256::digest(payload);
        descriptor.checksum = u64::from_le_bytes(checksum[..8].try_into().expect("checksum slice"));

        assert!(verify_slot_checksum(&descriptor, payload));
        assert!(!verify_slot_checksum(&descriptor, b"tampered payload"));
    }

    /// Verify that `verify_slot_checksums` reads the full slot across multiple chunks.
    ///
    /// Previously the code called `reader.read_slot()`, which delegates to
    /// `StreamBackend.read_slot()` for large files.  `StreamBackend` truncates
    /// reads to `DEFAULT_CHUNK_SIZE` (64 KB), so any slot larger than that would
    /// produce a wrong checksum and verification would fail.  The fix hashes the
    /// slot incrementally via `backend_mut().read_at()` in 256 KB chunks.
    ///
    /// This test constructs a minimal package whose slot payload is larger than
    /// `DEFAULT_CHUNK_SIZE` (filled with a known byte pattern) and asserts that
    /// `verify_slot_checksums` returns `Ok(true)`.
    #[test]
    fn test_verify_slot_checksums_multi_chunk_slot() {
        use crate::psp::format_2025::constants::{HEADER_SIZE, MAGIC_TRAILER_SIZE, PSPF_VERSION};
        use crate::psp::format_2025::defaults::DEFAULT_CHUNK_SIZE;
        use crate::psp::format_2025::index::Index;
        use flate2::Compression;
        use flate2::write::GzEncoder;
        use sha2::{Digest as _, Sha256};
        use std::io::Write;
        use tempfile::NamedTempFile;

        // Build a slot payload that spans multiple 256 KB read chunks (e.g. 500 KB).
        let slot_size = DEFAULT_CHUNK_SIZE * 8; // 512 KB — definitely multi-chunk
        let slot_content: Vec<u8> = (0..slot_size).map(|i| (i % 251) as u8).collect();

        let checksum_raw = Sha256::digest(&slot_content);
        let checksum = u64::from_le_bytes(checksum_raw[..8].try_into().expect("slice"));

        let mut file = NamedTempFile::new().expect("temp file");
        let mut offset: u64 = 0;

        // Write slot data
        file.write_all(&slot_content).expect("write slot");
        let slot_offset = offset;
        offset += slot_size as u64;

        // Write slot descriptor table
        let slot_table_offset = offset;
        let mut desc = SlotDescriptor::new(0);
        desc.offset = slot_offset;
        desc.size = slot_size as u64;
        desc.original_size = slot_size as u64;
        desc.checksum = checksum;
        file.write_all(&desc.pack()).expect("write descriptor");
        offset += 64;

        // Write gzip metadata
        let meta_json = br#"{"format":"PSPF/2025","package":{"name":"test","version":"0.0.1"},"slots":[],"execution":{"primary_slot":0,"command":"echo"}}"#;
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

        let idx_bytes = index.pack();
        let mut trailer = vec![0u8; MAGIC_TRAILER_SIZE];
        trailer[..4].copy_from_slice(&[0xF0, 0x9F, 0x93, 0xA6]); // 📦
        trailer[4..4 + HEADER_SIZE].copy_from_slice(&idx_bytes);
        trailer[4 + HEADER_SIZE..].copy_from_slice(&[0xF0, 0x9F, 0xAA, 0x84]); // 🪄
        file.write_all(&trailer).expect("write trailer");
        file.flush().expect("flush");

        let path = file.into_temp_path();
        let mut reader = super::super::reader::Reader::new(path.as_ref()).expect("create reader");

        let result = verify_slot_checksums(&mut reader);
        assert!(
            result.expect("verify_slot_checksums should not error"),
            "multi-chunk slot checksum must verify correctly"
        );
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

    /// Build a minimal Reader backed by a temp file that has NO attestation slot,
    /// but has a non-zero `attestation_sbom_digest` in the index.
    fn build_no_attestation_slot_reader(
        digest_hex: &str,
    ) -> (super::super::reader::Reader, tempfile::TempPath) {
        use crate::psp::format_2025::constants::{HEADER_SIZE, MAGIC_TRAILER_SIZE, PSPF_VERSION};
        use crate::psp::format_2025::index::Index;
        use flate2::Compression;
        use flate2::write::GzEncoder;
        use sha2::{Digest as _, Sha256};
        use std::io::Write;
        use tempfile::NamedTempFile;

        let mut file = NamedTempFile::new().expect("temp file");
        let mut offset: u64 = 0;

        // ── No slot data — slot table is empty ───────────────────────────────
        let slot_table_offset = offset;

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

        // ── Build index with non-zero attestation_sbom_digest but slot_count=0 ─
        let mut index = Index::new();
        index.format_version = PSPF_VERSION;
        index.package_size = trailer_offset + MAGIC_TRAILER_SIZE as u64;
        index.slot_table_offset = slot_table_offset;
        index.slot_table_size = 0;
        index.slot_count = 0;
        index.metadata_offset = meta_offset;
        index.metadata_size = meta_size;

        let meta_hash: [u8; 32] = Sha256::digest(&gz_buf).into();
        index.metadata_checksum = meta_hash;

        // Set a non-zero attestation_sbom_digest
        let bytes = digest_hex.as_bytes();
        let len = bytes.len().min(64);
        index.attestation_sbom_digest[..len].copy_from_slice(&bytes[..len]);

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
    fn test_attestation_sbom_digest_present_no_slot() {
        // Use a plausible non-zero digest hex string (SHA-256 of empty string).
        let digest_hex = hex::encode(Sha256::digest(b""));
        let (mut reader, _path) = build_no_attestation_slot_reader(&digest_hex);
        let err = verify_attestation_sbom_digest(&mut reader)
            .expect_err("should fail when digest is set but no attestation slot exists");
        assert!(
            err.to_string().contains("attestation"),
            "error should mention attestation: {err}"
        );
    }

    // ─── Policy hash unit tests ───────────────────────────────────────────────

    /// Build a minimal Reader whose metadata optionally includes a `"policy"` JSON
    /// value and whose index has `attestation_policy_hash` set to `policy_hash_hex`
    /// (pass `None` to leave zero-filled / absent).
    fn build_policy_hash_reader(
        policy_json: Option<&str>,
        policy_hash_hex: Option<&str>,
    ) -> (super::super::reader::Reader, tempfile::TempPath) {
        use crate::psp::format_2025::constants::{HEADER_SIZE, MAGIC_TRAILER_SIZE, PSPF_VERSION};
        use crate::psp::format_2025::index::Index;
        use flate2::Compression;
        use flate2::write::GzEncoder;
        use sha2::{Digest as _, Sha256};
        use std::io::Write;
        use tempfile::NamedTempFile;

        let mut file = NamedTempFile::new().expect("temp file");
        let mut offset: u64 = 0;

        // Build metadata JSON, inserting policy key when provided.
        // Must include "format" and "execution" to satisfy Metadata deserialization.
        let meta_json: Vec<u8> = if let Some(p) = policy_json {
            format!(
                r#"{{"format":"PSPF/2025","package":{{"name":"test","version":"0.0.1"}},"slots":[],"execution":{{"primary_slot":0,"command":"echo"}},"policy":{p}}}"#
            )
            .into_bytes()
        } else {
            br#"{"format":"PSPF/2025","package":{"name":"test","version":"0.0.1"},"slots":[],"execution":{"primary_slot":0,"command":"echo"}}"#.to_vec()
        };

        let mut gz_buf = Vec::new();
        {
            let mut enc = GzEncoder::new(&mut gz_buf, Compression::default());
            enc.write_all(&meta_json).expect("gz write");
            enc.finish().expect("gz finish");
        }
        let meta_offset = offset;
        let meta_size = gz_buf.len() as u64;
        file.write_all(&gz_buf).expect("write metadata");
        offset += meta_size;

        let trailer_offset = offset;

        let mut index = Index::new();
        index.format_version = PSPF_VERSION;
        index.package_size = trailer_offset + MAGIC_TRAILER_SIZE as u64;
        index.slot_table_offset = 0;
        index.slot_table_size = 0;
        index.slot_count = 0;
        index.metadata_offset = meta_offset;
        index.metadata_size = meta_size;

        let meta_hash: [u8; 32] = Sha256::digest(&gz_buf).into();
        index.metadata_checksum = meta_hash;

        if let Some(hex_str) = policy_hash_hex {
            let bytes = hex_str.as_bytes();
            let len = bytes.len().min(64);
            index.attestation_policy_hash[..len].copy_from_slice(&bytes[..len]);
        }

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
    fn test_verify_attestation_policy_hash_zero_field_skip() {
        // No hash set → verification must be skipped regardless of policy presence.
        let (mut reader, _path) = build_policy_hash_reader(None, None);
        verify_attestation_policy_hash(&mut reader).expect("expected nil for zero policy hash");
    }

    #[test]
    fn test_verify_attestation_policy_hash_match() {
        let policy_json = r#"{"platforms":["linux_amd64"],"refuse_root":true}"#;
        // Compute the expected hash the same way the function does.
        let policy_value: serde_json::Value =
            serde_json::from_str(policy_json).expect("parse policy");
        let canonical = serde_json::to_string(&policy_value).expect("serialise");
        let hash = Sha256::digest(canonical.as_bytes());
        let hash_hex = hex::encode(hash);

        let (mut reader, _path) = build_policy_hash_reader(Some(policy_json), Some(&hash_hex));
        verify_attestation_policy_hash(&mut reader)
            .expect("expected no error for matching policy hash");
    }

    #[test]
    fn test_verify_attestation_policy_hash_mismatch() {
        let policy_json = r#"{"platforms":["linux_amd64"]}"#;
        let wrong_hex = hex::encode(Sha256::digest(b"")); // SHA-256 of empty string

        let (mut reader, _path) = build_policy_hash_reader(Some(policy_json), Some(&wrong_hex));
        let err = verify_attestation_policy_hash(&mut reader)
            .expect_err("expected error for mismatched policy hash");
        assert!(
            err.to_string().contains("mismatch"),
            "error should mention mismatch: {err}"
        );
    }

    #[test]
    fn test_verify_attestation_policy_hash_present_no_policy_fails() {
        let fake_hash = hex::encode(Sha256::digest(b"anything")); // non-zero

        // No policy in metadata but hash is set → fail-closed.
        let (mut reader, _path) = build_policy_hash_reader(None, Some(&fake_hash));
        let err = verify_attestation_policy_hash(&mut reader)
            .expect_err("expected error when hash set but metadata has no policy");
        assert!(
            err.to_string().contains("policy"),
            "error should mention policy: {err}"
        );
    }

    proptest! {
        /// Checksum of data always matches descriptor built from that data.
        #[test]
        fn prop_checksum_consistent(data in proptest::collection::vec(any::<u8>(), 0..1024)) {
            let checksum = Sha256::digest(&data);
            let mut checksum_bytes = [0u8; 8];
            checksum_bytes.copy_from_slice(&checksum[..8]);
            let expected = u64::from_le_bytes(checksum_bytes);

            let mut descriptor = SlotDescriptor::new(1);
            descriptor.checksum = expected;
            descriptor.size = data.len() as u64;
            descriptor.original_size = data.len() as u64;

            prop_assert!(verify_slot_checksum(&descriptor, &data));
        }

        /// Changing any byte in data must cause checksum mismatch.
        #[test]
        fn prop_tamper_always_detected(
            data in proptest::collection::vec(any::<u8>(), 1..256),
            flip_idx in any::<proptest::sample::Index>()
        ) {
            let checksum = Sha256::digest(&data);
            let mut checksum_bytes = [0u8; 8];
            checksum_bytes.copy_from_slice(&checksum[..8]);
            let expected = u64::from_le_bytes(checksum_bytes);

            let mut descriptor = SlotDescriptor::new(1);
            descriptor.checksum = expected;
            descriptor.size = data.len() as u64;
            descriptor.original_size = data.len() as u64;

            let mut tampered = data.clone();
            let idx = flip_idx.index(tampered.len());
            tampered[idx] ^= 0xFF;
            prop_assert!(!verify_slot_checksum(&descriptor, &tampered));
        }
    }
}
