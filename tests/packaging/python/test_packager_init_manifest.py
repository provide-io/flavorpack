#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonPackager - Python-specific packaging orchestration."""

from __future__ import annotations

from pathlib import Path
import tomllib
from unittest.mock import patch

import pytest

from flavor.packaging.python.packager import PythonPackager


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

        with pytest.raises(FileNotFoundError, match=r"No pyproject\.toml found"):
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

        with pytest.raises(ValueError, match=r"missing project\.name"):
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

        with pytest.raises(tomllib.TOMLDecodeError):  # tomllib will raise parsing error
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


# 🌶️📦🔚
