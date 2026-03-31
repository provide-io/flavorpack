# Enterprise Security — Plan 2: Trusted Key Store

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the trusted key store (Pillar 1): flat-file `.pub` key registry under XDG config dirs, `flavor trust` CLI subcommands, and launcher-side fingerprint verification in Go and Rust.

**Architecture:** Python writes the key fingerprint into `index.attestation_key_fp` at build time. At launch, Go/Rust launchers load `.pub` files from the resolved trusted-keys directory, compute fingerprints, and compare. Behaviour when no store exists is unchanged (backwards compatible). Operator policy via `require_trusted_key` controls warn vs. hard-block.

**Tech Stack:** Python 3.11+, click, cryptography (Ed25519), Go 1.26, Rust 1.86, `cyclonedx-python-lib` (Plan 3 — not needed here).

**Prerequisite:** Plan 1 complete (provides `get_config_dir()`, `get_trusted_keys_dir()`, attestation index fields).

**Spec:** `docs/superpowers/specs/2026-03-31-enterprise-security-design.md` § Pillar 1

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/flavor/config/trust.py` | Key loading, fingerprint compute/match, trust resolution |
| Create | `src/flavor/commands/trust.py` | `flavor trust` CLI group (add/list/remove/verify) |
| Modify | `src/flavor/cli.py` | Register `trust` command group |
| Modify | `src/flavor/psp/format_2025/pspf_builder.py` | Write key fingerprint into `attestation_key_fp` |
| Create | `src/flavor-go/pkg/psp/format_2025/trust.go` | Go trust store loader and fingerprint checker |
| Modify | `src/flavor-go/pkg/psp/format_2025/execution.go` | Call trust check before execution |
| Create | `src/flavor-rs/src/psp/format_2025/trust.rs` | Rust trust store loader and fingerprint checker |
| Modify | `src/flavor-rs/src/psp/format_2025/mod.rs` | Declare `trust` module |
| Modify | `src/flavor-rs/src/main.rs` (or launcher entry) | Call trust check before execution |
| Create | `tests/config/test_trust.py` | Unit tests for trust store loading and fingerprint |
| Create | `tests/cli/test_trust_command.py` | Unit tests for `flavor trust` subcommands |
| Create | `tests/parity/test_trust_parity.py` | Parity tests for trust resolution logic |

---

## Task 1: Python trust store — key loading and fingerprint

**Files:**
- Create: `src/flavor/config/trust.py`
- Test: `tests/config/test_trust.py`

Ed25519 public key fingerprint = SHA-256 of the raw 32-byte key material, hex-encoded (64 ASCII chars).

- [ ] **Step 1: Write the failing tests**

```python
# tests/config/test_trust.py
"""Tests for the trusted key store."""

import os
from pathlib import Path
from unittest import mock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from flavor.config.trust import (
    compute_key_fingerprint,
    load_trusted_keys,
    is_key_trusted,
)


def _make_pub_key_pem(tmp_path: Path, name: str | None = None) -> tuple[Path, str]:
    """Generate an Ed25519 key, write .pub PEM, return (path, fingerprint)."""
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PublicFormat,
    )
    import hashlib

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    fingerprint = hashlib.sha256(raw).hexdigest()

    label = f"# Name: {name}\n" if name else ""
    content = label.encode() + pub_bytes
    pub_file = tmp_path / f"{fingerprint[:8]}.pub"
    pub_file.write_bytes(content)
    return pub_file, fingerprint


def test_compute_key_fingerprint() -> None:
    """Fingerprint is SHA-256 of raw 32-byte Ed25519 public key, hex-encoded."""
    import hashlib
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    expected = hashlib.sha256(raw).hexdigest()
    assert compute_key_fingerprint(public_key) == expected


def test_load_trusted_keys_empty_dir(tmp_path: Path) -> None:
    """Empty trusted-keys directory returns empty dict."""
    (tmp_path / "trusted-keys").mkdir()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(tmp_path / "trusted-keys")}):
        keys = load_trusted_keys()
    assert keys == {}


def test_load_trusted_keys_reads_pub_files(tmp_path: Path) -> None:
    """Each .pub file contributes one entry keyed by fingerprint."""
    keys_dir = tmp_path / "trusted-keys"
    keys_dir.mkdir()
    _make_pub_key_pem(keys_dir, "CI pipeline")
    _make_pub_key_pem(keys_dir, "Release signing")
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(keys_dir)}):
        keys = load_trusted_keys()
    assert len(keys) == 2


def test_load_trusted_keys_missing_dir_returns_empty() -> None:
    """Missing trusted-keys directory returns empty dict (no error)."""
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": "/nonexistent/path"}):
        keys = load_trusted_keys()
    assert keys == {}


def test_is_key_trusted_match(tmp_path: Path) -> None:
    """is_key_trusted returns True when fingerprint matches a loaded key."""
    keys_dir = tmp_path / "trusted-keys"
    keys_dir.mkdir()
    _, fingerprint = _make_pub_key_pem(keys_dir)
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(keys_dir)}):
        assert is_key_trusted(fingerprint) is True


def test_is_key_trusted_no_match(tmp_path: Path) -> None:
    """is_key_trusted returns False when fingerprint is not in the store."""
    keys_dir = tmp_path / "trusted-keys"
    keys_dir.mkdir()
    _make_pub_key_pem(keys_dir)
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(keys_dir)}):
        assert is_key_trusted("deadbeef" * 8) is False


def test_is_key_trusted_no_store_returns_none() -> None:
    """is_key_trusted returns None when no key store exists (no-op mode)."""
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": "/nonexistent/path"}):
        assert is_key_trusted("anyfingerprint") is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/config/test_trust.py -v
```
Expected: ImportError

- [ ] **Step 3: Create `src/flavor/config/trust.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Trusted key store for FlavorPack package signature verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)

from flavor.config.dirs import get_system_config_dir, get_trusted_keys_dir
from flavor.console import get_command_logger

log = get_command_logger("config.trust")


def compute_key_fingerprint(public_key: Ed25519PublicKey) -> str:
    """Return the SHA-256 fingerprint of an Ed25519 public key.

    The fingerprint is SHA-256 of the raw 32-byte key material, hex-encoded
    (64 ASCII characters, lowercase).
    """
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def _load_keys_from_dir(keys_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all .pub files from a directory.

    Returns:
        Mapping of fingerprint → {"name": str | None, "path": Path, "key": Ed25519PublicKey}
    """
    if not keys_dir.is_dir():
        return {}

    result: dict[str, dict[str, Any]] = {}
    for pub_file in sorted(keys_dir.glob("*.pub")):
        try:
            content = pub_file.read_bytes()
            name: str | None = None

            # Extract optional "# Name: <label>" comment
            lines = content.decode("utf-8", errors="replace").splitlines()
            pem_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("# Name:"):
                    name = stripped[len("# Name:"):].strip()
                else:
                    pem_lines.append(line)
            pem_content = "\n".join(pem_lines).encode()

            key = load_pem_public_key(pem_content)
            if not isinstance(key, Ed25519PublicKey):
                log.warning("Skipping non-Ed25519 key", path=str(pub_file))
                continue

            fingerprint = compute_key_fingerprint(key)
            result[fingerprint] = {"name": name, "path": pub_file, "key": key}
            log.trace("Loaded trusted key", fingerprint=fingerprint[:16], name=name)
        except Exception as exc:
            log.warning("Failed to load key file", path=str(pub_file), error=str(exc))

    return result


def load_trusted_keys(*, include_system: bool = True) -> dict[str, dict[str, Any]]:
    """Load all trusted keys from user and (optionally) system stores.

    Returns:
        Mapping of fingerprint → {"name", "path", "key"}.
        Empty dict if no store directories exist.
    """
    keys: dict[str, dict[str, Any]] = {}

    if include_system:
        system_keys_dir = get_system_config_dir() / "trusted-keys"
        keys.update(_load_keys_from_dir(system_keys_dir))

    user_keys_dir = get_trusted_keys_dir(system=False)
    keys.update(_load_keys_from_dir(user_keys_dir))

    return keys


def is_key_trusted(fingerprint: str, *, include_system: bool = True) -> bool | None:
    """Check whether a key fingerprint is in the trusted store.

    Returns:
        True  — fingerprint found in store
        False — store exists but fingerprint not found
        None  — no store directories exist (no-op / backwards-compat mode)
    """
    user_keys_dir = get_trusted_keys_dir(system=False)
    system_keys_dir = get_system_config_dir() / "trusted-keys"

    store_exists = user_keys_dir.is_dir() or (include_system and system_keys_dir.is_dir())
    if not store_exists:
        return None

    keys = load_trusted_keys(include_system=include_system)
    return fingerprint in keys


# 🌶️📦🔚
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/config/test_trust.py -v
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add src/flavor/config/trust.py tests/config/test_trust.py
git commit -m "feat(trust): add trusted key store loader and fingerprint computation"
```

---

## Task 2: Write key fingerprint at build time

**Files:**
- Modify: `src/flavor/psp/format_2025/pspf_builder.py`

At build time, the builder already has access to the Ed25519 public key (it's written into `index.public_key`). We extract the fingerprint and also write it into `index.attestation_key_fp`.

- [ ] **Step 1: Write a test that the fingerprint is present after building**

```python
# tests/format_2025/test_key_fingerprint_in_index.py
"""Tests that the builder writes key fingerprint into the index attestation field."""

import hashlib
from pathlib import Path

import pytest

from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.reader import PSPFReader
from flavor.config.trust import compute_key_fingerprint


@pytest.mark.integration
def test_built_package_has_key_fingerprint(built_package_path: Path) -> None:
    """A signed package has a non-empty key fingerprint in attestation_key_fp."""
    with PSPFReader(built_package_path) as reader:
        index = reader.read_index()

    assert index.attestation_key_fp != b"\x00" * 64
    # Should be 64 hex chars (SHA-256)
    fp = index.attestation_key_fp.rstrip(b"\x00").decode("ascii")
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)
```

Note: `built_package_path` is a fixture from the integration test conftest that builds a minimal package. If that fixture doesn't exist yet, skip this test with `@pytest.mark.skip(reason="requires integration fixture")` and add it when integration tests exist.

- [ ] **Step 2: Find where the index is finalised in `pspf_builder.py`**

```bash
grep -n "public_key\|index\." src/flavor/psp/format_2025/pspf_builder.py | head -40
```

Identify the line where `index.public_key` is set (typically inside `pack()` or a helper that assembles the final index).

- [ ] **Step 3: Add fingerprint computation**

After the line that sets `index.public_key = <key_bytes>`, add:

```python
# Write key fingerprint into attestation field
from flavor.config.trust import compute_key_fingerprint
from cryptography.hazmat.primitives.serialization import load_der_public_key
_pub_key_obj = load_der_public_key(...)  # use whichever deserialization matches existing code
index.attestation_key_fp = compute_key_fingerprint(_pub_key_obj).encode("ascii").ljust(64, b"\x00")[:64]
```

Adapt the key-loading approach to match the existing code in `pspf_builder.py` — do not introduce a new deserialization path if one already exists.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/format_2025/ -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/flavor/psp/format_2025/pspf_builder.py tests/format_2025/test_key_fingerprint_in_index.py
git commit -m "feat(builder): write key fingerprint into index attestation field"
```

---

## Task 3: `flavor trust` CLI subcommands

**Files:**
- Create: `src/flavor/commands/trust.py`
- Modify: `src/flavor/cli.py`
- Test: `tests/cli/test_trust_command.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/cli/test_trust_command.py
"""Tests for `flavor trust` subcommands."""

import os
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from click.testing import CliRunner

from flavor.cli import cli


def _write_pub_key(path: Path, name: str | None = None) -> str:
    """Write an Ed25519 .pub key, return fingerprint."""
    import hashlib

    private_key = Ed25519PrivateKey.generate()
    pub_key = private_key.public_key()
    pem = pub_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    raw = pub_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    fp = hashlib.sha256(raw).hexdigest()
    label = f"# Name: {name}\n".encode() if name else b""
    path.write_bytes(label + pem)
    return fp


def test_trust_add_copies_key(tmp_path: Path) -> None:
    """flavor trust add copies the key into the trusted-keys store."""
    store_dir = tmp_path / "trusted-keys"
    store_dir.mkdir()
    src_key = tmp_path / "signer.pub"
    fp = _write_pub_key(src_key, "CI pipeline")

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = runner.invoke(cli, ["trust", "add", str(src_key), "--name", "CI pipeline"])
    assert result.exit_code == 0, result.output
    assert any(f.suffix == ".pub" for f in store_dir.iterdir())


def test_trust_list_shows_keys(tmp_path: Path) -> None:
    """flavor trust list prints fingerprints of loaded keys."""
    store_dir = tmp_path / "trusted-keys"
    store_dir.mkdir()
    fp = _write_pub_key(store_dir / "key1.pub", "Release signing")

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = runner.invoke(cli, ["trust", "list"])
    assert result.exit_code == 0, result.output
    assert fp[:16] in result.output


def test_trust_remove_deletes_key(tmp_path: Path) -> None:
    """flavor trust remove deletes the matching .pub file."""
    store_dir = tmp_path / "trusted-keys"
    store_dir.mkdir()
    fp = _write_pub_key(store_dir / "key1.pub")

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = runner.invoke(cli, ["trust", "remove", fp])
    assert result.exit_code == 0, result.output
    assert list(store_dir.glob("*.pub")) == []


def test_trust_remove_unknown_fingerprint_exits_nonzero(tmp_path: Path) -> None:
    """flavor trust remove with unknown fingerprint exits nonzero."""
    store_dir = tmp_path / "trusted-keys"
    store_dir.mkdir()
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = runner.invoke(cli, ["trust", "remove", "a" * 64])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/cli/test_trust_command.py -v
```
Expected: ImportError or SystemExit (no `trust` command)

- [ ] **Step 3: Create `src/flavor/commands/trust.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""flavor trust — manage the trusted signing key store."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)
from provide.foundation.console import perr, pout

from flavor.config.dirs import get_trusted_keys_dir
from flavor.config.trust import compute_key_fingerprint, load_trusted_keys
from flavor.console import get_command_logger

log = get_command_logger("trust")


@click.group("trust")
def trust_group() -> None:
    """Manage the trusted signing key store.

    Keys are stored as Ed25519 PEM files in the trusted-keys directory.
    Packages signed by keys not in the store will be warned about (or blocked
    if require_trusted_key = true in policy.toml).
    """


@trust_group.command("add")
@click.argument("key_file", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--name", default=None, help="Human-readable label for this key.")
@click.option(
    "--global", "global_", is_flag=True, default=False,
    help="Add to system store (/etc/flavor/trusted-keys). Requires root.",
)
def trust_add(key_file: str, name: str | None, global_: bool) -> None:
    """Add a public key to the trusted-keys store."""
    src = Path(key_file)
    try:
        raw_bytes = src.read_bytes()
        # Strip optional Name comment before parsing
        pem_lines = [
            line for line in raw_bytes.decode().splitlines()
            if not line.strip().startswith("# Name:")
        ]
        pub_key = load_pem_public_key("\n".join(pem_lines).encode())
        fp = compute_key_fingerprint(pub_key)  # type: ignore[arg-type]
    except Exception as exc:
        perr(f"Failed to read key: {exc}")
        raise SystemExit(1) from exc

    store_dir = get_trusted_keys_dir(system=global_)
    store_dir.mkdir(parents=True, exist_ok=True)

    dest = store_dir / f"{fp[:16]}.pub"
    label = f"# Name: {name}\n".encode() if name else b""
    raw_pem = pub_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)  # type: ignore[arg-type]
    dest.write_bytes(label + raw_pem)

    pout(f"Added key {fp[:16]}...  ({name or 'no label'})  → {dest}")


@trust_group.command("list")
@click.option(
    "--global", "global_", is_flag=True, default=False,
    help="Show system store only.",
)
def trust_list(global_: bool) -> None:
    """List all trusted keys and their fingerprints."""
    from flavor.config.dirs import get_system_config_dir

    if global_:
        from flavor.config.trust import _load_keys_from_dir
        keys = _load_keys_from_dir(get_system_config_dir() / "trusted-keys")
    else:
        keys = load_trusted_keys()

    if not keys:
        pout("No trusted keys found.")
        return

    for fp, info in sorted(keys.items()):
        label = info.get("name") or "(no label)"
        pout(f"  {fp}  {label}")


@trust_group.command("remove")
@click.argument("fingerprint")
@click.option(
    "--global", "global_", is_flag=True, default=False,
    help="Remove from system store. Requires root.",
)
def trust_remove(fingerprint: str, global_: bool) -> None:
    """Remove a key from the trusted-keys store by fingerprint."""
    store_dir = get_trusted_keys_dir(system=global_)
    keys = load_trusted_keys(include_system=global_)

    if fingerprint not in keys:
        perr(f"Key not found: {fingerprint[:16]}...")
        raise SystemExit(1)

    key_path = Path(keys[fingerprint]["path"])
    key_path.unlink()
    pout(f"Removed {fingerprint[:16]}...  from {store_dir}")


@trust_group.command("verify")
@click.argument("package_file", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def trust_verify(package_file: str) -> None:
    """Check whether a package's signing key is in the trusted store."""
    from flavor.config.trust import is_key_trusted
    from flavor.psp.format_2025.reader import PSPFReader

    pkg_path = Path(package_file)
    with PSPFReader(pkg_path) as reader:
        index = reader.read_index()

    fp_bytes = index.attestation_key_fp.rstrip(b"\x00")
    if not fp_bytes:
        perr("Package has no key fingerprint in attestation field (built with old FlavorPack?).")
        raise SystemExit(2)

    fp = fp_bytes.decode("ascii")
    result = is_key_trusted(fp)

    if result is None:
        pout(f"No trusted-keys store found. Key fingerprint: {fp[:16]}...")
        pout("Run `flavor init` to set up a key store.")
    elif result:
        pout(f"✓ Key {fp[:16]}... is trusted.")
    else:
        perr(f"✗ Key {fp[:16]}... is NOT in the trusted store.")
        raise SystemExit(1)


# 🌶️📦🔚
```

- [ ] **Step 4: Register command group in `src/flavor/cli.py`**

Add import:
```python
from flavor.commands.trust import trust_group
```

Add registration:
```python
cli.add_command(trust_group, name="trust")
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/cli/test_trust_command.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/flavor/commands/trust.py src/flavor/cli.py tests/cli/test_trust_command.py
git commit -m "feat(cli): add flavor trust add/list/remove/verify subcommands"
```

---

## Task 4: Go launcher — trusted key verification

**Files:**
- Create: `src/flavor-go/pkg/psp/format_2025/trust.go`
- Modify: `src/flavor-go/pkg/psp/format_2025/execution.go`

- [ ] **Step 1: Create `src/flavor-go/pkg/psp/format_2025/trust.go`**

```go
package format_2025

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"golang.org/x/crypto/ed25519"
)

// TrustedKey represents a loaded trusted public key.
type TrustedKey struct {
	Fingerprint string
	Name        string
	Path        string
}

// GetTrustedKeysDir returns the user-level trusted-keys directory.
// Priority: FLAVOR_TRUSTED_KEYS_DIR → FLAVOR_CONFIG_DIR/trusted-keys
//           → XDG_CONFIG_HOME/flavor/trusted-keys → ~/.config/flavor/trusted-keys
func GetTrustedKeysDir() string {
	if dir := os.Getenv("FLAVOR_TRUSTED_KEYS_DIR"); dir != "" {
		return dir
	}
	return filepath.Join(getConfigRoot(), "trusted-keys")
}

// getConfigRoot mirrors GetCacheRoot() for config directories.
func getConfigRoot() string {
	if configDir := os.Getenv("FLAVOR_CONFIG_DIR"); configDir != "" {
		return configDir
	}
	if xdgConfig := os.Getenv("XDG_CONFIG_HOME"); xdgConfig != "" {
		return filepath.Join(xdgConfig, "flavor")
	}
	switch runtime.GOOS {
	case "windows":
		if appData := os.Getenv("APPDATA"); appData != "" {
			return filepath.Join(appData, "flavor")
		}
	default:
		if home := os.Getenv("HOME"); home != "" {
			return filepath.Join(home, ".config", "flavor")
		}
	}
	return filepath.Join(os.TempDir(), "flavor", "config")
}

// ComputeKeyFingerprint returns the SHA-256 fingerprint of a raw Ed25519 public key.
// Input must be exactly 32 bytes. Returns lowercase hex string (64 chars).
func ComputeKeyFingerprint(rawPublicKey []byte) (string, error) {
	if len(rawPublicKey) != ed25519.PublicKeySize {
		return "", fmt.Errorf("invalid Ed25519 public key length: %d", len(rawPublicKey))
	}
	hash := sha256.Sum256(rawPublicKey)
	return hex.EncodeToString(hash[:]), nil
}

// LoadTrustedKeys loads all .pub PEM files from user (and optionally system) store.
// Returns map of fingerprint → TrustedKey.
// Returns empty map (not error) if the directory does not exist.
func LoadTrustedKeys(includeSystem bool) (map[string]TrustedKey, error) {
	keys := make(map[string]TrustedKey)

	var dirs []string
	if includeSystem {
		dirs = append(dirs, getSystemTrustedKeysDir())
	}
	dirs = append(dirs, GetTrustedKeysDir())

	for _, dir := range dirs {
		entries, err := os.ReadDir(dir)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return nil, fmt.Errorf("reading trusted-keys dir %s: %w", dir, err)
		}
		for _, entry := range entries {
			if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".pub") {
				continue
			}
			path := filepath.Join(dir, entry.Name())
			key, err := loadPubKeyFile(path)
			if err != nil {
				// Skip malformed files; do not abort
				continue
			}
			keys[key.Fingerprint] = key
		}
	}
	return keys, nil
}

func getSystemTrustedKeysDir() string {
	if runtime.GOOS == "windows" {
		if programData := os.Getenv("PROGRAMDATA"); programData != "" {
			return filepath.Join(programData, "flavor", "trusted-keys")
		}
		return filepath.Join("C:\\ProgramData", "flavor", "trusted-keys")
	}
	return "/etc/flavor/trusted-keys"
}

// loadPubKeyFile reads an Ed25519 PEM public key file, extracts the raw key
// bytes, computes the fingerprint, and returns a TrustedKey.
func loadPubKeyFile(path string) (TrustedKey, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return TrustedKey{}, err
	}

	var name string
	var pemLines []string
	for _, line := range strings.Split(string(data), "\n") {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "# Name:") {
			name = strings.TrimSpace(strings.TrimPrefix(trimmed, "# Name:"))
		} else {
			pemLines = append(pemLines, line)
		}
	}

	rawKey, err := parseEd25519PEM([]byte(strings.Join(pemLines, "\n")))
	if err != nil {
		return TrustedKey{}, fmt.Errorf("parse Ed25519 PEM from %s: %w", path, err)
	}

	fp, err := ComputeKeyFingerprint(rawKey)
	if err != nil {
		return TrustedKey{}, err
	}

	return TrustedKey{Fingerprint: fp, Name: name, Path: path}, nil
}

// parseEd25519PEM decodes a PEM SubjectPublicKeyInfo block and returns the raw
// 32-byte Ed25519 public key. The last 32 bytes of the DER encoding are the key.
func parseEd25519PEM(pemData []byte) ([]byte, error) {
	// Use encoding/pem + crypto/x509 for standard parsing.
	// Avoid importing crypto/x509 into the whole binary by keeping this contained.
	import (
		"crypto/x509"
		"encoding/pem"
	)
	block, _ := pem.Decode(pemData)
	if block == nil {
		return nil, fmt.Errorf("no PEM block found")
	}
	pub, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("parse PKIX public key: %w", err)
	}
	ed25519Pub, ok := pub.(ed25519.PublicKey)
	if !ok {
		return nil, fmt.Errorf("key is not Ed25519")
	}
	return []byte(ed25519Pub), nil
}

// IsTrustedKeyResult describes the trust check outcome.
type IsTrustedKeyResult int

const (
	TrustResultNoStore  IsTrustedKeyResult = iota // No key store directory exists
	TrustResultTrusted                            // Fingerprint found in store
	TrustResultUntrusted                          // Store exists but fingerprint not found
)

// IsKeyTrusted checks whether fingerprint is in the trusted store.
// storeExists indicates whether any trusted-keys directory was found.
func IsKeyTrusted(fingerprint string) (IsTrustedKeyResult, error) {
	userDir := GetTrustedKeysDir()
	sysDir := getSystemTrustedKeysDir()

	_, userErr := os.Stat(userDir)
	_, sysErr := os.Stat(sysDir)

	if os.IsNotExist(userErr) && os.IsNotExist(sysErr) {
		return TrustResultNoStore, nil
	}

	keys, err := LoadTrustedKeys(true)
	if err != nil {
		return TrustResultNoStore, err
	}

	if _, found := keys[fingerprint]; found {
		return TrustResultTrusted, nil
	}
	return TrustResultUntrusted, nil
}
```

Note: The import block inside `parseEd25519PEM` won't compile as written. Move the `crypto/x509` and `encoding/pem` imports to the package-level import block. The code is structured this way for clarity — fix the imports when implementing.

- [ ] **Step 2: Integrate into execution flow**

In `src/flavor-go/pkg/psp/format_2025/execution.go`, find where execution begins (after signature verification) and add the trust check:

```go
// Trust store check (Step 2 of launch sequence)
if len(index.AttestationKeyFp) > 0 {
    fp := strings.TrimRight(string(index.AttestationKeyFp[:]), "\x00")
    if fp != "" {
        result, err := IsKeyTrusted(fp)
        if err != nil {
            log.Printf("WARN: trust store check failed: %v", err)
        } else if result == TrustResultUntrusted {
            // Check operator policy: require_trusted_key
            if requireTrustedKey {
                return fmt.Errorf("signing key not in trusted store: %s", fp[:16])
            }
            log.Printf("WARN: signing key not in trusted store: %s...", fp[:16])
        }
    }
}
```

The `requireTrustedKey` value should come from reading policy.toml (implemented in Plan 4). For now, default it to `false`.

- [ ] **Step 3: Add `AttestationKeyFp` field to Go index struct**

Find the Go index struct (likely `metadata.go` or similar) and add:

```go
AttestationKeyFp [64]byte
```

Map it to the correct byte offset in the 8192-byte index (the attestation fields start at byte `8192 - 6816 = 1376`).

- [ ] **Step 4: Build and verify**

```bash
cd src/flavor-go && go build ./... && go vet ./... && cd ../..
```
Expected: compiles cleanly

- [ ] **Step 5: Commit**

```bash
git add src/flavor-go/
git commit -m "feat(go): add trusted key store verification in launcher"
```

---

## Task 5: Rust launcher — trusted key verification

**Files:**
- Create: `src/flavor-rs/src/psp/format_2025/trust.rs`
- Modify: `src/flavor-rs/src/psp/format_2025/mod.rs`

- [ ] **Step 1: Create `src/flavor-rs/src/psp/format_2025/trust.rs`**

```rust
//! Trusted key store for FlavorPack launcher.

use std::fs;
use std::path::{Path, PathBuf};
use std::collections::HashMap;

/// Returns the user-level trusted-keys directory.
pub fn get_trusted_keys_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("FLAVOR_TRUSTED_KEYS_DIR") {
        return PathBuf::from(dir);
    }
    get_config_root().join("trusted-keys")
}

fn get_config_root() -> PathBuf {
    if let Ok(dir) = std::env::var("FLAVOR_CONFIG_DIR") {
        return PathBuf::from(dir);
    }
    if let Ok(xdg) = std::env::var("XDG_CONFIG_HOME") {
        return PathBuf::from(xdg).join("flavor");
    }
    #[cfg(target_os = "windows")]
    {
        if let Ok(appdata) = std::env::var("APPDATA") {
            return PathBuf::from(appdata).join("flavor");
        }
    }
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("/tmp"))
        .join(".config")
        .join("flavor")
}

fn get_system_trusted_keys_dir() -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        if let Ok(pd) = std::env::var("PROGRAMDATA") {
            return PathBuf::from(pd).join("flavor").join("trusted-keys");
        }
        return PathBuf::from("C:\\ProgramData\\flavor\\trusted-keys");
    }
    #[cfg(not(target_os = "windows"))]
    PathBuf::from("/etc/flavor/trusted-keys")
}

/// SHA-256 fingerprint of raw 32-byte Ed25519 key, hex-encoded.
pub fn compute_key_fingerprint(raw_key: &[u8]) -> Option<String> {
    if raw_key.len() != 32 {
        return None;
    }
    use sha2::{Digest, Sha256};
    let hash = Sha256::digest(raw_key);
    Some(hex::encode(hash))
}

/// Load all .pub files from a directory. Skips malformed files silently.
fn load_keys_from_dir(dir: &Path) -> HashMap<String, PathBuf> {
    let mut keys = HashMap::new();
    let entries = match fs::read_dir(dir) {
        Ok(e) => e,
        Err(_) => return keys,
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("pub") {
            continue;
        }
        if let Some(fp) = load_pub_key_fingerprint(&path) {
            keys.insert(fp, path);
        }
    }
    keys
}

fn load_pub_key_fingerprint(path: &Path) -> Option<String> {
    let content = fs::read_to_string(path).ok()?;
    let pem_content: String = content
        .lines()
        .filter(|l| !l.trim().starts_with("# Name:"))
        .collect::<Vec<_>>()
        .join("\n");

    // Parse Ed25519 SubjectPublicKeyInfo PEM — last 32 bytes are the raw key.
    let der = pem::parse(pem_content.as_bytes()).ok()?.contents;
    if der.len() < 32 {
        return None;
    }
    let raw_key = &der[der.len() - 32..];
    compute_key_fingerprint(raw_key)
}

/// Trust check result.
#[derive(Debug, PartialEq)]
pub enum TrustResult {
    NoStore,      // No trusted-keys directory exists
    Trusted,      // Fingerprint found
    Untrusted,    // Store exists, fingerprint not found
}

/// Check whether a key fingerprint is in the trusted store.
pub fn is_key_trusted(fingerprint: &str) -> TrustResult {
    let user_dir = get_trusted_keys_dir();
    let sys_dir = get_system_trusted_keys_dir();

    let user_exists = user_dir.is_dir();
    let sys_exists = sys_dir.is_dir();

    if !user_exists && !sys_exists {
        return TrustResult::NoStore;
    }

    let mut keys = HashMap::new();
    if sys_exists {
        keys.extend(load_keys_from_dir(&sys_dir));
    }
    if user_exists {
        keys.extend(load_keys_from_dir(&user_dir));
    }

    if keys.contains_key(fingerprint) {
        TrustResult::Trusted
    } else {
        TrustResult::Untrusted
    }
}
```

- [ ] **Step 2: Register the module**

In `src/flavor-rs/src/psp/format_2025/mod.rs`, add:

```rust
pub mod trust;
```

- [ ] **Step 3: Add `sha2`, `hex`, `pem`, `dirs` dependencies to `Cargo.toml` (if not already present)**

In `src/flavor-rs/Cargo.toml`:
```toml
sha2 = "0.10"
hex = "0.4"
pem = "3"
dirs = "5"
```

Check existing dependencies first — avoid duplicating.

- [ ] **Step 4: Integrate trust check in launcher**

Find the Rust launcher's execution entry point. After signature verification, add:

```rust
// Trust store check
let fp_bytes = &index.attestation_key_fp;
let fp_str: &str = std::str::from_utf8(fp_bytes)
    .unwrap_or("")
    .trim_end_matches('\0');
if !fp_str.is_empty() {
    match trust::is_key_trusted(fp_str) {
        trust::TrustResult::Untrusted => {
            if require_trusted_key {
                return Err(format!("signing key not in trusted store: {}...", &fp_str[..16]).into());
            }
            eprintln!("WARN: signing key not in trusted store: {}...", &fp_str[..16]);
        }
        trust::TrustResult::NoStore | trust::TrustResult::Trusted => {}
    }
}
```

`require_trusted_key` defaults to `false` until Plan 4.

- [ ] **Step 5: Build and test**

```bash
cd src/flavor-rs && cargo build && cargo clippy -- -D warnings && cargo test && cd ../..
```
Expected: compiles, no warnings

- [ ] **Step 6: Commit**

```bash
git add src/flavor-rs/
git commit -m "feat(rust): add trusted key store verification in launcher"
```

---

## Task 6: Parity tests and final verification

**Files:**
- Create: `tests/parity/test_trust_parity.py`

- [ ] **Step 1: Write parity tests**

```python
# tests/parity/test_trust_parity.py
"""Parity tests for trusted key store behavior."""

import pytest


@pytest.mark.parity
@pytest.mark.parity_category("Trusted Key Store")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_no_store_is_no_op() -> None:
    """When no trusted-keys directory exists, packages execute without restriction."""
    import os
    from unittest import mock
    from flavor.config.trust import is_key_trusted

    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": "/nonexistent/path/xyz"}):
        result = is_key_trusted("a" * 64)
    assert result is None  # None = no-op, not a failure


@pytest.mark.parity
@pytest.mark.parity_category("Trusted Key Store")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_trusted_key_returns_true(tmp_path) -> None:
    """Known key fingerprint is trusted."""
    import os
    import hashlib
    from unittest import mock
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from flavor.config.trust import is_key_trusted

    keys_dir = tmp_path / "trusted-keys"
    keys_dir.mkdir()
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    raw = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    fp = hashlib.sha256(raw).hexdigest()
    (keys_dir / "key.pub").write_bytes(pem)

    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(keys_dir)}):
        assert is_key_trusted(fp) is True


@pytest.mark.parity
@pytest.mark.parity_category("Trusted Key Store")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_unknown_key_returns_false(tmp_path) -> None:
    """Unknown fingerprint in existing store returns False."""
    import os
    from unittest import mock
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from flavor.config.trust import is_key_trusted

    keys_dir = tmp_path / "trusted-keys"
    keys_dir.mkdir()
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    (keys_dir / "key.pub").write_bytes(pem)

    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(keys_dir)}):
        assert is_key_trusted("unknown" + "a" * 57) is False
```

- [ ] **Step 2: Run full test suite**

```bash
uv run pytest -x -q
uv run pytest -m parity --parity-report -v
cat reports/parity-report.md
```
Expected: "Trusted Key Store" section appears in report

- [ ] **Step 3: Lint and type check**

```bash
uv run ruff check src/ tests/
uv run mypy src/flavor
cd src/flavor-go && go vet ./... && cd ../..
cd src/flavor-rs && cargo clippy -- -D warnings && cd ../..
```

- [ ] **Step 4: Commit and push**

```bash
git add tests/parity/test_trust_parity.py
git commit -m "test(parity): add trust store parity tests"
git push origin fix/enterprise-security-pillar1
```
