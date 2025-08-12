"""
Additional tests for `cli.py` to improve test coverage, focusing on failure paths.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from flavor.cli import main as cli_main
from flavor.exceptions import BuildError, PackagingError


def test_cli_package_fails(tmp_path: Path) -> None:
    """
    Tests that the `package` command handles exceptions from the orchestrator.
    """
    runner = CliRunner()
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.touch()

    with patch(
        "flavor.cli.build_package_from_manifest",
        side_effect=PackagingError("Mocked packaging failure"),
    ) as mock_package:
        result = runner.invoke(
            cli_main,
            [
                "package",
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
    package_file = tmp_path / "package.pspf"
    package_file.touch()

    with patch(
        "flavor.cli.verify_package",
        side_effect=BuildError("Mocked verification failure"),
    ) as mock_verify:
        result = runner.invoke(cli_main, ["verify", str(package_file)])
        assert result.exit_code != 0
        assert "Go-based verification failed" in result.output
        mock_verify.assert_called_once()


# 📦🍜🧪🪄
