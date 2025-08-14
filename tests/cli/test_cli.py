from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from flavor.cli import main as cli_main


def test_cli_package_and_verify(tmp_path: Path) -> None:
    """
    Tests the full CLI flow: 'package' a provider and then 'verify' it.
    """
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    pyproject_path = project_dir / "pyproject.toml"
    pyproject_path.touch()

    with patch("flavor.cli.build_package_from_manifest") as mock_build:
        mock_build.return_value = [Path("fake/artifact")]
        package_result = runner.invoke(
            cli_main,
            ["package", "--manifest", str(pyproject_path)],
        )
        assert package_result.exit_code == 0, (
            f"Package command failed: {package_result.output}"
        )
        mock_build.assert_called_once_with(pyproject_path, output_path=None, launcher_type=None)

    fake_package_file = tmp_path / "fake.pspf"
    fake_package_file.touch()

    with patch("flavor.cli.verify_package") as mock_verify:
        mock_verify.return_value = {
            'format': 'PSPF/2025',
            'version': '1.0.0',
            'launcher_size': 1024 * 1024,  # 1 MB
            'slot_count': 1,
            'package': {'name': 'test-package', 'version': '1.0.0'},
            'slots': [{'index': 0, 'name': 'main', 'size': 512 * 1024}],
            'signature_valid': True
        }
        verify_result = runner.invoke(cli_main, ["verify", str(fake_package_file)])
        assert verify_result.exit_code == 0, (
            f"Verify command failed: {verify_result.output}"
        )
        mock_verify.assert_called_once_with(fake_package_file)


def test_cli_keygen(tmp_path: Path) -> None:
    """Tests the 'keygen' command."""
    runner = CliRunner()
    keys_dir = tmp_path / "test_keys"

    with patch("flavor.cli.generate_key_pair") as mock_keygen:
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


# 📦🍜🧪🪄
