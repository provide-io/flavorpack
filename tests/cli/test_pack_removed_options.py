#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Regression tests for removed --output-format and --output-file CLI options.

These options were accepted but never used, so they were removed from the
``flavor pack`` command. These tests ensure they stay removed and that the
remaining valid options continue to work.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import pytest

from flavor.cli import main as cli_main


@pytest.mark.unit
class TestRemovedPackOptions:
    """Verify that --output-format and --output-file are no longer accepted."""

    def test_output_format_rejected(self, tmp_path: Path) -> None:
        """--output-format should be rejected as an unrecognized option."""
        runner = CliRunner()
        pyproject = tmp_path / "pyproject.toml"
        pyproject.touch()

        result = runner.invoke(
            cli_main,
            ["pack", "--manifest", str(pyproject), "--output-format", "json"],
        )
        assert result.exit_code != 0
        assert "No such option: --output-format" in result.output

    def test_output_file_rejected(self, tmp_path: Path) -> None:
        """--output-file should be rejected as an unrecognized option."""
        runner = CliRunner()
        pyproject = tmp_path / "pyproject.toml"
        pyproject.touch()

        result = runner.invoke(
            cli_main,
            ["pack", "--manifest", str(pyproject), "--output-file", "out.psp"],
        )
        assert result.exit_code != 0
        assert "No such option: --output-file" in result.output


@pytest.mark.unit
class TestPackCommandBasicInvocation:
    """Verify the pack command still works without removed options."""

    def test_pack_runs_without_removed_options(self, tmp_path: Path) -> None:
        """pack command should succeed with only valid options."""
        runner = CliRunner()
        pyproject = tmp_path / "pyproject.toml"
        pyproject.touch()

        fake_artifact = tmp_path / "artifact.psp"
        fake_artifact.touch()

        with (
            patch("flavor.commands.package.build_package_from_manifest") as mock_build,
            patch("flavor.commands.package.verify_package") as mock_verify,
        ):
            mock_build.return_value = [fake_artifact]
            mock_verify.return_value = {"valid": True, "signature_valid": True}

            result = runner.invoke(
                cli_main,
                ["pack", "--manifest", str(pyproject)],
            )
            assert result.exit_code == 0, f"Pack failed: {result.output}"
            mock_build.assert_called_once()


@pytest.mark.unit
class TestPackValidOptionsAccepted:
    """Verify that existing valid options are still accepted by the pack command."""

    def _invoke_pack(
        self,
        runner: CliRunner,
        tmp_path: Path,
        extra_args: list[str],
    ) -> tuple[int, str]:
        """Helper to invoke pack with mocked internals and return (exit_code, output)."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.touch()

        fake_artifact = tmp_path / "artifact.psp"
        fake_artifact.touch()

        with (
            patch("flavor.commands.package.build_package_from_manifest") as mock_build,
            patch("flavor.commands.package.verify_package") as mock_verify,
        ):
            mock_build.return_value = [fake_artifact]
            mock_verify.return_value = {"valid": True, "signature_valid": True}

            result = runner.invoke(
                cli_main,
                ["pack", "--manifest", str(pyproject), *extra_args],
            )
        return result.exit_code, result.output

    def test_verify_flag(self, tmp_path: Path) -> None:
        """--verify flag should be accepted."""
        runner = CliRunner()
        code, output = self._invoke_pack(runner, tmp_path, ["--verify"])
        assert code == 0, f"--verify failed: {output}"

    def test_no_verify_flag(self, tmp_path: Path) -> None:
        """--no-verify flag should be accepted."""
        runner = CliRunner()
        code, output = self._invoke_pack(runner, tmp_path, ["--no-verify"])
        assert code == 0, f"--no-verify failed: {output}"

    def test_strip_flag(self, tmp_path: Path) -> None:
        """--strip flag should be accepted."""
        runner = CliRunner()
        code, output = self._invoke_pack(runner, tmp_path, ["--strip"])
        assert code == 0, f"--strip failed: {output}"

    def test_quiet_flag(self, tmp_path: Path) -> None:
        """--quiet flag should be accepted."""
        runner = CliRunner()
        code, output = self._invoke_pack(runner, tmp_path, ["--quiet"])
        assert code == 0, f"--quiet failed: {output}"

    def test_progress_flag(self, tmp_path: Path) -> None:
        """--progress flag should be accepted."""
        runner = CliRunner()
        code, output = self._invoke_pack(runner, tmp_path, ["--progress"])
        assert code == 0, f"--progress failed: {output}"

    def test_output_option(self, tmp_path: Path) -> None:
        """--output (the valid output path option) should be accepted."""
        runner = CliRunner()
        out_path = str(tmp_path / "custom_output.psp")
        code, output = self._invoke_pack(runner, tmp_path, ["--output", out_path])
        assert code == 0, f"--output failed: {output}"

    def test_key_seed_option(self, tmp_path: Path) -> None:
        """--key-seed option should be accepted."""
        runner = CliRunner()
        code, output = self._invoke_pack(runner, tmp_path, ["--key-seed", "test-seed"])
        assert code == 0, f"--key-seed failed: {output}"


# 🌶️📦🔚
