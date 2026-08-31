//! Golden vectors for the crates that decide whether a package verifies.
//!
//! `sha2`, `ed25519-dalek` and `pem` sit directly on the signing and checksum
//! paths. When one of them changes behaviour, the committed format fixtures
//! stop verifying -- but a 17 KB blob failing to verify does not say *why*.
//! These vectors do: each pins one crate's output for one fixed input, so a
//! breaking upgrade names itself.
//!
//! Every expected value here was produced independently by the Go standard
//! library (`crypto/sha256`, `crypto/sha512`, `crypto/ed25519`), not by the
//! crates under test, so they are an outside check rather than a recording of
//! whatever this code happened to do.

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use flavor::psp::format_2025::keys::generate_keys_from_seed;
use sha2::{Digest, Sha256, Sha512};

/// The message the non-empty vectors are taken over.
const MESSAGE: &[u8] = b"flavorpack format compatibility vector";

/// RFC 8032 section 7.1 test 1: a published Ed25519 vector.
const RFC8032_SEED: &str = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60";
const RFC8032_PUBLIC_KEY: &str = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a";
const RFC8032_SIGNATURE_EMPTY: &str = concat!(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155",
    "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
);
const SIGNATURE_OVER_MESSAGE: &str = concat!(
    "effffb474d92c63297df3e186e33e1424c78c177146abcfe412c5639bec14ec5",
    "e2b47e8f44c08004279bde19ddd15dd17dd14238b44ca3093b52e8155fe9d80c"
);

/// The seed the committed format fixtures are signed with.
const FIXTURE_KEY_SEED: &str = "flavorpack-format-compat-fixture-v1";
const FIXTURE_PUBLIC_KEY: &str = "00d88e9ee4f0deaf06d28f94e545cdc858dcd8a7371de3ca3e392c0b4263696c";

/// Decode a hex constant into the fixed-size array the crypto APIs want.
fn seed_bytes(hex_seed: &str) -> [u8; 32] {
    hex::decode(hex_seed)
        .expect("valid hex")
        .try_into()
        .expect("32 bytes")
}

#[test]
fn sha256_matches_the_reference_implementation() {
    assert_eq!(
        hex::encode(Sha256::digest(b"")),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha2 changed its SHA-256 output; every slot and index checksum moves with it"
    );
    assert_eq!(
        hex::encode(Sha256::digest(MESSAGE)),
        "02db63cdb4e0191ad5e7c95f26f8a2a91a2e723cfc4cbe38f61740b55274e7d9"
    );
}

#[test]
fn sha512_matches_the_reference_implementation() {
    assert_eq!(
        hex::encode(Sha512::digest(b"")),
        concat!(
            "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce",
            "47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
        ),
        "sha2 changed its SHA-512 output"
    );
    assert_eq!(
        hex::encode(Sha512::digest(MESSAGE)),
        concat!(
            "71151bf184a09a2f0957c9360d64f7356ff60222712377d1cd1b23e9a53f9535",
            "2c749bab390b0968d488edd059a53b2c21402e284421e31e521251e147969db3"
        )
    );
}

#[test]
fn ed25519_public_keys_derive_unchanged() {
    let signing_key = SigningKey::from_bytes(&seed_bytes(RFC8032_SEED));
    assert_eq!(
        hex::encode(signing_key.verifying_key().to_bytes()),
        RFC8032_PUBLIC_KEY,
        "ed25519-dalek derives a different public key from the same seed"
    );
}

#[test]
fn ed25519_signatures_are_byte_identical() {
    // Ed25519 signing is deterministic, so the exact bytes are part of the
    // contract: a package signed before an upgrade has to verify after it.
    let signing_key = SigningKey::from_bytes(&seed_bytes(RFC8032_SEED));

    assert_eq!(
        hex::encode(signing_key.sign(b"").to_bytes()),
        RFC8032_SIGNATURE_EMPTY,
        "ed25519-dalek produces different signature bytes; existing seals will not match"
    );
    assert_eq!(
        hex::encode(signing_key.sign(MESSAGE).to_bytes()),
        SIGNATURE_OVER_MESSAGE
    );
}

#[test]
fn ed25519_verifies_a_signature_it_did_not_produce() {
    // The direction that matters in the field: bytes recorded elsewhere,
    // checked by this build.
    let verifying_key =
        VerifyingKey::from_bytes(&seed_bytes(RFC8032_PUBLIC_KEY)).expect("public key parses");
    let signature = Signature::from_slice(&hex::decode(SIGNATURE_OVER_MESSAGE).expect("valid hex"))
        .expect("signature parses");

    verifying_key
        .verify(MESSAGE, &signature)
        .expect("a signature made elsewhere still verifies here");

    assert!(
        verifying_key.verify(b"tampered", &signature).is_err(),
        "verification accepted a message the signature does not cover"
    );
}

#[test]
fn seed_string_derivation_is_unchanged() {
    // What --key-seed does: SHA-256 the string, use the digest as the Ed25519
    // seed. Every deterministically-built package in the wild depends on this
    // pair of crates producing the same answer they did when it was built.
    let (_, verifying_key) = generate_keys_from_seed(FIXTURE_KEY_SEED);
    assert_eq!(
        hex::encode(verifying_key.to_bytes()),
        FIXTURE_PUBLIC_KEY,
        "--key-seed now derives a different key; deterministic builds are no longer reproducible"
    );
}

#[test]
fn pem_parses_an_spki_public_key_unchanged() {
    // The builders accept SPKI-wrapped Ed25519 keys and slice the raw 32 bytes
    // out at a fixed offset, so any change in what `pem` hands back moves that
    // offset silently.
    let spki = "-----BEGIN PUBLIC KEY-----\n\
                MCowBQYDK2VwAyEA11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo=\n\
                -----END PUBLIC KEY-----\n";

    let parsed = pem::parse(spki).expect("pem parses");
    assert_eq!(parsed.tag(), "PUBLIC KEY");
    assert_eq!(parsed.contents().len(), 44, "SPKI header plus 32 key bytes");
    assert_eq!(
        hex::encode(&parsed.contents()[12..44]),
        RFC8032_PUBLIC_KEY,
        "pem returns different bytes; the fixed SPKI offset in keys.rs no longer lands on the key"
    );
}
