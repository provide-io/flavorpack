#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonSlotBuilder transitive dependency resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from flavor.packaging.python.slot_builder import PythonSlotBuilder


class TestTransitiveDependencies:
    """Test resolve_transitive_dependencies method."""

    def test_resolve_transitive_no_pyproject(self, tmp_path: Path) -> None:
        """Test transitive dependency resolution with no pyproject.toml."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create a dependency directory without pyproject.toml
        dep_dir = tmp_path / "dep1"
        dep_dir.mkdir()

        result = builder.resolve_transitive_dependencies(dep_dir)

        # Should still include the dependency itself
        assert len(result) == 1
        assert result[0] == dep_dir.resolve()

    def test_resolve_transitive_empty_dependencies(self, tmp_path: Path) -> None:
        """Test transitive dependency resolution with pyproject but no dependencies."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create a dependency with pyproject.toml but no dependencies
        dep_dir = tmp_path / "dep1"
        dep_dir.mkdir()
        pyproject = dep_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "dep1"
version = "0.1.0"

[tool.flavor.build]
# No dependencies
""")

        result = builder.resolve_transitive_dependencies(dep_dir)

        # Should include just the dependency itself
        assert len(result) == 1
        assert result[0] == dep_dir.resolve()

    def test_resolve_transitive_with_one_dependency(self, tmp_path: Path) -> None:
        """Test transitive dependency resolution with one dependency."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create dep2 (leaf dependency)
        dep2_dir = tmp_path / "dep2"
        dep2_dir.mkdir()
        dep2_pyproject = dep2_dir / "pyproject.toml"
        dep2_pyproject.write_text("""
[project]
name = "dep2"
version = "0.1.0"
""")

        # Create dep1 that depends on dep2
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        dep1_pyproject = dep1_dir / "pyproject.toml"
        dep1_pyproject.write_text("""
[project]
name = "dep1"
version = "0.1.0"

[tool.flavor.build]
dependencies = ["../dep2"]
""")

        result = builder.resolve_transitive_dependencies(dep1_dir)

        # Should return [dep2, dep1] in that order (deepest first)
        assert len(result) == 2
        assert result[0] == dep2_dir.resolve()
        assert result[1] == dep1_dir.resolve()

    def test_resolve_transitive_deep_chain(self, tmp_path: Path) -> None:
        """Test transitive dependency resolution with deep dependency chain."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create dep3 (leaf)
        dep3_dir = tmp_path / "dep3"
        dep3_dir.mkdir()
        (dep3_dir / "pyproject.toml").write_text("""
[project]
name = "dep3"
version = "0.1.0"
""")

        # Create dep2 that depends on dep3
        dep2_dir = tmp_path / "dep2"
        dep2_dir.mkdir()
        (dep2_dir / "pyproject.toml").write_text("""
[project]
name = "dep2"
version = "0.1.0"

[tool.flavor.build]
dependencies = ["../dep3"]
""")

        # Create dep1 that depends on dep2
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text("""
[project]
name = "dep1"
version = "0.1.0"

[tool.flavor.build]
dependencies = ["../dep2"]
""")

        result = builder.resolve_transitive_dependencies(dep1_dir)

        # Should return [dep3, dep2, dep1] in that order
        assert len(result) == 3
        assert result[0] == dep3_dir.resolve()
        assert result[1] == dep2_dir.resolve()
        assert result[2] == dep1_dir.resolve()

    def test_resolve_transitive_multiple_dependencies(self, tmp_path: Path) -> None:
        """Test transitive dependency resolution with multiple dependencies."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create dep2 and dep3 (leaves)
        dep2_dir = tmp_path / "dep2"
        dep2_dir.mkdir()
        (dep2_dir / "pyproject.toml").write_text("""
[project]
name = "dep2"
version = "0.1.0"
""")

        dep3_dir = tmp_path / "dep3"
        dep3_dir.mkdir()
        (dep3_dir / "pyproject.toml").write_text("""
[project]
name = "dep3"
version = "0.1.0"
""")

        # Create dep1 that depends on both dep2 and dep3
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text("""
[project]
name = "dep1"
version = "0.1.0"

[tool.flavor.build]
dependencies = ["../dep2", "../dep3"]
""")

        result = builder.resolve_transitive_dependencies(dep1_dir)

        # Should return [dep2, dep3, dep1] - all deps before dep1
        assert len(result) == 3
        assert result[2] == dep1_dir.resolve()
        # dep2 and dep3 should both be in the list
        assert dep2_dir.resolve() in result
        assert dep3_dir.resolve() in result

    def test_resolve_transitive_circular_dependency(self, tmp_path: Path) -> None:
        """Test transitive dependency resolution with circular dependency."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create dep1 and dep2 directories
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()

        dep2_dir = tmp_path / "dep2"
        dep2_dir.mkdir()

        # dep1 depends on dep2
        (dep1_dir / "pyproject.toml").write_text("""
[project]
name = "dep1"
version = "0.1.0"

[tool.flavor.build]
dependencies = ["../dep2"]
""")

        # dep2 depends on dep1 (circular)
        (dep2_dir / "pyproject.toml").write_text("""
[project]
name = "dep2"
version = "0.1.0"

[tool.flavor.build]
dependencies = ["../dep1"]
""")

        result = builder.resolve_transitive_dependencies(dep1_dir)

        # Should handle circular dependencies gracefully
        # Each dependency should appear only once
        assert len(result) == 2
        dep_names = [d.name for d in result]
        assert dep_names.count("dep1") == 1
        assert dep_names.count("dep2") == 1

    def test_resolve_transitive_missing_subdependency(self, tmp_path: Path) -> None:
        """Test transitive dependency resolution with missing sub-dependency."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create dep1 that depends on non-existent dep2
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text("""
[project]
name = "dep1"
version = "0.1.0"

[tool.flavor.build]
dependencies = ["../dep2"]
""")

        # dep2 doesn't exist

        result = builder.resolve_transitive_dependencies(dep1_dir)

        # Should still return dep1, but log warning about missing dep2
        assert len(result) == 1
        assert result[0] == dep1_dir.resolve()

    def test_resolve_transitive_invalid_pyproject(self, tmp_path: Path) -> None:
        """Test transitive dependency resolution with invalid pyproject.toml."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create dep1 with invalid pyproject.toml
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text("invalid toml content {{{")

        result = builder.resolve_transitive_dependencies(dep1_dir)

        # Should still return dep1, but log warning about invalid pyproject
        assert len(result) == 1
        assert result[0] == dep1_dir.resolve()

    def test_resolve_transitive_seen_tracking(self, tmp_path: Path) -> None:
        """Test that seen set properly tracks visited dependencies."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create a diamond dependency pattern:
        #     dep1
        #    /    \
        #  dep2   dep3
        #    \    /
        #     dep4

        dep4_dir = tmp_path / "dep4"
        dep4_dir.mkdir()
        (dep4_dir / "pyproject.toml").write_text('[project]\nname = "dep4"')

        dep2_dir = tmp_path / "dep2"
        dep2_dir.mkdir()
        (dep2_dir / "pyproject.toml").write_text("""
[project]
name = "dep2"

[tool.flavor.build]
dependencies = ["../dep4"]
""")

        dep3_dir = tmp_path / "dep3"
        dep3_dir.mkdir()
        (dep3_dir / "pyproject.toml").write_text("""
[project]
name = "dep3"

[tool.flavor.build]
dependencies = ["../dep4"]
""")

        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text("""
[project]
name = "dep1"

[tool.flavor.build]
dependencies = ["../dep2", "../dep3"]
""")

        result = builder.resolve_transitive_dependencies(dep1_dir)

        # dep4 should appear only once despite being depended on by both dep2 and dep3
        dep_names = [d.name for d in result]
        assert dep_names.count("dep4") == 1
        assert len(result) == 4  # dep4, dep2, dep3, dep1

    def test_resolve_transitive_depth_tracking(self, tmp_path: Path) -> None:
        """Test that depth parameter is properly tracked during recursion."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create simple chain for depth tracking
        dep2_dir = tmp_path / "dep2"
        dep2_dir.mkdir()
        (dep2_dir / "pyproject.toml").write_text('[project]\nname = "dep2"')

        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text("""
[project]
name = "dep1"

[tool.flavor.build]
dependencies = ["../dep2"]
""")

        # Call with explicit depth
        result = builder.resolve_transitive_dependencies(dep1_dir, depth=0)

        # Should work correctly with depth parameter
        assert len(result) == 2

    def test_resolve_transitive_with_seen_parameter(self, tmp_path: Path) -> None:
        """Test passing seen set to resolve_transitive_dependencies."""
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
        )

        # Create simple dependency
        dep1_dir = tmp_path / "dep1"
        dep1_dir.mkdir()
        (dep1_dir / "pyproject.toml").write_text('[project]\nname = "dep1"')

        # Pass a pre-populated seen set
        seen = {dep1_dir.resolve()}
        result = builder.resolve_transitive_dependencies(dep1_dir, seen=seen)

        # Should return empty list since dep1 is already in seen
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
