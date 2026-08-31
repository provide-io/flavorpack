# Format-compatibility fixtures

Packages built by one toolchain, committed, and verified by every toolchain that
comes after.

## Why they exist

Every other test in this repository builds a package and verifies it in the same
run, with the same code on both sides. That proves the implementation is
self-consistent. It cannot prove the *format* is stable, because when signing,
hashing, or layout changes, both sides move together and the test still passes.

The failure that hides in that gap is the expensive one: a package built and
shipped last quarter stops verifying after a dependency bump, and nothing catches
it until a user's install fails.

These fixtures close it. They were built once, by the toolchain named in
`expected.json`, and are never rebuilt. Any later change that breaks
backward compatibility — a new signature encoding, a different digest, a moved
field — fails these tests instead of a customer.

## What is pinned

`expected.json` records, per fixture:

| Field | Catches |
|---|---|
| `sha256`, `size` | accidental regeneration, which would void the guarantee |
| `public_key` | drift in seed → Ed25519 key derivation |
| `key_fingerprint` | drift in SHA-256 over the signing key |
| `slot_count` | slot table layout changes |

All three producers derive the same key from `key_seed`, so a single
`public_key` value across the fixtures is itself a cross-implementation
assertion.

## Who reads them

| Test | Path |
|---|---|
| Python | `tests/format_2025/test_format_compat.py` |
| Rust | `src/flavor-rs/tests/format_compat.rs` |
| Go | `src/flavor-go/pkg/psp/format_2025/format_compat_test.go` |

Each verifies every fixture, so the matrix is three producers × three consumers.

## What is inside one

A 125-byte payload slot and a 500-byte shell script standing in for the launcher.
Verification measures the launcher and covers its bytes but never runs it, so a
stub keeps each fixture in the 10–40 KB range instead of the tens of megabytes a
real launcher would add.

## Regenerating

Don't, in the ordinary case. Rebuilding a generation replaces a cross-version
guarantee with a tautology, which is why the generator refuses without `--force`.

When the format changes in a way the old fixtures genuinely cannot express, add a
generation rather than overwriting one:

```bash
mkdir -p tests/fixtures/format_compat/v2/inputs
cp tests/fixtures/format_compat/v1/inputs/* tests/fixtures/format_compat/v2/inputs/
python scripts/gen_format_fixtures.py --generation v2
```

Keep `v1` and keep reading it. An old generation that still verifies is the whole
point; one that no longer can is a deliberate, reviewable break.
