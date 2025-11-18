#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonSlotBuilder core functionality."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from flavor.packaging.python.slot_builder import PythonSlotBuilder


class TestSlotBuilderInit:
    """Test PythonSlotBuilder initialization."""

    def test_init_basic(self) -> None:
        """Test basic initialization with minimal parameters."""
        builder = PythonSlotBuilder(
            manifest_dir=Path("/tmp/test"),
            package_name="testpkg",
            entry_point="testpkg:main",
        )
        assert builder.manifest_dir == Path("/tmp/test")
        assert builder.package_name == "testpkg"
        assert builder.entry_point == "testpkg:main"
        assert builder.python_version == "3.11"
        assert builder.is_windows is False
        assert builder.manylinux_tag == "manylinux2014"
        assert builder.build_config == {}
        assert builder.wheel_builder is None
        assert builder.uv_exe == "uv"

    def test_init_with_all_params(self) -> None:
        """Test initialization with all parameters."""
        wheel_builder = Mock()
        build_config = {"version": "1.2.3", "dependencies": ["dep1"]}

        builder = PythonSlotBuilder(
            manifest_dir=Path("/tmp/test"),
            package_name="testpkg",
            entry_point="testpkg:main",
            python_version="3.12",
            is_windows=True,
            manylinux_tag="manylinux_2_28",
            build_config=build_config,
            wheel_builder=wheel_builder,
        )

        assert builder.python_version == "3.12"
        assert builder.is_windows is True
        assert builder.manylinux_tag == "manylinux_2_28"
        assert builder.build_config == build_config
        assert builder.wheel_builder is wheel_builder
        assert builder.uv_exe == "uv.exe"


class TestCopyExecutable:
    """Test _copy_executable method."""

    def test_copy_executable_unix(self, tmp_path: Path) -> None:
        """Test copying executable on Unix."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            is_windows=False,
        )

        src = tmp_path / "src" / "uv"
        src.parent.mkdir(parents=True)
        src.write_text("#!/bin/sh\necho uv")

        dest = tmp_path / "dest" / "uv"
        dest.parent.mkdir(parents=True)

        builder._copy_executable(src, dest)

        # Verify file was copied and is executable
        assert dest.exists()
        # Check that permissions include execute bit
        import stat

        assert dest.stat().st_mode & stat.S_IXUSR

    @patch("flavor.packaging.python.slot_builder.safe_copy")
    def test_copy_executable_windows(self, mock_copy: Mock, tmp_path: Path) -> None:
        """Test copying executable on Windows (no chmod)."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            is_windows=True,
        )

        src = tmp_path / "src" / "uv.exe"
        dest = tmp_path / "dest" / "uv.exe"

        builder._copy_executable(src, dest)

        mock_copy.assert_called_once_with(src, dest, preserve_mode=True, overwrite=True)
        # On Windows, no chmod should be called


class TestWriteJson:
    """Test _write_json method."""

    @patch("flavor.packaging.python.slot_builder.write_json")
    def test_write_json(self, mock_write: Mock) -> None:
        """Test JSON writing delegation."""
        builder = PythonSlotBuilder(
            manifest_dir=Path("/tmp/test"),
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        path = Path("/tmp/test.json")
        data = {"key": "value"}

        builder._write_json(path, data)

        mock_write.assert_called_once_with(path, data, indent=2)


class TestGetRequirementsFile:
    """Test _get_requirements_file method."""

    def test_get_requirements_file_requirements_txt(self, tmp_path: Path) -> None:
        """Test finding requirements.txt."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("pytest\n")

        result = builder._get_requirements_file()
        assert result == req_file

    def test_get_requirements_file_requirements_in(self, tmp_path: Path) -> None:
        """Test finding requirements.in."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        req_file = tmp_path / "requirements.in"
        req_file.write_text("pytest\n")

        result = builder._get_requirements_file()
        assert result == req_file

    def test_get_requirements_file_requirements_dir_base(self, tmp_path: Path) -> None:
        """Test finding requirements/base.txt."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        req_dir = tmp_path / "requirements"
        req_dir.mkdir()
        req_file = req_dir / "base.txt"
        req_file.write_text("pytest\n")

        result = builder._get_requirements_file()
        assert result == req_file

    def test_get_requirements_file_requirements_dir_requirements(self, tmp_path: Path) -> None:
        """Test finding requirements/requirements.txt."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        req_dir = tmp_path / "requirements"
        req_dir.mkdir()
        req_file = req_dir / "requirements.txt"
        req_file.write_text("pytest\n")

        result = builder._get_requirements_file()
        assert result == req_file

    def test_get_requirements_file_not_found(self, tmp_path: Path) -> None:
        """Test when no requirements file is found."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        result = builder._get_requirements_file()
        assert result is None

    def test_get_requirements_file_priority_order(self, tmp_path: Path) -> None:
        """Test that requirements.txt has priority over other files."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create multiple requirements files
        req_txt = tmp_path / "requirements.txt"
        req_txt.write_text("pytest\n")

        req_in = tmp_path / "requirements.in"
        req_in.write_text("pytest>=7\n")

        # Should return requirements.txt first
        result = builder._get_requirements_file()
        assert result == req_txt


class TestCreateMetadata:
    """Test _create_metadata method."""

    @patch("flavor.packaging.python.slot_builder.write_json")
    def test_create_metadata_basic(self, mock_write: Mock, tmp_path: Path) -> None:
        """Test metadata creation with basic config."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()

        builder._create_metadata(metadata_dir)

        assert mock_write.call_count == 2

        # Check package manifest call
        package_manifest_call = call(
            metadata_dir / "package_manifest.json",
            {
                "name": "testpkg",
                "version": "0.0.1",
                "entry_point": "testpkg:main",
                "python_version": "3.11",
            },
            indent=2,
        )

        # Check config call
        config_call = call(
            metadata_dir / "config.json",
            {
                "entry_point": "testpkg:main",
                "package_name": "testpkg",
            },
            indent=2,
        )

        mock_write.assert_has_calls([package_manifest_call, config_call])

    @patch("flavor.packaging.python.slot_builder.write_json")
    def test_create_metadata_with_version(self, mock_write: Mock, tmp_path: Path) -> None:
        """Test metadata creation with version in build config."""
        build_config = {"version": "1.2.3"}
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            build_config=build_config,
        )

        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()

        builder._create_metadata(metadata_dir)

        # Check that version from build_config is used
        package_manifest_call = mock_write.call_args_list[0]
        assert package_manifest_call[0][1]["version"] == "1.2.3"

    @patch("flavor.packaging.python.slot_builder.write_json")
    def test_create_metadata_custom_python_version(self, mock_write: Mock, tmp_path: Path) -> None:
        """Test metadata creation with custom Python version."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            python_version="3.12",
        )

        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()

        builder._create_metadata(metadata_dir)

        # Check that custom Python version is used
        package_manifest_call = mock_write.call_args_list[0]
        assert package_manifest_call[0][1]["python_version"] == "3.12"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
