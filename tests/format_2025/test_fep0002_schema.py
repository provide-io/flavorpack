#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Check FEP-0002's JSON Schema against the packages the builders produce.

FEP-0002 §8 publishes a schema and claims every package in
tests/fixtures/format_compat/ satisfies it. A specification whose schema nobody
runs describes whatever it described on the day it was written, so this runs it:
the schema is read out of the document itself, and the fixtures are read out of
the packages, and the two have to agree.

The fixtures are built once by each of the three implementations and committed,
so a producer that starts writing something else fails here.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator
import pytest

from flavor.psp.format_2025 import PSPFReader

pytestmark = [
    pytest.mark.cross_language,
    pytest.mark.packaging,
    pytest.mark.ci,
]

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = REPO_ROOT / "docs" / "reference" / "spec" / "fep-0002-json-metadata-format.md"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "format_compat"
FIXTURE_NAMES = ("rust.psp", "go.psp", "python.psp")


def _schema() -> dict[str, Any]:
    """Extract the published schema from FEP-0002 §8."""
    blocks = re.findall(r"```json\n(\{.*?\n\})\n```", SPEC.read_text(encoding="utf-8"), re.S)
    for block in blocks:
        candidate: dict[str, Any] = json.loads(block)
        if "$schema" in candidate:
            return candidate
    pytest.fail("FEP-0002 §8 has no JSON Schema block")


SCHEMA = _schema()


def test_published_schema_is_well_formed() -> None:
    """The schema in the specification is a valid Draft 2020-12 schema."""
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_committed_packages_satisfy_the_published_schema(name: str) -> None:
    """Each producer's package validates against FEP-0002 §8."""
    with PSPFReader(FIXTURE_ROOT / "v1" / name) as reader:
        document = reader.read_metadata()

    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(document), key=lambda e: list(e.path))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_execution_contract_fixture_satisfies_the_published_schema() -> None:
    """The execution-block fixture is a conforming document, not just a readable one."""
    document = json.loads((FIXTURE_ROOT / "execution" / "execution-block.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(SCHEMA).iter_errors(document))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_minimal_document_from_section_14_is_conforming() -> None:
    """The minimal example FEP-0002 §14 offers has to actually validate."""
    minimal = {
        "format": "PSPF/2025",
        "package": {"name": "minimal", "version": "1.0.0"},
        "slots": [],
        "execution": {"command": "true"},
    }
    assert not list(Draft202012Validator(SCHEMA).iter_errors(minimal))


def test_unknown_members_are_accepted() -> None:
    """§5.3 requires readers to tolerate unknown members, so the schema must too.

    A schema with additionalProperties false would reject documents the
    specification requires readers to accept, which is the one way this file
    could pass while describing the wrong format.
    """
    document = {
        "format": "PSPF/2025",
        "package": {"name": "minimal", "version": "1.0.0"},
        "slots": [],
        "execution": {"command": "true"},
        "a_field_from_a_later_producer": {"anything": 1},
    }
    assert not list(Draft202012Validator(SCHEMA).iter_errors(document))


@pytest.mark.parametrize(
    ("label", "document"),
    [
        ("missing format", {"package": {"name": "m", "version": "1"}, "slots": []}),
        ("wrong format", {"format": "PSPF/2024", "package": {"name": "m", "version": "1"}, "slots": []}),
        ("missing version", {"format": "PSPF/2025", "package": {"name": "m"}, "slots": []}),
        ("empty name", {"format": "PSPF/2025", "package": {"name": "", "version": "1"}, "slots": []}),
        ("slots not an array", {"format": "PSPF/2025", "package": {"name": "m", "version": "1"}, "slots": {}}),
        (
            "slot without a checksum",
            {
                "format": "PSPF/2025",
                "package": {"name": "m", "version": "1"},
                "slots": [
                    {
                        "slot": 0,
                        "id": "a",
                        "source": "",
                        "target": "t",
                        "size": 1,
                        "operations": "",
                        "purpose": "data",
                        "lifecycle": "runtime",
                    }
                ],
            },
        ),
        (
            "execution without a command",
            {
                "format": "PSPF/2025",
                "package": {"name": "m", "version": "1"},
                "slots": [],
                "execution": {},
            },
        ),
        (
            "verification without a seal",
            {
                "format": "PSPF/2025",
                "package": {"name": "m", "version": "1"},
                "slots": [],
                "verification": {"signed": True},
            },
        ),
    ],
)
def test_malformed_documents_are_rejected(label: str, document: dict[str, Any]) -> None:
    """The schema has to bite. One that accepts anything would pass every test above."""
    assert list(Draft202012Validator(SCHEMA).iter_errors(document)), f"{label} was accepted"


# 🌶️📦🔚
