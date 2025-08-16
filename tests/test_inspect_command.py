"""Tests for the inspect command."""

import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

from flavor.cli import cli
from flavor.inspect import PackageInspector


class TestPackageInspector:
    """Test the PackageInspector class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_package = self.temp_dir / "test.pspf"
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_mock_package(self):
        """Create a mock PSPF package for testing."""
        # This would be replaced with actual PSPF creation
        # For now, create a file that the inspector can analyze
        self.test_package.write_bytes(b"PSPF2025" + b"\x00" * 1000)
        return self.test_package
    
    def test_inspector_initialization(self):
        """Test PackageInspector initializes correctly."""
        package = self.create_mock_package()
        inspector = PackageInspector(package)
        assert inspector.package_path == package
        assert inspector.package_path.exists()
    
    def test_inspect_basic_info(self):
        """Test inspecting basic package information."""
        package = self.create_mock_package()
        inspector = PackageInspector(package)
        
        with patch.object(inspector, '_read_index') as mock_index:
            mock_index.return_value = {
                'format_version': 0x20250001,
                'package_size': 1008,
                'launcher_size': 100,
                'slot_count': 3
            }
            
            info = inspector.get_basic_info()
            
            assert info['format'] == 'PSPF/2025'
            assert info['size'] == 1008
            assert info['launcher_size'] == 100
            assert info['slot_count'] == 3
    
    def test_inspect_metadata(self):
        """Test inspecting package metadata."""
        package = self.create_mock_package()
        inspector = PackageInspector(package)
        
        with patch.object(inspector, '_read_metadata') as mock_meta:
            mock_meta.return_value = {
                'package': {'name': 'test-app', 'version': '1.0.0'},
                'slots': [
                    {'name': 'payload', 'size': 1000, 'encoding': 'gzip'},
                    {'name': 'runtime', 'size': 2000, 'encoding': 'none'}
                ],
                'execution': {'command': 'python main.py'},
                'build': {
                    'builder': 'rust/flavor',
                    'package_timestamp': '2025-01-01T00:00:00Z',
                    'builder_timestamp': '2025-01-01T00:00:00Z'
                }
            }
            
            metadata = inspector.get_metadata()
            
            assert metadata['package']['name'] == 'test-app'
            assert metadata['package']['version'] == '1.0.0'
            assert len(metadata['slots']) == 2
            assert metadata['build']['builder'] == 'rust/flavor'
    
    def test_inspect_slots_detail(self):
        """Test getting detailed slot information."""
        package = self.create_mock_package()
        inspector = PackageInspector(package)
        
        with patch.object(inspector, '_read_slots') as mock_slots:
            mock_slots.return_value = [
                {
                    'index': 0,
                    'name': 'payload',
                    'offset': 1024,
                    'size': 5000,
                    'checksum': 'abc123',
                    'encoding': 'gzip',
                    'purpose': 'payload',
                    'lifecycle': 'persistent'
                },
                {
                    'index': 1,
                    'name': 'runtime',
                    'offset': 6024,
                    'size': 10000,
                    'checksum': 'def456',
                    'encoding': 'none',
                    'purpose': 'runtime',
                    'lifecycle': 'volatile'
                }
            ]
            
            slots = inspector.get_slots_detail()
            
            assert len(slots) == 2
            assert slots[0]['name'] == 'payload'
            assert slots[0]['size'] == 5000
            assert slots[1]['name'] == 'runtime'
            assert slots[1]['lifecycle'] == 'volatile'
    
    def test_inspect_security_info(self):
        """Test inspecting security information."""
        package = self.create_mock_package()
        inspector = PackageInspector(package)
        
        with patch.object(inspector, '_read_security') as mock_sec:
            mock_sec.return_value = {
                'signed': True,
                'signature_valid': True,
                'ephemeral_key': 'abc123...',
                'integrity_seal': True,
                'checksums_valid': True
            }
            
            security = inspector.get_security_info()
            
            assert security['signed'] is True
            assert security['signature_valid'] is True
            assert security['integrity_seal'] is True
    
    def test_inspect_full_report(self):
        """Test generating full inspection report."""
        package = self.create_mock_package()
        inspector = PackageInspector(package)
        
        with patch.object(inspector, 'get_basic_info') as mock_basic, \
             patch.object(inspector, 'get_metadata') as mock_meta, \
             patch.object(inspector, 'get_slots_detail') as mock_slots, \
             patch.object(inspector, 'get_security_info') as mock_sec:
            
            mock_basic.return_value = {'format': 'PSPF/2025', 'size': 1000}
            mock_meta.return_value = {'package': {'name': 'test'}}
            mock_slots.return_value = [{'name': 'slot1'}]
            mock_sec.return_value = {'signed': True}
            
            report = inspector.generate_report()
            
            assert 'basic' in report
            assert 'metadata' in report
            assert 'slots' in report
            assert 'security' in report
            assert report['basic']['format'] == 'PSPF/2025'
    
    def test_inspect_output_formats(self):
        """Test different output formats for inspection."""
        package = self.create_mock_package()
        inspector = PackageInspector(package)
        
        with patch.object(inspector, 'generate_report') as mock_report:
            mock_report.return_value = {
                'basic': {'format': 'PSPF/2025'},
                'metadata': {'package': {'name': 'test'}}
            }
            
            # Test JSON output
            json_output = inspector.format_output('json')
            assert isinstance(json_output, str)
            data = json.loads(json_output)
            assert data['basic']['format'] == 'PSPF/2025'
            
            # Test human-readable output
            human_output = inspector.format_output('human')
            assert isinstance(human_output, str)
            assert 'PSPF/2025' in human_output
            
            # Test YAML output (if supported)
            yaml_output = inspector.format_output('yaml')
            assert isinstance(yaml_output, str)


class TestInspectCLICommand:
    """Test the inspect CLI command."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_inspect_command_basic(self):
        """Test basic inspect command."""
        test_package = self.temp_dir / "test.pspf"
        test_package.write_bytes(b"PSPF2025" + b"\x00" * 100)
        
        with patch('flavor.inspect.PackageInspector') as MockInspector:
            mock_instance = MagicMock()
            MockInspector.return_value = mock_instance
            mock_instance.format_output.return_value = "Package: test\nFormat: PSPF/2025"
            
            result = self.runner.invoke(cli, ["inspect", str(test_package)])
            
            assert result.exit_code == 0
            assert "PSPF/2025" in result.output
    
    def test_inspect_command_json_format(self):
        """Test inspect command with JSON output."""
        test_package = self.temp_dir / "test.pspf"
        test_package.write_bytes(b"PSPF2025" + b"\x00" * 100)
        
        with patch('flavor.inspect.PackageInspector') as MockInspector:
            mock_instance = MagicMock()
            MockInspector.return_value = mock_instance
            mock_instance.format_output.return_value = '{"format": "PSPF/2025"}'
            
            result = self.runner.invoke(cli, ["inspect", str(test_package), "--format", "json"])
            
            assert result.exit_code == 0
            assert '"format"' in result.output
            assert '"PSPF/2025"' in result.output
    
    def test_inspect_command_verbose(self):
        """Test inspect command with verbose output."""
        test_package = self.temp_dir / "test.pspf"
        test_package.write_bytes(b"PSPF2025" + b"\x00" * 100)
        
        with patch('flavor.inspect.PackageInspector') as MockInspector:
            mock_instance = MagicMock()
            MockInspector.return_value = mock_instance
            mock_instance.format_output.return_value = "Detailed output..."
            
            result = self.runner.invoke(cli, ["inspect", str(test_package), "--verbose"])
            
            assert result.exit_code == 0
    
    def test_inspect_command_nonexistent_file(self):
        """Test inspect command with non-existent file."""
        result = self.runner.invoke(cli, ["inspect", "/nonexistent/package.pspf"])
        
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()
    
    def test_inspect_command_invalid_package(self):
        """Test inspect command with invalid package."""
        invalid_package = self.temp_dir / "invalid.pspf"
        invalid_package.write_bytes(b"INVALID" + b"\x00" * 100)
        
        with patch('flavor.inspect.PackageInspector') as MockInspector:
            MockInspector.side_effect = ValueError("Invalid PSPF package")
            
            result = self.runner.invoke(cli, ["inspect", str(invalid_package)])
            
            assert result.exit_code != 0
            assert "Invalid" in result.output or "Error" in result.output