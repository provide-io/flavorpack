#!/usr/bin/env python3
"""
Mock Validation Tests

These tests ensure that our mock launchers accurately represent real launcher behavior.
They should be run as integration tests with real ingredients available.
"""

import pytest
from pathlib import Path

from tests.conftest import MOCK_LAUNCHER_DATA, MOCK_LAUNCHER_SIZE
from flavor.psp.format_2025 import PSPFBuilder, PSPFReader


@pytest.mark.integration
@pytest.mark.requires_ingredients  
class TestMockAccuracy:
    """Validate that our mocks accurately represent real behavior."""
    
    @pytest.fixture(autouse=True)
    def use_real_launcher(self, monkeypatch, request):
        """Override the global mock to use real launchers for these tests."""
        # Skip the global mock fixture for this test class
        from flavor.psp.format_2025.metadata import assembly
        
        # Store the original function
        original_load_launcher = assembly.load_launcher_binary
        
        # The global mock has already patched it, so we need to get the real one
        import importlib
        import sys
        
        # Remove the module from cache to force reimport
        if 'flavor.psp.format_2025.metadata.assembly' in sys.modules:
            del sys.modules['flavor.psp.format_2025.metadata.assembly']
        
        # Reimport to get the original function
        assembly_module = importlib.import_module('flavor.psp.format_2025.metadata.assembly')
        
        # Now assembly_module.load_launcher_binary is the real function
        # But the test still has the mock, so we need to explicitly restore it
        monkeypatch.setattr(assembly, "load_launcher_binary", assembly_module.load_launcher_binary)
    
    def test_launcher_size_assumption(self):
        """Verify mock launcher size is reasonable.
        
        The mock doesn't need to match exactly, but should be in a reasonable range
        for basic format testing.
        """
        from flavor.psp.format_2025.metadata.assembly import load_launcher_binary
        
        try:
            real_launcher = load_launcher_binary("rust")
            
            # Mock should be at least minimally sized
            assert MOCK_LAUNCHER_SIZE >= 100, "Mock launcher too small to be realistic"
            
            # For unit tests, we use a simplified mock that's much smaller than real
            # This is OK as long as the format structure is preserved
            assert len(MOCK_LAUNCHER_DATA) == MOCK_LAUNCHER_SIZE
            
        except FileNotFoundError:
            pytest.skip("Real launchers not available - skipping validation")
    
    def test_mock_package_structure(self, temp_dir):
        """Verify packages built with mocks have valid PSPF structure."""
        # This test uses the mock which is fine - we're testing the mock creates valid structure
        from flavor.psp.format_2025.metadata import assembly
        
        # Ensure we're using the mock for this test
        def mock_launcher(launcher_type):
            return MOCK_LAUNCHER_DATA
        
        # Use a local mock for this specific test
        import unittest.mock
        with unittest.mock.patch.object(assembly, 'load_launcher_binary', mock_launcher):
            output_file = temp_dir / "mock_test.psp"
            
            builder = PSPFBuilder.create().with_keys(seed="test")
            result = builder.metadata(
                format="PSPF/2025",
                package={"name": "mock-test", "version": "1.0.0"},
                allow_empty=True
            ).build(output_file)
            
            assert result.success, f"Build failed: {result.errors}"
        
        # Verify the package has valid PSPF structure
        reader = PSPFReader(output_file)
        
        # Check magic footer
        assert reader.verify_magic()
        
        # Check index block
        index = reader.read_index()
        assert index is not None
        assert index.format_magic == b'PSPF2025'
        
        # Check metadata
        metadata = reader.read_metadata()
        assert metadata['format'] == 'PSPF/2025'
        assert metadata['package']['name'] == 'mock-test'
    
    def test_mock_launcher_content(self):
        """Verify mock launcher has expected format markers."""
        # Our mock should have some identifying content
        assert b"FAKE_LAUNCHER_FOR_TEST" in MOCK_LAUNCHER_DATA
        
        # Mock should be properly padded
        assert len(MOCK_LAUNCHER_DATA) == MOCK_LAUNCHER_SIZE
    
    def test_build_with_mock_vs_real(self, temp_dir):
        """Compare package structure built with mock vs real launcher.
        
        This test builds two packages - one with mock and one with real launcher,
        and verifies they have compatible structure.
        """
        from flavor.psp.format_2025.metadata import assembly
        import unittest.mock
        
        # Build with mock
        mock_output = temp_dir / "mock_package.psp"
        
        def mock_launcher(launcher_type):
            return MOCK_LAUNCHER_DATA
        
        with unittest.mock.patch.object(assembly, 'load_launcher_binary', mock_launcher):
            builder1 = PSPFBuilder.create().with_keys(seed="test")
            result1 = builder1.metadata(
                format="PSPF/2025",
                package={"name": "test", "version": "1.0.0"},
                allow_empty=True
            ).build(mock_output)
            
            assert result1.success, f"Mock build failed: {result1.errors}"
        
        # Try to build with real launcher (may not be available)
        real_output = temp_dir / "real_package.psp"
        
        # Import fresh to try to get real function
        import importlib
        import sys
        if 'flavor.psp.format_2025.metadata.assembly' in sys.modules:
            del sys.modules['flavor.psp.format_2025.metadata.assembly']
        assembly_fresh = importlib.import_module('flavor.psp.format_2025.metadata.assembly')
        
        try:
            # Try to load real launcher first to see if it's available
            real_launcher_data = assembly_fresh.load_launcher_binary("rust")
            
            # If we got here, real launcher exists, so build with it
            with unittest.mock.patch.object(assembly, 'load_launcher_binary', assembly_fresh.load_launcher_binary):
                builder2 = PSPFBuilder.create().with_keys(seed="test")
                result2 = builder2.metadata(
                    format="PSPF/2025",
                    package={"name": "test", "version": "1.0.0"},
                    allow_empty=True
                ).build(real_output)
                
                assert result2.success, f"Real build failed: {result2.errors}"
            
            # Both should have valid PSPF structure
            for package_path in [mock_output, real_output]:
                reader = PSPFReader(package_path)
                assert reader.verify_magic()
                assert reader.read_index() is not None
                assert reader.read_metadata()['format'] == 'PSPF/2025'
                
        except FileNotFoundError:
            pytest.skip("Real launchers not available - skipping comparison")


@pytest.mark.unit
class TestMockContract:
    """Ensure mock launcher follows the expected contract."""
    
    def test_mock_is_bytes(self):
        """Mock launcher should be bytes."""
        assert isinstance(MOCK_LAUNCHER_DATA, bytes)
    
    def test_mock_has_minimum_size(self):
        """Mock launcher should have minimum size."""
        assert len(MOCK_LAUNCHER_DATA) >= 100
    
    def test_mock_size_matches_constant(self):
        """Mock data length should match declared size."""
        assert len(MOCK_LAUNCHER_DATA) == MOCK_LAUNCHER_SIZE
    
    def test_mock_has_identifier(self):
        """Mock should have identifying marker for debugging."""
        assert b"FAKE_LAUNCHER_FOR_TEST" in MOCK_LAUNCHER_DATA