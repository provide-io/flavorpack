#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for metadata assembly functionality."""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from flavor.psp.format_2025.metadata import (
    assemble_metadata,
    create_build_metadata,
    create_launcher_metadata,
    create_verification_metadata,
    get_launcher_info,
)
from flavor.psp.format_2025.spec import BuildSpec, KeyConfig


class TestBuildMetadata:
    """Test build metadata creation."""

    def test_create_build_metadata(self) -> None:
        """Test build metadata creation with current platform info."""
        metadata = create_build_metadata()

        assert metadata["tool"] == "flavor-python"
        assert "tool_version" in metadata
        assert "timestamp" in metadata

        # Verify timestamp is ISO format
        timestamp = datetime.datetime.fromisoformat(metadata["timestamp"])
        assert timestamp.tzinfo is not None  # Must have timezone

        # Platform info
        assert "platform" in metadata
        assert metadata["platform"]["os"] in ["darwin", "linux", "windows", "macos"]
        assert metadata["platform"]["arch"] in ["arm64", "amd64", "x86_64"]
        assert "host" in metadata["platform"]

    def test_build_metadata_deterministic_flag(self) -> None:
        """Test deterministic build flag."""
        # With seed
        metadata = create_build_metadata(deterministic=True)
        assert metadata["deterministic"] is True

        # Without seed
        metadata = create_build_metadata(deterministic=False)
        assert metadata["deterministic"] is False


class TestLauncherMetadata:
    """Test launcher metadata creation."""

    @pytest.fixture
    def mock_launcher_binary(self) -> bytes:
        """Mock launcher binary data."""
        return b"FAKE_LAUNCHER_BINARY" * 1000  # Fake binary data

    def test_get_launcher_info(self, mock_launcher_binary: bytes) -> None:
        """Test launcher info extraction."""
        with patch("flavor.psp.format_2025.metadata.assembly.load_launcher_binary") as mock_load:
            mock_load.return_value = mock_launcher_binary

            info = get_launcher_info("rust")

            assert "data" in info
            assert info["data"] == mock_launcher_binary
            assert info["tool"] == "flavor-rs-launcher"
            assert "tool_version" in info
            assert "checksum" in info
            assert info["checksum"].startswith("sha256:")
            assert "capabilities" in info
            assert isinstance(info["capabilities"], list)

    def test_launcher_info_go(self, mock_launcher_binary: bytes) -> None:
        """Test Go launcher info."""
        with patch("flavor.psp.format_2025.metadata.assembly.load_launcher_binary") as mock_load:
            mock_load.return_value = mock_launcher_binary

            info = get_launcher_info("go")
            assert info["tool"] == "flavor-go-launcher"

    def test_launcher_info_python_uses_rust(self, mock_launcher_binary: bytes) -> None:
        """Test Python launcher uses Rust launcher."""
        with patch("flavor.psp.format_2025.metadata.assembly.load_launcher_binary") as mock_load:
            mock_load.return_value = mock_launcher_binary

            info = get_launcher_info("python")
            assert info["tool"] == "flavor-rs-launcher"

    def test_launcher_checksum_consistency(self, mock_launcher_binary: bytes) -> None:
        """Test launcher checksum is consistent."""
        with patch("flavor.psp.format_2025.metadata.assembly.load_launcher_binary") as mock_load:
            mock_load.return_value = mock_launcher_binary

            info1 = get_launcher_info("rust")
            info2 = get_launcher_info("rust")
            assert info1["checksum"] == info2["checksum"]

    def test_create_launcher_metadata(self, mock_launcher_binary: bytes) -> None:
        """Test launcher metadata structure creation."""
        launcher_info = {
            "data": mock_launcher_binary,
            "tool": "flavor-rs-launcher",
            "tool_version": "1.0.0",
            "checksum": "abc123",
            "capabilities": ["mmap", "async"],
        }

        metadata = create_launcher_metadata(launcher_info)

        assert metadata["tool"] == "flavor-rs-launcher"
        assert metadata["tool_version"] == "1.0.0"
        assert metadata["size"] == len(mock_launcher_binary)
        assert metadata["checksum"] == "sha256:abc123"
        assert metadata["capabilities"] == ["mmap", "async"]


class TestVerificationMetadata:
    """Test verification metadata creation."""

    def test_create_verification_metadata_default(self) -> None:
        """Test verification metadata with defaults."""
        spec = BuildSpec()
        metadata = create_verification_metadata(spec)

        assert metadata["integrity_seal"]["required"] is True
        assert metadata["integrity_seal"]["algorithm"] == "ed25519"
        assert metadata["signed"] is True
        assert metadata["require_verification"] is True

    def test_create_verification_metadata_with_seed(self) -> None:
        """Test verification metadata with deterministic key."""

        spec = BuildSpec().with_keys(KeyConfig(key_seed="test-seed"))
        metadata = create_verification_metadata(spec)

        assert metadata["signed"] is True
        assert metadata["require_verification"] is True

    def test_create_verification_metadata_insecure(self) -> None:
        """Test verification metadata defaults to requiring verification."""
        # Since BuildOptions doesn't have insecure_mode, verification is always required
        spec = BuildSpec()
        metadata = create_verification_metadata(spec)

        # Default behavior: always require verification
        assert metadata["require_verification"] is True


class TestMetadataAssembly:
    """Test complete metadata assembly."""

    @pytest.fixture
    def basic_spec(self) -> BuildSpec:
        """Create basic build spec."""
        return BuildSpec().with_metadata(
            package={"name": "test-app", "version": "1.0.0"},
            execution={"command": "{workenv}/bin/app"},
        )

    @pytest.fixture
    def mock_launcher_info(self) -> dict[str, Any]:
        """Mock launcher info."""
        return {
            "data": b"FAKE_LAUNCHER",
            "tool": "flavor-rs-launcher",
            "tool_version": "1.0.0",
            "checksum": "abc123",
            "capabilities": ["mmap"],
        }

    def test_assemble_complete_metadata(
        self, basic_spec: BuildSpec, mock_launcher_info: dict[str, Any]
    ) -> None:
        """Test complete metadata assembly."""
        slots = []  # Empty slots for now

        metadata = assemble_metadata(basic_spec, slots, mock_launcher_info)

        # Core fields
        assert metadata["format"] == "PSPF/2025"
        assert metadata["format_version"] == "1.0.0"

        # Package info
        assert metadata["package"]["name"] == "test-app"
        assert metadata["package"]["version"] == "1.0.0"

        # Execution info
        assert metadata["execution"]["command"] == "{workenv}/bin/app"

        # Verification section
        assert "verification" in metadata
        assert metadata["verification"]["integrity_seal"]["required"] is True

        # Build section
        assert "build" in metadata
        assert metadata["build"]["tool"] == "flavor-python"

        # Launcher section
        assert "launcher" in metadata
        assert metadata["launcher"]["tool"] == "flavor-rs-launcher"

        # Compatibility section
        assert "compatibility" in metadata
        assert metadata["compatibility"]["min_format_version"] == "1.0.0"

    def test_assemble_metadata_with_optional_sections(
        self, basic_spec: BuildSpec, mock_launcher_info: dict[str, Any]
    ) -> None:
        """Test metadata assembly with optional sections."""
        spec = basic_spec.with_metadata(
            cache_validation={"check_file": "{workenv}/marker"},
            setup_commands=[{"type": "execute", "command": "echo hello"}],
            runtime={"env": {"set": {"FOO": "bar"}}},
            workenv={"directories": [{"path": "tmp", "mode": "0700"}]},
        )

        metadata = assemble_metadata(spec, [], mock_launcher_info)

        assert "cache_validation" in metadata
        assert "setup_commands" in metadata
        assert "runtime" in metadata
        assert "workenv" in metadata

    def test_assemble_metadata_with_slots(
        self, basic_spec: BuildSpec, mock_launcher_info: dict[str, Any]
    ) -> None:
        """Test metadata assembly includes slot information."""
        # Create mock slots
        mock_slot = MagicMock()
        mock_slot.metadata.to_dict.return_value = {
            "index": 0,
            "name": "payload",
            "size": 1024,
            "codec": "gzip",
        }

        metadata = assemble_metadata(basic_spec, [mock_slot], mock_launcher_info)

        assert len(metadata["slots"]) == 1
        assert metadata["slots"][0]["name"] == "payload"

    def test_metadata_features_tracking(
        self, basic_spec: BuildSpec, mock_launcher_info: dict[str, Any]
    ) -> None:
        """Test that metadata tracks features used."""
        spec = basic_spec.with_metadata(
            workenv={"directories": [{"path": "tmp"}]},
            runtime={"env": {"set": {"FOO": "bar"}}},
            setup_commands=[{"type": "execute", "command": "ls"}],
        )

        metadata = assemble_metadata(spec, [], mock_launcher_info)

        features = metadata["compatibility"]["features"]
        assert "workenv_dirs" in features
        assert "runtime_env" in features
        assert "setup_commands" in features


# 🌶️📦🔚
