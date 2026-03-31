# Enterprise Security — Plan 4: Launch-Time Policy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Pillar 3 — builder-declared package execution constraints plus operator policy overlay. The merger rule is "stricter wins". Launchers enforce the merged policy before execution. `flavor policy` CLI provides show/check/init.

**Architecture:** Builder writes constraints into `pyproject.toml` `[tool.flavor.policy]`; they are stored in package metadata at build time. At launch, Go/Rust read both the package-declared policy and `/etc/flavor/policy.toml`, merge them (stricter wins per field), and enforce before `execve`. Python implements the merge logic and the `flavor policy` CLI. The `policy_hash` index field binds the declared policy to the package digest.

**Tech Stack:** Python `tomllib` (3.11 stdlib), `tomli-w` for writing, click, Go 1.26, Rust 1.86.

**Prerequisites:** Plans 1, 2, and 3 complete.

**Spec:** `docs/superpowers/specs/2026-03-31-enterprise-security-design.md` § Pillar 3

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/flavor/config/policy.py` | Policy schema, parsing, merge logic |
| Create | `src/flavor/commands/policy.py` | `flavor policy` CLI group (show/check/init) |
| Modify | `src/flavor/cli.py` | Register `policy` command group |
| Modify | `src/flavor/psp/format_2025/pspf_builder.py` | Write policy constraints + policy_hash into index |
| Create | `src/flavor-go/pkg/psp/format_2025/execution_policy.go` | Policy loading, merge, enforcement (Go) |
| Modify | `src/flavor-go/pkg/psp/format_2025/execution.go` | Call policy enforcement |
| Create | `src/flavor-rs/src/psp/format_2025/policy.rs` | Policy loading, merge, enforcement (Rust) |
| Modify | `src/flavor-rs/src/psp/format_2025/mod.rs` | Declare `policy` module |
| Create | `tests/config/test_policy.py` | Unit tests for policy merge logic |
| Create | `tests/cli/test_policy_command.py` | Unit tests for `flavor policy` |
| Create | `tests/parity/test_policy_parity.py` | Parity tests for policy enforcement |

---

## Task 1: Python policy schema and merge logic

**Files:**
- Create: `src/flavor/config/policy.py`
- Test: `tests/config/test_policy.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/config/test_policy.py
"""Tests for FlavorPack launch-time policy."""

import os
from pathlib import Path
from unittest import mock

import pytest

from flavor.config.policy import (
    PackagePolicy,
    OperatorPolicy,
    EffectivePolicy,
    merge_policy,
    load_operator_policy,
    parse_package_policy,
)


def test_parse_package_policy_empty() -> None:
    """Missing [tool.flavor.policy] returns permissive defaults."""
    policy = parse_package_policy({})
    assert policy.refuse_root is False
    assert policy.max_age_days is None
    assert policy.platforms == []
    assert policy.require_env == []


def test_parse_package_policy_full() -> None:
    """All fields parsed correctly."""
    raw = {
        "platforms": ["linux_amd64", "linux_arm64"],
        "refuse_root": True,
        "max_age_days": 365,
        "require_env": ["MYAPP_LICENSE"],
    }
    policy = parse_package_policy(raw)
    assert policy.platforms == ["linux_amd64", "linux_arm64"]
    assert policy.refuse_root is True
    assert policy.max_age_days == 365
    assert policy.require_env == ["MYAPP_LICENSE"]


def test_merge_refuse_root_stricter_wins() -> None:
    """If either side refuses root, merged policy refuses root."""
    pkg = PackagePolicy(refuse_root=False)
    op = OperatorPolicy(refuse_root=True)
    merged = merge_policy(pkg, op)
    assert merged.refuse_root is True


def test_merge_max_age_lower_wins() -> None:
    """Lower max_age_days wins."""
    pkg = PackagePolicy(max_age_days=365)
    op = OperatorPolicy(max_age_days=90)
    merged = merge_policy(pkg, op)
    assert merged.max_age_days == 90


def test_merge_max_age_none_operator_uses_package() -> None:
    """If operator doesn't set max_age_days, package value is used."""
    pkg = PackagePolicy(max_age_days=180)
    op = OperatorPolicy()
    merged = merge_policy(pkg, op)
    assert merged.max_age_days == 180


def test_merge_platforms_intersection() -> None:
    """Effective platforms = intersection of package and operator allow lists."""
    pkg = PackagePolicy(platforms=["linux_amd64", "darwin_arm64"])
    op = OperatorPolicy(allow_platforms=["linux_amd64", "linux_arm64"])
    merged = merge_policy(pkg, op)
    assert merged.platforms == ["linux_amd64"]


def test_merge_require_env_union() -> None:
    """Required env vars from both sides are combined."""
    pkg = PackagePolicy(require_env=["APP_KEY"])
    op = OperatorPolicy()
    merged = merge_policy(pkg, op)
    assert "APP_KEY" in merged.require_env


def test_load_operator_policy_missing_file_returns_defaults(tmp_path: Path) -> None:
    """Missing policy.toml returns a permissive OperatorPolicy."""
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        policy = load_operator_policy()
    assert policy.require_trusted_key is False
    assert policy.refuse_root is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/config/test_policy.py -v
```
Expected: ImportError

- [ ] **Step 3: Create `src/flavor/config/policy.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""FlavorPack launch-time policy: schema, parsing, and merge logic."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from attrs import define, field

from flavor.config.dirs import get_policy_file
from flavor.console import get_command_logger

log = get_command_logger("config.policy")

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[import]
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]


@define
class PackagePolicy:
    """Constraints declared by the package builder in pyproject.toml."""

    platforms: list[str] = field(factory=list)
    refuse_root: bool = field(default=False)
    max_age_days: int | None = field(default=None)
    require_env: list[str] = field(factory=list)


@define
class OperatorPolicy:
    """Operator overlay from /etc/flavor/policy.toml or user policy.toml."""

    require_trusted_key: bool = field(default=False)
    use_os_keychain: bool = field(default=False)
    refuse_root: bool = field(default=False)
    max_age_days: int | None = field(default=None)
    allow_platforms: list[str] = field(factory=list)
    require_sbom: bool = field(default=False)


@define
class EffectivePolicy:
    """Merged policy: the stricter of package + operator wins per field."""

    platforms: list[str] = field(factory=list)
    refuse_root: bool = field(default=False)
    max_age_days: int | None = field(default=None)
    require_env: list[str] = field(factory=list)
    require_trusted_key: bool = field(default=False)
    use_os_keychain: bool = field(default=False)
    require_sbom: bool = field(default=False)


def parse_package_policy(raw: dict[str, Any]) -> PackagePolicy:
    """Parse [tool.flavor.policy] dict from pyproject.toml into a PackagePolicy."""
    return PackagePolicy(
        platforms=raw.get("platforms", []),
        refuse_root=bool(raw.get("refuse_root", False)),
        max_age_days=raw.get("max_age_days"),
        require_env=raw.get("require_env", []),
    )


def _parse_operator_policy(raw: dict[str, Any]) -> OperatorPolicy:
    """Parse policy.toml content into an OperatorPolicy."""
    trust = raw.get("trust", {})
    execution = raw.get("execution", {})
    attestation = raw.get("attestation", {})
    return OperatorPolicy(
        require_trusted_key=bool(trust.get("require_trusted_key", False)),
        use_os_keychain=bool(trust.get("use_os_keychain", False)),
        refuse_root=bool(execution.get("refuse_root", False)),
        max_age_days=execution.get("max_age_days"),
        allow_platforms=execution.get("allow_platforms", []),
        require_sbom=bool(attestation.get("require_sbom", False)),
    )


def load_operator_policy(*, system: bool = True, user: bool = True) -> OperatorPolicy:
    """Load the operator policy file(s).

    System policy (/etc/flavor/policy.toml) is loaded first, then user policy
    overrides it. If neither file exists, returns a permissive default.
    """
    merged: dict[str, Any] = {}

    if system:
        from flavor.config.dirs import get_system_config_dir
        system_file = get_system_config_dir() / "policy.toml"
        if system_file.exists():
            try:
                with system_file.open("rb") as f:
                    merged.update(tomllib.load(f))
            except Exception as exc:
                log.warning("Failed to read system policy", path=str(system_file), error=str(exc))

    if user:
        user_file = get_policy_file(system=False)
        if user_file.exists():
            try:
                with user_file.open("rb") as f:
                    user_raw = tomllib.load(f)
                # Deep merge: user overrides system
                for section, values in user_raw.items():
                    if isinstance(values, dict):
                        merged.setdefault(section, {}).update(values)
                    else:
                        merged[section] = values
            except Exception as exc:
                log.warning("Failed to read user policy", path=str(user_file), error=str(exc))

    return _parse_operator_policy(merged)


def merge_policy(pkg: PackagePolicy, op: OperatorPolicy) -> EffectivePolicy:
    """Merge package-declared and operator policies. Stricter always wins.

    An operator can tighten a constraint but never loosen it.
    """
    # Platforms: intersection of both non-empty lists
    if pkg.platforms and op.allow_platforms:
        platforms = [p for p in pkg.platforms if p in op.allow_platforms]
    elif op.allow_platforms:
        platforms = list(op.allow_platforms)
    else:
        platforms = list(pkg.platforms)

    # refuse_root: True if either side says True
    refuse_root = pkg.refuse_root or op.refuse_root

    # max_age_days: minimum of the two (None = no limit)
    if pkg.max_age_days is not None and op.max_age_days is not None:
        max_age_days: int | None = min(pkg.max_age_days, op.max_age_days)
    elif pkg.max_age_days is not None:
        max_age_days = pkg.max_age_days
    else:
        max_age_days = op.max_age_days

    # require_env: union
    require_env = list(set(pkg.require_env))

    return EffectivePolicy(
        platforms=platforms,
        refuse_root=refuse_root,
        max_age_days=max_age_days,
        require_env=require_env,
        require_trusted_key=op.require_trusted_key,
        use_os_keychain=op.use_os_keychain,
        require_sbom=op.require_sbom,
    )


# 🌶️📦🔚
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/config/test_policy.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/flavor/config/policy.py tests/config/test_policy.py
git commit -m "feat(policy): add policy schema, parsing, and stricter-wins merge logic"
```

---

## Task 2: `flavor policy` CLI

**Files:**
- Create: `src/flavor/commands/policy.py`
- Modify: `src/flavor/cli.py`
- Test: `tests/cli/test_policy_command.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/cli/test_policy_command.py
"""Tests for `flavor policy` subcommands."""

import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from flavor.cli import cli


def test_policy_init_creates_policy_toml(tmp_path: Path) -> None:
    """flavor policy init scaffolds a commented-out policy.toml."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["policy", "init"])
    assert result.exit_code == 0, result.output
    policy_file = tmp_path / "policy.toml"
    assert policy_file.exists()
    content = policy_file.read_text(encoding="utf-8")
    assert "require_trusted_key" in content


def test_policy_init_idempotent(tmp_path: Path) -> None:
    """flavor policy init does not overwrite existing policy.toml."""
    runner = CliRunner()
    env = {"FLAVOR_CONFIG_DIR": str(tmp_path)}
    policy_file = tmp_path / "policy.toml"
    policy_file.parent.mkdir(parents=True, exist_ok=True)
    policy_file.write_text("# MY CONFIG\n", encoding="utf-8")
    with mock.patch.dict(os.environ, env):
        runner.invoke(cli, ["policy", "init"])
    assert "MY CONFIG" in policy_file.read_text(encoding="utf-8")


def test_policy_show_prints_effective_policy(tmp_path: Path) -> None:
    """flavor policy show prints the effective policy as TOML/text."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["policy", "show"])
    assert result.exit_code == 0, result.output
    # At minimum should mention key fields
    assert "require_trusted_key" in result.output or "trust" in result.output.lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/cli/test_policy_command.py -v
```
Expected: ImportError or SystemExit

- [ ] **Step 3: Create `src/flavor/commands/policy.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""flavor policy — manage and inspect launch-time execution policy."""

from __future__ import annotations

from pathlib import Path

import click
from provide.foundation.console import perr, pout

from flavor.config.dirs import get_policy_file, get_system_config_dir
from flavor.config.policy import load_operator_policy, merge_policy, PackagePolicy
from flavor.console import get_command_logger

log = get_command_logger("policy")

_POLICY_TOML_SCAFFOLD = """\
# FlavorPack operator policy
# Generated by: flavor policy init
#
# Each setting here can only TIGHTEN package-declared constraints.
# An operator can refuse_root = true even if a package says false.
# An operator cannot allow a package to run that has its own refuse_root = true.
#
# [trust]
# # Require packages to be signed by a key in the trusted store.
# require_trusted_key = false
#
# # Also consult the OS certificate store for key trust (macOS/Windows).
# use_os_keychain = false
#
# [execution]
# # Block execution as root/Administrator.
# refuse_root = false
#
# # Maximum package age in days (build_timestamp from provenance).
# # max_age_days = 365
#
# # Restrict to these platforms (leave unset to allow all).
# # allow_platforms = ["linux_amd64", "linux_arm64"]
#
# [attestation]
# # Block packages that have no SBOM attestation slot.
# require_sbom = false
"""


@click.group("policy")
def policy_group() -> None:
    """Manage FlavorPack launch-time execution policy.

    Policy controls what packages are allowed to run on this host.
    Operator settings can only tighten package-declared constraints.
    """


@policy_group.command("init")
@click.option(
    "--global", "global_", is_flag=True, default=False,
    help="Scaffold system-wide policy at /etc/flavor/policy.toml (requires root).",
)
def policy_init(global_: bool) -> None:
    """Scaffold a policy.toml with all options commented out."""
    policy_file = get_policy_file(system=global_)
    policy_file.parent.mkdir(parents=True, exist_ok=True)

    if policy_file.exists():
        pout(f"  {policy_file}  (already exists, not modified)")
    else:
        policy_file.write_text(_POLICY_TOML_SCAFFOLD, encoding="utf-8")
        pout(f"✓ {policy_file}  (scaffolded)")

    scope = "system" if global_ else "user"
    pout(f"\nFlavorPack {scope} policy file ready. Edit it to enforce constraints.")


@policy_group.command("show")
def policy_show() -> None:
    """Print the effective policy (operator defaults) for this host."""
    op = load_operator_policy()
    pout("[trust]")
    pout(f"  require_trusted_key = {str(op.require_trusted_key).lower()}")
    pout(f"  use_os_keychain     = {str(op.use_os_keychain).lower()}")
    pout("")
    pout("[execution]")
    pout(f"  refuse_root     = {str(op.refuse_root).lower()}")
    if op.max_age_days is not None:
        pout(f"  max_age_days    = {op.max_age_days}")
    else:
        pout("  max_age_days    = (no limit)")
    if op.allow_platforms:
        pout(f"  allow_platforms = {op.allow_platforms}")
    else:
        pout("  allow_platforms = (all platforms)")
    pout("")
    pout("[attestation]")
    pout(f"  require_sbom = {str(op.require_sbom).lower()}")


@policy_group.command("check")
@click.argument("package_file", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def policy_check(package_file: str) -> None:
    """Dry-run: would this package be allowed to run on this host?"""
    import sys
    from datetime import datetime, timezone
    from flavor.psp.format_2025.reader import PSPFReader
    from flavor.config.policy import parse_package_policy

    pkg_path = Path(package_file)
    with PSPFReader(pkg_path) as reader:
        metadata = reader.read_metadata()
        index = reader.read_index()

    # Load package-declared policy from metadata
    pkg_raw = metadata.get("policy", {})
    pkg_policy = parse_package_policy(pkg_raw)

    # Load operator policy
    op_policy = load_operator_policy()

    # Merge
    effective = merge_policy(pkg_policy, op_policy)

    # Check platform
    current_platform = _get_current_platform()
    if effective.platforms and current_platform not in effective.platforms:
        perr(f"❌ Platform not permitted: {current_platform} not in {effective.platforms}")
        sys.exit(1)

    # Check root
    if effective.refuse_root and _is_root():
        perr("❌ Package refuses to run as root")
        sys.exit(1)

    # Check age
    if effective.max_age_days is not None:
        build_ts = index.build_timestamp
        if build_ts > 0:
            age_days = (datetime.now(timezone.utc).timestamp() - build_ts) / 86400
            if age_days > effective.max_age_days:
                perr(f"❌ Package is {int(age_days)} days old; policy requires max {effective.max_age_days}")
                sys.exit(1)

    # Check env vars
    import os
    missing = [var for var in effective.require_env if not os.environ.get(var)]
    if missing:
        for var in missing:
            perr(f"❌ Required environment variable not set: {var}")
        sys.exit(1)

    pout(f"✓ Package would be allowed on this host.")
    pout(f"  Platform: {current_platform}")
    pout(f"  refuse_root: {effective.refuse_root}")
    pout(f"  max_age_days: {effective.max_age_days or '(no limit)'}")


def _get_current_platform() -> str:
    import platform as _platform
    import sys as _sys
    os_name = "linux" if _sys.platform.startswith("linux") else (
        "darwin" if _sys.platform == "darwin" else "windows"
    )
    machine = _platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    return f"{os_name}_{arch}"


def _is_root() -> bool:
    import os
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False  # Windows


# 🌶️📦🔚
```

- [ ] **Step 4: Register command group in `src/flavor/cli.py`**

Add import:
```python
from flavor.commands.policy import policy_group
```

Add registration:
```python
cli.add_command(policy_group, name="policy")
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/cli/test_policy_command.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/flavor/commands/policy.py src/flavor/cli.py tests/cli/test_policy_command.py
git commit -m "feat(cli): add flavor policy show/check/init subcommands"
```

---

## Task 3: Write policy hash at build time

**Files:**
- Modify: `src/flavor/psp/format_2025/pspf_builder.py`

- [ ] **Step 1: Write a test**

```python
# tests/format_2025/test_policy_hash_in_index.py
"""Tests that PSPFBuilder writes policy_hash when a policy is declared."""

import json, hashlib
from pathlib import Path

import pytest

from flavor.psp.format_2025.reader import PSPFReader


@pytest.mark.integration
def test_built_package_with_policy_has_policy_hash(built_package_with_policy_path: Path) -> None:
    """A package built with [tool.flavor.policy] has a non-zero policy_hash."""
    with PSPFReader(built_package_with_policy_path) as reader:
        index = reader.read_index()
        metadata = reader.read_metadata()

    policy_hash = index.attestation_policy_hash.rstrip(b"\x00")
    assert policy_hash != b""

    # Verify: hash of canonical JSON of the declared policy
    declared = metadata.get("policy", {})
    canonical = json.dumps(declared, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(canonical.encode()).hexdigest()
    assert policy_hash.decode("ascii") == expected
```

- [ ] **Step 2: Add policy_hash computation to PSPFBuilder**

In `pspf_builder.py`, in the section where `attestation_sbom_digest` is written, add:

```python
# Write policy_hash into index
policy_raw = self._spec.get("policy", {})
if policy_raw:
    import json, hashlib
    canonical_policy = json.dumps(policy_raw, sort_keys=True, separators=(",", ":"))
    policy_hash = hashlib.sha256(canonical_policy.encode()).hexdigest()
    self._index.attestation_policy_hash = policy_hash.encode("ascii").ljust(64, b"\x00")[:64]
```

Also store the policy dict in package metadata so `flavor policy check` can read it.

- [ ] **Step 3: Run tests (mark integration as skip if no fixture)**

```bash
uv run pytest tests/format_2025/test_policy_hash_in_index.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/flavor/psp/format_2025/pspf_builder.py tests/format_2025/test_policy_hash_in_index.py
git commit -m "feat(builder): write policy_hash into index attestation field"
```

---

## Task 4: Go launcher — policy enforcement

**Files:**
- Create: `src/flavor-go/pkg/psp/format_2025/execution_policy.go`
- Modify: `src/flavor-go/pkg/psp/format_2025/execution.go`

- [ ] **Step 1: Create `execution_policy.go`**

```go
package format_2025

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

// PackagePolicy mirrors the Python PackagePolicy struct.
type PackagePolicy struct {
	Platforms   []string `json:"platforms"`
	RefuseRoot  bool     `json:"refuse_root"`
	MaxAgeDays  *int     `json:"max_age_days"`
	RequireEnv  []string `json:"require_env"`
}

// OperatorPolicy mirrors the Python OperatorPolicy struct.
type OperatorPolicy struct {
	RequireTrustedKey bool     `json:"require_trusted_key"`
	UseOsKeychain     bool     `json:"use_os_keychain"`
	RefuseRoot        bool     `json:"refuse_root"`
	MaxAgeDays        *int     `json:"max_age_days"`
	AllowPlatforms    []string `json:"allow_platforms"`
	RequireSBOM       bool     `json:"require_sbom"`
}

// EffectivePolicy is the merged result.
type EffectivePolicy struct {
	Platforms         []string
	RefuseRoot        bool
	MaxAgeDays        *int
	RequireEnv        []string
	RequireTrustedKey bool
	RequireSBOM       bool
}

// LoadOperatorPolicy reads /etc/flavor/policy.toml (or platform equivalent).
// Returns permissive defaults if the file does not exist.
func LoadOperatorPolicy() (OperatorPolicy, error) {
	// Use a simple TOML subset parser for the policy fields we care about.
	// Rather than pulling in a full TOML library, read key = value pairs.
	policy := OperatorPolicy{}

	paths := []string{
		getSystemPolicyFile(),
		getUserPolicyFile(),
	}

	for _, path := range paths {
		data, err := os.ReadFile(path)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return policy, fmt.Errorf("reading policy %s: %w", path, err)
		}
		parseMinimalTOML(data, &policy)
	}
	return policy, nil
}

func getSystemPolicyFile() string {
	if runtime.GOOS == "windows" {
		if pd := os.Getenv("PROGRAMDATA"); pd != "" {
			return filepath.Join(pd, "flavor", "policy.toml")
		}
		return filepath.Join("C:\\ProgramData", "flavor", "policy.toml")
	}
	return "/etc/flavor/policy.toml"
}

func getUserPolicyFile() string {
	if configDir := os.Getenv("FLAVOR_CONFIG_DIR"); configDir != "" {
		return filepath.Join(configDir, "policy.toml")
	}
	if xdgConfig := os.Getenv("XDG_CONFIG_HOME"); xdgConfig != "" {
		return filepath.Join(xdgConfig, "flavor", "policy.toml")
	}
	if home := os.Getenv("HOME"); home != "" {
		return filepath.Join(home, ".config", "flavor", "policy.toml")
	}
	return ""
}

// parseMinimalTOML is a line-by-line parser for the small subset of TOML used
// in policy.toml: [section] headers and key = value bool/int/string-list lines.
func parseMinimalTOML(data []byte, policy *OperatorPolicy) {
	section := ""
	for _, rawLine := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(rawLine)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			section = strings.ToLower(line[1 : len(line)-1])
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])

		switch section + "." + key {
		case "trust.require_trusted_key":
			policy.RequireTrustedKey = val == "true"
		case "trust.use_os_keychain":
			policy.UseOsKeychain = val == "true"
		case "execution.refuse_root":
			policy.RefuseRoot = val == "true"
		case "execution.max_age_days":
			var n int
			if _, err := fmt.Sscanf(val, "%d", &n); err == nil {
				policy.MaxAgeDays = &n
			}
		case "attestation.require_sbom":
			policy.RequireSBOM = val == "true"
		}
	}
}

// MergePolicy produces an EffectivePolicy where stricter always wins.
func MergePolicy(pkg PackagePolicy, op OperatorPolicy) EffectivePolicy {
	effective := EffectivePolicy{}

	// Platforms: intersection
	if len(pkg.Platforms) > 0 && len(op.AllowPlatforms) > 0 {
		opSet := make(map[string]bool)
		for _, p := range op.AllowPlatforms {
			opSet[p] = true
		}
		for _, p := range pkg.Platforms {
			if opSet[p] {
				effective.Platforms = append(effective.Platforms, p)
			}
		}
	} else if len(op.AllowPlatforms) > 0 {
		effective.Platforms = op.AllowPlatforms
	} else {
		effective.Platforms = pkg.Platforms
	}

	// refuse_root
	effective.RefuseRoot = pkg.RefuseRoot || op.RefuseRoot

	// max_age_days: minimum
	if pkg.MaxAgeDays != nil && op.MaxAgeDays != nil {
		if *pkg.MaxAgeDays < *op.MaxAgeDays {
			effective.MaxAgeDays = pkg.MaxAgeDays
		} else {
			effective.MaxAgeDays = op.MaxAgeDays
		}
	} else if pkg.MaxAgeDays != nil {
		effective.MaxAgeDays = pkg.MaxAgeDays
	} else {
		effective.MaxAgeDays = op.MaxAgeDays
	}

	effective.RequireEnv = pkg.RequireEnv
	effective.RequireTrustedKey = op.RequireTrustedKey
	effective.RequireSBOM = op.RequireSBOM

	return effective
}

// EnforcePolicy checks the effective policy against the current environment.
// Returns a descriptive error on the first violation.
func EnforcePolicy(policy EffectivePolicy, buildTimestamp int64, hasSBOM bool) error {
	currentPlatform := getCurrentPlatform()

	// 1. Platform check
	if len(policy.Platforms) > 0 {
		found := false
		for _, p := range policy.Platforms {
			if p == currentPlatform {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("platform not permitted: %s not in %v", currentPlatform, policy.Platforms)
		}
	}

	// 2. Root check
	if policy.RefuseRoot && os.Getuid() == 0 {
		return fmt.Errorf("refused to run as root")
	}

	// 3. Age check
	if policy.MaxAgeDays != nil && buildTimestamp > 0 {
		ageDays := int(time.Since(time.Unix(buildTimestamp, 0)).Hours() / 24)
		if ageDays > *policy.MaxAgeDays {
			return fmt.Errorf("package is %d days old — policy requires max %d days", ageDays, *policy.MaxAgeDays)
		}
	}

	// 4. Environment variable check
	for _, envVar := range policy.RequireEnv {
		if os.Getenv(envVar) == "" {
			return fmt.Errorf("required environment variable not set: %s", envVar)
		}
	}

	// 5. SBOM check
	if policy.RequireSBOM && !hasSBOM {
		return fmt.Errorf("package built without attestation slot — operator policy requires SBOM")
	}

	return nil
}

func getCurrentPlatform() string {
	osName := "linux"
	switch runtime.GOOS {
	case "darwin":
		osName = "darwin"
	case "windows":
		osName = "windows"
	}
	arch := "amd64"
	switch runtime.GOARCH {
	case "arm64":
		arch = "arm64"
	}
	return osName + "_" + arch
}

// ParsePackagePolicyJSON parses package-declared policy from the metadata JSON.
func ParsePackagePolicyJSON(raw []byte) (PackagePolicy, error) {
	var policy PackagePolicy
	if len(raw) == 0 {
		return policy, nil
	}
	err := json.Unmarshal(raw, &policy)
	return policy, err
}
```

- [ ] **Step 2: Wire into execution.go**

In `src/flavor-go/pkg/psp/format_2025/execution.go`, after trust check (from Plan 2), add:

```go
// Policy enforcement (Steps 3–7 of launch sequence)
opPolicy, err := LoadOperatorPolicy()
if err != nil {
    log.Printf("WARN: failed to load operator policy: %v", err)
    opPolicy = OperatorPolicy{} // permissive default
}

pkgPolicyJSON := metadata["policy"] // read from package metadata JSON
pkgPolicy, _ := ParsePackagePolicyJSON(pkgPolicyJSON)
effective := MergePolicy(pkgPolicy, opPolicy)

hasSBOM := /* check if attestation slot exists */ false
if err := EnforcePolicy(effective, int64(index.BuildTimestamp), hasSBOM); err != nil {
    return fmt.Errorf("policy violation: %w", err)
}
```

Adapt field names to match the actual index/metadata struct in this codebase.

- [ ] **Step 3: Build and verify**

```bash
cd src/flavor-go && go build ./... && go vet ./... && cd ../..
```

- [ ] **Step 4: Commit**

```bash
git add src/flavor-go/
git commit -m "feat(go): add policy enforcement at launch time"
```

---

## Task 5: Rust launcher — policy enforcement

**Files:**
- Create: `src/flavor-rs/src/psp/format_2025/policy.rs`
- Modify: `src/flavor-rs/src/psp/format_2025/mod.rs`

- [ ] **Step 1: Create `policy.rs`**

```rust
//! Launch-time policy enforcement for the Rust launcher.

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

/// Package-declared constraints (from package metadata).
#[derive(Default, Debug)]
pub struct PackagePolicy {
    pub platforms: Vec<String>,
    pub refuse_root: bool,
    pub max_age_days: Option<u64>,
    pub require_env: Vec<String>,
}

/// Operator policy (from policy.toml).
#[derive(Default, Debug)]
pub struct OperatorPolicy {
    pub require_trusted_key: bool,
    pub use_os_keychain: bool,
    pub refuse_root: bool,
    pub max_age_days: Option<u64>,
    pub allow_platforms: Vec<String>,
    pub require_sbom: bool,
}

/// Merged policy: stricter wins.
#[derive(Default, Debug)]
pub struct EffectivePolicy {
    pub platforms: Vec<String>,
    pub refuse_root: bool,
    pub max_age_days: Option<u64>,
    pub require_env: Vec<String>,
    pub require_trusted_key: bool,
    pub require_sbom: bool,
}

fn get_system_policy_path() -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        if let Ok(pd) = std::env::var("PROGRAMDATA") {
            return PathBuf::from(pd).join("flavor").join("policy.toml");
        }
        return PathBuf::from("C:\\ProgramData\\flavor\\policy.toml");
    }
    #[cfg(not(target_os = "windows"))]
    PathBuf::from("/etc/flavor/policy.toml")
}

fn get_user_policy_path() -> Option<PathBuf> {
    if let Ok(dir) = std::env::var("FLAVOR_CONFIG_DIR") {
        return Some(PathBuf::from(dir).join("policy.toml"));
    }
    if let Ok(xdg) = std::env::var("XDG_CONFIG_HOME") {
        return Some(PathBuf::from(xdg).join("flavor").join("policy.toml"));
    }
    dirs::home_dir().map(|h| h.join(".config").join("flavor").join("policy.toml"))
}

/// Parse a minimal TOML policy file. Handles only the fields FlavorPack needs.
fn parse_policy_file(content: &str, policy: &mut OperatorPolicy) {
    let mut section = String::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            section = line[1..line.len() - 1].to_lowercase();
            continue;
        }
        let parts: Vec<&str> = line.splitn(2, '=').collect();
        if parts.len() != 2 {
            continue;
        }
        let key = parts[0].trim();
        let val = parts[1].trim();
        match (section.as_str(), key) {
            ("trust", "require_trusted_key") => policy.require_trusted_key = val == "true",
            ("trust", "use_os_keychain") => policy.use_os_keychain = val == "true",
            ("execution", "refuse_root") => policy.refuse_root = val == "true",
            ("execution", "max_age_days") => {
                if let Ok(n) = val.parse::<u64>() {
                    policy.max_age_days = Some(n);
                }
            }
            ("attestation", "require_sbom") => policy.require_sbom = val == "true",
            _ => {}
        }
    }
}

/// Load operator policy from system and user files.
pub fn load_operator_policy() -> OperatorPolicy {
    let mut policy = OperatorPolicy::default();
    if let Ok(content) = fs::read_to_string(get_system_policy_path()) {
        parse_policy_file(&content, &mut policy);
    }
    if let Some(path) = get_user_policy_path() {
        if let Ok(content) = fs::read_to_string(path) {
            parse_policy_file(&content, &mut policy);
        }
    }
    policy
}

/// Merge package + operator policy. Stricter always wins.
pub fn merge_policy(pkg: PackagePolicy, op: OperatorPolicy) -> EffectivePolicy {
    let platforms = if !pkg.platforms.is_empty() && !op.allow_platforms.is_empty() {
        pkg.platforms.iter()
            .filter(|p| op.allow_platforms.contains(p))
            .cloned()
            .collect()
    } else if !op.allow_platforms.is_empty() {
        op.allow_platforms.clone()
    } else {
        pkg.platforms.clone()
    };

    let refuse_root = pkg.refuse_root || op.refuse_root;

    let max_age_days = match (pkg.max_age_days, op.max_age_days) {
        (Some(a), Some(b)) => Some(a.min(b)),
        (Some(a), None) => Some(a),
        (None, b) => b,
    };

    EffectivePolicy {
        platforms,
        refuse_root,
        max_age_days,
        require_env: pkg.require_env,
        require_trusted_key: op.require_trusted_key,
        require_sbom: op.require_sbom,
    }
}

/// Enforce policy against current runtime environment.
/// Returns Err with a descriptive message on first violation.
pub fn enforce_policy(
    policy: &EffectivePolicy,
    build_timestamp: u64,
    has_sbom: bool,
) -> Result<(), String> {
    let current_platform = get_current_platform();

    // Platform check
    if !policy.platforms.is_empty() && !policy.platforms.contains(&current_platform) {
        return Err(format!(
            "platform not permitted: {} not in {:?}",
            current_platform, policy.platforms
        ));
    }

    // Root check
    #[cfg(unix)]
    if policy.refuse_root {
        if unsafe { libc::geteuid() } == 0 {
            return Err("refused to run as root".to_string());
        }
    }

    // Age check
    if let Some(max_days) = policy.max_age_days {
        if build_timestamp > 0 {
            use std::time::{SystemTime, UNIX_EPOCH};
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            let age_days = (now.saturating_sub(build_timestamp)) / 86400;
            if age_days > max_days {
                return Err(format!(
                    "package is {} days old — policy requires max {} days",
                    age_days, max_days
                ));
            }
        }
    }

    // Environment variable check
    for var in &policy.require_env {
        if std::env::var(var).is_err() {
            return Err(format!("required environment variable not set: {}", var));
        }
    }

    // SBOM check
    if policy.require_sbom && !has_sbom {
        return Err("package built without attestation slot — operator policy requires SBOM".to_string());
    }

    Ok(())
}

fn get_current_platform() -> String {
    let os = if cfg!(target_os = "linux") {
        "linux"
    } else if cfg!(target_os = "macos") {
        "darwin"
    } else {
        "windows"
    };
    let arch = if cfg!(target_arch = "aarch64") { "arm64" } else { "amd64" };
    format!("{}_{}", os, arch)
}
```

- [ ] **Step 2: Register in `mod.rs`**

```rust
pub mod policy;
```

- [ ] **Step 3: Add `libc` to `Cargo.toml` if not present**

```toml
[target.'cfg(unix)'.dependencies]
libc = "0.2"
```

- [ ] **Step 4: Wire policy enforcement into launcher**

After the trust check (Plan 2), add:

```rust
let op_policy = policy::load_operator_policy();
let pkg_policy = policy::PackagePolicy {
    platforms: metadata.policy.platforms.clone().unwrap_or_default(),
    refuse_root: metadata.policy.refuse_root.unwrap_or(false),
    max_age_days: metadata.policy.max_age_days,
    require_env: metadata.policy.require_env.clone().unwrap_or_default(),
};
let effective = policy::merge_policy(pkg_policy, op_policy);
let has_sbom = slots.iter().any(|s| s.lifecycle == LifecycleAttestation);
policy::enforce_policy(&effective, index.build_timestamp, has_sbom)
    .map_err(|e| format!("policy violation: {}", e))?;
```

Adapt field names to match the actual index/metadata struct.

- [ ] **Step 5: Build and test**

```bash
cd src/flavor-rs && cargo build && cargo clippy -- -D warnings && cargo test && cd ../..
```

- [ ] **Step 6: Commit**

```bash
git add src/flavor-rs/
git commit -m "feat(rust): add policy enforcement at launch time"
```

---

## Task 6: Parity tests and final verification

**Files:**
- Create: `tests/parity/test_policy_parity.py`

- [ ] **Step 1: Write parity tests**

```python
# tests/parity/test_policy_parity.py
"""Parity tests for launch-time policy enforcement."""

import pytest

from flavor.config.policy import (
    EffectivePolicy,
    OperatorPolicy,
    PackagePolicy,
    merge_policy,
)


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_stricter_wins_refuse_root() -> None:
    """Operator refuse_root=true overrides package refuse_root=false."""
    pkg = PackagePolicy(refuse_root=False)
    op = OperatorPolicy(refuse_root=True)
    effective = merge_policy(pkg, op)
    assert effective.refuse_root is True


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_max_age_lower_wins() -> None:
    """Lower max_age_days always wins."""
    pkg = PackagePolicy(max_age_days=365)
    op = OperatorPolicy(max_age_days=90)
    effective = merge_policy(pkg, op)
    assert effective.max_age_days == 90


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_platform_intersection() -> None:
    """Effective platform list is intersection of package and operator."""
    pkg = PackagePolicy(platforms=["linux_amd64", "darwin_arm64"])
    op = OperatorPolicy(allow_platforms=["linux_amd64", "linux_arm64"])
    effective = merge_policy(pkg, op)
    assert effective.platforms == ["linux_amd64"]


@pytest.mark.parity
@pytest.mark.parity_category("Policy Enforcement")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_no_policy_is_permissive() -> None:
    """Empty/default policy allows execution."""
    pkg = PackagePolicy()
    op = OperatorPolicy()
    effective = merge_policy(pkg, op)
    assert effective.refuse_root is False
    assert effective.max_age_days is None
    assert effective.platforms == []
    assert effective.require_env == []
    assert effective.require_trusted_key is False
```

- [ ] **Step 2: Run full suite**

```bash
uv run pytest -x -q
uv run pytest -m parity --parity-report -v
cat reports/parity-report.md
```
Expected: "Policy Enforcement" section appears in the report

- [ ] **Step 3: Lint and type check**

```bash
uv run ruff check src/ tests/
uv run mypy src/flavor
cd src/flavor-go && go vet ./... && cd ../..
cd src/flavor-rs && cargo clippy -- -D warnings && cd ../..
```

- [ ] **Step 4: Final commit and push**

```bash
git add tests/parity/test_policy_parity.py
git commit -m "test(parity): add policy enforcement parity tests"
git push origin fix/enterprise-security-pillar3
```

---

## After all 4 plans are merged

Run the complete verification from the spec:

```bash
uv run flavor init
FLAVOR_CONFIG_DIR=/tmp/flavor-test uv run flavor init
uv run flavor trust list
uv run flavor keygen /tmp/test-key
uv run flavor trust add /tmp/test-key.pub --name "test key"
uv run flavor trust list
uv run flavor policy show
uv run pytest -m parity --parity-report -v
cat reports/parity-report.md
```
