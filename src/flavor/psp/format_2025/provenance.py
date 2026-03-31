#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Provenance record assembly for PSPF attestation slots."""

from __future__ import annotations

from datetime import UTC, datetime
import os
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
    signing_key_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Assemble a provenance record.

    Args:
        builder_name: Name of the builder tool (e.g. "flavor-python").
        builder_version: Version of the builder tool.
        build_timestamp: Unix timestamp (seconds since epoch). When
            SOURCE_DATE_EPOCH is set in the environment, pass its value
            here for reproducible builds.
        platform_os: Target operating system (e.g. "linux", "darwin").
        platform_arch: Target architecture (e.g. "amd64", "arm64").
        python_version: Python interpreter version string.
        launcher_language: Language of the launcher binary ("go" or "rust").
        launcher_version: Version of the launcher binary.
        launcher_hash: Hash of the launcher binary (e.g. "sha256:<hex>").
        signing_key_fingerprint: Hex fingerprint of the signing key, or
            None if the package is unsigned.

    Returns:
        Provenance record dict, JSON-serialisable.
    """
    ts = datetime.fromtimestamp(build_timestamp, tz=UTC).isoformat()
    source_date_epoch_str = os.environ.get("SOURCE_DATE_EPOCH", "")
    reproducible = bool(source_date_epoch_str.strip())

    record: dict[str, Any] = {
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
        "reproducible": reproducible,
    }

    if signing_key_fingerprint is not None:
        record["signing_attestation_key_fp"] = f"sha256:{signing_key_fingerprint}"
    else:
        record["signing_attestation_key_fp"] = None

    return record


# 🌶️📦🔚
