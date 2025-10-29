#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonSlotBuilder wheel building."""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

from flavor.packaging.python.slot_builder import PythonSlotBuilder


class TestBuildWheels:
    """Test _build_wheels method."""

    def test_build_wheels_no_dependencies(self, tmp_path: Path) -> None:
        """Test building wheels with no local dependencies."""
        mock_wheel_builder = Mock()
        mock_wheel_builder.build_and_resolve_project.return_value = {
            "total_wheels": 5,
            "project_wheel": Mock(name="testpkg-0.1.0-py3-none-any.whl"),
        }

        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )

        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()

        builder._build_wheels(wheels_dir)

        # Verify wheel builder was called with correct parameters
        mock_wheel_builder.build_and_resolve_project.assert_called_once()
        call_kwargs = mock_wheel_builder.build_and_resolve_project.call_args[1]
        assert call_kwargs["python_exe"] == Path(sys.executable)
        assert call_kwargs["project_dir"] == tmp_path
        assert call_kwargs["build_dir"] == wheels_dir.parent
        assert call_kwargs["extra_packages"] == []

    def test_build_wheels_with_local_dependencies(self, tmp_path: Path) -> None:
        """Test building wheels with local dependencies."""
        # Create local dependency directories
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text('[project]\nname = "dep1"')

        dep2_dir = tmp_path / "dep2"
        dep2_dir.mkdir()
        (dep2_dir / "pyproject.toml").write_text('[project]\nname = "dep2"')

        # Mock wheel builder
        mock_wheel_builder = Mock()
        mock_dep1_wheel = Mock(name="dep1-0.1.0-py3-none-any.whl")
        mock_dep2_wheel = Mock(name="dep2-0.1.0-py3-none-any.whl")
        mock_project_wheel = Mock(name="testpkg-0.1.0-py3-none-any.whl")

        mock_wheel_builder.build_wheel_from_source.side_effect = [
            mock_dep1_wheel,
            mock_dep2_wheel,
        ]
        mock_wheel_builder.build_and_resolve_project.return_value = {
            "total_wheels": 7,
            "project_wheel": mock_project_wheel,
        }

        # Create builder with local dependencies
        build_config = {
            "dependencies": ["dep1", "dep2"],
        }
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            build_config=build_config,
            wheel_builder=mock_wheel_builder,
        )

        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()

        builder._build_wheels(wheels_dir)

        # Verify local dependency wheels were built
        assert mock_wheel_builder.build_wheel_from_source.call_count == 2

        # Verify first dependency was built
        call1 = mock_wheel_builder.build_wheel_from_source.call_args_list[0]
        assert call1[1]["python_exe"] == Path(sys.executable)
        assert call1[1]["source_path"] == dep1_dir
        assert call1[1]["wheel_dir"] == wheels_dir

        # Verify second dependency was built
        call2 = mock_wheel_builder.build_wheel_from_source.call_args_list[1]
        assert call2[1]["python_exe"] == Path(sys.executable)
        assert call2[1]["source_path"] == dep2_dir
        assert call2[1]["wheel_dir"] == wheels_dir

        # Verify project build was called
        mock_wheel_builder.build_and_resolve_project.assert_called_once()

    def test_build_wheels_missing_local_dependency(self, tmp_path: Path) -> None:
        """Test building wheels with missing local dependency."""
        # Create only dep1, not dep2
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text('[project]\nname = "dep1"')

        # Mock wheel builder
        mock_wheel_builder = Mock()
        mock_dep1_wheel = Mock(name="dep1-0.1.0-py3-none-any.whl")
        mock_project_wheel = Mock(name="testpkg-0.1.0-py3-none-any.whl")

        mock_wheel_builder.build_wheel_from_source.return_value = mock_dep1_wheel
        mock_wheel_builder.build_and_resolve_project.return_value = {
            "total_wheels": 5,
            "project_wheel": mock_project_wheel,
        }

        # Create builder with local dependencies including missing one
        build_config = {
            "dependencies": ["dep1", "dep2"],  # dep2 doesn't exist
        }
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            build_config=build_config,
            wheel_builder=mock_wheel_builder,
        )

        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()

        builder._build_wheels(wheels_dir)

        # Should build dep1 but log warning about missing dep2
        assert mock_wheel_builder.build_wheel_from_source.call_count == 1

        # Should still call project build
        mock_wheel_builder.build_and_resolve_project.assert_called_once()

    def test_build_wheels_with_extra_packages(self, tmp_path: Path) -> None:
        """Test building wheels with extra packages configuration."""
        mock_wheel_builder = Mock()
        mock_wheel_builder.build_and_resolve_project.return_value = {
            "total_wheels": 8,
            "project_wheel": Mock(name="testpkg-0.1.0-py3-none-any.whl"),
        }

        build_config = {
            "extra_packages": ["numpy", "pandas"],
        }
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            build_config=build_config,
            wheel_builder=mock_wheel_builder,
        )

        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()

        builder._build_wheels(wheels_dir)

        # Verify extra_packages were passed to build_and_resolve_project
        call_kwargs = mock_wheel_builder.build_and_resolve_project.call_args[1]
        assert call_kwargs["extra_packages"] == ["numpy", "pandas"]

    def test_build_wheels_local_dep_not_directory(self, tmp_path: Path) -> None:
        """Test building wheels when local dependency exists but is a file."""
        # Create a file instead of directory
        dep1_file = tmp_path / "dep1"
        dep1_file.write_text("not a directory")

        # Mock wheel builder
        mock_wheel_builder = Mock()
        mock_project_wheel = Mock(name="testpkg-0.1.0-py3-none-any.whl")
        mock_wheel_builder.build_and_resolve_project.return_value = {
            "total_wheels": 5,
            "project_wheel": mock_project_wheel,
        }

        # Create builder with local dependency that's a file
        build_config = {
            "dependencies": ["dep1"],
        }
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            build_config=build_config,
            wheel_builder=mock_wheel_builder,
        )

        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()

        builder._build_wheels(wheels_dir)

        # Should not attempt to build dep1 (it's not a directory)
        mock_wheel_builder.build_wheel_from_source.assert_not_called()

        # Should still call project build
        mock_wheel_builder.build_and_resolve_project.assert_called_once()

    def test_build_wheels_complex_scenario(self, tmp_path: Path) -> None:
        """Test building wheels with complex scenario: multiple deps, extra packages."""
        # Create local dependencies
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text('[project]\nname = "dep1"')

        dep2_dir = tmp_path / "dep2"
        dep2_dir.mkdir()
        (dep2_dir / "pyproject.toml").write_text('[project]\nname = "dep2"')

        # Mock wheel builder
        mock_wheel_builder = Mock()
        mock_dep1_wheel = Mock(name="dep1-0.1.0-py3-none-any.whl")
        mock_dep2_wheel = Mock(name="dep2-0.1.0-py3-none-any.whl")
        mock_project_wheel = Mock(name="testpkg-1.2.3-py3-none-any.whl")

        mock_wheel_builder.build_wheel_from_source.side_effect = [
            mock_dep1_wheel,
            mock_dep2_wheel,
        ]
        mock_wheel_builder.build_and_resolve_project.return_value = {
            "total_wheels": 12,
            "project_wheel": mock_project_wheel,
        }

        # Create builder with full configuration
        build_config = {
            "version": "1.2.3",
            "dependencies": ["dep1", "dep2", "missing_dep"],
            "extra_packages": ["requests", "click"],
        }
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            build_config=build_config,
            wheel_builder=mock_wheel_builder,
        )

        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()

        builder._build_wheels(wheels_dir)

        # Verify local dependencies were built (2 out of 3, missing_dep doesn't exist)
        assert mock_wheel_builder.build_wheel_from_source.call_count == 2

        # Verify project build with extra packages
        mock_wheel_builder.build_and_resolve_project.assert_called_once()
        call_kwargs = mock_wheel_builder.build_and_resolve_project.call_args[1]
        assert call_kwargs["extra_packages"] == ["requests", "click"]
        assert call_kwargs["project_dir"] == tmp_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
