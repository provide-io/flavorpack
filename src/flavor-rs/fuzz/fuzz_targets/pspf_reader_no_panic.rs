#![no_main]

use flavor_rs::psp::format_2025::{
    constants::{MAGIC_TRAILER_SIZE, MAGIC_WAND_EMOJI_BYTES, PACKAGE_EMOJI_BYTES, PSPF_VERSION},
    index::Index,
    reader::Reader,
};
use libfuzzer_sys::fuzz_target;
use sha2::{Digest, Sha256};
use std::io::Write;
use tempfile::NamedTempFile;

fn build_candidate(metadata_bytes: &[u8]) -> Vec<u8> {
    let mut index = Index::new();
    index.format_version = PSPF_VERSION;
    index.package_size = metadata_bytes.len() as u64 + MAGIC_TRAILER_SIZE as u64;
    index.metadata_offset = 0;
    index.metadata_size = metadata_bytes.len() as u64;
    index.slot_table_offset = metadata_bytes.len() as u64;
    index.slot_table_size = 0;
    index.slot_count = 0;
    index.metadata_checksum = Sha256::digest(metadata_bytes).into();

    let index_bytes = index.pack();
    let mut candidate = Vec::with_capacity(metadata_bytes.len() + MAGIC_TRAILER_SIZE);
    candidate.extend_from_slice(metadata_bytes);
    candidate.extend_from_slice(PACKAGE_EMOJI_BYTES);
    candidate.extend_from_slice(&index_bytes);
    candidate.extend_from_slice(MAGIC_WAND_EMOJI_BYTES);
    candidate
}

fuzz_target!(|data: &[u8]| {
    let Ok(mut file) = NamedTempFile::new() else {
        return;
    };
    let candidate = build_candidate(data);

    if file.write_all(&candidate).is_err() {
        return;
    }
    if file.flush().is_err() {
        return;
    }

    if let Ok(mut reader) = Reader::new(file.path()) {
        let _ = reader.read_index();
        let _ = reader.read_slot_descriptors();
        let _ = reader.read_metadata();
    }
});
