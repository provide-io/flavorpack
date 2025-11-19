#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the high-level flavor API."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor import build_package_from_manifest


@pytest.fixture
def pyproject_factory(tmp_path: Path) -> Callable[[str], Path]:
    """Factory to create pyproject.toml files for testing."""

    def _create_pyproject(content: str) -> Path:
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(content)
        (tmp_path / "keys").mkdir()
        return pyproject_path

    return _create_pyproject


@patch("flavor.packaging.orchestrator.PackagingOrchestrator.build_package")
def test_build_package_from_manifest_success(
    mock_build: Mock, pyproject_factory: Callable[[str], Path]
) -> None:
    """Verify build_package_from_manifest succeeds with a valid config."""
    pyproject_content = """
[project]
name = "my-test-package"
version = "1.2.3"

[project.scripts]
my-test-package = "my_app.main:cli"

[tool.flavor]
name = "my-flavor-name"
"""
    pyproject_path = pyproject_factory(pyproject_content)
    artifacts = build_package_from_manifest(pyproject_path)

    assert artifacts is not None
    mock_build.assert_called_once()


def test_build_package_from_manifest_missing_config(pyproject_factory: Callable[[str], Path]) -> None:
    """Verify build_package_from_manifest fails if essential config is missing."""
    # This pyproject.toml is missing the entry_point (via [project.scripts])
    pyproject_content = """
[project]
name = "my-test-package"
version = "1.2.3"

[tool.flavor]
# No entry_point defined here either
"""
    pyproject_path = pyproject_factory(pyproject_content)

    with pytest.raises(ValueError, match="Project entry_point must be defined"):
        build_package_from_manifest(pyproject_path)


def test_build_package_from_manifest_missing_version(pyproject_factory: Callable[[str], Path]) -> None:
    """Verify build_package_from_manifest fails if version is missing."""
    pyproject_content = """
[project]
name = "my-test-package"
# version is missing

[project.scripts]
my-test-package = "my_app.main:cli"
"""
    pyproject_path = pyproject_factory(pyproject_content)

    with pytest.raises(ValueError, match="Project version must be defined"):
        build_package_from_manifest(pyproject_path)


# 🌶️📦🔚
