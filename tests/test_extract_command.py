#!/usr/bin/env python3
"""Tests for the extract commands."""

import json
from pathlib import Path
import subprocess
import tarfile

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
    taster_dir = Path("/REDACTED_ABS_PATH")
    if not taster_dir.exists():
        pytest.skip("Taster helper package not found")

    launcher_bin = Path(
        "/REDACTED_ABS_PATH"
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


class TestExtractCommand:
    """Test the extract command."""

    def test_extract_single_slot(self, test_package, tmp_path):
        """Test extracting a single slot."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "extracted.tgz"

        # Extract slot 2 (wheels)
        result = runner.invoke(
            cli, ["extract", str(test_package), "2", str(output_file)]
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        assert "Extracting slot 2: wheels" in result.output
        assert "✅ Extracted" in result.output

    def test_extract_invalid_slot(self, test_package, tmp_path):
        """Test extracting an invalid slot index."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "extracted.tgz"

        # Try to extract non-existent slot 99
        result = runner.invoke(
            cli, ["extract", str(test_package), "99", str(output_file)]
        )

        assert result.exit_code != 0
        assert "Invalid slot index 99" in result.output

    def test_extract_existing_file_no_force(self, test_package, tmp_path):
        """Test extracting to an existing file without force."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "extracted.tgz"
        output_file.write_text("existing content")

        result = runner.invoke(
            cli, ["extract", str(test_package), "2", str(output_file)]
        )

        assert result.exit_code != 0
        assert "Output file already exists" in result.output
        assert "Use --force to overwrite" in result.output

    def test_extract_existing_file_with_force(self, test_package, tmp_path):
        """Test extracting to an existing file with force."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "extracted.tgz"
        output_file.write_text("existing content")

        result = runner.invoke(
            cli, ["extract", "--force", str(test_package), "2", str(output_file)]
        )

        assert result.exit_code == 0
        assert output_file.stat().st_size > len("existing content")

    def test_extract_all_slots(self, test_package, tmp_path):
        """Test extracting all slots."""
        runner = click.testing.CliRunner()
        output_dir = tmp_path / "extracted"

        result = runner.invoke(cli, ["extract-all", str(test_package), str(output_dir)])

        assert result.exit_code == 0
        assert output_dir.exists()
        assert "Extracting 3 slots" in result.output
        assert "✅ Extracted all slots" in result.output

        # Check that files were created
        files = list(output_dir.glob("*"))
        assert len(files) >= 4  # 3 slots + metadata.json

        # Check metadata.json
        metadata_file = output_dir / "metadata.json"
        assert metadata_file.exists()
        metadata = json.loads(metadata_file.read_text())
        assert "package" in metadata
        assert "slots" in metadata

    def test_extract_all_with_existing_files(self, test_package, tmp_path):
        """Test extract-all with existing files (skip)."""
        runner = click.testing.CliRunner()
        output_dir = tmp_path / "extracted"
        output_dir.mkdir()

        # Create an existing file
        existing = output_dir / "00_uv.gz"
        existing.write_text("existing")

        result = runner.invoke(cli, ["extract-all", str(test_package), str(output_dir)])

        assert result.exit_code == 0
        assert "⏭️  Skipping 00_uv.gz (exists)" in result.output
        # Should still extract other files
        assert "01_python.tgz" in result.output

    def test_extract_all_with_force(self, test_package, tmp_path):
        """Test extract-all with force flag."""
        runner = click.testing.CliRunner()
        output_dir = tmp_path / "extracted"
        output_dir.mkdir()

        # Create an existing file
        existing = output_dir / "00_uv.gz"
        existing.write_text("existing")

        result = runner.invoke(
            cli, ["extract-all", "--force", str(test_package), str(output_dir)]
        )

        assert result.exit_code == 0
        assert "00_uv" in result.output
        # File should be overwritten
        assert existing.stat().st_size > len("existing")

    def test_extract_slot_contents_valid(self, test_package, tmp_path):
        """Test that extracted slot contents are valid."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "wheels.tgz"

        # Extract wheels slot
        result = runner.invoke(
            cli, ["extract", str(test_package), "2", str(output_file)]
        )

        assert result.exit_code == 0

        # The extracted file is already a tar archive (the slot was stored as tgz)
        # So we open it as plain tar, not tar.gz
        with tarfile.open(output_file, "r") as tar:
            members = tar.getnames()
            # Should contain wheel files
            assert any(name.endswith(".whl") for name in members)
