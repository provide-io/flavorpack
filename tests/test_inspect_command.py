#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the inspect command."""

import json
from pathlib import Path

import click.testing

from flavor.cli import cli


class TestInspectCommand:
    """Test the inspect command."""

    def test_inspect_basic(self, mock_test_package: Path) -> None:
        """Test basic inspect command output."""
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["inspect", str(mock_test_package)])

        assert result.exit_code == 0
        assert "Package:" in result.output
        assert "Format: PSPF/" in result.output
        assert "Launcher:" in result.output
        assert "Slots:" in result.output

    def test_inspect_json(self, mock_test_package: Path) -> None:
        """Test JSON output of inspect command."""
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["inspect", "--json", str(mock_test_package)])

        assert result.exit_code == 0

        # Parse JSON output
        lines = result.output.strip().split("\n")
        # Find where JSON starts (after telemetry logs)
        json_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break

        json_str = "\n".join(lines[json_start:])
        data = json.loads(json_str)

        assert "package" in data
        assert "format" in data
        assert "size" in data
        assert "launcher_size" in data
        assert "slots" in data
        assert isinstance(data["slots"], list)
        assert len(data["slots"]) == 3  # main, config, wheels

    def test_inspect_nonexistent_file(self) -> None:
        """Test inspect with non-existent file."""
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["inspect", "/tmp/nonexistent.psp"])

        assert result.exit_code != 0
        # Click validates file existence, so we get a different error message
        assert "does not exist" in result.output.lower()

    def test_inspect_slot_metadata(self, mock_test_package: Path) -> None:
        """Test that slot metadata is properly displayed."""
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["inspect", "--json", str(mock_test_package)])

        assert result.exit_code == 0

        # Parse JSON output
        lines = result.output.strip().split("\n")
        json_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break

        json_str = "\n".join(lines[json_start:])
        data = json.loads(json_str)

        # Check slot metadata
        slots = data["slots"]
        for slot in slots:
            assert "index" in slot
            assert "name" in slot  # This is the ID field returned as "name" in JSON
            assert "purpose" in slot
            assert "size" in slot
            assert "operations" in slot

        # Check that we have expected slot IDs
        slot_ids = [s["name"] for s in slots]  # JSON returns ID as "name" for compatibility
        assert "main" in slot_ids
        assert "config" in slot_ids
        assert "wheels" in slot_ids


# 🌶️📦🔚
