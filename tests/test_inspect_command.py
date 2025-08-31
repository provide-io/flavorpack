#!/usr/bin/env python3
"""Tests for the inspect command."""

import json
import subprocess
import tempfile
from pathlib import Path

import click.testing
import pytest

from flavor.cli import cli


@pytest.fixture
def test_package(tmp_path):
    """Create a test PSPF package for testing."""
    # Check if test package already exists from previous run
    existing_package = Path("/tmp/test-taster.psp")
    if existing_package.exists():
        return existing_package

    # Otherwise try to build one using the taster helper package
    taster_dir = Path("/Users/tim/code/gh/provide-io/flavorpack/helpers/taster")
    if not taster_dir.exists():
        pytest.skip("Taster helper package not found")

    launcher_bin = Path(
        "/Users/tim/code/gh/provide-io/flavorpack/ingredients/bin/flavor-go-launcher-darwin_arm64"
    )
    if not launcher_bin.exists():
        pytest.skip("Launcher binary not found")

    output_path = tmp_path / "test.psp"

    # Build using flavor CLI directly
    result = subprocess.run(
        [
            "../../workenv/flavor_darwin_arm64/bin/flavor",
            "pack",
            "--manifest",
            "pyproject.toml",
            "--output",
            str(output_path),
            "--launcher-bin",
            str(launcher_bin),
            "--key-seed",
            "test123",
        ],
        cwd=taster_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.skip(f"Failed to build test package: {result.stderr}")

    return output_path


class TestInspectCommand:
    """Test the inspect command."""

    def test_inspect_basic(self, test_package):
        """Test basic inspect command output."""
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["inspect", str(test_package)])

        assert result.exit_code == 0
        assert "Package:" in result.output
        assert "Format: PSPF/" in result.output
        assert "Launcher:" in result.output
        assert "Slots:" in result.output

    def test_inspect_json(self, test_package):
        """Test JSON output of inspect command."""
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["inspect", "--json", str(test_package)])

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
        assert len(data["slots"]) >= 3  # At least uv, python, wheels

    def test_inspect_nonexistent_file(self):
        """Test inspect with non-existent file."""
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["inspect", "/tmp/nonexistent.psp"])

        assert result.exit_code != 0
        # Click validates file existence, so we get a different error message
        assert "does not exist" in result.output.lower()

    def test_inspect_slot_metadata(self, test_package):
        """Test that slot metadata is properly displayed."""
        runner = click.testing.CliRunner()
        result = runner.invoke(cli, ["inspect", "--json", str(test_package)])

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
            assert "encoding" in slot

        # Check that we have expected slot IDs
        slot_ids = [s["name"] for s in slots]  # JSON returns ID as "name" for compatibility
        assert "uv" in slot_ids
        assert "python" in slot_ids
        assert "wheels" in slot_ids
