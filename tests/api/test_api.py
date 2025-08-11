"""Tests for the public api.py module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from flavor import api
from flavor.exceptions import BuildError


def test_build_package_from_manifest_success(tmp_path: Path) -> None:
    """Tests the happy path for building from a manifest."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    pyproject_path = project_dir / "pyproject.toml"
    keys_dir = project_dir / "keys"
    keys_dir.mkdir()
    (keys_dir / "provider-private.key").touch()
    (keys_dir / "provider-public.key").touch()

    pyproject_content = """
[project]
name = "my-provider"
version = "1.0.0"
scripts = {"terraform-provider-myprovider" = "my.provider:main"}

[tool.pspf]
provider_name = "myprovider"
entry_point = "my.provider:main"
"""
    pyproject_path.write_text(pyproject_content)

    with patch("flavor.api.PackagingOrchestrator") as mock_orchestrator_cls:
        mock_orchestrator = mock_orchestrator_cls.return_value
        # Create the expected output file so chmod works
        expected_output = project_dir / "dist" / "pspf" / "darwin_arm64" / "terraform-provider-myprovider_v1.0.0"
        expected_output.parent.mkdir(parents=True, exist_ok=True)
        expected_output.touch()
        
        artifacts = api.build_package_from_manifest(pyproject_path)
        
        assert len(artifacts) == 1
        assert artifacts[0].name == "my-provider.flavor"
        mock_orchestrator_cls.assert_called_once()
        mock_orchestrator.build_package.assert_called_once()


def test_build_package_from_manifest_missing_config(tmp_path: Path) -> None:
    """Tests that build fails if config is missing from the manifest."""
    pyproject_path = tmp_path / "pyproject.toml"
    # THE FIX: Add the scripts table so the test can proceed to the intended check.
    pyproject_path.write_text('[project]\nname = "test"\nversion="1"\n[project.scripts]\n"a"="b"')

    with pytest.raises(BuildError, match="A \\[tool.pspf\\] section was not found"):
        api.build_package_from_manifest(pyproject_path)





# 📦🍜🧪🪄
