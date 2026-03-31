#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""CycloneDX 1.6 SBOM generation for PSPF attestation slots."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

_ALG_NORMALIZE = {
    "SHA256": "SHA-256",
    "SHA512": "SHA-512",
    "SHA384": "SHA-384",
    "SHA1": "SHA-1",
    "MD5": "MD5",
}


def _parse_hash(hash_str: str) -> tuple[str, str]:
    """Parse a hash string into (algorithm, value) tuple.

    Handles both "alg:value" format and plain hash values.
    """
    if ":" in hash_str:
        alg, value = hash_str.split(":", 1)
        alg = _ALG_NORMALIZE.get(alg.upper(), alg.upper())
        return alg, value
    return "SHA-256", hash_str


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
            alg, value = _parse_hash(pkg["hash"])
            component["hashes"] = [{"alg": alg, "content": value}]
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
        alg, value = _parse_hash(package_info["python_hash"])
        py_component["hashes"] = [{"alg": alg, "content": value}]
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
        alg, value = _parse_hash(package_info["launcher_hash"])
        launcher_component["hashes"] = [{"alg": alg, "content": value}]
    components.append(launcher_component)

    # FlavorPack builder
    components.append(
        {
            "type": "application",
            "name": package_info.get("builder_name", "flavor-python"),
            "version": package_info.get("builder_version", "unknown"),
            "description": "FlavorPack PSPF builder",
        }
    )

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "tools": [
                {
                    "vendor": "provide.io",
                    "name": "flavorpack",
                    "version": package_info.get("builder_version", "unknown"),
                }
            ],
        },
        "components": components,
    }


# 🌶️📦🔚
