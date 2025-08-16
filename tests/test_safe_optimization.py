#!/usr/bin/env python3
"""Tests for safe optimization features."""

import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from flavor.safe_optimization import SafeOptimizer, DependencyAnalyzer


class TestSafeOptimizer:
    """Test the SafeOptimizer class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_wheel(self, name: str = "test_package-1.0.0-py3-none-any.whl") -> Path:
        """Create a test wheel with various files."""
        wheel_path = self.temp_dir / name
        
        with zipfile.ZipFile(wheel_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add main package files
            zf.writestr("test_package/__init__.py", "# Main package")
            zf.writestr("test_package/core.py", "def main(): pass")
            
            # Add cache files (should be removed)
            zf.writestr("test_package/__pycache__/core.cpython-39.pyc", b"FAKE_PYC")
            zf.writestr("test_package/__pycache__/__init__.cpython-39.pyc", b"FAKE_PYC")
            
            # Add test files (should be removed)
            zf.writestr("test_package/tests/__init__.py", "# Tests")
            zf.writestr("test_package/tests/test_core.py", "def test_main(): pass")
            zf.writestr("test_package/test_utils.py", "# Test utils")
            
            # Add docs (should be removed)
            zf.writestr("test_package/README.md", "# Documentation")
            zf.writestr("test_package/docs/guide.rst", "User Guide")
            zf.writestr("test_package/CHANGELOG.txt", "Changelog")
            
            # Add type hints (should be removed)
            zf.writestr("test_package/core.pyi", "def main() -> None: ...")
            zf.writestr("test_package/py.typed", "")
            
            # Add license (should be kept)
            zf.writestr("test_package/LICENSE.txt", "MIT License")
            
            # Add metadata (should be kept)
            zf.writestr("test_package-1.0.0.dist-info/METADATA", "Name: test_package")
            
        return wheel_path
    
    def test_remove_cache_files(self):
        """Test removing __pycache__ and .pyc files."""
        wheel_path = self.create_test_wheel()
        optimizer = SafeOptimizer()
        
        # Check original contents
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            original_files = zf.namelist()
            assert any("__pycache__" in f for f in original_files)
            assert any(".pyc" in f for f in original_files)
        
        # Optimize
        saved = optimizer.remove_cache_files(wheel_path)
        
        # Check optimized contents
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            new_files = zf.namelist()
            assert not any("__pycache__" in f for f in new_files)
            assert not any(".pyc" in f for f in new_files)
            assert "test_package/core.py" in new_files  # Main files kept
        
        assert saved > 0
    
    def test_remove_test_files(self):
        """Test removing test directories and files."""
        wheel_path = self.create_test_wheel()
        optimizer = SafeOptimizer()
        
        # Optimize
        saved = optimizer.remove_test_files(wheel_path)
        
        # Check optimized contents
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            new_files = zf.namelist()
            assert not any("tests/" in f for f in new_files)
            assert not any("test_" in f for f in new_files)
            assert "test_package/core.py" in new_files  # Main files kept
        
        assert saved > 0
    
    def test_remove_docs(self):
        """Test removing documentation files."""
        wheel_path = self.create_test_wheel()
        optimizer = SafeOptimizer()
        
        # Optimize
        saved = optimizer.remove_docs(wheel_path)
        
        # Check optimized contents
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            new_files = zf.namelist()
            assert not any(".md" in f for f in new_files)
            assert not any(".rst" in f for f in new_files)
            assert not any("CHANGELOG" in f for f in new_files)
            assert "test_package/LICENSE.txt" in new_files  # License kept
            assert "test_package/core.py" in new_files  # Main files kept
        
        assert saved > 0
    
    def test_strip_type_hints(self):
        """Test removing type stub files."""
        wheel_path = self.create_test_wheel()
        optimizer = SafeOptimizer()
        
        # Optimize
        saved = optimizer.strip_type_hints(wheel_path)
        
        # Check optimized contents
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            new_files = zf.namelist()
            assert not any(".pyi" in f for f in new_files)
            assert not any("py.typed" in f for f in new_files)
            assert "test_package/core.py" in new_files  # Main files kept
        
        assert saved > 0
    
    def test_all_optimizations(self):
        """Test applying all optimizations together."""
        wheel_path = self.create_test_wheel()
        original_size = wheel_path.stat().st_size
        
        optimizer = SafeOptimizer()
        
        total_saved = 0
        total_saved += optimizer.remove_cache_files(wheel_path)
        total_saved += optimizer.remove_test_files(wheel_path)
        total_saved += optimizer.remove_docs(wheel_path)
        total_saved += optimizer.strip_type_hints(wheel_path)
        
        new_size = wheel_path.stat().st_size
        
        # Should be significantly smaller
        assert new_size < original_size
        assert total_saved > 0
        
        # Check that core functionality is preserved
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            new_files = zf.namelist()
            assert "test_package/__init__.py" in new_files
            assert "test_package/core.py" in new_files
            assert "test_package/LICENSE.txt" in new_files
            assert "test_package-1.0.0.dist-info/METADATA" in new_files
            
            # All removable files should be gone
            assert not any("__pycache__" in f for f in new_files)
            assert not any("test" in f.lower() for f in new_files if "test_package" in f)
            assert not any(f.endswith((".md", ".rst", ".pyi")) for f in new_files)


class TestDependencyAnalyzer:
    """Test the DependencyAnalyzer class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_analyze_imports(self):
        """Test analyzing imports in a project."""
        # Create test Python files
        (self.temp_dir / "main.py").write_text("""
import os
import json
from pathlib import Path
import click

def main():
    pass
""")
        
        (self.temp_dir / "utils.py").write_text("""
import sys
import json
from typing import List

def helper():
    pass
""")
        
        analyzer = DependencyAnalyzer()
        imports = analyzer.analyze_imports(self.temp_dir)
        
        # Check detected imports
        assert "os" in imports
        assert "json" in imports
        assert "pathlib" in imports
        assert "click" in imports
        assert "sys" in imports
        assert "typing" in imports
        
        # Check which files use each import
        assert str(self.temp_dir / "main.py") in imports["json"]
        assert str(self.temp_dir / "utils.py") in imports["json"]
        assert len(imports["json"]) == 2
    
    def test_suggest_removals(self):
        """Test suggesting packages that might be removable."""
        analyzer = DependencyAnalyzer()
        
        required = {"click", "requests", "numpy"}
        installed = {"click", "requests", "numpy", "pytest", "black", "pip", "setuptools"}
        
        suggestions = analyzer.suggest_removals(required, installed)
        
        # Should suggest test/dev tools but not core packages
        assert "pytest" in suggestions
        assert "black" in suggestions
        
        # Should never suggest removing these
        assert "pip" not in suggestions
        assert "setuptools" not in suggestions
        
        # Should not suggest required packages
        assert "click" not in suggestions
        assert "requests" not in suggestions