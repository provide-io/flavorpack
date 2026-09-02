//! Verify the committed cross-version format-compatibility fixtures.
//!
//! These packages were built once, by an older toolchain, and are never rebuilt.
//! Every other test in this crate builds and verifies inside a single run, so
//! both sides of the comparison move together and a format change stays
//! invisible. These fixtures are the only thing that fails when a package built
//! before a crypto or hashing change stops verifying after it -- which is
//! exactly the risk carried by an `ed25519-dalek` or `sha2` major bump.
//!
//! See tests/fixtures/format_compat/README.md.

use std::fs;
use std::path::{Path, PathBuf};

use flavor::psp::format_2025::{self, Metadata, Reader};
use serde_json::Value;
use sha2::{Digest, Sha256};

const GENERATION: &str = "v1";

/// Locate the fixture generation directory relative to the crate.
fn fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/fixtures/format_compat")
        .join(GENERATION)
}

/// Load the pinned facts for the current fixture generation.
fn expected() -> Value {
    let path = fixture_dir().join("expected.json");
    let raw = fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {}: {e}", path.display()));
    serde_json::from_str(&raw).expect("parse expected.json")
}

/// Yield every fixture name recorded in expected.json, in a stable order.
fn fixture_names(expected: &Value) -> Vec<String> {
    let mut names: Vec<String> = expected["fixtures"]
        .as_object()
        .expect("expected.json has a fixtures object")
        .keys()
        .cloned()
        .collect();
    names.sort();
    assert!(!names.is_empty(), "expected.json lists no fixtures");
    names
}

#[test]
fn fixture_bytes_are_unchanged() {
    // Regenerating a fixture silently converts this whole file into a
    // tautology, so the digest is pinned and any rebuild has to be argued for
    // in review.
    let expected = expected();

    for name in fixture_names(&expected) {
        let path = fixture_dir().join(&name);
        let data = fs::read(&path).unwrap_or_else(|e| panic!("read {}: {e}", path.display()));
        let pinned = &expected["fixtures"][&name];

        assert_eq!(
            data.len() as u64,
            pinned["size"].as_u64().expect("size"),
            "{name}: size changed"
        );
        assert_eq!(
            hex::encode(Sha256::digest(&data)),
            pinned["sha256"].as_str().expect("sha256"),
            "{name} was regenerated. That destroys the cross-version guarantee: \
             the fixture is only evidence while it predates the code verifying it."
        );
    }
}

#[test]
fn old_packages_still_verify() {
    let expected = expected();

    for name in fixture_names(&expected) {
        let path = fixture_dir().join(&name);
        let result = format_2025::verify(&path)
            .unwrap_or_else(|e| panic!("{name}: verification errored: {e}"));

        assert!(result.valid, "{name} no longer verifies");
        assert!(result.checksums_valid, "{name}: checksums no longer match");
        assert!(
            result.signature_valid,
            "{name}: Ed25519 seal no longer verifies"
        );
        assert_eq!(result.format, "PSPF/2025", "{name}: format changed");
        assert_eq!(
            result.package_name,
            expected["package"]["name"].as_str().expect("name"),
            "{name}: package name changed"
        );
        assert_eq!(
            result.package_version,
            expected["package"]["version"].as_str().expect("version"),
            "{name}: package version changed"
        );
        assert_eq!(
            result.slot_count as u64,
            expected["fixtures"][&name]["slot_count"]
                .as_u64()
                .expect("slot_count"),
            "{name}: slot count changed"
        );
    }
}

#[test]
fn signing_key_material_is_stable() {
    // Both values are derived from the committed seed, so a drift here means
    // key derivation or the digest behind the fingerprint has changed
    // underneath us.
    let expected = expected();

    for name in fixture_names(&expected) {
        let path = fixture_dir().join(&name);
        let mut reader = Reader::new(&path).unwrap_or_else(|e| panic!("{name}: open: {e}"));
        let index = reader
            .read_index()
            .unwrap_or_else(|e| panic!("{name}: read_index: {e}"))
            .clone();
        let pinned = &expected["fixtures"][&name];

        assert_eq!(
            hex::encode(index.public_key),
            pinned["public_key"].as_str().expect("public_key"),
            "{name}: embedded public key changed"
        );

        let fingerprint: String = String::from_utf8_lossy(&index.attestation_key_fp)
            .trim_end_matches('\0')
            .to_string();
        assert_eq!(
            fingerprint,
            pinned["key_fingerprint"].as_str().expect("key_fingerprint"),
            "{name}: signing key fingerprint changed"
        );
    }
}

#[test]
fn payload_slot_round_trips() {
    let expected = expected();
    let payload = fs::read(fixture_dir().join("inputs/payload.txt")).expect("read payload");

    for name in fixture_names(&expected) {
        let path = fixture_dir().join(&name);
        let mut reader = Reader::new(&path).unwrap_or_else(|e| panic!("{name}: open: {e}"));
        let descriptors = reader
            .read_slot_descriptors()
            .unwrap_or_else(|e| panic!("{name}: read_slot_descriptors: {e}"));
        let data = reader
            .read_slot(&descriptors[0])
            .unwrap_or_else(|e| panic!("{name}: read_slot: {e}"));

        assert_eq!(
            data, payload,
            "{name}: slot 0 no longer decodes to the payload"
        );
    }
}

#[test]
fn every_producer_derives_the_same_key() {
    // Deterministic key generation is only useful if it is deterministic across
    // implementations, not merely within one.
    let expected = expected();
    let names = fixture_names(&expected);

    let first = expected["fixtures"][&names[0]]["public_key"]
        .as_str()
        .expect("public_key");
    for name in &names {
        assert_eq!(
            expected["fixtures"][name]["public_key"]
                .as_str()
                .expect("public_key"),
            first,
            "{name}: producers disagree on the key derived from the seed"
        );
    }
}

/// One metadata document that every implementation must read the same way.
///
/// The counterpart — that packages carrying `execution.primary_slot` still
/// parse, which every package in `v1/` does — is asserted by
/// `old_packages_still_verify` here, and probed explicitly in the Go and Python
/// harnesses, which can reach the raw metadata bytes.
///
/// The environment is written under `env` by Python and this implementation,
/// and Go read `environment`, so a block set by either of the others was
/// dropped in silence. See tests/fixtures/format_compat/execution/README.md.
#[test]
fn execution_block_is_readable() {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/fixtures/format_compat/execution/execution-block.json");
    let raw = fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {}: {e}", path.display()));

    let metadata: Metadata = serde_json::from_str(&raw).expect("fixture must parse");

    let execution = metadata
        .execution
        .as_ref()
        .expect("the fixture declares an execution block");
    assert_eq!(execution.command, "true");
    assert_eq!(
        execution.env.get("MODE").map(String::as_str),
        Some("prod"),
        "the environment must be read from the \"env\" key"
    );
}
