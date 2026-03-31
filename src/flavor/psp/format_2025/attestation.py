#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Attestation slot assembly: combines SBOM + provenance and computes the slot digest."""

from __future__ import annotations

import hashlib
import json
from typing import Any, cast

from flavor.psp.format_2025.provenance import build_provenance
from flavor.psp.format_2025.sbom import build_sbom


def build_attestation(
    package_info: dict[str, Any],
    *,
    signing_key_fingerprint: str | None = None,
    sbom_enabled: bool = True,
) -> tuple[bytes, str]:
    """Build the attestation slot content and compute its SHA-256 digest.

    ``package_info`` is passed to :func:`build_sbom` as-is.  The provenance
    record is assembled from the individual fields extracted from
    ``package_info`` so that callers only need to supply a single dict.

    Args:
        package_info: Dict with keys understood by :func:`build_sbom` plus:
            builder_name, builder_version, build_timestamp, platform_os,
            platform_arch, python_version, launcher_language, launcher_version,
            launcher_hash.
        signing_key_fingerprint: Hex fingerprint of the Ed25519 signing key,
            or ``None`` / empty string for unsigned packages.
        sbom_enabled: When *False* the ``sbom`` key is omitted from the
            attestation (opt-out support).

    Returns:
        A 2-tuple of:

        * **content_bytes** - canonical JSON (UTF-8, sorted keys, no extra
          whitespace) to be written as the attestation slot file.
        * **hex_digest** - SHA-256 of *content_bytes*, hex-encoded (64 chars).
    """
    sbom = build_sbom(package_info, enabled=sbom_enabled)

    provenance = build_provenance(
        builder_name=package_info.get("builder_name", "flavor-python"),
        builder_version=package_info.get("builder_version", "unknown"),
        build_timestamp=int(package_info.get("build_timestamp", 0)),
        platform_os=package_info.get("platform_os", "unknown"),
        platform_arch=package_info.get("platform_arch", "unknown"),
        python_version=package_info.get("python_version", "unknown"),
        launcher_language=package_info.get("launcher_language", "unknown"),
        launcher_version=package_info.get("launcher_version", "unknown"),
        launcher_hash=package_info.get("launcher_hash", ""),
        signing_key_fingerprint=signing_key_fingerprint or None,
    )

    attestation: dict[str, Any] = {"provenance": provenance}
    if sbom is not None:
        attestation["sbom"] = sbom

    content_bytes = json.dumps(attestation, sort_keys=True, separators=(",", ":")).encode("utf-8")
    hex_digest = hashlib.sha256(content_bytes).hexdigest()

    return content_bytes, hex_digest


def parse_attestation(content_bytes: bytes) -> dict[str, Any]:
    """Parse attestation slot content bytes into a dict."""
    return cast(dict[str, Any], json.loads(content_bytes.decode("utf-8")))


# 🌶️📦🔚
