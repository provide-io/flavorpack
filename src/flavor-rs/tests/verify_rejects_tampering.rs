//! The verification contract, asserted against the committed fixtures.
//!
//! This mirrors the Go tests in `launcher_cli_verify_test.go`. Both
//! implementations must give the same verdict on the same bytes, and the
//! interesting case is a package where every unkeyed checksum still adds up and
//! only the Ed25519 seal is wrong -- which is exactly what an attacker who can
//! rewrite the file produces, and what Go's `verify` used to accept.

use std::fs;
use std::path::{Path, PathBuf};

use adler2::Adler32;
use flavor::psp::format_2025;
use serde_json::Value;
use tempfile::tempdir;

/// Byte layout of the trailer, from constants.rs: 📦 + 8192-byte index + 🪄.
const MAGIC_TRAILER_SIZE: usize = 8200;
const HEADER_SIZE: usize = 8192;
/// Offsets within the index block.
const CHECKSUM_RANGE: std::ops::Range<usize> = 4..8;
const SIGNATURE_START: usize = 128;

fn fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tests/fixtures/format_compat/v1")
}

/// Names of the committed fixtures, read from the file that pins them.
fn fixture_names() -> Vec<String> {
    let raw = fs::read_to_string(fixture_dir().join("expected.json")).expect("read expected.json");
    let expected: Value = serde_json::from_str(&raw).expect("parse expected.json");
    let mut names: Vec<String> = expected["fixtures"]
        .as_object()
        .expect("fixtures object")
        .keys()
        .cloned()
        .collect();
    names.sort();
    names
}

/// Copy a fixture, corrupt one byte of its Ed25519 signature, and repair the
/// index checksum so that every *unkeyed* check still passes.
fn tamper_with_the_seal(source: &Path, destination: &Path) {
    let mut bytes = fs::read(source).expect("read fixture");
    let trailer_start = bytes.len() - MAGIC_TRAILER_SIZE;
    let index_start = trailer_start + 4;

    bytes[index_start + SIGNATURE_START] ^= 0xFF;

    // Recompute the Adler-32 over the index with its own checksum field zeroed,
    // the order the builder writes it in. Without this the package would fail
    // on the index instead, and the test would prove nothing about the seal.
    let mut index = bytes[index_start..index_start + HEADER_SIZE].to_vec();
    index[CHECKSUM_RANGE].copy_from_slice(&[0u8; 4]);
    let mut adler = Adler32::new();
    adler.write_slice(&index);
    let checksum = adler.checksum();
    bytes[index_start + CHECKSUM_RANGE.start..index_start + CHECKSUM_RANGE.end]
        .copy_from_slice(&checksum.to_le_bytes());

    fs::write(destination, bytes).expect("write tampered fixture");
}

#[test]
fn a_tampered_seal_is_rejected_on_every_fixture() {
    let temp = tempdir().expect("tempdir");

    for name in fixture_names() {
        let tampered = temp.path().join(&name);
        tamper_with_the_seal(&fixture_dir().join(&name), &tampered);

        let result = format_2025::verify(&tampered)
            .unwrap_or_else(|e| panic!("{name}: verification errored: {e}"));

        assert!(
            !result.signature_valid,
            "{name}: a corrupted Ed25519 signature was reported as valid"
        );
        assert!(
            !result.valid,
            "{name}: a package with a broken seal was reported as verified, even though \
             every unkeyed checksum in it still adds up"
        );
        assert!(
            result.checksums_valid,
            "{name}: the tampering was supposed to leave the checksums intact, so this \
             test is no longer isolating the signature"
        );
    }
}

#[test]
fn an_untouched_fixture_still_verifies() {
    // The control: whatever the test above rejects, it rejects for the reason
    // stated and not because the fixtures stopped verifying.
    for name in fixture_names() {
        let result = format_2025::verify(&fixture_dir().join(&name))
            .unwrap_or_else(|e| panic!("{name}: verification errored: {e}"));

        assert!(result.valid, "{name} no longer verifies");
        assert!(result.signature_valid, "{name}: seal no longer verifies");
    }
}
