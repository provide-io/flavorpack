#!/usr/bin/env python3
"""Tests for the helper management system."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from flavor.helpers import HelperInfo, HelperManager


@pytest.mark.helpers
@pytest.mark.requires_helpers
class TestHelperManager:
    """Test the HelperManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create a temporary directory structure
        self.temp_dir = Path(tempfile.mkdtemp())
        self.helpers_dir = self.temp_dir / "helpers"
        self.helpers_bin = self.helpers_dir / "bin"
        self.src_dir = self.temp_dir / "src" / "flavor"
        
        # Create directories
        self.helpers_bin.mkdir(parents=True)
        self.src_dir.mkdir(parents=True)
        
        # Patch the HelperManager to use our temp directory
        self.manager = HelperManager()
        self.manager.flavor_root = self.temp_dir
        self.manager.helpers_dir = self.helpers_dir
        self.manager.helpers_bin = self.helpers_bin
        self.manager.src_dir = self.src_dir
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_fake_helper(self, name: str, content: str = "#!/bin/sh\necho 'test'") -> Path:
        """Create a fake helper binary for testing."""
        helper_path = self.helpers_bin / name
        helper_path.write_text(content)
        helper_path.chmod(0o755)
        return helper_path
    
    def test_list_helpers_empty(self):
        """Test listing helpers when none exist."""
        helpers = self.manager.list_helpers()
        assert helpers == {"launchers": [], "builders": []}
    
    def test_list_helpers_with_binaries(self):
        """Test listing helpers when binaries exist."""
        # Create fake helpers
        self.create_fake_helper("flavor-go-launcher")
        self.create_fake_helper("flavor-rs-launcher")
        self.create_fake_helper("flavor-go-builder")
        self.create_fake_helper("flavor-rs-builder")
        
        helpers = self.manager.list_helpers()
        
        # Check launchers
        assert len(helpers["launchers"]) == 2
        launcher_names = [h.name for h in helpers["launchers"]]
        assert "flavor-go-launcher" in launcher_names
        assert "flavor-rs-launcher" in launcher_names
        
        # Check builders
        assert len(helpers["builders"]) == 2
        builder_names = [h.name for h in helpers["builders"]]
        assert "flavor-go-builder" in builder_names
        assert "flavor-rs-builder" in builder_names
    
    def test_get_helper_info(self):
        """Test getting information about a specific helper."""
        # Create a fake helper
        helper_path = self.create_fake_helper("flavor-go-launcher")
        
        info = self.manager._get_helper_info(helper_path)
        
        assert info is not None
        assert info.name == "flavor-go-launcher"
        assert info.path == helper_path
        assert info.type == "launcher"
        assert info.language == "go"
        assert info.size > 0
        assert info.checksum is not None
    
    def test_get_helper_info_rust_alias(self):
        """Test that 'rs' is correctly mapped to 'rust'."""
        helper_path = self.create_fake_helper("flavor-rs-builder")
        
        info = self.manager._get_helper_info(helper_path)
        
        assert info is not None
        assert info.language == "rust"  # 'rs' should be mapped to 'rust'
        assert info.type == "builder"
    
    def test_get_helper_info_by_name(self):
        """Test getting helper info by name."""
        self.create_fake_helper("flavor-go-launcher")
        
        # Exact match
        info = self.manager.get_helper_info("flavor-go-launcher")
        assert info is not None
        assert info.name == "flavor-go-launcher"
        
        # Partial match
        info = self.manager.get_helper_info("go-launcher")
        assert info is not None
        assert info.name == "flavor-go-launcher"
        
        # Non-existent
        info = self.manager.get_helper_info("non-existent")
        assert info is None
    
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_build_go_helpers(self, mock_run, mock_which):
        """Test building Go helpers."""
        # Mock Go availability
        mock_which.return_value = "/usr/bin/go"
        
        # Mock subprocess to create the output files
        def mock_run_side_effect(cmd, **kwargs):
            # Extract output path from go build command
            if "-o" in cmd:
                output_idx = cmd.index("-o") + 1
                output_path = Path(cmd[output_idx])
                # Create the output file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("fake binary")
            return MagicMock(returncode=0)
        
        mock_run.side_effect = mock_run_side_effect
        
        # Create source directories
        go_launcher_src = self.src_dir / "go" / "cmd" / "pspf-launcher"
        go_launcher_src.mkdir(parents=True)
        go_builder_src = self.src_dir / "go" / "cmd" / "pspf-builder"
        go_builder_src.mkdir(parents=True)
        
        built = self.manager._build_go_helpers()
        
        # Should have built 2 helpers
        assert len(built) == 2
        
        # Check that go build was called correctly
        assert mock_run.call_count == 2
        
        # Verify output paths
        assert self.helpers_bin / "flavor-go-launcher" in built
        assert self.helpers_bin / "flavor-go-builder" in built
    
    @patch("shutil.which")
    def test_build_go_helpers_no_compiler(self, mock_which):
        """Test building Go helpers when Go is not available."""
        mock_which.return_value = None
        
        built = self.manager._build_go_helpers()
        
        assert len(built) == 0
    
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_build_rust_helpers(self, mock_run, mock_which):
        """Test building Rust helpers."""
        # Mock Cargo availability
        mock_which.return_value = "/usr/bin/cargo"
        mock_run.return_value = MagicMock(returncode=0)
        
        # Create source directories and fake built binaries
        rust_launcher_src = self.src_dir / "rust" / "pspf-launcher-rs"
        rust_launcher_src.mkdir(parents=True)
        rust_launcher_target = rust_launcher_src / "target" / "release"
        rust_launcher_target.mkdir(parents=True)
        (rust_launcher_target / "pspf-launcher-rs").write_text("fake binary")
        
        rust_builder_src = self.src_dir / "rust" / "pspf-builder-rs"
        rust_builder_src.mkdir(parents=True)
        rust_builder_target = rust_builder_src / "target" / "release"
        rust_builder_target.mkdir(parents=True)
        (rust_builder_target / "pspf-builder-rs").write_text("fake binary")
        
        built = self.manager._build_rust_helpers()
        
        # Should have built 2 helpers
        assert len(built) == 2
        
        # Check that cargo build was called correctly
        assert mock_run.call_count == 2
        
        # Verify output paths
        assert self.helpers_bin / "flavor-rs-launcher" in built
        assert self.helpers_bin / "flavor-rs-builder" in built
    
    @patch("shutil.which")
    def test_build_rust_helpers_no_compiler(self, mock_which):
        """Test building Rust helpers when Cargo is not available."""
        mock_which.return_value = None
        
        built = self.manager._build_rust_helpers()
        
        assert len(built) == 0
    
    def test_build_helpers_all_languages(self):
        """Test building helpers for all languages."""
        with patch.object(self.manager, "_build_go_helpers") as mock_go:
            with patch.object(self.manager, "_build_rust_helpers") as mock_rust:
                mock_go.return_value = [Path("go1"), Path("go2")]
                mock_rust.return_value = [Path("rust1"), Path("rust2")]
                
                built = self.manager.build_helpers()
                
                # Both builders should be called
                mock_go.assert_called_once()
                mock_rust.assert_called_once()
                
                # Should return all built paths
                assert len(built) == 4
    
    def test_build_helpers_specific_language(self):
        """Test building helpers for a specific language."""
        with patch.object(self.manager, "_build_go_helpers") as mock_go:
            with patch.object(self.manager, "_build_rust_helpers") as mock_rust:
                mock_go.return_value = [Path("go1"), Path("go2")]
                
                built = self.manager.build_helpers(language="go")
                
                # Only Go builder should be called
                mock_go.assert_called_once()
                mock_rust.assert_not_called()
                
                assert len(built) == 2
    
    def test_build_helpers_force_rebuild(self):
        """Test force rebuilding existing helpers."""
        # Create existing helper
        existing = self.create_fake_helper("flavor-go-launcher")
        
        with patch.object(self.manager, "_build_go_helpers") as mock_go:
            mock_go.return_value = [existing]
            
            # Without force, shouldn't rebuild
            built = self.manager.build_helpers(language="go", force=False)
            mock_go.assert_called_with(False)
            
            # With force, should rebuild
            built = self.manager.build_helpers(language="go", force=True)
            mock_go.assert_called_with(True)
    
    def test_clean_helpers_all(self):
        """Test cleaning all helpers."""
        # Create fake helpers
        go_launcher = self.create_fake_helper("flavor-go-launcher")
        rs_launcher = self.create_fake_helper("flavor-rs-launcher")
        go_builder = self.create_fake_helper("flavor-go-builder")
        rs_builder = self.create_fake_helper("flavor-rs-builder")
        
        removed = self.manager.clean_helpers()
        
        # All should be removed
        assert len(removed) == 4
        assert not go_launcher.exists()
        assert not rs_launcher.exists()
        assert not go_builder.exists()
        assert not rs_builder.exists()
    
    def test_clean_helpers_specific_language(self):
        """Test cleaning helpers for a specific language."""
        # Create fake helpers
        go_launcher = self.create_fake_helper("flavor-go-launcher")
        rs_launcher = self.create_fake_helper("flavor-rs-launcher")
        go_builder = self.create_fake_helper("flavor-go-builder")
        rs_builder = self.create_fake_helper("flavor-rs-builder")
        
        removed = self.manager.clean_helpers(language="go")
        
        # Only Go helpers should be removed
        assert len(removed) == 2
        assert not go_launcher.exists()
        assert not go_builder.exists()
        assert rs_launcher.exists()
        assert rs_builder.exists()
    
    def test_clean_helpers_rust_aliases(self):
        """Test that cleaning 'rust' also cleans 'rs' prefixed helpers."""
        rs_launcher = self.create_fake_helper("flavor-rs-launcher")
        rust_builder = self.create_fake_helper("flavor-rust-builder")
        
        removed = self.manager.clean_helpers(language="rust")
        
        # Both rs and rust prefixed files should be removed
        assert len(removed) == 2
        assert not rs_launcher.exists()
        assert not rust_builder.exists()
    
    @patch("subprocess.run")
    def test_test_helpers_success(self, mock_run):
        """Test testing helpers successfully."""
        # Create fake helpers
        self.create_fake_helper("flavor-go-launcher")
        self.create_fake_helper("flavor-rs-builder")
        
        # Mock successful version calls
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="version 1.0.0",
            stderr=""
        )
        
        results = self.manager.test_helpers()
        
        assert len(results["passed"]) == 2
        assert len(results["failed"]) == 0
        assert "flavor-go-launcher" in results["passed"]
        assert "flavor-rs-builder" in results["passed"]
    
    @patch("subprocess.run")
    def test_test_helpers_failure(self, mock_run):
        """Test testing helpers with failures."""
        # Create fake helper
        self.create_fake_helper("flavor-go-launcher")
        
        # Mock failed version call
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error"
        )
        
        results = self.manager.test_helpers()
        
        assert len(results["passed"]) == 0
        assert len(results["failed"]) == 1
        assert results["failed"][0]["name"] == "flavor-go-launcher"
    
    @patch("subprocess.run")
    def test_test_helpers_timeout(self, mock_run):
        """Test testing helpers with timeout."""
        # Create fake helper
        self.create_fake_helper("flavor-go-launcher")
        
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
        
        results = self.manager.test_helpers()
        
        assert len(results["passed"]) == 0
        assert len(results["failed"]) == 1
        assert "Timeout" in results["failed"][0]["error"]
    
    def test_test_helpers_not_executable(self):
        """Test testing helpers that are not executable."""
        # Create non-executable file
        helper = self.helpers_bin / "flavor-go-launcher"
        helper.write_text("not executable")
        helper.chmod(0o644)  # Not executable
        
        results = self.manager.test_helpers()
        
        assert len(results["passed"]) == 0
        assert len(results["failed"]) == 1
        assert "not executable" in results["failed"][0]["error"]
    
    @patch("subprocess.run")
    def test_test_helpers_specific_language(self, mock_run):
        """Test testing helpers for a specific language."""
        # Create fake helpers
        self.create_fake_helper("flavor-go-launcher")
        self.create_fake_helper("flavor-rs-builder")
        
        mock_run.return_value = MagicMock(returncode=0)
        
        results = self.manager.test_helpers(language="go")
        
        assert len(results["passed"]) == 1
        assert len(results["skipped"]) == 1
        assert "flavor-go-launcher" in results["passed"]
        assert "flavor-rs-builder" in results["skipped"]
    
    def test_install_prebuilt_placeholder(self):
        """Test that install_prebuilt is a placeholder for now."""
        installed = self.manager.install_prebuilt()
        assert installed == []


@pytest.mark.helpers
@pytest.mark.unit
class TestHelperInfo:
    """Test the HelperInfo dataclass."""
    
    def test_helper_info_creation(self):
        """Test creating a HelperInfo object."""
        info = HelperInfo(
            name="flavor-go-launcher",
            path=Path("/helpers/bin/flavor-go-launcher"),
            type="launcher",
            language="go",
            size=4096,
            checksum="abc123",
            version="1.0.0",
            built_from=Path("/src/go/cmd/pspf-launcher"),
        )
        
        assert info.name == "flavor-go-launcher"
        assert info.type == "launcher"
        assert info.language == "go"
        assert info.size == 4096
        assert info.checksum == "abc123"
        assert info.version == "1.0.0"