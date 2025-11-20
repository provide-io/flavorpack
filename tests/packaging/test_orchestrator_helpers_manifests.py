#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for orchestrator_helpers manifest creation functions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from flavor.packaging.orchestrator_helpers import (
    create_builder_manifest,
    create_python_builder_metadata,
)


class TestCreateBuilderManifest:
    """Test create_builder_manifest function."""

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_unix_basic(self, mock_is_windows: Path, tmp_path: Path) -> None:
        """Test creating builder manifest on Unix without runtime env."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config={},
            slots=slots,
            key_paths=key_paths,
        )

        assert manifest["name"] == "testpkg"
        assert manifest["version"] == "1.0.0"
        assert manifest["command"] == "{workenv}/bin/testpkg"
        assert "cache_validation" in manifest
        assert "workenv" in manifest
        assert "setup_commands" in manifest
        assert "slots" in manifest
        assert "signature" in manifest
        # Should have runtime with default isolation (safe by default)
        assert "runtime" in manifest
        assert "env" in manifest["runtime"]
        assert "unset" in manifest["runtime"]["env"]
        # Default isolation vars
        assert manifest["runtime"]["env"]["unset"] == [
            "PYTHONPATH",
            "UV_PROJECT_ENVIRONMENT",
            "PYTHONHOME",
            "UV_CACHE_DIR",
            "VIRTUAL_ENV",
        ]

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_with_cli_scripts(self, mock_is_windows: Path, tmp_path: Path) -> None:
        """Test creating builder manifest with CLI scripts."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        build_config = {"cli_scripts": {"mytool": "pkg.cli:main"}}

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
            slots=slots,
            key_paths=key_paths,
        )

        assert manifest["command"] == "{workenv}/bin/mytool"

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_with_runtime_env_unset(
        self, mock_is_windows: Path, tmp_path: Path
    ) -> None:
        """Test creating builder manifest with runtime env unset."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        build_config = {
            "execution": {
                "runtime": {
                    "env": {
                        "unset": ["DEBUG", "TEMP_VAR"],
                    }
                }
            }
        }

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
            slots=slots,
            key_paths=key_paths,
        )

        assert "runtime" in manifest
        assert "env" in manifest["runtime"]
        assert "unset" in manifest["runtime"]["env"]
        # Should merge defaults + user vars (defaults first, no duplicates)
        assert manifest["runtime"]["env"]["unset"] == [
            "PYTHONPATH",
            "UV_PROJECT_ENVIRONMENT",
            "PYTHONHOME",
            "UV_CACHE_DIR",
            "VIRTUAL_ENV",
            "DEBUG",
            "TEMP_VAR",
        ]

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_with_runtime_env_set(self, mock_is_windows: Path, tmp_path: Path) -> None:
        """Test creating builder manifest with runtime env set."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        build_config = {
            "execution": {
                "runtime": {
                    "env": {
                        "set": {"FOO": "bar", "BAZ": "qux"},
                    }
                }
            }
        }

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
            slots=slots,
            key_paths=key_paths,
        )

        assert "runtime" in manifest
        assert "env" in manifest["runtime"]
        assert "set" in manifest["runtime"]["env"]
        assert manifest["runtime"]["env"]["set"] == {"FOO": "bar", "BAZ": "qux"}

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_with_runtime_env_pass(
        self, mock_is_windows: Path, tmp_path: Path
    ) -> None:
        """Test creating builder manifest with runtime env pass."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        build_config = {
            "execution": {
                "runtime": {
                    "env": {
                        "pass": ["PATH", "HOME"],
                    }
                }
            }
        }

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
            slots=slots,
            key_paths=key_paths,
        )

        assert "runtime" in manifest
        assert "env" in manifest["runtime"]
        assert "pass" in manifest["runtime"]["env"]
        assert manifest["runtime"]["env"]["pass"] == ["PATH", "HOME"]

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_with_runtime_env_map(self, mock_is_windows: Path, tmp_path: Path) -> None:
        """Test creating builder manifest with runtime env map."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        build_config = {
            "execution": {
                "runtime": {
                    "env": {
                        "map": {"OLD_VAR": "NEW_VAR"},
                    }
                }
            }
        }

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
            slots=slots,
            key_paths=key_paths,
        )

        assert "runtime" in manifest
        assert "env" in manifest["runtime"]
        assert "map" in manifest["runtime"]["env"]
        assert manifest["runtime"]["env"]["map"] == {"OLD_VAR": "NEW_VAR"}

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_with_all_runtime_env(self, mock_is_windows: Path, tmp_path: Path) -> None:
        """Test creating builder manifest with all runtime env options."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        build_config = {
            "execution": {
                "runtime": {
                    "env": {
                        "unset": ["DEBUG"],
                        "pass": ["PATH"],
                        "set": {"FOO": "bar"},
                        "map": {"OLD": "NEW"},
                    }
                }
            }
        }

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
            slots=slots,
            key_paths=key_paths,
        )

        assert "runtime" in manifest
        assert "env" in manifest["runtime"]
        assert len(manifest["runtime"]["env"]) == 4
        assert "unset" in manifest["runtime"]["env"]
        assert "pass" in manifest["runtime"]["env"]
        assert "set" in manifest["runtime"]["env"]
        assert "map" in manifest["runtime"]["env"]

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_with_empty_runtime_env(
        self, mock_is_windows: Path, tmp_path: Path
    ) -> None:
        """Test creating builder manifest with empty runtime env (should not add runtime key)."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        build_config: dict[str, Any] = {
            "execution": {
                "runtime": {
                    "env": {
                        # All empty values
                        "unset": [],
                        "pass": [],
                        "set": {},
                        "map": {},
                    }
                }
            }
        }

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
            slots=slots,
            key_paths=key_paths,
        )

        # Even with empty user config, should still apply default isolation (safe by default)
        assert "runtime" in manifest
        assert "env" in manifest["runtime"]
        assert "unset" in manifest["runtime"]["env"]
        # Should have default isolation vars even when user provided empty config
        assert manifest["runtime"]["env"]["unset"] == [
            "PYTHONPATH",
            "UV_PROJECT_ENVIRONMENT",
            "PYTHONHOME",
            "UV_CACHE_DIR",
            "VIRTUAL_ENV",
        ]

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_builder_manifest_isolated_false(self, mock_is_windows: Path, tmp_path: Path) -> None:
        """Test creating builder manifest with isolated=false (opt-out of default isolation)."""

        slots = {
            "uv": tmp_path / "uv",
            "python": tmp_path / "python.tgz",
            "wheels": tmp_path / "wheels.tar",
        }

        key_paths: dict[str, str | None] = {"private": None, "public": None}

        build_config: dict[str, Any] = {
            "execution": {
                "runtime": {
                    "env": {
                        "isolated": False,  # Explicitly opt out of default isolation
                    }
                }
            }
        }

        manifest = create_builder_manifest(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
            slots=slots,
            key_paths=key_paths,
        )

        # When isolated=false, no runtime section should be added (user opted out)
        assert "runtime" not in manifest


class TestCreatePythonBuilderMetadata:
    """Test create_python_builder_metadata function."""

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_python_builder_metadata_unix_basic(self, mock_is_windows: Path) -> None:
        """Test creating Python builder metadata on Unix without runtime env."""

        metadata = create_python_builder_metadata(
            package_name="testpkg",
            version="1.0.0",
            build_config={},
        )

        assert metadata["package"]["name"] == "testpkg"
        assert metadata["package"]["version"] == "1.0.0"
        assert metadata["execution"]["command"] == "{workenv}/bin/testpkg"
        assert "cache_validation" in metadata
        assert "workenv" in metadata
        assert "setup_commands" in metadata
        # Should have runtime with default isolation (safe by default)
        assert "runtime" in metadata
        assert "env" in metadata["runtime"]
        assert "unset" in metadata["runtime"]["env"]
        assert metadata["runtime"]["env"]["unset"] == [
            "PYTHONPATH",
            "UV_PROJECT_ENVIRONMENT",
            "PYTHONHOME",
            "UV_CACHE_DIR",
            "VIRTUAL_ENV",
        ]

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_python_builder_metadata_with_runtime_env(self, mock_is_windows: Path) -> None:
        """Test creating Python builder metadata with runtime env."""

        build_config = {
            "execution": {
                "runtime": {
                    "env": {
                        "unset": ["DEBUG"],
                        "pass": ["PATH"],
                        "set": {"FOO": "bar"},
                        "map": {"OLD": "NEW"},
                    }
                }
            }
        }

        metadata = create_python_builder_metadata(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
        )

        assert "runtime" in metadata
        assert "env" in metadata["runtime"]
        # Should merge defaults + user vars
        assert metadata["runtime"]["env"]["unset"] == [
            "PYTHONPATH",
            "UV_PROJECT_ENVIRONMENT",
            "PYTHONHOME",
            "UV_CACHE_DIR",
            "VIRTUAL_ENV",
            "DEBUG",
        ]
        assert metadata["runtime"]["env"]["pass"] == ["PATH"]
        assert metadata["runtime"]["env"]["set"] == {"FOO": "bar"}
        assert metadata["runtime"]["env"]["map"] == {"OLD": "NEW"}

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=True)
    def test_create_python_builder_metadata_windows(self, mock_is_windows: Path) -> None:
        """Test creating Python builder metadata on Windows."""

        metadata = create_python_builder_metadata(
            package_name="testpkg",
            version="1.0.0",
            build_config={},
        )

        assert metadata["execution"]["command"] == "{workenv}/Scripts/testpkg.exe"
        # Check that UV command uses uv.exe
        uv_command = metadata["setup_commands"][0]["command"]
        assert "uv.exe" in uv_command

    @patch("flavor.packaging.orchestrator_helpers.is_windows", return_value=False)
    def test_create_python_builder_metadata_with_cli_scripts(self, mock_is_windows: Path) -> None:
        """Test creating Python builder metadata with CLI scripts."""

        build_config = {"cli_scripts": {"mytool": "pkg.cli:main"}}

        metadata = create_python_builder_metadata(
            package_name="testpkg",
            version="1.0.0",
            build_config=build_config,
        )

        assert metadata["execution"]["command"] == "{workenv}/bin/mytool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
