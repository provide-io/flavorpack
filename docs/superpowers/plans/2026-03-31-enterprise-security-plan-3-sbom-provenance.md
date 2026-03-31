# Enterprise Security — Plan 3: SBOM & Provenance

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Pillar 2 — embed a CycloneDX 1.6 SBOM and build provenance record into every package as an attestation slot. Bind the slot's digest into the index block. Extend `flavor inspect` with `--sbom` and `--provenance` flags.

**Architecture:** A new `_attestation` slot (lifecycle=11) contains a single JSON file with `sbom` (CycloneDX 1.6) and `provenance` sub-keys. The builder writes `SHA-256(canonical-json)` into `index.attestation_sbom_digest`. Launchers re-hash and compare. Python does all SBOM generation; Go/Rust only compare the digest.

**Tech Stack:** Python `cyclonedx-python-lib`, `cryptography`, attrs, click. Go/Rust: SHA-256 only.

**Prerequisite:** Plan 1 complete (attestation index fields, lifecycle=11 constant).

**Spec:** `docs/superpowers/specs/2026-03-31-enterprise-security-design.md` § Pillar 2

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/flavor/psp/format_2025/sbom.py` | CycloneDX 1.6 SBOM generation |
| Create | `src/flavor/psp/format_2025/provenance.py` | Provenance record assembly |
| Create | `src/flavor/psp/format_2025/attestation.py` | Combine SBOM + provenance; compute digest |
| Modify | `src/flavor/psp/format_2025/pspf_builder.py` | Add attestation slot creation |
| Modify | `src/flavor/commands/inspect.py` | Add `--sbom` and `--provenance` options |
| Modify | `src/flavor-go/pkg/psp/format_2025/reader_verify.go` | Verify SBOM digest |
| Modify | `src/flavor-rs/src/psp/format_2025/reader.rs` | Verify SBOM digest |
| Create | `tests/format_2025/test_sbom.py` | SBOM generation tests |
| Create | `tests/format_2025/test_provenance.py` | Provenance record tests |
| Create | `tests/format_2025/test_attestation_slot.py` | Attestation slot round-trip tests |
| Create | `tests/cli/test_inspect_sbom.py` | `flavor inspect --sbom/--provenance` tests |
| Create | `tests/parity/test_sbom_parity.py` | Parity tests for digest verification |

---

## Task 1: CycloneDX SBOM generation

**Files:**
- Create: `src/flavor/psp/format_2025/sbom.py`
- Test: `tests/format_2025/test_sbom.py`

- [ ] **Step 1: Add `cyclonedx-python-lib` dependency**

In `pyproject.toml` under `[project] dependencies`:
```toml
"cyclonedx-python-lib>=7.0.0",
```

Run:
```bash
uv sync
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/format_2025/test_sbom.py
"""Tests for CycloneDX SBOM generation."""

import json
from unittest import mock

import pytest

from flavor.psp.format_2025.sbom import build_sbom


def _minimal_package_info() -> dict:
    return {
        "packages": [
            {"name": "requests", "version": "2.31.0", "purl": "pkg:pypi/requests@2.31.0",
             "hash": "sha256:abcdef0123456789" * 4, "license": "Apache-2.0"},
        ],
        "python_version": "3.11.12",
        "python_hash": "sha256:00" * 16,
        "launcher_language": "go",
        "launcher_version": "1.24.1",
        "launcher_hash": "sha256:11" * 16,
        "builder_name": "flavor-python",
        "builder_version": "0.3.21",
    }


def test_build_sbom_returns_dict() -> None:
    """build_sbom returns a dict with CycloneDX top-level keys."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.6"
    assert "components" in sbom


def test_sbom_includes_python_packages() -> None:
    """SBOM components include the Python packages."""
    info = _minimal_package_info()
    sbom = build_sbom(info)
    names = {c["name"] for c in sbom["components"]}
    assert "requests" in names


def test_sbom_includes_python_runtime() -> None:
    """SBOM components include the Python runtime."""
    sbom = build_sbom(_minimal_package_info())
    types = [c.get("type") for c in sbom["components"]]
    # At least one framework/runtime entry expected
    assert any(t in ("framework", "runtime", "library") for t in types)


def test_sbom_includes_launcher() -> None:
    """SBOM components include the launcher binary."""
    sbom = build_sbom(_minimal_package_info())
    names = {c["name"] for c in sbom["components"]}
    assert any("launcher" in n.lower() or "flavor" in n.lower() for n in names)


def test_sbom_is_json_serialisable() -> None:
    """build_sbom output is JSON-serialisable."""
    sbom = build_sbom(_minimal_package_info())
    serialised = json.dumps(sbom, sort_keys=True)
    assert len(serialised) > 100


def test_sbom_disabled_returns_none(tmp_path) -> None:
    """build_sbom returns None when sbom=False in pyproject.toml config."""
    from flavor.psp.format_2025.sbom import build_sbom
    result = build_sbom(_minimal_package_info(), enabled=False)
    assert result is None
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
uv run pytest tests/format_2025/test_sbom.py -v
```
Expected: ImportError

- [ ] **Step 4: Create `src/flavor/psp/format_2025/sbom.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""CycloneDX 1.6 SBOM generation for PSPF attestation slots."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def build_sbom(
    package_info: dict[str, Any],
    *,
    enabled: bool = True,
) -> dict[str, Any] | None:
    """Build a CycloneDX 1.6 SBOM document.

    Args:
        package_info: Dict with keys:
            packages: list of {name, version, purl, hash, license}
            python_version: str
            python_hash: str
            launcher_language: str ("go" or "rust")
            launcher_version: str
            launcher_hash: str
            builder_name: str
            builder_version: str
        enabled: If False, returns None (opt-out support).

    Returns:
        CycloneDX 1.6 SBOM as a dict, or None if disabled.
    """
    if not enabled:
        return None

    components: list[dict[str, Any]] = []

    # Python packages
    for pkg in package_info.get("packages", []):
        component: dict[str, Any] = {
            "type": "library",
            "name": pkg["name"],
            "version": pkg["version"],
            "purl": pkg["purl"],
        }
        if pkg.get("license"):
            component["licenses"] = [{"expression": pkg["license"]}]
        if pkg.get("hash"):
            alg, value = pkg["hash"].split(":", 1) if ":" in pkg["hash"] else ("SHA-256", pkg["hash"])
            component["hashes"] = [{"alg": alg.upper(), "content": value}]
        components.append(component)

    # Python runtime
    py_version = package_info.get("python_version", "unknown")
    py_component: dict[str, Any] = {
        "type": "framework",
        "name": "python",
        "version": py_version,
        "description": "CPython runtime interpreter",
    }
    if package_info.get("python_hash"):
        alg, value = package_info["python_hash"].split(":", 1) if ":" in package_info["python_hash"] else ("SHA-256", package_info["python_hash"])
        py_component["hashes"] = [{"alg": alg.upper(), "content": value}]
    components.append(py_component)

    # Launcher binary
    launcher_lang = package_info.get("launcher_language", "unknown")
    launcher_component: dict[str, Any] = {
        "type": "application",
        "name": f"flavor-{launcher_lang}-launcher",
        "version": package_info.get("launcher_version", "unknown"),
        "description": f"PSPF launcher binary ({launcher_lang})",
    }
    if package_info.get("launcher_hash"):
        alg, value = package_info["launcher_hash"].split(":", 1) if ":" in package_info["launcher_hash"] else ("SHA-256", package_info["launcher_hash"])
        launcher_component["hashes"] = [{"alg": alg.upper(), "content": value}]
    components.append(launcher_component)

    # FlavorPack builder
    components.append({
        "type": "application",
        "name": package_info.get("builder_name", "flavor-python"),
        "version": package_info.get("builder_version", "unknown"),
        "description": "FlavorPack PSPF builder",
    })

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [
                {"vendor": "provide.io", "name": "flavorpack", "version": package_info.get("builder_version", "unknown")}
            ],
        },
        "components": components,
    }


# 🌶️📦🔚
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run pytest tests/format_2025/test_sbom.py -v
```
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/flavor/psp/format_2025/sbom.py tests/format_2025/test_sbom.py pyproject.toml uv.lock
git commit -m "feat(sbom): add CycloneDX 1.6 SBOM generation"
```

---

## Task 2: Provenance record

**Files:**
- Create: `src/flavor/psp/format_2025/provenance.py`
- Test: `tests/format_2025/test_provenance.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/format_2025/test_provenance.py
"""Tests for provenance record assembly."""

import pytest

from flavor.psp.format_2025.provenance import build_provenance


def test_provenance_has_required_fields() -> None:
    """Provenance record contains all spec-required fields."""
    prov = build_provenance(
        builder_name="flavor-python",
        builder_version="0.3.21",
        build_timestamp=1743379200,
        platform_os="linux",
        platform_arch="amd64",
        python_version="3.11.12",
        launcher_language="go",
        launcher_version="1.24.1",
        launcher_hash="sha256:" + "ab" * 32,
        signing_key_fingerprint="cd" * 32,
    )
    assert prov["builder"] == "flavor-python"
    assert prov["builder_version"] == "0.3.21"
    assert prov["build_timestamp"] == "2026-03-31T00:00:00+00:00"
    assert prov["platform"]["os"] == "linux"
    assert prov["platform"]["arch"] == "amd64"
    assert prov["python"]["version"] == "3.11.12"
    assert prov["launcher"]["language"] == "go"
    assert prov["signing_key_fingerprint"] == "cd" * 32


def test_provenance_reproducible_flag() -> None:
    """reproducible is True when SOURCE_DATE_EPOCH is set."""
    import os
    from unittest import mock
    with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1743379200"}):
        prov = build_provenance(
            builder_name="x", builder_version="1", build_timestamp=1743379200,
            platform_os="linux", platform_arch="amd64", python_version="3.11",
            launcher_language="go", launcher_version="1.24", launcher_hash="",
            signing_key_fingerprint="",
        )
    assert prov["reproducible"] is True
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/format_2025/test_provenance.py -v
```
Expected: ImportError

- [ ] **Step 3: Create `src/flavor/psp/format_2025/provenance.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Provenance record assembly for PSPF attestation slots."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


def build_provenance(
    *,
    builder_name: str,
    builder_version: str,
    build_timestamp: int,
    platform_os: str,
    platform_arch: str,
    python_version: str,
    launcher_language: str,
    launcher_version: str,
    launcher_hash: str,
    signing_key_fingerprint: str,
) -> dict[str, Any]:
    """Assemble a provenance record.

    Args:
        build_timestamp: Unix timestamp (seconds since epoch) — use SOURCE_DATE_EPOCH
                         when set for reproducible builds.

    Returns:
        Provenance record dict, JSON-serialisable.
    """
    ts = datetime.fromtimestamp(build_timestamp, tz=timezone.utc).isoformat()
    source_date_epoch_str = os.environ.get("SOURCE_DATE_EPOCH", "")
    reproducible = bool(source_date_epoch_str.strip())

    return {
        "builder": builder_name,
        "builder_version": builder_version,
        "build_timestamp": ts,
        "source_date_epoch": build_timestamp,
        "platform": {
            "os": platform_os,
            "arch": platform_arch,
        },
        "python": {
            "version": python_version,
            "implementation": "cpython",
        },
        "launcher": {
            "language": launcher_language,
            "version": launcher_version,
            "hash": launcher_hash,
        },
        "signing_key_fingerprint": signing_key_fingerprint,
        "reproducible": reproducible,
    }


# 🌶️📦🔚
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/format_2025/test_provenance.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/flavor/psp/format_2025/provenance.py tests/format_2025/test_provenance.py
git commit -m "feat(provenance): add build provenance record assembly"
```

---

## Task 3: Attestation slot — combine, canonicalise, digest

**Files:**
- Create: `src/flavor/psp/format_2025/attestation.py`
- Test: `tests/format_2025/test_attestation_slot.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/format_2025/test_attestation_slot.py
"""Tests for attestation slot assembly and digest."""

import hashlib
import json

from flavor.psp.format_2025.attestation import build_attestation_payload, compute_attestation_digest


def test_attestation_payload_has_sbom_and_provenance() -> None:
    """Attestation payload contains both 'sbom' and 'provenance' keys."""
    payload = build_attestation_payload(
        sbom={"bomFormat": "CycloneDX", "specVersion": "1.6", "components": []},
        provenance={"builder": "x", "builder_version": "1"},
    )
    assert "sbom" in payload
    assert "provenance" in payload


def test_attestation_digest_is_sha256_of_canonical_json() -> None:
    """Digest is SHA-256 of sorted-keys, no trailing whitespace JSON."""
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "components": []}
    prov = {"builder": "x"}
    payload = build_attestation_payload(sbom=sbom, provenance=prov)
    digest = compute_attestation_digest(payload)

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(canonical.encode()).hexdigest()
    assert digest == expected


def test_attestation_digest_is_64_hex_chars() -> None:
    """Digest is exactly 64 lowercase hex characters."""
    payload = build_attestation_payload(
        sbom={"bomFormat": "CycloneDX", "specVersion": "1.6", "components": []},
        provenance={},
    )
    digest = compute_attestation_digest(payload)
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_no_sbom_returns_provenance_only() -> None:
    """When sbom=None (disabled), payload only contains provenance."""
    payload = build_attestation_payload(sbom=None, provenance={"builder": "x"})
    assert "sbom" not in payload
    assert "provenance" in payload
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/format_2025/test_attestation_slot.py -v
```
Expected: ImportError

- [ ] **Step 3: Create `src/flavor/psp/format_2025/attestation.py`**

```python
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Attestation slot assembly: combines SBOM + provenance and computes digest."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def build_attestation_payload(
    *,
    sbom: dict[str, Any] | None,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Combine SBOM and provenance into an attestation payload dict.

    Args:
        sbom: CycloneDX SBOM dict, or None if SBOM generation is disabled.
        provenance: Provenance record dict.

    Returns:
        Attestation payload — JSON-serialisable, ready for digest computation.
    """
    payload: dict[str, Any] = {"provenance": provenance}
    if sbom is not None:
        payload["sbom"] = sbom
    return payload


def compute_attestation_digest(payload: dict[str, Any]) -> str:
    """Compute the SHA-256 digest of the canonical attestation JSON.

    Canonical form: keys sorted, no trailing whitespace, no extra spaces.

    Returns:
        64-character lowercase hex string.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def serialise_attestation(payload: dict[str, Any]) -> bytes:
    """Serialise attestation payload to bytes for slot storage."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), indent=2).encode()


# 🌶️📦🔚
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/format_2025/test_attestation_slot.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/flavor/psp/format_2025/attestation.py tests/format_2025/test_attestation_slot.py
git commit -m "feat(attestation): add payload assembly and digest computation"
```

---

## Task 4: Wire attestation into PSPFBuilder

**Files:**
- Modify: `src/flavor/psp/format_2025/pspf_builder.py`

- [ ] **Step 1: Identify where slots are added in PSPFBuilder**

```bash
grep -n "add_slot\|_slots\|with_slot" src/flavor/psp/format_2025/pspf_builder.py | head -20
```

- [ ] **Step 2: Write an integration test**

```python
# tests/format_2025/test_attestation_builder_integration.py
"""Tests that PSPFBuilder writes the attestation slot and index digest."""

import pytest
from pathlib import Path

from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.constants import LIFECYCLE_ATTESTATION


@pytest.mark.integration
def test_built_package_has_attestation_slot(built_package_path: Path) -> None:
    """A built package has a slot with lifecycle=attestation."""
    with PSPFReader(built_package_path) as reader:
        metadata = reader.read_metadata()

    slots = metadata.get("slots", [])
    attestation_slots = [s for s in slots if s.get("lifecycle") == "attestation"]
    assert len(attestation_slots) == 1, f"Expected 1 attestation slot, got {len(attestation_slots)}"


@pytest.mark.integration
def test_built_package_attestation_digest_matches(built_package_path: Path) -> None:
    """The index attestation_sbom_digest matches SHA-256 of the attestation slot content."""
    import hashlib
    import json

    with PSPFReader(built_package_path) as reader:
        index = reader.read_index()
        metadata = reader.read_metadata()

    digest_bytes = index.attestation_sbom_digest.rstrip(b"\x00")
    if not digest_bytes:
        pytest.skip("Package built without attestation (SBOM disabled)")

    expected_digest = digest_bytes.decode("ascii")

    # Find and read the attestation slot
    slots = metadata.get("slots", [])
    att_slot = next((s for s in slots if s.get("lifecycle") == "attestation"), None)
    assert att_slot is not None

    # Read the slot content — this depends on how PSPFReader extracts slots
    # Adjust to match actual reader API
    slot_content = reader.read_slot_content(att_slot["id"])
    actual_digest = hashlib.sha256(slot_content).hexdigest()
    assert actual_digest == expected_digest
```

Note: if `built_package_path` fixture or `reader.read_slot_content()` does not exist, mark with `@pytest.mark.skip` and implement the fixture in the integration conftest.

- [ ] **Step 3: Extend PSPFBuilder to generate attestation slot**

In `pspf_builder.py`, find the `pack()` method or equivalent final assembly step. After all slots are added, add attestation slot generation:

```python
# Generate attestation slot (if not opted out)
if self._spec.get("sbom", True):  # default enabled
    from flavor.psp.format_2025.sbom import build_sbom
    from flavor.psp.format_2025.provenance import build_provenance
    from flavor.psp.format_2025.attestation import (
        build_attestation_payload,
        compute_attestation_digest,
        serialise_attestation,
    )
    import tempfile, os

    pkg_info = self._collect_sbom_package_info()  # implement below
    sbom = build_sbom(pkg_info)
    provenance = build_provenance(
        builder_name=self._builder_name,
        builder_version=self._builder_version,
        build_timestamp=self._build_timestamp,
        platform_os=self._platform_os,
        platform_arch=self._platform_arch,
        python_version=self._python_version,
        launcher_language=self._launcher_language,
        launcher_version=self._launcher_version,
        launcher_hash=self._launcher_hash,
        signing_key_fingerprint=self._signing_key_fingerprint,
    )
    payload = build_attestation_payload(sbom=sbom, provenance=provenance)
    digest = compute_attestation_digest(payload)
    content = serialise_attestation(payload)

    # Write attestation slot content to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(content)
        att_path = f.name
    self._temp_files.append(att_path)

    # Store digest in index
    self._index.attestation_sbom_digest = digest.encode("ascii").ljust(64, b"\x00")[:64]

    # Add the attestation slot (id="_attestation", lifecycle=11)
    # Adapt to the actual add_slot() signature in this builder
```

Implement `_collect_sbom_package_info()` to gather wheel metadata from `self._installed_packages` or equivalent. The exact implementation depends on the existing builder internals — read the file carefully before writing this method.

- [ ] **Step 4: Run the integration test**

```bash
uv run pytest tests/format_2025/test_attestation_builder_integration.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/flavor/psp/format_2025/pspf_builder.py tests/format_2025/test_attestation_builder_integration.py
git commit -m "feat(builder): write attestation slot and index digest"
```

---

## Task 5: `flavor inspect --sbom / --provenance`

**Files:**
- Modify: `src/flavor/commands/inspect.py`
- Test: `tests/cli/test_inspect_sbom.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/cli/test_inspect_sbom.py
"""Tests for flavor inspect --sbom and --provenance flags."""

import json
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from flavor.cli import cli


@pytest.mark.integration
def test_inspect_sbom_prints_cyclonedx(built_package_path: Path) -> None:
    """--sbom flag prints valid CycloneDX JSON to stdout."""
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", str(built_package_path), "--sbom"])
    assert result.exit_code == 0, result.output
    sbom = json.loads(result.output)
    assert sbom["bomFormat"] == "CycloneDX"


@pytest.mark.integration
def test_inspect_provenance_prints_record(built_package_path: Path) -> None:
    """--provenance flag prints provenance JSON to stdout."""
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", str(built_package_path), "--provenance"])
    assert result.exit_code == 0, result.output
    prov = json.loads(result.output)
    assert "builder" in prov
    assert "build_timestamp" in prov


@pytest.mark.integration
def test_inspect_sbom_no_attestation_prints_warning(tmp_path: Path, old_package_path: Path) -> None:
    """Packages without attestation slot print a clear warning."""
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", str(old_package_path), "--sbom"])
    assert "attestation" in result.output.lower() or result.exit_code != 0
```

Note: `built_package_path` and `old_package_path` are integration fixtures. Skip if unavailable.

- [ ] **Step 2: Add `--sbom` and `--provenance` options to `inspect_command`**

In `src/flavor/commands/inspect.py`, add two new options to the `inspect_command`:

```python
@click.option("--sbom", "show_sbom", is_flag=True, help="Print the CycloneDX SBOM to stdout.")
@click.option("--provenance", "show_provenance", is_flag=True, help="Print the provenance record to stdout.")
```

In the command body, after reading the reader:

```python
if show_sbom or show_provenance:
    # Find attestation slot
    att_slot = next(
        (s for s in slots_metadata if s.get("lifecycle") == "attestation"), None
    )
    if att_slot is None:
        perr("Package has no attestation slot (built with old FlavorPack or SBOM disabled).")
        raise SystemExit(2)

    att_content = reader.read_slot_content(att_slot["id"])
    att_payload = json.loads(att_content)

    if show_sbom:
        if "sbom" not in att_payload:
            perr("Attestation slot has no SBOM (built with sbom = false).")
            raise SystemExit(2)
        pout(json.dumps(att_payload["sbom"], indent=2))
        return

    if show_provenance:
        pout(json.dumps(att_payload.get("provenance", {}), indent=2))
        return
```

Add `import json` to the imports if not already there.

- [ ] **Step 3: Run tests (skip integration ones)**

```bash
uv run pytest tests/cli/test_inspect_sbom.py -v -k "not integration"
uv run pytest tests/cli/test_inspect_sbom.py -v  # runs integration too if fixtures exist
```

- [ ] **Step 4: Commit**

```bash
git add src/flavor/commands/inspect.py tests/cli/test_inspect_sbom.py
git commit -m "feat(cli): add flavor inspect --sbom and --provenance flags"
```

---

## Task 6: Go/Rust — SBOM digest verification

**Files:**
- Modify: `src/flavor-go/pkg/psp/format_2025/reader_verify.go`
- Modify: `src/flavor-rs/src/psp/format_2025/reader.rs`

Go and Rust launchers do NOT parse the SBOM JSON — they only re-hash the attestation slot content and compare to `index.attestation_sbom_digest`.

- [ ] **Step 1: Go — add SBOM digest verification**

In `src/flavor-go/pkg/psp/format_2025/reader_verify.go`, after reading the attestation slot content, add:

```go
// Verify SBOM digest (if attestation_sbom_digest is set)
digestBytes := index.AttestationSbomDigest
digestStr := strings.TrimRight(string(digestBytes[:]), "\x00")
if digestStr != "" {
    actualHash := sha256.Sum256(attestationSlotContent)
    actualHex := hex.EncodeToString(actualHash[:])
    if actualHex != digestStr {
        return fmt.Errorf("attestation SBOM digest mismatch: index says %s, computed %s",
            digestStr[:16], actualHex[:16])
    }
}
```

Add `index.AttestationSbomDigest [64]byte` to the Go index struct (alongside `AttestationKeyFp` added in Plan 2).

- [ ] **Step 2: Rust — add SBOM digest verification**

In `src/flavor-rs/src/psp/format_2025/reader.rs`, after extracting the attestation slot:

```rust
// Verify SBOM digest
let digest_bytes = &index.attestation_sbom_digest;
let digest_str = std::str::from_utf8(digest_bytes)
    .unwrap_or("")
    .trim_end_matches('\0');
if !digest_str.is_empty() {
    use sha2::{Digest, Sha256};
    let actual_hash = hex::encode(Sha256::digest(&attestation_slot_content));
    if actual_hash != digest_str {
        return Err(format!(
            "attestation SBOM digest mismatch: index says {}..., computed {}...",
            &digest_str[..16], &actual_hash[..16]
        ).into());
    }
}
```

- [ ] **Step 3: Build both**

```bash
cd src/flavor-go && go build ./... && go vet ./... && cd ../..
cd src/flavor-rs && cargo build && cargo clippy -- -D warnings && cd ../..
```

- [ ] **Step 4: Parity tests**

```python
# tests/parity/test_sbom_parity.py
"""Parity tests for SBOM digest verification."""
import pytest


@pytest.mark.parity
@pytest.mark.parity_category("SBOM Digest Verification")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_sbom_digest_computed_correctly() -> None:
    """attestation_sbom_digest matches SHA-256 of canonical attestation JSON."""
    import hashlib, json
    from flavor.psp.format_2025.attestation import (
        build_attestation_payload,
        compute_attestation_digest,
        serialise_attestation,
    )

    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "components": []}
    prov = {"builder": "test"}
    payload = build_attestation_payload(sbom=sbom, provenance=prov)

    # compute_attestation_digest uses canonical JSON (sort_keys, no spaces)
    digest = compute_attestation_digest(payload)
    # verify: SHA-256 of the canonical form
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    assert digest == hashlib.sha256(canonical.encode()).hexdigest()


@pytest.mark.parity
@pytest.mark.parity_category("SBOM Digest Verification")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_sbom_absent_is_not_an_error() -> None:
    """Packages without attestation_sbom_digest pass digest check (backwards compat)."""
    from flavor.psp.format_2025.index import PSPFIndex
    idx = PSPFIndex()
    # All zeros = no digest = skip check
    assert idx.attestation_sbom_digest == b"\x00" * 64
```

```bash
uv run pytest tests/parity/test_sbom_parity.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/flavor-go/ src/flavor-rs/ tests/parity/test_sbom_parity.py
git commit -m "feat(go,rust): verify SBOM digest at launch time"
```

---

## Task 7: Final verification

- [ ] **Step 1: Full test suite**

```bash
uv run pytest -x -q
uv run pytest -m parity --parity-report -v
```

- [ ] **Step 2: Lint and type check**

```bash
uv run ruff check src/ tests/
uv run mypy src/flavor
cd src/flavor-go && go vet ./... && cd ../..
cd src/flavor-rs && cargo clippy -- -D warnings && cd ../..
```

- [ ] **Step 3: Manual smoke test**

```bash
# Build a test package
FLAVOR_INCLUDE_BUILD_HOST=0 uv run flavor pack tests/assets/hello_world/ -o /tmp/test.psp

# Inspect SBOM
uv run flavor inspect /tmp/test.psp --sbom | head -20

# Inspect provenance
uv run flavor inspect /tmp/test.psp --provenance
```

- [ ] **Step 4: Push**

```bash
git push origin fix/enterprise-security-pillar2
```
