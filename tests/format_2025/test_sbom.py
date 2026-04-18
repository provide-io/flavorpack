# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for CycloneDX 1.6 SBOM generation."""

from __future__ import annotations

import json
from typing import Any

from flavor.psp.format_2025.sbom import build_sbom


def _minimal_package_info() -> dict[str, Any]:
    return {
        "packages": [
            {
                "name": "requests",
                "version": "2.31.0",
                "purl": "pkg:pypi/requests@2.31.0",
                "hash": "sha256:" + "abcdef0123456789" * 4,
                "license": "Apache-2.0",
            },
        ],
        "python_version": "3.11.12",
        "python_hash": "sha256:" + "00" * 16,
        "launcher_language": "go",
        "launcher_version": "1.24.1",
        "launcher_hash": "sha256:" + "11" * 16,
        "builder_name": "flavor-python",
        "builder_version": "0.3.21",
    }


def test_build_sbom_returns_dict() -> None:
    """build_sbom returns a dict with CycloneDX top-level keys."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.6"
    assert "components" in sbom


def test_sbom_has_serial_number() -> None:
    """SBOM has a URN serialNumber."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    assert sbom["serialNumber"].startswith("urn:uuid:")


def test_sbom_has_metadata_timestamp() -> None:
    """SBOM metadata contains a timestamp and tools list."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    assert "timestamp" in sbom["metadata"]
    assert len(sbom["metadata"]["tools"]) == 1
    assert sbom["metadata"]["tools"][0]["vendor"] == "provide.io"


def test_sbom_includes_python_packages() -> None:
    """SBOM components include the Python packages from input."""
    info = _minimal_package_info()
    sbom = build_sbom(info)
    assert sbom is not None
    names = {c["name"] for c in sbom["components"]}
    assert "requests" in names


def test_sbom_package_has_purl_and_hash() -> None:
    """Package component has purl and hashes fields."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    pkg_component = next(c for c in sbom["components"] if c["name"] == "requests")
    assert pkg_component["purl"] == "pkg:pypi/requests@2.31.0"
    assert len(pkg_component["hashes"]) == 1
    assert pkg_component["hashes"][0]["alg"] == "SHA-256"


def test_sbom_package_has_license() -> None:
    """Package component with license has licenses field."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    pkg_component = next(c for c in sbom["components"] if c["name"] == "requests")
    assert pkg_component["licenses"] == [{"expression": "Apache-2.0"}]


def test_sbom_includes_python_runtime() -> None:
    """SBOM components include the Python runtime framework component."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    framework_components = [c for c in sbom["components"] if c.get("type") == "framework"]
    assert len(framework_components) >= 1
    python_component = next((c for c in framework_components if c["name"] == "python"), None)
    assert python_component is not None
    assert python_component["version"] == "3.11.12"


def test_sbom_python_runtime_has_hash() -> None:
    """Python runtime component includes hashes when python_hash is provided."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    python_component = next(c for c in sbom["components"] if c["name"] == "python")
    assert "hashes" in python_component
    assert python_component["hashes"][0]["alg"] == "SHA-256"


def test_sbom_includes_launcher() -> None:
    """SBOM components include the launcher binary."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    names = {c["name"] for c in sbom["components"]}
    assert any("launcher" in n.lower() for n in names)


def test_sbom_launcher_has_correct_name() -> None:
    """Launcher component name reflects the launcher_language."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    launcher = next(c for c in sbom["components"] if "launcher" in c["name"])
    assert launcher["name"] == "flavor-go-launcher"
    assert launcher["version"] == "1.24.1"


def test_sbom_launcher_has_hash() -> None:
    """Launcher component includes hashes when launcher_hash is provided."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    launcher = next(c for c in sbom["components"] if "launcher" in c["name"])
    assert "hashes" in launcher
    assert launcher["hashes"][0]["alg"] == "SHA-256"


def test_sbom_includes_builder() -> None:
    """SBOM components include the Flavorpack builder."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    builder = next(c for c in sbom["components"] if c.get("name") == "flavor-python")
    assert builder["version"] == "0.3.21"
    assert builder["description"] == "Flavorpack PSPF builder"


def test_sbom_is_json_serialisable() -> None:
    """build_sbom output is JSON-serialisable."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    serialised = json.dumps(sbom, sort_keys=True)
    assert len(serialised) > 100


def test_sbom_disabled_returns_none() -> None:
    """build_sbom returns None when enabled=False."""
    result = build_sbom(_minimal_package_info(), enabled=False)
    assert result is None


def test_sbom_empty_packages_list() -> None:
    """build_sbom works with an empty packages list."""
    info: dict[str, Any] = {
        "packages": [],
        "python_version": "3.11.0",
        "builder_version": "0.1.0",
    }
    sbom = build_sbom(info)
    assert sbom is not None
    assert sbom["bomFormat"] == "CycloneDX"
    # Should have python runtime + launcher + builder (3 components minimum)
    assert len(sbom["components"]) >= 3


def test_sbom_no_packages_key() -> None:
    """build_sbom works when 'packages' key is absent."""
    info: dict[str, Any] = {
        "python_version": "3.12.0",
        "builder_version": "0.2.0",
    }
    sbom = build_sbom(info)
    assert sbom is not None
    assert "components" in sbom


def test_sbom_no_python_hash() -> None:
    """Python component has no hashes when python_hash is absent."""
    info = _minimal_package_info()
    del info["python_hash"]
    sbom = build_sbom(info)
    assert sbom is not None
    python_component = next(c for c in sbom["components"] if c["name"] == "python")
    assert "hashes" not in python_component


def test_sbom_no_launcher_hash() -> None:
    """Launcher component has no hashes when launcher_hash is absent."""
    info = _minimal_package_info()
    del info["launcher_hash"]
    sbom = build_sbom(info)
    assert sbom is not None
    launcher = next(c for c in sbom["components"] if "launcher" in c["name"])
    assert "hashes" not in launcher


def test_sbom_hash_without_colon_prefix() -> None:
    """Hash strings without ':' separator default to SHA-256 algorithm."""
    info = _minimal_package_info()
    # Set hashes without the "alg:" prefix
    info["python_hash"] = "deadbeef" * 8
    info["launcher_hash"] = "cafebabe" * 8
    info["packages"][0]["hash"] = "feedface" * 8
    sbom = build_sbom(info)
    assert sbom is not None
    python_component = next(c for c in sbom["components"] if c["name"] == "python")
    assert python_component["hashes"][0]["alg"] == "SHA-256"
    assert python_component["hashes"][0]["content"] == "deadbeef" * 8

    launcher = next(c for c in sbom["components"] if "launcher" in c["name"])
    assert launcher["hashes"][0]["alg"] == "SHA-256"

    pkg = next(c for c in sbom["components"] if c["name"] == "requests")
    assert pkg["hashes"][0]["alg"] == "SHA-256"


def test_sbom_package_without_hash() -> None:
    """Package component without hash field has no hashes entry."""
    info = _minimal_package_info()
    del info["packages"][0]["hash"]
    sbom = build_sbom(info)
    assert sbom is not None
    pkg = next(c for c in sbom["components"] if c["name"] == "requests")
    assert "hashes" not in pkg


def test_sbom_package_without_license() -> None:
    """Package component without license has no licenses entry."""
    info = _minimal_package_info()
    del info["packages"][0]["license"]
    sbom = build_sbom(info)
    assert sbom is not None
    pkg = next(c for c in sbom["components"] if c["name"] == "requests")
    assert "licenses" not in pkg


def test_sbom_defaults_for_missing_info_keys() -> None:
    """build_sbom uses sensible defaults when optional keys are missing."""
    sbom = build_sbom({})
    assert sbom is not None
    python_component = next(c for c in sbom["components"] if c["name"] == "python")
    assert python_component["version"] == "unknown"
    launcher = next(c for c in sbom["components"] if "launcher" in c["name"])
    assert launcher["name"] == "flavor-unknown-launcher"
    builder = next(c for c in sbom["components"] if c.get("description") == "Flavorpack PSPF builder")
    assert builder["name"] == "flavor-python"
    assert builder["version"] == "unknown"
