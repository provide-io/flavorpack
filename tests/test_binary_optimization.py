"""Tests for binary optimization features (strip flag, compression)."""

import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest
from click.testing import CliRunner

from flavor.cli import cli
from flavor.optimization import BinaryOptimizer


class TestBinaryOptimizer:
    """Test the BinaryOptimizer class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_binary = self.temp_dir / "test_binary"
        # Create a fake binary with some data
        self.test_binary.write_bytes(b"\x7fELF" + b"X" * 10000)  # Fake ELF header
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_strip_binary(self):
        """Test stripping debug symbols from binary."""
        optimizer = BinaryOptimizer()
        
        original_size = self.test_binary.stat().st_size
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = optimizer.strip_binary(self.test_binary)
            
            assert result['success'] is True
            assert result['original_size'] == original_size
            mock_run.assert_called_once()
            
            # Check strip command was called with correct args
            call_args = mock_run.call_args[0][0]
            assert 'strip' in call_args[0]
            assert str(self.test_binary) in call_args
    
    def test_strip_binary_failure(self):
        """Test handling strip command failure."""
        optimizer = BinaryOptimizer()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="strip failed")
            
            result = optimizer.strip_binary(self.test_binary)
            
            assert result['success'] is False
            assert 'error' in result
    
    def test_compress_with_upx(self):
        """Test compressing binary with UPX."""
        optimizer = BinaryOptimizer()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = optimizer.compress_upx(self.test_binary)
            
            assert result['success'] is True
            mock_run.assert_called_once()
            
            # Check UPX command was called
            call_args = mock_run.call_args[0][0]
            assert 'upx' in call_args[0]
    
    def test_compress_upx_not_available(self):
        """Test handling when UPX is not available."""
        optimizer = BinaryOptimizer()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("upx not found")
            
            result = optimizer.compress_upx(self.test_binary)
            
            assert result['success'] is False
            assert 'not available' in result.get('error', '').lower()
    
    def test_optimize_binary_full_pipeline(self):
        """Test full optimization pipeline."""
        optimizer = BinaryOptimizer()
        
        with patch.object(optimizer, 'strip_binary') as mock_strip, \
             patch.object(optimizer, 'compress_upx') as mock_upx:
            
            mock_strip.return_value = {'success': True, 'size_reduction': 1000}
            mock_upx.return_value = {'success': True, 'size_reduction': 2000}
            
            result = optimizer.optimize(self.test_binary, strip=True, compress=True)
            
            assert result['total_reduction'] == 3000
            mock_strip.assert_called_once()
            mock_upx.assert_called_once()
    
    def test_optimize_strip_only(self):
        """Test optimization with only strip flag."""
        optimizer = BinaryOptimizer()
        
        with patch.object(optimizer, 'strip_binary') as mock_strip, \
             patch.object(optimizer, 'compress_upx') as mock_upx:
            
            mock_strip.return_value = {'success': True, 'size_reduction': 1000}
            
            result = optimizer.optimize(self.test_binary, strip=True, compress=False)
            
            assert result['total_reduction'] == 1000
            mock_strip.assert_called_once()
            mock_upx.assert_not_called()


class TestStripFlagIntegration:
    """Test the --strip flag in the build process."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('flavor.cli.build_package_from_manifest')
    def test_package_with_strip_flag(self, mock_build):
        """Test package command with --strip flag."""
        manifest = self.temp_dir / "pyproject.toml"
        manifest.write_text("[tool.flavor]\nname = 'test'\nentry_point = 'main:app'")
        
        mock_build.return_value = [self.temp_dir / "test.psp"]
        
        result = self.runner.invoke(cli, [
            "package",
            "--manifest", str(manifest),
            "--output", str(self.temp_dir / "test.psp"),
            "--strip"
        ])
        
        # Check that strip flag was passed through
        mock_build.assert_called_once()
        args, kwargs = mock_build.call_args
        assert kwargs.get('strip_binaries') == True
    
    def test_strip_flag_shows_size_reduction(self):
        """Test that strip flag shows size reduction in output."""
        manifest = self.temp_dir / "pyproject.toml"
        manifest.write_text("[tool.flavor]\nname = 'test'\nentry_point = 'main:app'")
        
        with patch('flavor.cli.build_package_from_manifest') as mock_build:
            mock_build.return_value = [self.temp_dir / "test.psp"]
            
            result = self.runner.invoke(cli, [
                "package",
                "--manifest", str(manifest),
                "--output", str(self.temp_dir / "test.psp"),
                "--strip"
            ])
            
            # The CLI shows a message about optimization when strip is used
            assert "optimized" in result.output.lower() or "stripped" in result.output.lower()