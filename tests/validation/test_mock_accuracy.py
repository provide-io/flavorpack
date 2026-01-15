#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Mock Validation Tests

These tests ensure that our mock launchers accurately represent real launcher behavior.
They should be run as integration tests with real helpers available."""

from __future__ import annotations

from pathlib import Path

import pytest

from flavor.psp.format_2025 import PSPFBuilder, PSPFReader
from tests.conftest import MOCK_LAUNCHER_DATA, MOCK_LAUNCHER_SIZE


@pytest.mark.integration
@pytest.mark.requires_helpers
class TestMockAccuracy:
    """Validate that our mocks accurately represent real behavior."""

    @pytest.fixture()
    def use_real_launcher(self, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
        """Override the global mock to use real launchers for these tests.

        Note: Only use this fixture for tests that explicitly need real launchers.
        Most tests should work with the global mock.
        """
        # Skip the global mock fixture for this test class
        # Store the original function
        # The global mock has already patched it, so we need to get the real one
        import importlib
        import sys

        from flavor.psp.format_2025.metadata import assembly

        # Remove the module from cache to force reimport
        if "flavor.psp.format_2025.metadata.assembly" in sys.modules:
            del sys.modules["flavor.psp.format_2025.metadata.assembly"]

        # Reimport to get the original function
        assembly_module = importlib.import_module("flavor.psp.format_2025.metadata.assembly")

        # Now assembly_module.load_launcher_binary is the real function
        # But the test still has the mock, so we need to explicitly restore it
        monkeypatch.setattr(assembly, "load_launcher_binary", assembly_module.load_launcher_binary)

    def test_mock_launcher_content(self) -> None:
        """Verify mock launcher has expected format markers."""
        # Our mock should have some identifying content
        assert b"FAKE_LAUNCHER_FOR_TEST" in MOCK_LAUNCHER_DATA

        # Mock should be properly padded
        assert len(MOCK_LAUNCHER_DATA) == MOCK_LAUNCHER_SIZE

    def test_build_with_mock_vs_real(self, temp_dir: Path) -> None:
        """Compare package structure built with mock vs real launcher.

        This test builds two packages - one with mock and one with real launcher,
        and verifies they have compatible structure.
        """
        import unittest.mock

        from flavor.psp.format_2025.metadata import assembly

        # Build with mock
        mock_output = temp_dir / "mock_package.psp"

        def mock_launcher(launcher_type: str) -> bytes:
            return MOCK_LAUNCHER_DATA

        with unittest.mock.patch.object(assembly, "load_launcher_binary", mock_launcher):
            builder1 = PSPFBuilder.create().with_keys(seed="test")
            result1 = builder1.metadata(
                format="PSPF/2025",
                package={"name": "test", "version": "1.0.0"},
                allow_empty=True,
            ).build(mock_output)

            assert result1.success, f"Mock build failed: {result1.errors}"

        # Try to build with real launcher (may not be available)
        real_output = temp_dir / "real_package.psp"

        # Import fresh to try to get real function
        import importlib
        import sys

        if "flavor.psp.format_2025.metadata.assembly" in sys.modules:
            del sys.modules["flavor.psp.format_2025.metadata.assembly"]
        assembly_fresh = importlib.import_module("flavor.psp.format_2025.metadata.assembly")

        try:
            # Try to load real launcher first to see if it's available
            assembly_fresh.load_launcher_binary("rust")

            # If we got here, real launcher exists, so build with it
            with unittest.mock.patch.object(
                assembly, "load_launcher_binary", assembly_fresh.load_launcher_binary
            ):
                builder2 = PSPFBuilder.create().with_keys(seed="test")
                result2 = builder2.metadata(
                    format="PSPF/2025",
                    package={"name": "test", "version": "1.0.0"},
                    allow_empty=True,
                ).build(real_output)

                assert result2.success, f"Real build failed: {result2.errors}"

            # Both should have valid PSPF structure
            for package_path in [mock_output, real_output]:
                reader = PSPFReader(package_path)
                assert reader.verify_magic_trailer()
                assert reader.read_index() is not None
                assert reader.read_metadata()["format"] == "PSPF/2025"

        except FileNotFoundError:
            pytest.skip("Real launchers not available - skipping comparison")


@pytest.mark.unit
class TestMockContract:
    """Ensure mock launcher follows the expected contract."""

    def test_mock_is_bytes(self) -> None:
        """Mock launcher should be bytes."""
        assert isinstance(MOCK_LAUNCHER_DATA, bytes)

    def test_mock_has_minimum_size(self) -> None:
        """Mock launcher should have minimum size."""
        assert len(MOCK_LAUNCHER_DATA) >= 100

    def test_mock_size_matches_constant(self) -> None:
        """Mock data length should match declared size."""
        assert len(MOCK_LAUNCHER_DATA) == MOCK_LAUNCHER_SIZE

    def test_mock_has_identifier(self) -> None:
        """Mock should have identifying marker for debugging."""
        assert b"FAKE_LAUNCHER_FOR_TEST" in MOCK_LAUNCHER_DATA


# 🌶️📦🔚
