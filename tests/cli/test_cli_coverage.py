#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Additional tests for `cli.py` to improve test coverage, focusing on failure paths."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from flavor.cli import main as cli_main
from flavor.exceptions import PackagingError, VerificationError


def test_cli_pack_fails(tmp_path: Path) -> None:
    """
    Tests that the `pack` command handles exceptions from the orchestrator.
    """
    runner = CliRunner()
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.touch()

    with patch(
        "flavor.commands.package.build_package_from_manifest",
        side_effect=PackagingError("Mocked packaging failure"),
    ) as mock_package:
        result = runner.invoke(
            cli_main,
            [
                "pack",
                "--manifest",
                str(pyproject_path),
            ],
        )
        assert result.exit_code != 0
        assert "Packaging Failed" in result.output
        assert "Mocked packaging failure" in result.output
        mock_package.assert_called_once()


def test_cli_verify_fails(tmp_path: Path) -> None:
    """
    Tests that the `verify` command handles exceptions from the reader.
    """
    runner = CliRunner()
    package_file = tmp_path / "package.psp"
    package_file.touch()

    with patch(
        "flavor.commands.verify.verify_package",
        side_effect=VerificationError("Mocked verification failure"),
    ) as mock_verify:
        result = runner.invoke(cli_main, ["verify", str(package_file)])
        assert result.exit_code != 0
        assert "Verification failed: Mocked verification failure" in result.output
        mock_verify.assert_called_once()


# 🌶️📦🔚
