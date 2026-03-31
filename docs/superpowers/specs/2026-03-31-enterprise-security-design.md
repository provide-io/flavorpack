# FlavorPack Enterprise Security Design

**Date:** 2026-03-31
**Status:** Approved for implementation
**Scope:** Trusted key store, full provenance/SBOM, launch-time policy enforcement

---

## Overview

Three coordinated pillars extend FlavorPack's existing Ed25519 signature model into a full
enterprise security story. All changes are backwards-compatible: packages built today continue
to work on launchers that implement this spec, and old launchers ignore the new index fields.

### Pillars

| Pillar | What it adds |
|--------|-------------|
| **1 — Trusted Key Store** | Host-side registry of approved signing keys; launchers refuse (or warn on) packages signed by unknown keys |
| **2 — Full Provenance & SBOM** | CycloneDX 1.6 SBOM + build provenance embedded as an attestation slot; digest bound to index block |
| **3 — Launch-Time Policy** | Builder-declared execution constraints + operator policy overlay; operator can only tighten, never loosen |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PSPF Package (.psp)                                        │
│  ┌─────────────────┐  ┌──────────────────────────────────┐  │
│  │  Index Block    │  │  Slot: lifecycle=attestation     │  │
│  │  (existing)     │  │  - CycloneDX 1.6 SBOM (JSON)     │  │
│  │  + attestation  │  │  - build provenance record       │  │
│  │    sbom_digest  │  │  - signing key fingerprint       │  │
│  │    policy_hash  │  └──────────────────────────────────┘  │
│  │    key_fp       │                                         │
│  └─────────────────┘                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Host (execution environment)                               │
│  /etc/flavor/trusted-keys/*.pub   ← system key trust        │
│  ~/.config/flavor/trusted-keys/   ← per-user key trust      │
│  $FLAVOR_TRUSTED_KEYS_DIR         ← env var override        │
│  /etc/flavor/policy.toml          ← operator policy         │
│  OS trust store (optional tier 2)                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Launcher enforcement sequence                              │
│  1. Verify Ed25519 signature          (existing)            │
│  2. Check key fingerprint vs trust store  [NEW]             │
│  3. Enforce package-declared policy       [NEW]             │
│  4. Apply operator policy overlay         [NEW]             │
│  5. Validate SBOM digest                  [NEW]             │
│  6. Execute                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Format changes

The PSPF index block gains one new optional section, `attestation`, with three fields:

| Field | Type | Description |
|-------|------|-------------|
| `key_fingerprint` | `string` | SHA-256 of the Ed25519 public key, hex-encoded |
| `sbom_digest` | `string` | SHA-256 of the attestation slot content, hex-encoded |
| `policy_hash` | `string` | SHA-256 of the serialised policy declaration, hex-encoded |

One new slot lifecycle value: `attestation`. Treated identically to `init` at extraction time
(extracted on first run, removed from workenv after use). Launchers that do not understand
`attestation` treat it as `init` — safe fallback, no data is stranded in the workenv.

---

## Pillar 1 — Trusted Key Store

### Key store layout

```
/etc/flavor/trusted-keys/     # system-wide; managed by ops/MDM/Ansible
~/.config/flavor/trusted-keys/  # per-user
$FLAVOR_TRUSTED_KEYS_DIR      # override (highest priority)
```

Each file is an Ed25519 public key in PEM format. Files must have a `.pub` extension.
An optional `# Name: <label>` comment line in the file identifies the key owner in CLI output.

### Trust resolution at launch

1. Launcher reads `index.attestation.key_fingerprint` from the package.
2. Launcher loads all `.pub` files from the resolved key store directories (system, then user).
3. If the fingerprint matches any loaded key → trusted.
4. If no key store directories exist → behavior governed by operator policy
   (`require_trusted_key`, default `false` → warn only).
5. If directories exist but no match → behavior governed by `require_trusted_key`
   (default `false` → warn; `true` → hard block).

### OS trust store (Tier 2, opt-in)

Enabled via `/etc/flavor/policy.toml`:

```toml
[trust]
use_os_keychain = true
```

When enabled, the launcher additionally checks the OS certificate store (macOS Keychain,
Windows CertStore, Linux `/etc/ssl`) for a certificate whose public key matches the fingerprint.
Allows MDM-provisioned keys to be trusted without deploying flat files.

### Backwards compatibility

If no trust store directories exist and `require_trusted_key` is not set, behaviour is
identical to today: signature is verified against the key embedded in the package and
execution proceeds. The trust store is purely additive.

| Configuration | Behaviour |
|---|---|
| No trusted-keys dir, no policy | Existing — signature verified against embedded key |
| trusted-keys dir exists, key matches | Trusted — proceed |
| trusted-keys dir exists, no match, `require_trusted_key = false` | Warn, proceed |
| trusted-keys dir exists, no match, `require_trusted_key = true` | Hard block |

### CLI: `flavor trust`

```bash
flavor trust add ./signer.pub --name "CI pipeline"   # add to user store
flavor trust list                                     # show all trusted keys + fingerprints
flavor trust remove <fingerprint>                     # remove from user store
flavor trust verify ./myapp.psp                      # check if package key is trusted
```

---

## Pillar 2 — Full Provenance & SBOM

### Attestation slot

A new slot with `id: "_attestation"`, `lifecycle: attestation`, `target: "_attestation"`,
containing a single JSON file with two top-level keys: `sbom` and `provenance`.

### SBOM (`sbom`)

CycloneDX 1.6 JSON format. Components covered:

- **Python packages**: all packages installed into the slot (name, version, SPDX license
  expression, `pkg:pypi` purl, SHA-256 hash of wheel)
- **Python runtime**: version, implementation, hash of the embedded interpreter binary
- **Launcher binary**: language (go/rust), version, compiler version, SHA-256 hash
- **FlavorPack itself**: builder name, version

### Provenance record (`provenance`)

```json
{
  "builder": "flavor-python",
  "builder_version": "0.3.21",
  "build_timestamp": "2026-03-31T00:00:00Z",
  "source_date_epoch": 1743379200,
  "platform": { "os": "linux", "arch": "amd64" },
  "python": { "version": "3.11.12", "implementation": "cpython" },
  "launcher": {
    "language": "go",
    "version": "1.24.1",
    "hash": "sha256:abc..."
  },
  "signing_key_fingerprint": "sha256:def...",
  "reproducible": true
}
```

### Digest binding

The SHA-256 of the full attestation JSON (canonicalised — keys sorted, no trailing whitespace)
is written into `index.attestation.sbom_digest`. At verification time the launcher re-hashes
the attestation slot content and compares. Tampering with the SBOM is detected identically to
slot tampering today.

Launchers do not parse the SBOM JSON — they only compare the digest. Full SBOM parsing lives
in Python (`flavor inspect`, `flavor verify`).

### CLI: `flavor inspect` additions

```bash
flavor inspect myapp.psp --sbom                  # print CycloneDX JSON to stdout
flavor inspect myapp.psp --sbom-format spdx      # convert to SPDX 2.3 on output
flavor inspect myapp.psp --provenance            # print provenance record
flavor inspect myapp.psp --sbom > sbom.json      # pipe for submission to dependency scanners
```

### `pyproject.toml` opt-out

SBOM generation is on by default. To disable (e.g., for development builds):

```toml
[tool.flavor]
sbom = false
```

---

## Pillar 3 — Launch-Time Policy

### Package-declared constraints (`pyproject.toml`)

```toml
[tool.flavor.policy]
platforms = ["linux_amd64", "linux_arm64", "darwin_arm64"]
min_os_version = { linux = "4.15", macos = "12.0", windows = "10" }
refuse_root = true
max_age_days = 365
require_env = ["MYAPP_LICENSE_KEY"]
```

Embedded in package metadata at build time. Enforced by the launcher before execution.
These are a **floor** — operator policy can tighten them but not loosen them.

### Operator policy overlay (`/etc/flavor/policy.toml`)

```toml
[trust]
require_trusted_key = true
use_os_keychain = false

[execution]
refuse_root = true
max_age_days = 90
allow_platforms = ["linux_amd64", "linux_arm64"]

[attestation]
require_sbom = true     # block packages built without attestation slot
```

Operator policy is evaluated after package-declared constraints. For each constraint,
the **stricter** of the two values wins. A package declaring `refuse_root = false` (or not
declaring it) can still be blocked by operator policy setting `refuse_root = true`. The
reverse is not possible.

### Enforcement order

1. Platform check (package platforms list ∩ operator allow_platforms)
2. OS version check
3. Root check (refuse_root)
4. Age check (max_age_days computed from `provenance.build_timestamp`)
5. Environment variable presence check
6. Trust key check (Pillar 1)
7. SBOM digest check (Pillar 2, if `require_sbom = true`)

First failure stops evaluation and exits with a descriptive error.

### Error messages

```
❌ Platform not permitted: darwin_arm64 not in package policy [linux_amd64, linux_arm64]
❌ Refused to run as root (declared by package)
❌ Package is 400 days old — operator policy requires max 90 days
❌ Required environment variable not set: MYAPP_LICENSE_KEY
❌ Signing key not in trusted store: sha256:abc...
❌ Package built without attestation slot — operator policy requires SBOM
```

### CLI: `flavor policy`

```bash
flavor policy show                  # print effective policy (package + operator merged)
flavor policy check ./myapp.psp     # dry-run: would this package be allowed on this host?
flavor policy init                  # scaffold /etc/flavor/policy.toml with comments
```

---

## Implementation scope

### Python (`src/flavor/`)

- SBOM generation: new `psp/format_2025/sbom.py` using `cyclonedx-python-lib`
- Provenance record assembly: extend `metadata/assembly.py`
- Attestation slot creation: extend `pspf_builder.py`
- Policy declaration: extend `spec.py` and `pyproject.toml` parsing
- `flavor trust` subcommands: new `cli/trust.py`
- `flavor policy` subcommands: new `cli/policy.py`
- `flavor inspect --sbom / --provenance`: extend existing inspect command

### Go (`src/flavor-go/`)

- Trusted key store loading and fingerprint matching
- Attestation index fields: extend `metadata.go`
- Policy enforcement: new `execution_policy.go`
- SBOM digest verification: extend `reader_verify.go`

### Rust (`src/flavor-rs/`)

- Mirror Go changes: trusted key loading, policy enforcement, digest verification
- New `src/psp/format_2025/policy.rs`

### Format

- `attestation` section in index block (Python writes, Go + Rust read)
- `attestation` slot lifecycle value (all three languages)
- No format version bump required — all new fields are optional; old launchers skip them

### Dependencies

| Language | New dependency | Purpose |
|----------|---------------|---------|
| Python | `cyclonedx-python-lib` | CycloneDX SBOM generation |
| Python | `spdx-tools` (optional) | SPDX output conversion |
| Go | none | Digest check only, no JSON parsing |
| Rust | none | Digest check only, no JSON parsing |

---

## Testing

- Unit tests for SBOM generation (Python): verify CycloneDX schema validity
- Unit tests for policy merging: package + operator combinations, stricter-wins logic
- Unit tests for trust store loading: flat files, missing dirs, fingerprint matching
- Parity tests (`tests/parity/`): new category "Policy Enforcement" — Python/Go/Rust all
  enforce the same constraints
- Integration tests: end-to-end pack → verify → execute with trust store and policy config
- Security tests: policy bypass attempts (root check, age check, platform check)

---

## Non-goals

- Package registry or distribution infrastructure
- Key revocation lists (CRL/OCSP) — out of scope for this iteration
- Runtime sandboxing (seccomp, AppArmor, namespaces) — separate concern
- Windows ARM64 PE reconstruction — pre-existing known gap, unchanged
