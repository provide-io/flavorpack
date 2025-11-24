#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the extract commands."""

import json
from pathlib import Path
import tarfile

import click.testing

from flavor.cli import cli


class TestExtractCommand:
    """Test the extract command."""

    def test_extract_single_slot(self, mock_test_package: Path, tmp_path: Path) -> None:
        """Test extracting a single slot."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "extracted.tar"

        # Extract slot 2 (wheels)
        result = runner.invoke(cli, ["extract", str(mock_test_package), "2", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        assert "Extracting slot 2: wheels" in result.output

    def test_extract_invalid_slot(self, mock_test_package: Path, tmp_path: Path) -> None:
        """Test extracting an invalid slot index."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "extracted.tgz"

        # Try to extract non-existent slot 99
        result = runner.invoke(cli, ["extract", str(mock_test_package), "99", str(output_file)])

        assert result.exit_code != 0
        assert "Invalid slot index 99" in result.output

    def test_extract_existing_file_no_force(self, mock_test_package: Path, tmp_path: Path) -> None:
        """Test extracting to an existing file without force."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "extracted.tgz"
        output_file.write_text("existing content")

        result = runner.invoke(cli, ["extract", str(mock_test_package), "2", str(output_file)])

        assert result.exit_code != 0
        assert "Output file already exists" in result.output
        assert "Use --force to overwrite" in result.output

    def test_extract_existing_file_with_force(self, mock_test_package: Path, tmp_path: Path) -> None:
        """Test extracting to an existing file with force."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "extracted.tgz"
        output_file.write_text("existing content")

        result = runner.invoke(cli, ["extract", "--force", str(mock_test_package), "2", str(output_file)])

        assert result.exit_code == 0
        assert output_file.stat().st_size > len("existing content")

    def test_extract_all_slots(self, mock_test_package: Path, tmp_path: Path) -> None:
        """Test extracting all slots."""
        runner = click.testing.CliRunner()
        output_dir = tmp_path / "extracted"

        result = runner.invoke(cli, ["extract-all", str(mock_test_package), str(output_dir)])

        assert result.exit_code == 0
        assert output_dir.exists()
        assert "Extracting 3 slots" in result.output

        # Check that files were created
        files = list(output_dir.glob("*"))
        assert len(files) >= 4  # 3 slots + metadata.json

        # Check metadata.json
        metadata_file = output_dir / "metadata.json"
        assert metadata_file.exists()
        metadata = json.loads(metadata_file.read_text())
        assert "package" in metadata
        assert "slots" in metadata

    def test_extract_all_with_existing_files(self, mock_test_package: Path, tmp_path: Path) -> None:
        """Test extract-all with existing files (skip)."""
        runner = click.testing.CliRunner()
        output_dir = tmp_path / "extracted"
        output_dir.mkdir()

        # Create an existing file
        existing = output_dir / "00_main"
        existing.write_text("existing")

        result = runner.invoke(cli, ["extract-all", str(mock_test_package), str(output_dir)])

        assert result.exit_code == 0
        assert "⏭️  Skipping 00_main (exists)" in result.output
        # Should still extract other files
        assert "01_config" in result.output

    def test_extract_all_with_force(self, mock_test_package: Path, tmp_path: Path) -> None:
        """Test extract-all with force flag."""
        runner = click.testing.CliRunner()
        output_dir = tmp_path / "extracted"
        output_dir.mkdir()

        # Create an existing file
        existing = output_dir / "00_main"
        existing.write_text("existing")

        result = runner.invoke(cli, ["extract-all", "--force", str(mock_test_package), str(output_dir)])

        assert result.exit_code == 0
        assert "00_main" in result.output
        # File should be overwritten
        assert existing.stat().st_size > len("existing")

    def test_extract_slot_contents_valid(self, mock_test_package: Path, tmp_path: Path) -> None:
        """Test that extracted slot contents are valid."""
        runner = click.testing.CliRunner()
        output_file = tmp_path / "wheels.tar"

        # Extract wheels slot
        result = runner.invoke(cli, ["extract", str(mock_test_package), "2", str(output_file)])

        assert result.exit_code == 0

        # The extracted file is already a tar archive (the slot was stored as tgz)
        # So we open it as plain tar, not tar.gz
        with tarfile.open(output_file, "r") as tar:
            members = tar.getnames()
            # Should contain wheel files
            assert any(name.endswith(".whl") for name in members)


# 🌶️📦🔚
