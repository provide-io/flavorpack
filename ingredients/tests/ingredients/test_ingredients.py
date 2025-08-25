#!/usr/bin/env python3
"""Tests for the ingredient management system."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from flavor.ingredients.manager import IngredientInfo, IngredientManager


@pytest.mark.requires_ingredients
class TestIngredientManager:
    """Test the IngredientManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create a temporary directory structure
        self.temp_dir = Path(tempfile.mkdtemp())
        self.ingredients_dir = self.temp_dir / "ingredients"
        self.ingredients_bin = self.ingredients_dir / "bin"
        self.src_dir = self.temp_dir / "src" / "flavor"
        self.installed_ingredients_bin = self.temp_dir / "cache" / "flavor" / "ingredients" / "bin"
        
        # Create directories
        self.ingredients_bin.mkdir(parents=True)
        self.src_dir.mkdir(parents=True)
        self.installed_ingredients_bin.mkdir(parents=True)
        
        # Patch the IngredientManager to use our temp directory
        self.manager = IngredientManager()
        self.manager.flavor_root = self.temp_dir
        self.manager.ingredients_dir = self.ingredients_dir
        self.manager.ingredients_bin = self.ingredients_bin
        self.manager.src_dir = self.src_dir
        # Also override the installed ingredients directory to avoid finding real ingredients
        self.manager.installed_ingredients_bin = self.installed_ingredients_bin
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_fake_ingredient(self, name: str, content: str = "#!/bin/sh\necho 'test'") -> Path:
        """Create a fake ingredient binary for testing."""
        ingredient_path = self.ingredients_bin / name
        ingredient_path.write_text(content)
        ingredient_path.chmod(0o755)
        return ingredient_path
    
    def test_list_ingredients_empty(self):
        """Test listing ingredients when none exist."""
        ingredients = self.manager.list_ingredients()
        assert ingredients == {"launchers": [], "builders": []}
    
    def test_list_ingredients_with_binaries(self):
        """Test listing ingredients when binaries exist."""
        # Create fake ingredients
        self.create_fake_ingredient("flavor-go-launcher")
        self.create_fake_ingredient("flavor-rs-launcher")
        self.create_fake_ingredient("flavor-go-builder")
        self.create_fake_ingredient("flavor-rs-builder")
        
        ingredients = self.manager.list_ingredients()
        
        # Check launchers
        assert len(ingredients["launchers"]) == 2
        launcher_names = [h.name for h in ingredients["launchers"]]
        assert "flavor-go-launcher" in launcher_names
        assert "flavor-rs-launcher" in launcher_names
        
        # Check builders
        assert len(ingredients["builders"]) == 2
        builder_names = [h.name for h in ingredients["builders"]]
        assert "flavor-go-builder" in builder_names
        assert "flavor-rs-builder" in builder_names
    
    def test_get_ingredient_info(self):
        """Test getting information about a specific ingredient."""
        # Create a fake ingredient
        ingredient_path = self.create_fake_ingredient("flavor-go-launcher")
        
        info = self.manager._get_ingredient_info(ingredient_path)
        
        assert info is not None
        assert info.name == "flavor-go-launcher"
        assert info.path == ingredient_path
        assert info.type == "launcher"
        assert info.language == "go"
        assert info.size > 0
        assert info.checksum is not None
    
    def test_get_ingredient_info_rust_alias(self):
        """Test that 'rs' is correctly mapped to 'rust'."""
        ingredient_path = self.create_fake_ingredient("flavor-rs-builder")
        
        info = self.manager._get_ingredient_info(ingredient_path)
        
        assert info is not None
        assert info.language == "rust"  # 'rs' should be mapped to 'rust'
        assert info.type == "builder"
    
    def test_get_ingredient_info_by_name(self):
        """Test getting ingredient info by name."""
        self.create_fake_ingredient("flavor-go-launcher")
        
        # Exact match
        info = self.manager.get_ingredient_info("flavor-go-launcher")
        assert info is not None
        assert info.name == "flavor-go-launcher"
        
        # Partial match
        info = self.manager.get_ingredient_info("go-launcher")
        assert info is not None
        assert info.name == "flavor-go-launcher"
        
        # Non-existent
        info = self.manager.get_ingredient_info("non-existent")
        assert info is None
    
    @patch("shutil.which")
    @patch("flavor.ingredients.manager.run_command")
    def test_build_go_ingredients(self, mock_run, mock_which):
        """Test building Go ingredients."""
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
        go_launcher_src = self.src_dir / "go" / "cmd" / "flavor-go-launcher"
        go_launcher_src.mkdir(parents=True)
        go_builder_src = self.src_dir / "go" / "cmd" / "flavor-go-builder"
        go_builder_src.mkdir(parents=True)
        
        built = self.manager._build_go_ingredients()
        
        # Should have built 2 ingredients
        assert len(built) == 2
        
        # Check that go build was called correctly
        assert mock_run.call_count == 2
        
        # Verify output paths
        assert self.ingredients_bin / "flavor-go-launcher" in built
        assert self.ingredients_bin / "flavor-go-builder" in built
    
    @patch("shutil.which")
    def test_build_go_ingredients_no_compiler(self, mock_which):
        """Test building Go ingredients when Go is not available."""
        mock_which.return_value = None
        
        built = self.manager._build_go_ingredients()
        
        assert len(built) == 0
    
    @patch("shutil.copy2")
    @patch("shutil.which")
    @patch("flavor.ingredients.manager.run_command")
    @patch("flavor.utils.get_platform_string")
    def test_build_rust_ingredients(self, mock_platform, mock_run, mock_which, mock_copy):
        """Test building Rust ingredients."""
        # Mock platform string
        mock_platform.return_value = "darwin_arm64"
        
        # Mock Cargo availability
        mock_which.return_value = "/usr/bin/cargo"
        mock_run.return_value = MagicMock(returncode=0)
        
        # Create source directories and fake built binaries
        # The actual code looks for binaries in ingredients/flavor-rs/target/release
        rust_src_dir = self.ingredients_dir / "flavor-rs"
        rust_target = rust_src_dir / "target" / "release"
        rust_target.mkdir(parents=True)
        (rust_target / "flavor-rs-launcher").write_bytes(b"fake launcher binary")
        (rust_target / "flavor-rs-builder").write_bytes(b"fake builder binary")
        
        # Mock copy2 to simulate copying binaries
        def copy_side_effect(src, dst):
            # Create the destination file
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            Path(dst).write_bytes(b"fake binary")
            Path(dst).chmod(0o755)
        mock_copy.side_effect = copy_side_effect
        
        built = self.manager._build_rust_ingredients()
        
        # Should have built 2 ingredients  
        assert len(built) == 2
        
        # Check that cargo build was called correctly (workspace build)
        assert mock_run.call_count == 1  # Single workspace build
        
        # Verify output paths with platform suffix
        assert self.ingredients_bin / "flavor-rs-launcher-darwin_arm64" in built or self.ingredients_bin / "flavor-rs-launcher" in built
        assert self.ingredients_bin / "flavor-rs-builder-darwin_arm64" in built or self.ingredients_bin / "flavor-rs-builder" in built
    
    @patch("shutil.which")
    def test_build_rust_ingredients_no_compiler(self, mock_which):
        """Test building Rust ingredients when Cargo is not available."""
        mock_which.return_value = None
        
        built = self.manager._build_rust_ingredients()
        
        assert len(built) == 0
    
    def test_build_ingredients_all_languages(self):
        """Test building ingredients for all languages."""
        with patch.object(self.manager, "_build_go_ingredients") as mock_go:
            with patch.object(self.manager, "_build_rust_ingredients") as mock_rust:
                mock_go.return_value = [Path("go1"), Path("go2")]
                mock_rust.return_value = [Path("rust1"), Path("rust2")]
                
                built = self.manager.build_ingredients()
                
                # Both builders should be called
                mock_go.assert_called_once()
                mock_rust.assert_called_once()
                
                # Should return all built paths
                assert len(built) == 4
    
    def test_build_ingredients_specific_language(self):
        """Test building ingredients for a specific language."""
        with patch.object(self.manager, "_build_go_ingredients") as mock_go:
            with patch.object(self.manager, "_build_rust_ingredients") as mock_rust:
                mock_go.return_value = [Path("go1"), Path("go2")]
                
                built = self.manager.build_ingredients(language="go")
                
                # Only Go builder should be called
                mock_go.assert_called_once()
                mock_rust.assert_not_called()
                
                assert len(built) == 2
    
    def test_build_ingredients_force_rebuild(self):
        """Test force rebuilding existing ingredients."""
        # Create existing ingredient
        existing = self.create_fake_ingredient("flavor-go-launcher")
        
        with patch.object(self.manager, "_build_go_ingredients") as mock_go:
            mock_go.return_value = [existing]
            
            # Without force, shouldn't rebuild
            built = self.manager.build_ingredients(language="go", force=False)
            mock_go.assert_called_with(False)
            
            # With force, should rebuild
            built = self.manager.build_ingredients(language="go", force=True)
            mock_go.assert_called_with(True)
    
    def test_clean_ingredients_all(self):
        """Test cleaning all ingredients."""
        # Create fake ingredients
        go_launcher = self.create_fake_ingredient("flavor-go-launcher")
        rs_launcher = self.create_fake_ingredient("flavor-rs-launcher")
        go_builder = self.create_fake_ingredient("flavor-go-builder")
        rs_builder = self.create_fake_ingredient("flavor-rs-builder")
        
        removed = self.manager.clean_ingredients()
        
        # All should be removed
        assert len(removed) == 4
        assert not go_launcher.exists()
        assert not rs_launcher.exists()
        assert not go_builder.exists()
        assert not rs_builder.exists()
    
    def test_clean_ingredients_specific_language(self):
        """Test cleaning ingredients for a specific language."""
        # Create fake ingredients
        go_launcher = self.create_fake_ingredient("flavor-go-launcher")
        rs_launcher = self.create_fake_ingredient("flavor-rs-launcher")
        go_builder = self.create_fake_ingredient("flavor-go-builder")
        rs_builder = self.create_fake_ingredient("flavor-rs-builder")
        
        removed = self.manager.clean_ingredients(language="go")
        
        # Only Go ingredients should be removed
        assert len(removed) == 2
        assert not go_launcher.exists()
        assert not go_builder.exists()
        assert rs_launcher.exists()
        assert rs_builder.exists()
    
    def test_clean_ingredients_rust_aliases(self):
        """Test that cleaning 'rust' also cleans 'rs' prefixed ingredients."""
        rs_launcher = self.create_fake_ingredient("flavor-rs-launcher")
        rust_builder = self.create_fake_ingredient("flavor-rs-builder")
        
        removed = self.manager.clean_ingredients(language="rust")
        
        # Both rs and rust prefixed files should be removed
        assert len(removed) == 2
        assert not rs_launcher.exists()
        assert not rust_builder.exists()
    
    @patch("flavor.ingredients.manager.run_command")
    def test_test_ingredients_success(self, mock_run):
        """Test testing ingredients successfully."""
        # Create fake ingredients
        self.create_fake_ingredient("flavor-go-launcher")
        self.create_fake_ingredient("flavor-rs-builder")
        
        # Mock successful version calls
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="version 1.0.0",
            stderr=""
        )
        
        results = self.manager.test_ingredients()
        
        assert len(results["passed"]) == 2
        assert len(results["failed"]) == 0
        assert "flavor-go-launcher" in results["passed"]
        assert "flavor-rs-builder" in results["passed"]
    
    @patch("flavor.ingredients.manager.run_command")
    def test_test_ingredients_failure(self, mock_run):
        """Test testing ingredients with failures."""
        # Create fake ingredient
        self.create_fake_ingredient("flavor-go-launcher")
        
        # Mock failed version call
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error"
        )
        
        results = self.manager.test_ingredients()
        
        assert len(results["passed"]) == 0
        assert len(results["failed"]) == 1
        assert results["failed"][0]["name"] == "flavor-go-launcher"
    
    @patch("flavor.ingredients.manager.run_command")
    def test_test_ingredients_timeout(self, mock_run):
        """Test testing ingredients with timeout."""
        # Create fake ingredient
        self.create_fake_ingredient("flavor-go-launcher")
        
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
        
        results = self.manager.test_ingredients()
        
        assert len(results["passed"]) == 0
        assert len(results["failed"]) == 1
        assert "timed out" in results["failed"][0]["error"].lower()
    
    def test_test_ingredients_not_executable(self):
        """Test testing ingredients that are not executable."""
        # Create non-executable file
        ingredient = self.ingredients_bin / "flavor-go-launcher"
        ingredient.write_text("not executable")
        ingredient.chmod(0o644)  # Not executable
        
        results = self.manager.test_ingredients()
        
        assert len(results["passed"]) == 0
        assert len(results["failed"]) == 1
        assert "not executable" in results["failed"][0]["error"]
    
    @patch("flavor.ingredients.manager.run_command")
    def test_test_ingredients_specific_language(self, mock_run):
        """Test testing ingredients for a specific language."""
        # Create fake ingredients
        self.create_fake_ingredient("flavor-go-launcher")
        self.create_fake_ingredient("flavor-rs-builder")
        
        mock_run.return_value = MagicMock(returncode=0)
        
        results = self.manager.test_ingredients(language="go")
        
        assert len(results["passed"]) == 1
        assert len(results["skipped"]) == 1
        assert "flavor-go-launcher" in results["passed"]
        assert "flavor-rs-builder" in results["skipped"]
    
    def test_get_ingredient_not_found(self):
        """Test that get_ingredient raises FileNotFoundError when ingredient not found."""
        with pytest.raises(FileNotFoundError, match="flavor-nonexistent"):
            self.manager.get_ingredient("flavor-nonexistent")


@pytest.mark.unit
@pytest.mark.requires_ingredients
class TestIngredientInfo:
    """Test the IngredientInfo dataclass."""
    
    def test_ingredient_info_creation(self):
        """Test creating a IngredientInfo object."""
        info = IngredientInfo(
            name="flavor-go-launcher",
            path=Path("/ingredients/bin/flavor-go-launcher"),
            type="launcher",
            language="go",
            size=4096,
            checksum="abc123",
            version="1.0.0",
            built_from=Path("/src/go/cmd/flavor-go-launcher"),
        )
        
        assert info.name == "flavor-go-launcher"
        assert info.type == "launcher"
        assert info.language == "go"
        assert info.size == 4096
        assert info.checksum == "abc123"
        assert info.version == "1.0.0"