# FEP-0003: PSPF/2025 Security Attestation Extension

**Status**: Standards Track
**Type**: Extension Protocol
**Created**: 2026-03-31
**Version**: v0.1
**Requires**: FEP-0001, FEP-0002

## Abstract

This document specifies the Security Attestation Extension to the Progressive Secure Package Format (PSPF/2025). It introduces a new slot lifecycle value (`attestation = 11`), a structured attestation index section within the FEP-0001 reserved region, a trusted key store with configurable enforcement, and an operator policy overlay mechanism. All additions are backwards-compatible: launchers that do not implement this extension treat the new index fields as reserved (zero-filled) and skip slots with unrecognised lifecycle values per FEP-0001 §6.1.

The format version `0x20250001` is unchanged. No format version bump is required.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Conventions and Terminology](#2-conventions-and-terminology)
3. [Attestation Lifecycle Value](#3-attestation-lifecycle-value)
4. [Index Block Attestation Section](#4-index-block-attestation-section)
5. [Attestation Slot Contents](#5-attestation-slot-contents)
6. [Trusted Key Store](#6-trusted-key-store)
7. [Operator Policy](#7-operator-policy)
8. [Package-Declared Policy](#8-package-declared-policy)
9. [Launch Sequence](#9-launch-sequence)
10. [flavor init Command](#10-flavor-init-command)
11. [Backwards Compatibility](#11-backwards-compatibility)
12. [Non-Goals](#12-non-goals)
13. [Security Considerations](#13-security-considerations)
14. [References](#14-references)

## 1. Introduction

### 1.1 Motivation

PSPF/2025 (FEP-0001) provides Ed25519 signature verification over package content. This is necessary but not sufficient for enterprise and regulated environments, which require:

- **Supply chain transparency**: Consumers must be able to inspect what Python packages, runtimes, and tools went into a build (Software Bill of Materials).
- **Build provenance**: Auditors need a verifiable record of when, where, and with what toolchain a package was assembled.
- **Key governance**: Organisations need to restrict execution to packages signed by approved keys, independently of the package author's own key management.
- **Declarative policy**: Package authors need to express constraints (target platforms, root execution refusal, environment prerequisites) that launchers enforce at startup.

This extension provides all four capabilities as an opt-in, backwards-compatible layer on top of the stable FEP-0001/FEP-0002 base.

### 1.2 Scope

This specification defines:
- The `attestation` lifecycle value (11) and its slot structure
- Three attestation fields within the FEP-0001 reserved index region
- CycloneDX 1.6 SBOM embedding and provenance record schema
- Trusted key store directory layout, resolution order, and enforcement modes
- Operator policy file format (`policy.toml`) and precedence rules
- Package-declared policy fields in `pyproject.toml`
- The enforced launch sequence for compliant launchers
- The `flavor init` command for bootstrapping host configuration

### 1.3 Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119] [RFC8174] when, and only when, they appear in all capitals, as shown here.

### 1.4 Relationship to Other FEPs

- **FEP-0001**: Defines the binary format, index block structure, lifecycle values, and signature verification. This document extends FEP-0001 §4 (index block) and §5 (slot lifecycle table).
- **FEP-0002**: Defines the JSON metadata schema. Provenance records defined here are standalone JSON objects within the attestation slot; they do not extend the FEP-0002 manifest schema.

## 2. Conventions and Terminology

**Attestation slot**: A slot with lifecycle value 11, containing SBOM and provenance data.
**Key fingerprint**: SHA-256 of the raw 32-byte Ed25519 public key, encoded as 64 lowercase hex ASCII characters.
**Operator policy**: Host-level TOML configuration that may tighten package-declared constraints.
**Package-declared policy**: Constraints expressed by the package author in `pyproject.toml`.
**SBOM**: Software Bill of Materials — a structured inventory of software components.
**Trusted key store**: A host-managed directory of approved Ed25519 public keys.

## 3. Attestation Lifecycle Value

FEP-0001 §5 defines the lifecycle value table for slots. This extension adds one new value:

| Value | Name | Description |
|---|---|---|
| 11 | `attestation` | Security attestation slot containing SBOM and build provenance |

A launcher that does not recognise lifecycle value 11 MUST treat the slot as `init` (extracted on first run, removed after execution) per FEP-0001 §6.1. This ensures old launchers handle attestation slots gracefully without error.

The slot identifier for the attestation slot is `"_attestation"` and its target path is `"_attestation"`. A package MUST NOT contain more than one slot with lifecycle value 11.

## 4. Index Block Attestation Section

The FEP-0001 index block contains a 6816-byte reserved region (see FEP-0001 §4.3). The first 192 bytes of this region are now defined as the **attestation section**:

| Offset within reserved | Size | Field | Description |
|---|---|---|---|
| 0 | 64 bytes | `key_fingerprint` | SHA-256 of the Ed25519 public key (raw 32 bytes), hex-encoded ASCII |
| 64 | 64 bytes | `sbom_digest` | SHA-256 of the attestation slot content (canonical JSON), hex-encoded ASCII |
| 128 | 64 bytes | `policy_hash` | SHA-256 of the package-declared policy JSON (canonical form), hex-encoded ASCII |

All three fields are optional. A zero-filled field (all 64 bytes are `0x00`) indicates that the field is absent. A launcher implementing this extension MUST skip the associated check for any absent field.

The remaining 6624 bytes of the reserved region (offsets 192–6815) remain reserved and MUST be zero-filled by compliant builders.

### 4.1 Field Encoding

All three digest fields are encoded as lowercase hexadecimal ASCII. Builders MUST NOT use uppercase hex. Parsers SHOULD accept both cases for robustness but MUST emit lowercase.

### 4.2 Builder Requirements

A builder implementing this extension MUST:
1. Compute `key_fingerprint` as `SHA-256(raw_ed25519_public_key_bytes)`, hex-encoded.
2. Compute `sbom_digest` as `SHA-256(attestation_slot_content_bytes)` after serialising the attestation slot content to canonical JSON (RFC 8785 or equivalent: sorted keys, no insignificant whitespace).
3. Compute `policy_hash` as `SHA-256(canonical_policy_json_bytes)` where the policy JSON is derived from the `[tool.flavor.policy]` section of `pyproject.toml`, serialised to canonical JSON.
4. Write all three fields into the attestation section before computing the Ed25519 signature, so the signature covers the attestation fields.

## 5. Attestation Slot Contents

The attestation slot contains a single JSON file. The top-level object has two keys:

```json
{
  "sbom": { ... },
  "provenance": { ... }
}
```

Either key MAY be absent (but not both — an empty attestation slot SHOULD NOT be created). If `sbom` is absent, the `sbom_digest` index field MUST be zero-filled.

### 5.1 SBOM Format

The `sbom` value MUST be a valid CycloneDX 1.6 JSON object. The `components` array SHOULD include:
- All Python packages installed into the package (name, version, PURL)
- The Python runtime (version, implementation)
- The launcher binary (language, version, content hash)
- The FlavorPack builder (version, content hash)

Builders MAY include additional components. Consumers MUST NOT reject attestation slots that contain components beyond this list.

If `[tool.flavor] sbom = false` is set in `pyproject.toml`, the builder MUST omit the `sbom` key and MUST zero-fill `sbom_digest` in the index.

### 5.2 Provenance Record

The `provenance` value MUST be a JSON object conforming to the following schema:

```json
{
  "builder": "flavor-python",
  "builder_version": "0.3.21",
  "build_timestamp": "2026-03-31T00:00:00Z",
  "source_date_epoch": 1743379200,
  "platform": {
    "os": "linux",
    "arch": "amd64"
  },
  "python": {
    "version": "3.11.12",
    "implementation": "cpython"
  },
  "launcher": {
    "language": "go",
    "version": "1.24.1",
    "hash": "sha256:..."
  },
  "signing_key_fingerprint": "sha256:...",
  "reproducible": true
}
```

Field semantics:

| Field | Type | Required | Description |
|---|---|---|---|
| `builder` | string | REQUIRED | Identifies the builder implementation (e.g. `"flavor-python"`) |
| `builder_version` | string | REQUIRED | SemVer of the builder |
| `build_timestamp` | string | REQUIRED | ISO 8601 UTC timestamp of build completion |
| `source_date_epoch` | integer | RECOMMENDED | Unix timestamp for reproducible builds; used as `SOURCE_DATE_EPOCH` |
| `platform` | object | REQUIRED | `os` and `arch` of the build host |
| `python` | object | REQUIRED | `version` (string) and `implementation` (string) of the embedded Python |
| `launcher` | object | REQUIRED | `language`, `version`, and `hash` (prefixed with `sha256:`) of the embedded launcher |
| `signing_key_fingerprint` | string | REQUIRED | `sha256:` prefixed hex fingerprint of the Ed25519 signing key |
| `reproducible` | boolean | RECOMMENDED | `true` if the build used `SOURCE_DATE_EPOCH` and deterministic settings |

The `signing_key_fingerprint` in the provenance record MUST match the `key_fingerprint` field in the index attestation section (§4), without the `sha256:` prefix. A launcher MUST verify this consistency and MUST reject a package where they differ.

## 6. Trusted Key Store

A **trusted key store** is a host-managed directory containing approved Ed25519 public keys. Launchers implementing this extension MUST support the following resolution order for the user-level store:

1. Directory named by `FLAVOR_TRUSTED_KEYS_DIR` environment variable (if set and non-empty)
2. `$FLAVOR_CONFIG_DIR/trusted-keys/` if `FLAVOR_CONFIG_DIR` is set and non-empty
3. `$XDG_CONFIG_HOME/flavor/trusted-keys/` if `XDG_CONFIG_HOME` is set and non-empty
4. `~/.config/flavor/trusted-keys/` (XDG default)

The system-wide store is always `/etc/flavor/trusted-keys/`. Both stores are consulted; a key present in either is considered trusted.

### 6.1 Key File Format

Each file in a trusted-keys directory MUST have the `.pub` extension. The file content MUST be an Ed25519 public key in PEM SubjectPublicKeyInfo format. An optional comment line beginning with `# Name:` MAY appear before the PEM block to provide a human-readable label for the key.

Example:
```
# Name: release-signing-key-2026
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA...
-----END PUBLIC KEY-----
```

### 6.2 Key Fingerprint Computation

The fingerprint of a key is computed as:
```
fingerprint = hex(SHA-256(raw_ed25519_public_key_bytes))
```

where `raw_ed25519_public_key_bytes` is the 32-byte raw key material extracted from the SubjectPublicKeyInfo structure, not the full DER encoding.

### 6.3 Enforcement at Launch

| State | Behaviour |
|---|---|
| No trusted-keys directory exists and no policy requiring trusted key | Signature verified against embedded key; execution proceeds |
| Package key fingerprint matches a key in the store | Trusted — proceed |
| Package key not in store; `require_trusted_key = false` | SHOULD emit a warning to stderr; proceed |
| Package key not in store; `require_trusted_key = true` | MUST hard block; exit with non-zero status and descriptive error |

Launchers MUST NOT proceed past key store checks if the Ed25519 signature (FEP-0001 §7) has already failed verification.

## 7. Operator Policy

An operator policy file named `policy.toml` configures enforcement at the host level. Two locations are consulted:

- **System policy**: `/etc/flavor/policy.toml` (Linux/macOS) or `%ProgramData%\flavor\policy.toml` (Windows)
- **User policy**: resolved using the same precedence order as the trusted key store (§6), substituting `policy.toml` for the `trusted-keys/` directory

If both files exist, their fields are merged. For every field, the **stricter** value wins. Operator policy can only tighten package-declared constraints (§8), never loosen them.

### 7.1 Policy File Schema

```toml
[trust]
require_trusted_key = false   # true = hard block if signing key not in trusted store
use_os_keychain = false       # true = also accept keys from the OS certificate store

[execution]
refuse_root = false           # true = block if process is running as root/Administrator
# max_age_days = 365          # maximum permitted age (days) from build_timestamp
# allow_platforms = ["linux_amd64", "linux_arm64"]  # restrict to these platforms

[attestation]
require_sbom = false          # true = block packages that have no attestation slot
```

### 7.2 Field Semantics

| Section | Field | Type | Default | Description |
|---|---|---|---|---|
| `[trust]` | `require_trusted_key` | boolean | `false` | Hard-block packages whose signing key is not in the trusted store |
| `[trust]` | `use_os_keychain` | boolean | `false` | Treat OS certificate store keys as trusted |
| `[execution]` | `refuse_root` | boolean | `false` | Block execution when the effective UID is 0 (or Administrator on Windows) |
| `[execution]` | `max_age_days` | integer | absent | Block packages older than this many days relative to `build_timestamp` |
| `[execution]` | `allow_platforms` | string array | absent | Block packages built for platforms not in this list |
| `[attestation]` | `require_sbom` | boolean | `false` | Block packages with no attestation slot or absent `sbom` key |

Absent fields imply no additional constraint from the operator. A launcher MUST treat a missing `policy.toml` identically to a file containing only default values.

## 8. Package-Declared Policy

Package authors MAY declare execution constraints in `pyproject.toml` under `[tool.flavor.policy]`. These constraints are embedded in the package metadata (FEP-0002) at build time and enforced by the launcher before operator policy is applied.

```toml
[tool.flavor.policy]
platforms = ["linux_amd64", "linux_arm64", "darwin_arm64"]
refuse_root = true
max_age_days = 365
require_env = ["MYAPP_LICENSE_KEY"]
```

| Field | Type | Description |
|---|---|---|
| `platforms` | string array | List of target platform identifiers the package is permitted to run on |
| `refuse_root` | boolean | If `true`, the launcher MUST refuse to execute as root/Administrator |
| `max_age_days` | integer | If set, the launcher MUST refuse if `now - build_timestamp > max_age_days` |
| `require_env` | string array | List of environment variable names that MUST be present and non-empty at launch |

A launcher MUST enforce package-declared policy before applying operator policy. When both define the same constraint (e.g. `refuse_root`), the stricter value — i.e. `true` over `false`, smaller `max_age_days` — applies.

## 9. Launch Sequence

A launcher implementing this extension MUST enforce the following steps in order. The first failure MUST cause the launcher to exit with a non-zero status and a human-readable diagnostic message. The launcher MUST NOT proceed to a subsequent step if an earlier step fails.

1. **Signature verification** (FEP-0001 §7): Verify the Ed25519 signature over the entire package content. Reject if invalid.
2. **Attestation consistency** (§5.2): If `key_fingerprint` in the index is non-zero and an attestation slot is present, verify that `provenance.signing_key_fingerprint` (stripped of `sha256:` prefix) matches the index field. Reject if they differ.
3. **Key store check** (§6.3): If a trusted-keys directory exists or `require_trusted_key = true` (from either policy source), check the package's signing key fingerprint against the store. Apply enforcement per §6.3.
4. **Package-declared policy** (§8): Evaluate all constraints declared in the package metadata.
5. **Operator policy overlay** (§7): Evaluate operator policy fields, applying the stricter value for any field also declared by the package.
6. **SBOM digest verification** (§4): If `sbom_digest` in the index is non-zero, re-serialise the attestation slot content to canonical JSON, compute `SHA-256`, and compare to `sbom_digest`. Reject if they differ.
7. **Execute**: Proceed with normal FEP-0001 extraction and execution.

## 10. `flavor init` Command

The `flavor` CLI MUST provide an `init` subcommand:

```
flavor init [--global]
```

This command is idempotent. It MUST:
1. Create the trusted-keys directory (user-level by default; system-level with `--global`) if it does not exist.
2. Create a commented-out `policy.toml` scaffold in the same config directory, explaining all available fields, if the file does not already exist.
3. Print the paths of the created or pre-existing directories/files.
4. Exit with status 0.

`--global` targets `/etc/flavor/` on Linux/macOS and `%ProgramData%\flavor\` on Windows. On systems where the process lacks write permission to the system directory, the command MUST fail with a clear error message rather than silently falling back to the user directory.

## 11. Backwards Compatibility

### 11.1 Old launchers reading new packages

Packages built with FEP-0003 support set the three attestation index fields within the FEP-0001 reserved region. Old launchers that predate this extension read the reserved region as all-zeros per FEP-0001 §4.3 and ignore it. They encounter lifecycle value 11 for the attestation slot, treat it as an unknown lifecycle, and handle it as `init` per FEP-0001 §6.1: extract on first run, remove after execution. This is benign — the attestation JSON file is extracted and then cleaned up.

### 11.2 New launchers reading old packages

Packages built without FEP-0003 support have zero-filled attestation index fields and no attestation slot. A launcher implementing this extension MUST handle this gracefully:
- Zero-filled `key_fingerprint`, `sbom_digest`, and `policy_hash` fields MUST be treated as absent; no associated checks are performed.
- Absence of an attestation slot is not an error unless `require_sbom = true` in operator policy (§7.2), in which case the launcher MUST block with a descriptive message.

## 12. Non-Goals

The following are explicitly out of scope for this extension:

- **Key revocation lists**: This extension provides no mechanism for revoking previously trusted keys. Key revocation is an operational concern handled by removing keys from the trusted key store.
- **Runtime sandboxing**: This extension does not restrict what system calls or resources an executing package may access. Operating system sandboxing mechanisms (seccomp, AppArmor, containers) are outside scope.
- **Windows ARM64 PE reconstruction**: Attestation slot handling on the Windows ARM64 platform follows the same logic as all other platforms. Known issues with the Windows ARM64 launcher binary (see FEP-0001) are not addressed here.
- **Network-based key or policy fetching**: All key and policy data is sourced from local filesystem paths only.
- **SBOM vulnerability scanning**: This extension embeds an SBOM; it does not perform CVE matching or vulnerability assessment.

## 13. Security Considerations

### 13.1 Key Store Bypass Attacks

An attacker who can write to the trusted-keys directory can add an arbitrary key and thereby mark any self-signed package as trusted. Operators MUST ensure the trusted-keys directories are owned by root (or an appropriate privileged account) and not world-writable. The `flavor init --global` command creates `/etc/flavor/trusted-keys/` with mode `0755`; operators SHOULD further restrict this to `0750` or `0700` in high-security environments.

The `FLAVOR_TRUSTED_KEYS_DIR` environment variable allows a user-level override of the trusted-keys path. A privileged process that inherits an attacker-controlled environment may be directed to a malicious key store. Launchers running with elevated privileges SHOULD ignore user-level environment overrides (i.e. MUST use only the system store when running as root or Administrator and `refuse_root = false` is in effect).

### 13.2 Policy Downgrade Attacks

The package-declared policy is embedded in the signed FEP-0002 metadata; tampering with it invalidates the Ed25519 signature (step 1 of the launch sequence, §9). The `policy_hash` index field provides an additional integrity check over the policy JSON. Launchers MUST verify the signature before evaluating policy fields, and MUST verify `policy_hash` consistency if it is non-zero.

Operator policy cannot be protected by the package signature since it is host-controlled. An attacker with write access to `/etc/flavor/policy.toml` can loosen operator constraints. This is intentional — operators are trusted by definition — but access to system policy files MUST be restricted to privileged accounts.

### 13.3 SBOM Tampering

The `sbom_digest` index field binds the attestation slot content to the signed index block. An attacker who modifies the attestation slot content without updating the signature will cause the Ed25519 check (step 1, §9) to fail. An attacker who replaces the entire attestation slot and re-signs with a different key will be caught by the key store check (step 3) if the new key is not trusted.

The `sbom_digest` check (step 6 of §9) provides defence-in-depth: even if the index block is somehow forged, the SBOM content is independently verified against the digest committed in the index.

Consumers relying on SBOM data for compliance purposes SHOULD verify the full Ed25519 signature independently before processing the SBOM, and SHOULD record the `signing_key_fingerprint` alongside any compliance artefacts.

## 14. References

- [RFC2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997. <https://www.rfc-editor.org/rfc/rfc2119>
- [RFC8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017. <https://www.rfc-editor.org/rfc/rfc8174>
- [RFC8785] Rundgren, A., Jordan, B., Erdtman, S., "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020. <https://www.rfc-editor.org/rfc/rfc8785>
- [CycloneDX16] OWASP Foundation, "CycloneDX Specification v1.6", 2024. <https://cyclonedx.org/specification/overview/>
- [FEP-0001] FlavorPack Engineering Proposal 0001, "Progressive Secure Package Format (PSPF/2025) - Core Specification".
- [FEP-0002] FlavorPack Engineering Proposal 0002, "PSPF/2025 JSON Metadata Format Specification".
- [XDG-BASEDIR] freedesktop.org, "XDG Base Directory Specification". <https://specifications.freedesktop.org/basedir-spec/latest/>
