#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""The launcher hash carries its algorithm prefix exactly once.

``format_checksum`` returns a value that already reads ``sha256:<hex>``. It is
imported into the builder under the name ``calculate_checksum``, which reads
like it returns a bare digest, and one of the three call sites adds a prefix of
its own. The result reaches metadata, the SBOM and the attestation.

FEP-0002 §7.4 gives the grammar: the prefix appears once.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

from provide.foundation.crypto import format_checksum
import pytest

from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.sbom import build_sbom

CHECKSUM = re.compile(r"^[a-z0-9]+:[0-9a-fA-F]+$")
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


def test_format_checksum_already_carries_the_prefix() -> None:
    """The premise: a caller that adds ``sha256:`` is adding a second one."""
    assert format_checksum(b"x", "sha256").startswith("sha256:")
    assert CHECKSUM.match(format_checksum(b"x", "sha256"))


def test_builder_launcher_hash_has_one_prefix() -> None:
    """The value the builder stores matches the FEP-0002 §7.4 grammar."""
    launcher_hash = format_checksum(b"launcher bytes", "sha256")

    assert CHECKSUM.match(launcher_hash), launcher_hash
    assert launcher_hash.count(":") == 1, launcher_hash
    algorithm, digest = launcher_hash.split(":", 1)
    assert algorithm == "sha256"
    assert SHA256_HEX.match(digest), digest


def test_sbom_records_a_hash_a_consumer_can_use() -> None:
    """A doubled prefix survives into the SBOM as a hash that is not a digest.

    ``_parse_hash`` splits on the first colon, so ``sha256:sha256:<hex>`` yields
    a content field of ``sha256:<hex>`` under an algorithm of ``SHA-256``. That
    is a CycloneDX hash entry whose content is not hexadecimal.
    """
    launcher_hash = format_checksum(b"launcher bytes", "sha256")
    sbom = build_sbom(
        {
            "launcher_hash": launcher_hash,
            "launcher_language": "rust",
            "launcher_version": "1.0.0",
            "packages": [],
            "python_version": "3.11.0",
            "python_hash": "",
        }
    )

    assert sbom is not None, "build_sbom returned nothing for an enabled build"

    launcher = [c for c in sbom["components"] if "launcher" in c.get("name", "")]
    assert launcher, f"no launcher component in {[c.get('name') for c in sbom['components']]}"

    for entry in launcher[0]["hashes"]:
        assert SHA256_HEX.match(entry["content"]), (
            f"{entry['alg']} content {entry['content']!r} is not a hex digest"
        )


def test_a_built_package_carries_usable_hashes_in_its_attestation(tmp_path: Path) -> None:
    """End to end, through the builder, on a package it actually produced.

    The two tests above check the pieces. This one runs the builder and reads
    what it wrote, so it covers the call site rather than a reconstruction of it.
    """
    output = tmp_path / "hashed.psp"
    result = (
        PSPFBuilder.create()
        .metadata(name="hash-prefix-test", version="1.0.0")
        .add_slot(id="data", data=b"payload")
        .with_keys(seed="test-hash-prefix")
        .build(output)
    )
    assert result.success, result.errors

    with PSPFReader(output) as reader:
        descriptors = reader.read_slot_descriptors()
        attestation = json.loads(reader.read_slot(len(descriptors) - 1))

    hashes = [
        (component.get("name"), entry)
        for component in attestation.get("sbom", {}).get("components", [])
        for entry in (component.get("hashes") or [])
    ]
    assert hashes, "the attestation SBOM records no hashes at all"

    for name, entry in hashes:
        assert SHA256_HEX.match(entry["content"]), (
            f"{name}: {entry['alg']} content {entry['content']!r} is not a hex digest"
        )

    provenance = attestation.get("provenance", {})
    for key, value in provenance.items():
        if isinstance(value, str) and value.count(":") > 1 and value.startswith("sha256:"):
            pytest.fail(f"provenance.{key} carries a doubled algorithm prefix: {value!r}")


# 🌶️📦🔚
