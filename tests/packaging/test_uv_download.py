"""Test UV download functionality for manylinux2014 compatibility."""

from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from flavor.packaging.python.packager import PythonPackager


class TestUVDownload:
    """Test UV download functionality."""

    def test_pypa_pip_download_cmd_linux_amd64(self):
        """Test that pip download command includes manylinux2014 for Linux AMD64."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with (
            patch("flavor.packaging.python_packager.get_os_name", return_value="linux"),
            patch(
                "flavor.packaging.python_packager.get_arch_name", return_value="amd64"
            ),
        ):
            cmd = packager._get_pypa_pip_download_cmd(
                python_exe=Path("/usr/bin/python3"),
                dest_dir=Path("/tmp"),
                packages=["uv"],
                binary_only=True,
            )

            # Check that manylinux2014_x86_64 is in the command
            assert "--platform" in cmd
            assert "manylinux2014_x86_64" in cmd
            assert "--python-version" in cmd
            assert "--only-binary" in cmd
            assert ":all:" in cmd

    def test_pypa_pip_download_cmd_linux_arm64(self):
        """Test that pip download command includes manylinux2014 for Linux ARM64."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with (
            patch("flavor.packaging.python_packager.get_os_name", return_value="linux"),
            patch(
                "flavor.packaging.python_packager.get_arch_name", return_value="arm64"
            ),
        ):
            cmd = packager._get_pypa_pip_download_cmd(
                python_exe=Path("/usr/bin/python3"),
                dest_dir=Path("/tmp"),
                packages=["uv"],
                binary_only=True,
            )

            # Check that manylinux2014_aarch64 is in the command
            assert "--platform" in cmd
            assert "manylinux2014_aarch64" in cmd
            assert "--python-version" in cmd

    def test_pypa_pip_download_cmd_non_linux(self):
        """Test that pip download command doesn't add platform constraints on non-Linux."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with (
            patch(
                "flavor.packaging.python_packager.get_os_name", return_value="darwin"
            ),
            patch(
                "flavor.packaging.python_packager.get_arch_name", return_value="arm64"
            ),
        ):
            cmd = packager._get_pypa_pip_download_cmd(
                python_exe=Path("/usr/bin/python3"),
                dest_dir=Path("/tmp"),
                packages=["uv"],
                binary_only=True,
            )

            # Check that no manylinux platform constraints are added for macOS
            assert "manylinux2014" not in " ".join(cmd)
            assert "--only-binary" in cmd  # But binary-only should still be there

    def test_download_uv_wheel_validates_manylinux(self):
        """Test that _download_uv_wheel validates the wheel is manylinux2014."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a fake wheel file
            fake_wheel = (
                temp_path
                / "uv-0.8.14-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
            )

            # Create a minimal wheel with UV binary
            import zipfile

            with zipfile.ZipFile(fake_wheel, "w") as zf:
                # Add a fake UV binary
                zf.writestr("uv/uv", b"fake uv binary content")

            # Mock successful download with manylinux2014 wheel
            mock_run = MagicMock()
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Downloaded " + fake_wheel.name
            mock_run.return_value.stderr = ""

            # Need to mock at the actual usage location in the module
            with (
                patch("flavor.packaging.python_packager.run_command", mock_run),
                patch(
                    "flavor.packaging.python_packager.get_os_name", return_value="linux"
                ),
                patch(
                    "flavor.packaging.python_packager.get_arch_name",
                    return_value="amd64",
                ),
                patch.object(Path, "glob", return_value=[fake_wheel]),
            ):
                result = packager._download_uv_wheel(temp_path)

                # Should return the path to the extracted UV binary
                assert result is not None
                assert result.name == "uv"
                assert result.exists()

    def test_prepare_artifacts_linux_requires_uv(self):
        """Test that prepare_artifacts raises error on Linux if UV download fails."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with tempfile.TemporaryDirectory() as work_dir:
            work_path = Path(work_dir)

            with (
                patch(
                    "flavor.packaging.python_packager.get_os_name", return_value="linux"
                ),
                patch(
                    "flavor.packaging.python_packager.get_arch_name",
                    return_value="amd64",
                ),
                patch.object(packager, "_download_uv_wheel", return_value=None),
                patch.object(packager, "_build_wheels"),
            ):
                # Should raise error on Linux when UV download fails
                with pytest.raises(FileNotFoundError, match="manylinux2014"):
                    packager.prepare_artifacts(work_path)

    def test_download_uv_wheel_direct_fallback(self):
        """Test that _download_uv_wheel falls back to direct download when pip fails."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock run_command to fail on pip download but succeed on pip check
            def mock_run_side_effect(*args, **kwargs):
                cmd = args[0]
                # Allow pip --version check to succeed
                if "--version" in cmd:
                    result = MagicMock()
                    result.stdout = "pip 21.0.0"
                    result.stderr = ""
                    return result
                # But fail on actual download
                elif "download" in cmd:
                    raise Exception("pip download failed")
                # Default
                return MagicMock()

            mock_run = MagicMock(side_effect=mock_run_side_effect)

            # Mock urllib to return fake PyPI data
            fake_pypi_response = {
                "info": {"version": "0.8.14"},
                "releases": {
                    "0.8.14": [
                        {
                            "filename": "uv-0.8.14-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                            "url": "https://fake.url/uv.whl",
                        }
                    ]
                },
            }

            import json

            with (
                patch("flavor.packaging.python_packager.run_command", mock_run),
                patch(
                    "flavor.packaging.python_packager.get_os_name", return_value="linux"
                ),
                patch(
                    "flavor.packaging.python_packager.get_arch_name",
                    return_value="amd64",
                ),
                patch("urllib.request.urlopen") as mock_urlopen,
            ):
                # Mock PyPI JSON response
                mock_pypi = MagicMock()
                mock_pypi.read.return_value = json.dumps(fake_pypi_response).encode()

                # Mock wheel download
                mock_wheel = MagicMock()
                mock_wheel.read.return_value = b"fake wheel content"

                mock_urlopen.side_effect = [mock_pypi, mock_wheel]

                # The download should try pip first, fail, then try direct download
                # Since we're mocking the URL download, it will fail on extraction
                # but that's OK for this test
                result = packager._download_uv_wheel(temp_path)

                # Verify that urlopen was called (fallback was attempted)
                assert mock_urlopen.called
                assert mock_urlopen.call_count >= 1  # At least PyPI JSON was fetched

    def test_prepare_artifacts_non_linux_fallback(self):
        """Test that prepare_artifacts falls back to host UV on non-Linux."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with tempfile.TemporaryDirectory() as work_dir:
            work_path = Path(work_dir)

            # Create a fake host UV
            fake_uv_path = "/usr/local/bin/uv"

            with (
                patch(
                    "flavor.packaging.python_packager.get_os_name",
                    return_value="darwin",
                ),
                patch(
                    "flavor.packaging.python_packager.get_arch_name",
                    return_value="arm64",
                ),
                patch.object(packager, "_find_uv_command", return_value=fake_uv_path),
                patch.object(packager, "_copy_executable"),
                patch.object(packager, "_build_wheels"),
                patch.object(packager, "_create_metadata"),
                patch.object(packager, "_create_python_placeholder"),
                patch("tarfile.open"),
            ):
                # Don't pre-create directories - let the method create them

                # Create dummy archives to avoid stat errors
                (work_path / "payload.tgz").write_bytes(b"dummy")
                (work_path / "metadata.tgz").write_bytes(b"dummy")
                (work_path / "python.tgz").write_bytes(b"dummy")

                # Should not raise error on macOS when falling back to host UV
                artifacts = packager.prepare_artifacts(work_path)
                assert "uv_binary" in artifacts
