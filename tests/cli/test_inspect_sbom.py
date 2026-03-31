#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for flavor inspect --sbom and --provenance flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
import pytest

from flavor.cli import main as cli_main
from flavor.commands.inspect import _get_attestation, _output_attestation

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

SAMPLE_SBOM: dict[str, Any] = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "version": 1,
    "components": [],
}

SAMPLE_PROVENANCE: dict[str, Any] = {
    "builderName": "flavor-python",
    "builderVersion": "1.0.0",
    "buildTimestamp": 1700000000,
}

SAMPLE_ATTESTATION: dict[str, Any] = {
    "sbom": SAMPLE_SBOM,
    "provenance": SAMPLE_PROVENANCE,
}


def _make_mock_reader(
    *,
    has_attestation_slot: bool = True,
    attestation_data: dict[str, Any] | None = None,
) -> MagicMock:
    """Build a mock PSPFReader with configurable attestation slot."""
    from flavor.psp.format_2025.constants import LIFECYCLE_ATTESTATION, LIFECYCLE_RUNTIME

    reader = MagicMock()

    # Build slot descriptors
    if has_attestation_slot:
        attestation_slot = MagicMock()
        attestation_slot.lifecycle = LIFECYCLE_ATTESTATION
        slots = [attestation_slot]
    else:
        regular_slot = MagicMock()
        regular_slot.lifecycle = LIFECYCLE_RUNTIME
        slots = [regular_slot]

    reader.read_slot_descriptors.return_value = slots

    if has_attestation_slot:
        payload = attestation_data if attestation_data is not None else SAMPLE_ATTESTATION
        content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        reader.read_slot.return_value = content

    return reader


# ---------------------------------------------------------------------------
# Unit tests for _get_attestation
# ---------------------------------------------------------------------------


def test_get_attestation_returns_parsed_dict() -> None:
    """_get_attestation returns the parsed attestation dict when slot present."""
    reader = _make_mock_reader(has_attestation_slot=True)
    result = _get_attestation(reader)
    assert result is not None
    assert result["sbom"]["bomFormat"] == "CycloneDX"
    assert result["provenance"]["builderName"] == "flavor-python"


def test_get_attestation_returns_none_when_no_slot() -> None:
    """_get_attestation returns None when no attestation slot exists."""
    reader = _make_mock_reader(has_attestation_slot=False)
    result = _get_attestation(reader)
    assert result is None


# ---------------------------------------------------------------------------
# Unit tests for _output_attestation
# ---------------------------------------------------------------------------


def test_output_attestation_no_slot_prints_message(capsys: pytest.CaptureFixture[str]) -> None:
    """_output_attestation prints a friendly message when no attestation slot."""
    reader = _make_mock_reader(has_attestation_slot=False)
    with patch("flavor.commands.inspect.pout") as mock_pout:
        _output_attestation(reader, show_sbom=True, show_provenance=False)
        mock_pout.assert_called_once_with("No attestation slot found in this package.")


def test_output_attestation_sbom_no_sbom_key(capsys: pytest.CaptureFixture[str]) -> None:
    """_output_attestation prints 'no SBOM data' when attestation has no sbom key."""
    reader = _make_mock_reader(
        has_attestation_slot=True,
        attestation_data={"provenance": SAMPLE_PROVENANCE},
    )
    with patch("flavor.commands.inspect.pout") as mock_pout:
        _output_attestation(reader, show_sbom=True, show_provenance=False)
        mock_pout.assert_called_once_with("Package has no SBOM data.")


def test_output_attestation_provenance_no_provenance_key() -> None:
    """_output_attestation prints 'no provenance data' when attestation has no provenance key."""
    reader = _make_mock_reader(
        has_attestation_slot=True,
        attestation_data={"sbom": SAMPLE_SBOM},
    )
    with patch("flavor.commands.inspect.pout") as mock_pout:
        _output_attestation(reader, show_sbom=False, show_provenance=True)
        mock_pout.assert_called_once_with("Package has no provenance data.")


def test_output_attestation_prints_sbom_json() -> None:
    """_output_attestation prints formatted SBOM JSON when sbom key present."""
    reader = _make_mock_reader(has_attestation_slot=True)
    printed: list[str] = []
    with patch("flavor.commands.inspect.pout", side_effect=printed.append):
        _output_attestation(reader, show_sbom=True, show_provenance=False)
    assert len(printed) == 1
    parsed = json.loads(printed[0])
    assert parsed["bomFormat"] == "CycloneDX"


def test_output_attestation_prints_provenance_json() -> None:
    """_output_attestation prints formatted provenance JSON when provenance key present."""
    reader = _make_mock_reader(has_attestation_slot=True)
    printed: list[str] = []
    with patch("flavor.commands.inspect.pout", side_effect=printed.append):
        _output_attestation(reader, show_sbom=False, show_provenance=True)
    assert len(printed) == 1
    parsed = json.loads(printed[0])
    assert parsed["builderName"] == "flavor-python"


def test_output_attestation_prints_both() -> None:
    """_output_attestation prints both SBOM and provenance when both flags set."""
    reader = _make_mock_reader(has_attestation_slot=True)
    printed: list[str] = []
    with patch("flavor.commands.inspect.pout", side_effect=printed.append):
        _output_attestation(reader, show_sbom=True, show_provenance=True)
    assert len(printed) == 2
    sbom_out = json.loads(printed[0])
    prov_out = json.loads(printed[1])
    assert sbom_out["bomFormat"] == "CycloneDX"
    assert prov_out["builderName"] == "flavor-python"


# ---------------------------------------------------------------------------
# CLI integration tests via Click test runner
# ---------------------------------------------------------------------------


def test_inspect_sbom_prints_sbom(tmp_path: Path) -> None:
    """CLI: flavor inspect --sbom prints JSON containing 'CycloneDX'."""
    fake_pkg = tmp_path / "test.psp"
    fake_pkg.touch()

    runner = CliRunner()
    reader_mock = _make_mock_reader(has_attestation_slot=True)
    reader_mock.__enter__ = MagicMock(return_value=reader_mock)
    reader_mock.__exit__ = MagicMock(return_value=False)

    with patch("flavor.commands.inspect.PSPFReader", return_value=reader_mock):
        result = runner.invoke(cli_main, ["inspect", "--sbom", str(fake_pkg)])

    assert result.exit_code == 0, result.output
    assert "CycloneDX" in result.output


def test_inspect_provenance_prints_provenance(tmp_path: Path) -> None:
    """CLI: flavor inspect --provenance prints JSON containing builder info."""
    fake_pkg = tmp_path / "test.psp"
    fake_pkg.touch()

    runner = CliRunner()
    reader_mock = _make_mock_reader(has_attestation_slot=True)
    reader_mock.__enter__ = MagicMock(return_value=reader_mock)
    reader_mock.__exit__ = MagicMock(return_value=False)

    with patch("flavor.commands.inspect.PSPFReader", return_value=reader_mock):
        result = runner.invoke(cli_main, ["inspect", "--provenance", str(fake_pkg)])

    assert result.exit_code == 0, result.output
    assert "builderName" in result.output


def test_inspect_sbom_no_attestation_slot(tmp_path: Path) -> None:
    """CLI: flavor inspect --sbom with no attestation slot prints friendly message."""
    fake_pkg = tmp_path / "test.psp"
    fake_pkg.touch()

    runner = CliRunner()
    reader_mock = _make_mock_reader(has_attestation_slot=False)
    reader_mock.__enter__ = MagicMock(return_value=reader_mock)
    reader_mock.__exit__ = MagicMock(return_value=False)

    with patch("flavor.commands.inspect.PSPFReader", return_value=reader_mock):
        result = runner.invoke(cli_main, ["inspect", "--sbom", str(fake_pkg)])

    assert result.exit_code == 0, result.output
    assert "No attestation slot found in this package." in result.output


def test_inspect_sbom_no_sbom_key(tmp_path: Path) -> None:
    """CLI: flavor inspect --sbom when attestation has no sbom key prints 'no SBOM data'."""
    fake_pkg = tmp_path / "test.psp"
    fake_pkg.touch()

    runner = CliRunner()
    reader_mock = _make_mock_reader(
        has_attestation_slot=True,
        attestation_data={"provenance": SAMPLE_PROVENANCE},
    )
    reader_mock.__enter__ = MagicMock(return_value=reader_mock)
    reader_mock.__exit__ = MagicMock(return_value=False)

    with patch("flavor.commands.inspect.PSPFReader", return_value=reader_mock):
        result = runner.invoke(cli_main, ["inspect", "--sbom", str(fake_pkg)])

    assert result.exit_code == 0, result.output
    assert "Package has no SBOM data." in result.output


# 🌶️📦🔚
