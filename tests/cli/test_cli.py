#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from flavor.cli import main as cli_main


def test_cli_pack_and_verify(tmp_path: Path) -> None:
    """
    Tests the full CLI flow: 'pack' a provider and then 'verify' it.
    """
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    pyproject_path = project_dir / "pyproject.toml"
    pyproject_path.touch()

    with patch("flavor.commands.package.build_package_from_manifest") as mock_build:
        # Create a real fake artifact file that can be verified
        fake_artifact = tmp_path / "fake_artifact.psp"
        fake_artifact.touch()
        mock_build.return_value = [fake_artifact]

        # Also mock verify to avoid real verification
        with patch("flavor.commands.package.verify_package") as mock_verify:
            mock_verify.return_value = {"signature_valid": True}

            pack_result = runner.invoke(
                cli_main,
                ["pack", "--manifest", str(pyproject_path)],
            )
            assert pack_result.exit_code == 0, f"Pack command failed: {pack_result.output}"

        # Check that build was called with correct parameters
        args, kwargs = mock_build.call_args
        assert args[0] == pyproject_path
        assert not kwargs.get("strip_binaries")

    fake_package_file = tmp_path / "fake.psp"
    fake_package_file.touch()

    with patch("flavor.commands.verify.verify_package") as mock_verify:
        mock_verify.return_value = {
            "format": "PSPF/2025",
            "version": "1.0.0",
            "launcher_size": 1024 * 1024,  # 1 MB
            "slot_count": 1,
            "package": {"name": "test-package", "version": "1.0.0"},
            "slots": [{"index": 0, "id": "main", "size": 512 * 1024, "codec": "raw"}],
            "signature_valid": True,
        }
        verify_result = runner.invoke(cli_main, ["verify", str(fake_package_file)])
        assert verify_result.exit_code == 0, f"Verify command failed: {verify_result.output}"
        mock_verify.assert_called_once_with(fake_package_file)


def test_cli_keygen(tmp_path: Path) -> None:
    """Tests the 'keygen' command."""
    runner = CliRunner()
    keys_dir = tmp_path / "test_keys"

    with patch("flavor.commands.keygen.generate_key_pair") as mock_keygen:
        result = runner.invoke(
            cli_main,
            [
                "keygen",
                "--out-dir",
                str(keys_dir),
            ],
        )
        assert result.exit_code == 0, f"Keygen command failed: {result.output}"
        assert f"Package integrity key pair generated in '{keys_dir}'" in result.output
        mock_keygen.assert_called_once_with(keys_dir)


# 🌶️📦🔚
