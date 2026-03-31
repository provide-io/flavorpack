# Enterprise Security — Plan 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay the groundwork for all three enterprise security pillars: config dir resolution across all three languages, attestation index fields, lifecycle=11 constant, and the `flavor init [--global]` command.

**Architecture:** Mirror the existing `cache.py` / `GetCacheRoot()` pattern to add config-dir resolution in Python, Go, and Rust. Carve the attestation section out of the 6816-byte reserved space in the index block. Add the `flavor init` top-level command that sets up `/etc/flavor/` or `~/.config/flavor/` with the correct directory structure.

**Tech Stack:** Python 3.11+, attrs, click, Go 1.26, Rust 1.86, existing `get_str` / `get_cache_dir` patterns.

**Spec:** `docs/superpowers/specs/2026-03-31-enterprise-security-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/flavor/config/dirs.py` | `get_config_dir()`, `get_system_config_dir()` |
| Modify | `src/flavor/psp/format_2025/constants.py` | Add `LIFECYCLE_ATTESTATION = 11` |
| Modify | `src/flavor/psp/format_2025/index.py` | Add `attestation_*` fields carved from `reserved` |
| Modify | `src/flavor-go/pkg/psp/format_2025/constants.go` | Add `LifecycleAttestation = 11` |
| Modify | `src/flavor-go/internal/workenv/workenv.go` | Add `GetConfigRoot()` |
| Modify | `src/flavor-rs/src/psp/format_2025/constants.rs` | Add `LifecycleAttestation = 11` |
| Create | `src/flavor/commands/init.py` | `flavor init [--global]` click command |
| Modify | `src/flavor/cli.py` | Register `init` command |
| Create | `tests/config/test_dirs.py` | Unit tests for config dir resolution |
| Create | `tests/format_2025/test_attestation_index.py` | Unit tests for attestation fields round-trip |
| Create | `tests/cli/test_init_command.py` | Unit tests for `flavor init` |

---

## Task 1: Python config dir resolution

**Files:**
- Create: `src/flavor/config/dirs.py`
- Test: `tests/config/test_dirs.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/config/test_dirs.py
import os
from pathlib import Path
from unittest import mock

import pytest

from flavor.config.dirs import get_config_dir, get_system_config_dir


def test_config_dir_env_override(tmp_path: Path) -> None:
    """FLAVOR_CONFIG_DIR takes priority over everything."""
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        assert get_config_dir() == tmp_path


def test_config_dir_xdg(tmp_path: Path) -> None:
    """XDG_CONFIG_HOME is used when set."""
    env = {
        "XDG_CONFIG_HOME": str(tmp_path),
        "HOME": "/should-not-be-used",
    }
    with mock.patch.dict(os.environ, env, clear=False):
        with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": ""}, clear=False):
            assert get_config_dir() == tmp_path / "flavor"


def test_config_dir_default(tmp_path: Path) -> None:
    """Falls back to ~/.config/flavor."""
    env: dict[str, str] = {}
    with mock.patch.dict(os.environ, env, clear=False):
        # Patch HOME and remove overrides
        with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": "", "XDG_CONFIG_HOME": ""}):
            with mock.patch("pathlib.Path.home", return_value=tmp_path):
                result = get_config_dir()
    assert result == tmp_path / ".config" / "flavor"


def test_system_config_dir_linux() -> None:
    """System config is /etc/flavor on Linux/macOS."""
    with mock.patch("sys.platform", "linux"):
        assert get_system_config_dir() == Path("/etc/flavor")


def test_system_config_dir_windows(tmp_path: Path) -> None:
    """System config uses PROGRAMDATA on Windows."""
    with mock.patch("sys.platform", "win32"):
        with mock.patch.dict(os.environ, {"PROGRAMDATA": str(tmp_path)}):
            assert get_system_config_dir() == tmp_path / "flavor"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/tim/code/gh/provide-io/flavorpack
uv run pytest tests/config/test_dirs.py -v
```
Expected: ImportError (module doesn't exist yet)

- [ ] **Step 3: Create `src/flavor/config/dirs.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Config directory resolution for FlavorPack.

Uses XDG Base Directory specification:
  User config:   FLAVOR_CONFIG_DIR → XDG_CONFIG_HOME/flavor → ~/.config/flavor
  System config: /etc/flavor  (Linux/macOS)  |  %PROGRAMDATA%\\flavor  (Windows)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from provide.foundation.utils.environment import get_str

from flavor.console import get_command_logger

log = get_command_logger("config.dirs")


def get_config_dir() -> Path:
    """Return the user-level config directory for FlavorPack.

    Priority:
    1. ``FLAVOR_CONFIG_DIR`` environment variable (explicit override)
    2. ``$XDG_CONFIG_HOME/flavor``
    3. ``~/.config/flavor`` (XDG default)
    """
    config_dir = get_str("FLAVOR_CONFIG_DIR")
    if config_dir:
        log.trace("Using FLAVOR_CONFIG_DIR", path=config_dir)
        return Path(config_dir)

    xdg_config = get_str("XDG_CONFIG_HOME")
    if xdg_config:
        result = Path(xdg_config) / "flavor"
        log.trace("Using XDG_CONFIG_HOME", path=str(result))
        return result

    default = Path.home() / ".config" / "flavor"
    log.trace("Using default config dir", path=str(default))
    return default


def get_system_config_dir() -> Path:
    """Return the system-level config directory for FlavorPack.

    - Linux / macOS: ``/etc/flavor``
    - Windows:       ``%PROGRAMDATA%\\flavor``
    """
    if sys.platform == "win32":
        programdata = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
        return Path(programdata) / "flavor"
    return Path("/etc/flavor")


def get_trusted_keys_dir(*, system: bool = False) -> Path:
    """Return the trusted-keys directory.

    Args:
        system: If True, return the system-wide directory; otherwise user-level.

    Priority for user dir:
    1. ``FLAVOR_TRUSTED_KEYS_DIR``
    2. ``{get_config_dir()}/trusted-keys``
    """
    if system:
        return get_system_config_dir() / "trusted-keys"

    trusted_keys_override = get_str("FLAVOR_TRUSTED_KEYS_DIR")
    if trusted_keys_override:
        log.trace("Using FLAVOR_TRUSTED_KEYS_DIR", path=trusted_keys_override)
        return Path(trusted_keys_override)

    return get_config_dir() / "trusted-keys"


def get_policy_file(*, system: bool = False) -> Path:
    """Return the path to the policy.toml file.

    Args:
        system: If True, return the system-wide path; otherwise user-level.
    """
    if system:
        return get_system_config_dir() / "policy.toml"
    return get_config_dir() / "policy.toml"


# 🌶️📦🔚
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/config/test_dirs.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/flavor/config/dirs.py tests/config/test_dirs.py
git commit -m "feat(config): add get_config_dir() with XDG and env-var resolution"
```

---

## Task 2: Add `LIFECYCLE_ATTESTATION` constant in all three languages

**Files:**
- Modify: `src/flavor/psp/format_2025/constants.py`
- Modify: `src/flavor-go/pkg/psp/format_2025/constants.go`
- Modify: `src/flavor-rs/src/psp/format_2025/constants.rs`
- Test: `tests/parity/test_lifecycle_constants.py`

- [ ] **Step 1: Write the parity test**

```python
# tests/parity/test_lifecycle_constants.py
"""Parity test: all three languages define LifecycleAttestation = 11."""

import pytest

from flavor.psp.format_2025.constants import (
    LIFECYCLE_ATTESTATION,
    LIFECYCLE_FROM_STRING,
    LIFECYCLE_NAMES,
)


@pytest.mark.parity
@pytest.mark.parity_category("Format Constants")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_lifecycle_attestation_value() -> None:
    """LIFECYCLE_ATTESTATION must equal 11 in all three implementations."""
    assert LIFECYCLE_ATTESTATION == 11


@pytest.mark.parity
@pytest.mark.parity_category("Format Constants")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_lifecycle_attestation_in_names() -> None:
    """LIFECYCLE_NAMES must contain attestation → 11 mapping."""
    assert LIFECYCLE_NAMES[11] == "attestation"
    assert LIFECYCLE_FROM_STRING["attestation"] == 11
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/parity/test_lifecycle_constants.py -v
```
Expected: ImportError or AssertionError

- [ ] **Step 3: Update Python constants**

In `src/flavor/psp/format_2025/constants.py`, add after `LIFECYCLE_PLATFORM = 10`:

```python
LIFECYCLE_ATTESTATION = 11  # Security attestation slot (SBOM + provenance)
```

And update the two dicts:

```python
LIFECYCLE_NAMES = {
    LIFECYCLE_INIT: "init",
    LIFECYCLE_STARTUP: "startup",
    LIFECYCLE_RUNTIME: "runtime",
    LIFECYCLE_SHUTDOWN: "shutdown",
    LIFECYCLE_CACHE: "cache",
    LIFECYCLE_TEMPORARY: "temporary",
    LIFECYCLE_LAZY: "lazy",
    LIFECYCLE_EAGER: "eager",
    LIFECYCLE_DEV: "dev",
    LIFECYCLE_CONFIG: "config",
    LIFECYCLE_PLATFORM: "platform",
    LIFECYCLE_ATTESTATION: "attestation",
}

LIFECYCLE_FROM_STRING = {
    "init": LIFECYCLE_INIT,
    "startup": LIFECYCLE_STARTUP,
    "runtime": LIFECYCLE_RUNTIME,
    "shutdown": LIFECYCLE_SHUTDOWN,
    "cache": LIFECYCLE_CACHE,
    "temporary": LIFECYCLE_TEMPORARY,
    "lazy": LIFECYCLE_LAZY,
    "eager": LIFECYCLE_EAGER,
    "dev": LIFECYCLE_DEV,
    "config": LIFECYCLE_CONFIG,
    "platform": LIFECYCLE_PLATFORM,
    "attestation": LIFECYCLE_ATTESTATION,
}
```

- [ ] **Step 4: Update Go constants**

In `src/flavor-go/pkg/psp/format_2025/constants.go`, add after `LifecyclePlatform = 10`:

```go
LifecycleAttestation = 11 // Security attestation slot (SBOM + provenance)
```

- [ ] **Step 5: Update Rust constants**

In `src/flavor-rs/src/psp/format_2025/constants.rs`, add after `LifecyclePlatform`:

```rust
#[allow(non_upper_case_globals)]
pub const LifecycleAttestation: u8 = 11; // Security attestation slot (SBOM + provenance)
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/parity/test_lifecycle_constants.py -v
cd src/flavor-go && go vet ./... && cd ../..
cd src/flavor-rs && cargo check && cd ../..
```
Expected: Python test passes; Go and Rust compile cleanly

- [ ] **Step 7: Commit**

```bash
git add src/flavor/psp/format_2025/constants.py \
        src/flavor-go/pkg/psp/format_2025/constants.go \
        src/flavor-rs/src/psp/format_2025/constants.rs \
        tests/parity/test_lifecycle_constants.py
git commit -m "feat(format): add LifecycleAttestation=11 across Python, Go, Rust"
```

---

## Task 3: Add attestation fields to the index block

**Files:**
- Modify: `src/flavor/psp/format_2025/index.py`
- Test: `tests/format_2025/test_attestation_index.py`

The 6816-byte `reserved` field is carved: first 192 bytes become three 64-byte attestation digest fields. The remaining 6624 bytes stay reserved. Old writers write zeros; old readers ignore the reserved region. New readers extract the digests.

- [ ] **Step 1: Write the failing tests**

```python
# tests/format_2025/test_attestation_index.py
"""Tests for attestation fields in the PSPF index block."""

from flavor.psp.format_2025.index import PSPFIndex


def test_attestation_fields_default_to_empty() -> None:
    """New index block has empty (all-zero) attestation fields."""
    idx = PSPFIndex()
    assert idx.attestation_key_fp == b"\x00" * 64
    assert idx.attestation_sbom_digest == b"\x00" * 64
    assert idx.attestation_policy_hash == b"\x00" * 64


def test_attestation_round_trip() -> None:
    """Attestation fields survive pack/unpack unchanged."""
    idx = PSPFIndex()
    idx.attestation_key_fp = b"a" * 64
    idx.attestation_sbom_digest = b"b" * 64
    idx.attestation_policy_hash = b"c" * 64

    packed = idx.pack()
    assert len(packed) == 8192

    idx2 = PSPFIndex.unpack(packed)
    assert idx2.attestation_key_fp == b"a" * 64
    assert idx2.attestation_sbom_digest == b"b" * 64
    assert idx2.attestation_policy_hash == b"c" * 64


def test_reserved_region_untouched() -> None:
    """Bytes beyond the attestation section remain zero-filled."""
    idx = PSPFIndex()
    packed = idx.pack()
    # Reserved starts at byte 8192 - 6816 = 1376, attestation takes first 192
    # Remaining 6624 bytes (offsets 192..6815 within the reserved region) must be zero
    reserved_start = 8192 - 6816
    post_attestation = packed[reserved_start + 192 : reserved_start + 6816]
    assert post_attestation == b"\x00" * 6624


def test_index_block_is_still_8192_bytes() -> None:
    """Total packed size is exactly 8192 bytes."""
    idx = PSPFIndex()
    assert len(idx.pack()) == 8192
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/format_2025/test_attestation_index.py -v
```
Expected: AttributeError (fields don't exist yet)

- [ ] **Step 3: Update `PSPFIndex` in `index.py`**

Replace the FORMAT string's final `"6816s"` with three 64-byte fields plus remaining reserved, and add the corresponding attrs fields.

In `src/flavor/psp/format_2025/index.py`, change the FORMAT string's last two entries:

```python
# Replace:
#   "6816s"  # reserved
# With:
            "64s"  # attestation_key_fp (SHA-256 hex, 64 ASCII bytes)
            "64s"  # attestation_sbom_digest (SHA-256 hex, 64 ASCII bytes)
            "64s"  # attestation_policy_hash (SHA-256 hex, 64 ASCII bytes)
            "6624s"  # reserved (remaining future expansion)
```

Add the fields before `reserved`:

```python
    # Attestation fields (carved from reserved space — backwards compatible)
    attestation_key_fp: bytes = field(default=Factory(lambda: b"\x00" * 64))
    attestation_sbom_digest: bytes = field(default=Factory(lambda: b"\x00" * 64))
    attestation_policy_hash: bytes = field(default=Factory(lambda: b"\x00" * 64))

    # Reserved space (reduced from 6816 — first 192 bytes used for attestation above)
    reserved: bytes = field(default=Factory(lambda: b"\x00" * 6624))
```

In the `pack()` method, add the three new fields before `self.reserved` (and after `self.future_crypto`):

```python
            self.attestation_key_fp,
            self.attestation_sbom_digest,
            self.attestation_policy_hash,
            self.reserved,
```

Add or update the `unpack()` classmethod to populate the new fields. Find the unpack call and add three new tuple positions before `reserved`. The exact position depends on the current unpack — read `index.py:unpack` carefully and insert `attestation_key_fp`, `attestation_sbom_digest`, `attestation_policy_hash` before the final `reserved` assignment.

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/format_2025/test_attestation_index.py -v
uv run pytest tests/format_2025/ -v  # make sure nothing regressed
```
Expected: all 4 new tests pass; no existing format tests broken

- [ ] **Step 5: Commit**

```bash
git add src/flavor/psp/format_2025/index.py tests/format_2025/test_attestation_index.py
git commit -m "feat(format): add attestation fields to index block reserved space"
```

---

## Task 4: Add `GetConfigRoot()` to Go

**Files:**
- Modify: `src/flavor-go/internal/workenv/workenv.go`

- [ ] **Step 1: Add the function**

In `src/flavor-go/internal/workenv/workenv.go`, add after `GetCacheRoot()`:

```go
// GetConfigRoot returns the user-level config root directory.
// Priority:
//  1. FLAVOR_CONFIG_DIR environment variable
//  2. $XDG_CONFIG_HOME/flavor  (all platforms)
//  3. ~/.config/flavor         (XDG fallback)
//  4. %APPDATA%\flavor         (Windows only)
func GetConfigRoot() string {
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

// GetSystemConfigRoot returns the system-wide config root directory.
// Linux/macOS: /etc/flavor
// Windows:     %PROGRAMDATA%\flavor
func GetSystemConfigRoot() string {
	if runtime.GOOS == "windows" {
		if programData := os.Getenv("PROGRAMDATA"); programData != "" {
			return filepath.Join(programData, "flavor")
		}
		return filepath.Join("C:\\ProgramData", "flavor")
	}
	return "/etc/flavor"
}
```

- [ ] **Step 2: Verify it compiles**

```bash
cd src/flavor-go && go vet ./... && cd ../..
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add src/flavor-go/internal/workenv/workenv.go
git commit -m "feat(go): add GetConfigRoot() and GetSystemConfigRoot()"
```

---

## Task 5: `flavor init [--global]` command

**Files:**
- Create: `src/flavor/commands/init.py`
- Modify: `src/flavor/cli.py`
- Test: `tests/cli/test_init_command.py`

The command creates the config directory structure and scaffolds a commented-out `policy.toml`. It is idempotent: running it twice changes nothing.

- [ ] **Step 1: Write the failing tests**

```python
# tests/cli/test_init_command.py
"""Tests for `flavor init [--global]`."""

import os
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from flavor.cli import cli


def test_init_creates_user_dirs(tmp_path: Path) -> None:
    """flavor init creates trusted-keys dir and policy.toml under user config."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "trusted-keys").is_dir()
    assert (tmp_path / "policy.toml").exists()


def test_init_policy_toml_is_commented_out(tmp_path: Path) -> None:
    """Scaffolded policy.toml has all options commented out."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        runner.invoke(cli, ["init"])
    content = (tmp_path / "policy.toml").read_text(encoding="utf-8")
    # No uncommented TOML assignments
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            pytest.fail(f"Uncommented assignment in scaffolded policy.toml: {line!r}")


def test_init_is_idempotent(tmp_path: Path) -> None:
    """Running flavor init twice does not overwrite existing files."""
    runner = CliRunner()
    env = {"FLAVOR_CONFIG_DIR": str(tmp_path)}
    with mock.patch.dict(os.environ, env):
        runner.invoke(cli, ["init"])
    # Write a sentinel into policy.toml
    policy = tmp_path / "policy.toml"
    policy.write_text("# MY CUSTOM CONTENT\n", encoding="utf-8")
    with mock.patch.dict(os.environ, env):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "MY CUSTOM CONTENT" in policy.read_text(encoding="utf-8")


def test_init_global_uses_system_dir(tmp_path: Path) -> None:
    """flavor init --global targets the system config dir."""
    runner = CliRunner()
    with mock.patch(
        "flavor.config.dirs.get_system_config_dir", return_value=tmp_path
    ):
        result = runner.invoke(cli, ["init", "--global"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "trusted-keys").is_dir()
    assert (tmp_path / "policy.toml").exists()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/cli/test_init_command.py -v
```
Expected: ImportError or SystemExit (command not registered)

- [ ] **Step 3: Create `src/flavor/commands/init.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""flavor init — one-shot host setup for FlavorPack."""

from __future__ import annotations

from pathlib import Path

import click
from provide.foundation.console import pout

from flavor.config.dirs import get_config_dir, get_system_config_dir
from flavor.console import get_command_logger

log = get_command_logger("init")

_POLICY_TOML_SCAFFOLD = """\
# FlavorPack policy configuration
# Generated by: flavor init
#
# Uncomment and set values to override defaults.
# Operator policy can only TIGHTEN package-declared constraints, never loosen them.
#
# [trust]
# # Require all packages to be signed by a key in the trusted-keys store.
# # Default: false (warn only when store exists but key not found)
# require_trusted_key = false
#
# # Also check the OS keyring (macOS Keychain, Windows CertStore, Linux /etc/ssl)
# # for a certificate whose public key matches the package key fingerprint.
# # Default: false
# use_os_keychain = false
#
# [execution]
# # Block packages from running as root/Administrator.
# refuse_root = false
#
# # Maximum package age in days (computed from provenance.build_timestamp).
# # max_age_days = 365
#
# # Limit execution to these platforms (comma-separated).
# # allow_platforms = ["linux_amd64", "linux_arm64"]
#
# [attestation]
# # Block packages built without an attestation slot (SBOM + provenance).
# # Default: false
# require_sbom = false
"""


@click.command("init")
@click.option(
    "--global",
    "global_",
    is_flag=True,
    default=False,
    help="Set up system-wide config under /etc/flavor (requires root/sudo).",
)
def init_command(global_: bool) -> None:
    """Set up FlavorPack config directory structure on this host.

    Creates the trusted-keys directory and a commented-out policy.toml.
    Safe to run multiple times — existing files are never overwritten.
    """
    config_root: Path = get_system_config_dir() if global_ else get_config_dir()
    scope = "system" if global_ else "user"

    log.debug("Initializing FlavorPack config", scope=scope, root=str(config_root))

    # Create trusted-keys directory
    trusted_keys_dir = config_root / "trusted-keys"
    trusted_keys_dir.mkdir(parents=True, exist_ok=True)
    pout(f"✓ {trusted_keys_dir}")

    # Scaffold policy.toml (never overwrite)
    policy_file = config_root / "policy.toml"
    if not policy_file.exists():
        policy_file.write_text(_POLICY_TOML_SCAFFOLD, encoding="utf-8")
        pout(f"✓ {policy_file}  (scaffolded)")
    else:
        pout(f"  {policy_file}  (already exists, not modified)")

    pout(f"\nFlavorPack {scope} config initialised at {config_root}")
    if not global_:
        pout("  Add trusted keys with: flavor trust add <key.pub>")
        pout("  Edit policy with:      flavor policy init")
    else:
        pout("  Add trusted keys with: sudo flavor trust add <key.pub> --global")
        pout("  Edit policy with:      sudo flavor policy init --global")


# 🌶️📦🔚
```

- [ ] **Step 4: Register the command in `src/flavor/cli.py`**

Add the import after the existing imports:

```python
from flavor.commands.init import init_command
```

Add the registration before `main = cli`:

```python
cli.add_command(init_command, name="init")
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/cli/test_init_command.py -v
```
Expected: 4 passed

- [ ] **Step 6: Smoke test manually**

```bash
FLAVOR_CONFIG_DIR=/tmp/flavor-init-test uv run flavor init
ls -la /tmp/flavor-init-test/
cat /tmp/flavor-init-test/policy.toml
```

Expected:
```
✓ /tmp/flavor-init-test/trusted-keys
✓ /tmp/flavor-init-test/policy.toml  (scaffolded)

FlavorPack user config initialised at /tmp/flavor-init-test
```

- [ ] **Step 7: Commit**

```bash
git add src/flavor/commands/init.py src/flavor/cli.py tests/cli/test_init_command.py
git commit -m "feat(cli): add flavor init [--global] command"
```

---

## Task 6: Final verification

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -x -q
uv run pytest -m parity --parity-report -v
```
Expected: all pass; parity report includes "Format Constants" section

- [ ] **Step 2: Run linters**

```bash
uv run ruff check src/ tests/
uv run mypy src/flavor
cd src/flavor-go && gofmt -l . && go vet ./... && cd ../..
cd src/flavor-rs && cargo fmt --check && cargo clippy -- -D warnings && cd ../..
```
Expected: no errors

- [ ] **Step 3: Commit any lint fixes, then push**

```bash
git push origin fix/enterprise-security-foundation
```

---

## Dependency

Plans 2, 3, and 4 all depend on this plan being merged first. The order is:

1. **This plan** — config dirs, attestation index fields, lifecycle=11, `flavor init`
2. **Plan 2** — Trusted Key Store (uses `get_config_dir()`, `get_trusted_keys_dir()`)
3. **Plan 3** — SBOM & Provenance (uses attestation index fields, lifecycle=11)
4. **Plan 4** — Launch-Time Policy (uses `get_policy_file()`, attestation index fields)
