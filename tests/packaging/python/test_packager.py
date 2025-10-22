#
# tests/packaging/python/test_packager.py
#
"""Tests for PythonPackager - Python-specific packaging orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

import pytest

from flavor.packaging.python.packager import PythonPackager


@pytest.mark.unit
class TestPythonPackagerInit:
    """Test PythonPackager initialization."""

    def test_initialization_defaults(self, tmp_path: Path) -> None:
        """Test initialization with default parameters."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        assert packager.manifest_dir == manifest_dir
        assert packager.package_name == "test-package"
        assert packager.entry_point == "module:main"
        assert packager.python_version == "3.11"
        assert packager.build_config == {}
        assert packager.MANYLINUX_TAG == "manylinux2014"

    def test_initialization_custom_config(self, tmp_path: Path) -> None:
        """Test initialization with custom build_config."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()
        build_config = {"key": "value", "option": True}

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
            build_config=build_config,
            python_version="3.12",
        )

        assert packager.python_version == "3.12"
        assert packager.build_config == build_config
        assert packager.build_config["key"] == "value"

    def test_platform_detection(self, tmp_path: Path) -> None:
        """Test platform detection for Windows vs Unix."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        with patch("sys.platform", "win32"):
            packager_win = PythonPackager(
                manifest_dir=manifest_dir,
                package_name="test",
                entry_point="test:main",
            )
            assert packager_win.is_windows is True
            assert packager_win.venv_bin_dir == "Scripts"
            assert packager_win.uv_exe == "uv.exe"

        with patch("sys.platform", "linux"):
            packager_unix = PythonPackager(
                manifest_dir=manifest_dir,
                package_name="test",
                entry_point="test:main",
            )
            assert packager_unix.is_windows is False
            assert packager_unix.venv_bin_dir == "bin"
            assert packager_unix.uv_exe == "uv"


@pytest.mark.unit
class TestValidateManifest:
    """Test manifest validation."""

    def test_validate_manifest_success(self, tmp_path: Path) -> None:
        """Test successful manifest validation."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        # Create valid pyproject.toml
        pyproject_path = manifest_dir / "pyproject.toml"
        pyproject_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"
""")

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        result = packager.validate_manifest()
        assert result is True

    def test_validate_manifest_missing_file(self, tmp_path: Path) -> None:
        """Test validation fails when pyproject.toml is missing."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        with pytest.raises(FileNotFoundError, match="No pyproject.toml found"):
            packager.validate_manifest()

    def test_validate_manifest_missing_project_name(self, tmp_path: Path) -> None:
        """Test validation fails when project.name is missing."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        # Create pyproject.toml without project.name
        pyproject_path = manifest_dir / "pyproject.toml"
        pyproject_path.write_text("""
[project]
version = "1.0.0"
""")

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        with pytest.raises(ValueError, match="missing project.name"):
            packager.validate_manifest()

    def test_validate_manifest_invalid_entry_point_format(self, tmp_path: Path) -> None:
        """Test validation fails for invalid entry point format."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        # Create valid pyproject.toml
        pyproject_path = manifest_dir / "pyproject.toml"
        pyproject_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"
""")

        # Invalid entry point (no colon)
        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="invalid_no_colon",
        )

        with pytest.raises(ValueError, match="Invalid entry point format"):
            packager.validate_manifest()

    def test_validate_manifest_exception_handling(self, tmp_path: Path) -> None:
        """Test exception handling during validation."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        # Create invalid TOML file
        pyproject_path = manifest_dir / "pyproject.toml"
        pyproject_path.write_text("invalid toml ][{")

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        with pytest.raises(Exception):  # tomllib will raise parsing error
            packager.validate_manifest()


@pytest.mark.unit
class TestGetMetadata:
    """Test metadata extraction methods."""

    def test_get_package_metadata_full(self, tmp_path: Path) -> None:
        """Test extracting full package metadata."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        pyproject_path = manifest_dir / "pyproject.toml"
        pyproject_path.write_text("""
[project]
name = "test-package"
version = "2.3.4"
description = "A test package"
requires-python = ">=3.10"
dependencies = ["requests>=2.0", "click"]

[project.scripts]
test-cli = "test.cli:main"

[tool.flavor]
option = "value"
""")

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        metadata = packager.get_package_metadata()

        assert metadata["name"] == "test-package"
        assert metadata["version"] == "2.3.4"
        assert metadata["description"] == "A test package"
        assert metadata["dependencies"] == ["requests>=2.0", "click"]
        assert metadata["python_requires"] == ">=3.10"
        assert metadata["entry_points"] == {"test-cli": "test.cli:main"}
        assert metadata["flavor_config"] == {"option": "value"}

    def test_get_package_metadata_minimal(self, tmp_path: Path) -> None:
        """Test extracting metadata with minimal pyproject.toml."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        pyproject_path = manifest_dir / "pyproject.toml"
        pyproject_path.write_text("""
[project]
name = "minimal-package"
""")

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
            python_version="3.11",
        )

        metadata = packager.get_package_metadata()

        # Should use defaults
        assert metadata["name"] == "minimal-package"
        assert metadata["version"] == "0.0.1"
        assert metadata["description"] == ""
        assert metadata["dependencies"] == []
        assert metadata["python_requires"] == ">=3.11"
        assert metadata["entry_points"] == {}
        assert metadata["flavor_config"] == {}

    def test_get_runtime_dependencies(self, tmp_path: Path) -> None:
        """Test extracting runtime dependencies."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        pyproject_path = manifest_dir / "pyproject.toml"
        pyproject_path.write_text("""
[project]
name = "test-package"
dependencies = ["requests>=2.0", "click", "pydantic>=2.0"]
""")

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        deps = packager.get_runtime_dependencies()

        assert isinstance(deps, list)
        assert len(deps) == 3
        assert "requests>=2.0" in deps
        assert "click" in deps
        assert "pydantic>=2.0" in deps

    def test_get_build_dependencies(self, tmp_path: Path) -> None:
        """Test extracting build dependencies."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        pyproject_path = manifest_dir / "pyproject.toml"
        pyproject_path.write_text("""
[project]
name = "test-package"

[build-system]
requires = ["setuptools>=65", "wheel", "build"]
build-backend = "setuptools.build_meta"
""")

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_deps = packager.get_build_dependencies()

        assert isinstance(build_deps, list)
        assert len(build_deps) == 3
        assert "setuptools>=65" in build_deps
        assert "wheel" in build_deps
        assert "build" in build_deps


@pytest.mark.unit
class TestBuildEnvironment:
    """Test build environment creation."""

    def test_create_build_environment_with_uv(self, tmp_path: Path) -> None:
        """Test creating build environment using UV."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir()
        venv_dir = build_dir / "venv"
        venv_bin = venv_dir / packager.venv_bin_dir
        venv_bin.mkdir(parents=True)
        python_exe = venv_bin / ("python.exe" if packager.is_windows else "python")
        python_exe.touch()

        # Mock UV being available
        with patch.object(packager.env_builder, "find_uv_command") as mock_find_uv:
            mock_find_uv.return_value = "/usr/bin/uv"

            with patch.object(packager.uv, "create_venv") as mock_create_venv:
                with patch.object(packager.pypapip, "_get_pypapip_install_cmd") as mock_get_cmd:
                    mock_get_cmd.return_value = ["pip", "install", "pip", "wheel", "setuptools"]

                    with patch("provide.foundation.process.run") as mock_run:
                        result = packager.create_build_environment(build_dir)

                        # Verify UV was used
                        mock_find_uv.assert_called_once()
                        mock_create_venv.assert_called_once_with(venv_dir, "3.11")

                        # Verify pip/wheel installed
                        assert mock_get_cmd.called
                        assert mock_run.called

                        assert result == python_exe

    def test_create_build_environment_fallback_venv(self, tmp_path: Path) -> None:
        """Test fallback to standard venv when UV is not available."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir()
        venv_dir = build_dir / "venv"
        venv_bin = venv_dir / packager.venv_bin_dir
        venv_bin.mkdir(parents=True)
        python_exe = venv_bin / ("python.exe" if packager.is_windows else "python")
        python_exe.touch()

        # Mock UV not being available
        with patch.object(packager.env_builder, "find_uv_command") as mock_find_uv:
            mock_find_uv.return_value = None

            with patch("venv.create") as mock_venv_create:
                with patch.object(packager.pypapip, "_get_pypapip_install_cmd") as mock_get_cmd:
                    mock_get_cmd.return_value = ["pip", "install", "pip", "wheel", "setuptools"]

                    with patch("provide.foundation.process.run") as mock_run:
                        result = packager.create_build_environment(build_dir)

                        # Verify standard venv was used
                        mock_venv_create.assert_called_once_with(venv_dir, with_pip=True)

                        # Verify pip/wheel installed
                        assert mock_get_cmd.called
                        assert mock_run.called

                        assert result == python_exe

    def test_create_build_environment_pip_installation(self, tmp_path: Path) -> None:
        """Test pip and wheel installation in build environment."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir()
        venv_dir = build_dir / "venv"
        venv_bin = venv_dir / packager.venv_bin_dir
        venv_bin.mkdir(parents=True)
        python_exe = venv_bin / ("python.exe" if packager.is_windows else "python")
        python_exe.touch()

        with patch.object(packager.env_builder, "find_uv_command", return_value=None):
            with patch("venv.create"):
                with patch.object(packager.pypapip, "_get_pypapip_install_cmd") as mock_get_cmd:
                    install_cmd = ["python", "-m", "pip", "install", "pip", "wheel", "setuptools"]
                    mock_get_cmd.return_value = install_cmd

                    with patch("provide.foundation.process.run") as mock_run:
                        packager.create_build_environment(build_dir)

                        # Verify pip install command was called correctly
                        mock_get_cmd.assert_called_once_with(python_exe, ["pip", "wheel", "setuptools"])
                        mock_run.assert_called_once_with(install_cmd, check=True, capture_output=True)

    def test_create_build_environment_python_not_found(self, tmp_path: Path) -> None:
        """Test when python executable is not found in venv."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir()

        # Don't create the python executable

        with patch.object(packager.env_builder, "find_uv_command", return_value=None):
            with patch("venv.create"):
                # Python exe doesn't exist, so pip install should be skipped
                with patch("provide.foundation.process.run") as mock_run:
                    result = packager.create_build_environment(build_dir)

                    # run should not be called since python_exe doesn't exist
                    mock_run.assert_not_called()

                    # Still returns the expected path (even if it doesn't exist)
                    expected_python = build_dir / "venv" / packager.venv_bin_dir / (
                        "python.exe" if packager.is_windows else "python"
                    )
                    assert result == expected_python


@pytest.mark.unit
class TestGetPythonBinaryInfo:
    """Test Python binary information retrieval."""

    def test_get_python_binary_info_uv_found(self, tmp_path: Path) -> None:
        """Test when UV is found and available."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
            python_version="3.12",
        )

        with patch.object(packager.env_builder, "find_uv_command") as mock_find_uv:
            mock_find_uv.return_value = "/usr/bin/uv"

            info = packager.get_python_binary_info()

            assert info["version"] == "3.12"
            assert info["path"] is None  # UV handles Python
            assert info["is_system"] is False
            assert info["manager"] == "uv"

    def test_get_python_binary_info_uv_exception(self, tmp_path: Path) -> None:
        """Test fallback when UV raises exception."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
            python_version="3.11",
        )

        with patch.object(packager.env_builder, "find_uv_command") as mock_find_uv:
            mock_find_uv.side_effect = RuntimeError("UV not found")

            info = packager.get_python_binary_info()

            # Should fall back to system Python
            assert info["version"] == "3.11"
            assert info["path"] == sys.executable
            assert info["is_system"] is True
            assert info["manager"] == "system"

    def test_get_python_binary_info_system_fallback(self, tmp_path: Path) -> None:
        """Test system Python fallback when UV not available."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
            python_version="3.10",
        )

        with patch.object(packager.env_builder, "find_uv_command") as mock_find_uv:
            mock_find_uv.return_value = None  # UV not found

            info = packager.get_python_binary_info()

            assert info["version"] == "3.10"
            assert info["path"] == sys.executable
            assert info["is_system"] is True
            assert info["manager"] == "system"


@pytest.mark.unit
class TestArtifactPreparation:
    """Test artifact preparation."""

    def test_prepare_artifacts_delegation(self, tmp_path: Path) -> None:
        """Test prepare_artifacts delegates to slot_builder."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        expected_artifacts = {
            "payload_tgz": work_dir / "payload.tar.gz",
            "metadata_tgz": work_dir / "metadata.tar.gz",
            "uv_binary": work_dir / "uv",
            "python_tgz": work_dir / "python.tar.gz",
        }

        with patch.object(packager.slot_builder, "prepare_artifacts") as mock_prepare:
            mock_prepare.return_value = expected_artifacts

            result = packager.prepare_artifacts(work_dir)

            mock_prepare.assert_called_once_with(work_dir)
            assert result == expected_artifacts

    def test_prepare_artifacts_returns_artifact_dict(self, tmp_path: Path) -> None:
        """Test prepare_artifacts returns dictionary with artifact paths."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        artifact_paths = {
            "payload_tgz": tmp_path / "payload.tar.gz",
            "python_tgz": tmp_path / "python.tar.gz",
        }

        with patch.object(packager.slot_builder, "prepare_artifacts", return_value=artifact_paths):
            result = packager.prepare_artifacts(work_dir)

            assert isinstance(result, dict)
            assert "payload_tgz" in result
            assert isinstance(result["payload_tgz"], Path)


@pytest.mark.unit
class TestCleanup:
    """Test cleanup operations."""

    def test_clean_build_artifacts_all_dirs(self, tmp_path: Path) -> None:
        """Test cleaning all standard build directories."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Create directories to clean
        payload_dir = work_dir / "payload"
        payload_dir.mkdir()
        (payload_dir / "test.txt").write_text("test")

        metadata_dir = work_dir / "metadata_content"
        metadata_dir.mkdir()

        venv_dir = work_dir / "venv"
        venv_dir.mkdir()

        build_dir = work_dir / "build"
        build_dir.mkdir()

        with patch("provide.foundation.file.safe_rmtree") as mock_rmtree:
            packager.clean_build_artifacts(work_dir)

            # Verify safe_rmtree called for each directory
            assert mock_rmtree.call_count == 4
            calls = [call[0][0] for call in mock_rmtree.call_args_list]
            assert payload_dir in calls
            assert metadata_dir in calls
            assert venv_dir in calls
            assert build_dir in calls

    def test_clean_build_artifacts_missing_dirs(self, tmp_path: Path) -> None:
        """Test cleaning handles missing directories gracefully."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Don't create any directories

        with patch("provide.foundation.file.safe_rmtree") as mock_rmtree:
            packager.clean_build_artifacts(work_dir)

            # Should not call safe_rmtree since directories don't exist
            mock_rmtree.assert_not_called()

    def test_clean_build_artifacts_error_handling(self, tmp_path: Path) -> None:
        """Test error handling during cleanup."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        payload_dir = work_dir / "payload"
        payload_dir.mkdir()

        with patch("provide.foundation.file.safe_rmtree") as mock_rmtree:
            mock_rmtree.side_effect = PermissionError("Cannot remove directory")

            # Should not raise, just log error
            packager.clean_build_artifacts(work_dir)

            assert mock_rmtree.called

    def test_clean_build_artifacts_uses_safe_rmtree(self, tmp_path: Path) -> None:
        """Test that safe_rmtree is used with missing_ok=True."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        payload_dir = work_dir / "payload"
        payload_dir.mkdir()

        with patch("provide.foundation.file.safe_rmtree") as mock_rmtree:
            packager.clean_build_artifacts(work_dir)

            # Verify safe_rmtree called with missing_ok=True
            for call in mock_rmtree.call_args_list:
                assert call[1]["missing_ok"] is True


@pytest.mark.unit
class TestDelegationMethods:
    """Test delegation helper methods."""

    def test_copy_executable_delegation(self, tmp_path: Path) -> None:
        """Test _copy_executable delegates to env_builder."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        src = tmp_path / "source.exe"
        src.touch()
        dest = tmp_path / "dest.exe"

        with patch.object(packager.env_builder, "_copy_executable") as mock_copy:
            packager._copy_executable(src, dest)

            mock_copy.assert_called_once_with(src, dest)

    def test_download_uv_binary_delegation(self, tmp_path: Path) -> None:
        """Test download_uv_binary delegates to env_builder."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        dest_dir = tmp_path / "uv_dest"
        dest_dir.mkdir()
        uv_binary = dest_dir / "uv"

        with patch.object(packager.env_builder, "download_uv_wheel") as mock_download:
            mock_download.return_value = uv_binary

            result = packager.download_uv_binary(dest_dir)

            mock_download.assert_called_once_with(dest_dir)
            assert result == uv_binary

    def test_write_json_delegation(self, tmp_path: Path) -> None:
        """Test _write_json uses write_json utility."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        json_path = tmp_path / "data.json"
        data = {"key": "value", "number": 42}

        with patch("flavor.packaging.python.packager.write_json") as mock_write_json:
            packager._write_json(json_path, data)

            mock_write_json.assert_called_once_with(json_path, data, indent=2)


@pytest.mark.unit
class TestRepr:
    """Test string representation."""

    def test_repr_unix_platform(self, tmp_path: Path) -> None:
        """Test __repr__ returns correct string for Unix platform."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        with patch("sys.platform", "linux"):
            packager = PythonPackager(
                manifest_dir=manifest_dir,
                package_name="my-package",
                entry_point="module:main",
                python_version="3.12",
            )

            repr_str = repr(packager)

            assert "PythonPackager" in repr_str
            assert "package=my-package" in repr_str
            assert "python=3.12" in repr_str
            assert "platform=unix" in repr_str

    def test_repr_windows_platform(self, tmp_path: Path) -> None:
        """Test __repr__ returns correct string for Windows platform."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        with patch("sys.platform", "win32"):
            packager = PythonPackager(
                manifest_dir=manifest_dir,
                package_name="win-package",
                entry_point="module:main",
                python_version="3.11",
            )

            repr_str = repr(packager)

            assert "PythonPackager" in repr_str
            assert "package=win-package" in repr_str
            assert "python=3.11" in repr_str
            assert "platform=windows" in repr_str


# 🌶️🧪📦
