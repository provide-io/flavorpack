"""Comprehensive unit tests for PSPF packaging orchestrator."""

import json
import os
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call, MagicMock
import pytest

from flavor.packaging.orchestrator import PackagingOrchestrator
from flavor.exceptions import BuildError


class TestPackagingOrchestratorComprehensive:
    """Comprehensive tests for PackagingOrchestrator."""
    
    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create an orchestrator instance with test configuration."""
        # Create a dummy pyproject.toml for the orchestrator to read
        pyproject_content = """
[build-system]
requires = ["uv>=0.1.0"]
build-backend = "setuptools.build_meta"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        return PackagingOrchestrator(
            package_integrity_key_path=str(tmp_path / "test.key"),
            public_key_path=str(tmp_path / "test.pub"),
            output_flavor_path=str(tmp_path / "output.pspf"),
            build_config={
                "version": "1.0.0",
                "dependencies": ["../dep1", "../dep2"],
            },
            manifest_dir=tmp_path,
            provider_name="test-provider",
            entry_point="test.main:run",
            python_version="3.13",
        )
    
    def test_orchestrator_initialization(self, orchestrator, tmp_path):
        """Test orchestrator initializes with correct values."""
        assert orchestrator.package_integrity_key_path == str(tmp_path / "test.key")
        assert orchestrator.public_key_path == str(tmp_path / "test.pub")
        assert orchestrator.output_flavor_path == str(tmp_path / "output.pspf")
        assert orchestrator.provider_name == "test-provider"
        assert orchestrator.entry_point == "test.main:run"
        assert orchestrator.python_version == "3.13"
        assert orchestrator.build_config["version"] == "1.0.0"
        assert len(orchestrator.build_config["dependencies"]) == 2
    
    @patch("flavor.packaging.orchestrator.subprocess.run")
    @patch("flavor.packaging.orchestrator.ensure_go_binary")
    @patch("flavor.packaging.orchestrator.tempfile.TemporaryDirectory")
    def test_build_package_creates_correct_structure(self, mock_tempdir, mock_ensure_go, mock_run, orchestrator):
        """Test build_package creates the correct directory structure."""
        # Setup mocks
        temp_dir = tempfile.mkdtemp()
        mock_tempdir.return_value.__enter__ = Mock(return_value=temp_dir)
        mock_tempdir.return_value.__exit__ = Mock(return_value=None)
        mock_ensure_go.return_value = Path("/fake/flavor-packager")
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        try:
            orchestrator.build_package()
            
            # Verify directory structure was created
            payload_dir = Path(temp_dir) / "payload"
            assert payload_dir.exists()
            
            metadata_dir = payload_dir / "metadata"
            assert metadata_dir.exists()
            
            # Verify metadata files were created
            manifest_file = metadata_dir / "provider_manifest.json"
            assert manifest_file.exists()
            manifest_data = json.loads(manifest_file.read_text())
            assert manifest_data["name"] == "test-provider"
            assert manifest_data["version"] == "1.0.0"
            assert manifest_data["entry_point"] == "test.main:run"
            assert manifest_data["python_version"] == "3.13"
            
            config_file = metadata_dir / "config.json"
            assert config_file.exists()
            config_data = json.loads(config_file.read_text())
            assert config_data["entry_point"] == "test.main:run"
            assert config_data["provider_name"] == "test-provider"
            
            # Verify payload.tgz was created
            payload_tgz = Path(temp_dir) / "payload.tgz"
            assert payload_tgz.exists()
            
            # Verify tarball contains correct structure
            with tarfile.open(payload_tgz, "r:gz") as tar:
                names = tar.getnames()
                assert "cache" in names
                assert any("cache/metadata" in name for name in names)
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @patch("flavor.packaging.orchestrator.subprocess.run")
    def test_python_environment_creation(self, mock_run, orchestrator):
        """Test Python virtual environment is created correctly."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("flavor.packaging.orchestrator.tempfile.TemporaryDirectory") as mock_tempdir:
                mock_tempdir.return_value.__enter__ = Mock(return_value=temp_dir)
                mock_tempdir.return_value.__exit__ = Mock(return_value=None)
                
                with patch("flavor.packaging.orchestrator.ensure_go_binary") as mock_ensure_go:
                    mock_ensure_go.return_value = Path("/fake/flavor-packager")
                    
                    orchestrator.build_package()
                    
                    # Verify uv venv was called
                    # Check that the command was called with correct arguments
                    calls = mock_run.call_args_list
                    venv_called = False
                    for call_args in calls:
                        args = call_args[0][0]  # Get the command list
                        if len(args) >= 4 and args[0] == "uv" and args[1] == "venv":
                            if str(Path(temp_dir) / "payload") in args[2]:
                                if "--python" in args and "python3.13" in args:
                                    venv_called = True
                                    break
                    assert venv_called, "uv venv should have been called with correct arguments"
    
    @patch("flavor.packaging.orchestrator.subprocess.run")
    def test_dependencies_installation(self, mock_run, orchestrator, tmp_path):
        """Test dependencies are installed in correct order."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        # Create mock dependency directories
        dep1_path = tmp_path.parent / "dep1"
        dep2_path = tmp_path.parent / "dep2"
        dep1_path.mkdir()
        dep2_path.mkdir()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("flavor.packaging.orchestrator.tempfile.TemporaryDirectory") as mock_tempdir:
                mock_tempdir.return_value.__enter__ = Mock(return_value=temp_dir)
                mock_tempdir.return_value.__exit__ = Mock(return_value=None)
                
                with patch("flavor.packaging.orchestrator.ensure_go_binary") as mock_ensure_go:
                    mock_ensure_go.return_value = Path("/fake/flavor-packager")
                    
                    orchestrator.build_package()
                    
                    # Verify dependencies were installed
                    calls = mock_run.call_args_list
                    
                    # Check dep1 installation
                    dep1_install = False
                    for call in calls:
                        args = call[0][0] if call[0] else []
                        if isinstance(args, list) and len(args) >= 4:
                            if args[0] == "uv" and args[1] == "pip" and args[2] == "install":
                                # Check if dep1 path is in any of the arguments
                                if any("dep1" in str(arg) for arg in args):
                                    dep1_install = True
                                    break
                    assert dep1_install, "dep1 should be installed"
                    
                    # Check dep2 installation
                    dep2_install = False
                    for call in calls:
                        args = call[0][0] if call[0] else []
                        if isinstance(args, list) and len(args) >= 4:
                            if args[0] == "uv" and args[1] == "pip" and args[2] == "install":
                                # Check if dep2 path is in any of the arguments
                                if any("dep2" in str(arg) for arg in args):
                                    dep2_install = True
                                    break
                    assert dep2_install, "dep2 should be installed"
                    
                    # Check main package installation
                    main_install = False
                    for call in calls:
                        args = call[0][0] if call[0] else []
                        if isinstance(args, list) and len(args) >= 4:
                            if args[0] == "uv" and args[1] == "pip" and args[2] == "install":
                                # Check if the temp path (without /private prefix) is in any argument
                                if any(str(tmp_path).split("/private")[-1] in str(arg) for arg in args):
                                    main_install = True
                                    break
                    assert main_install, "main package should be installed"
    
    @patch("flavor.packaging.orchestrator.subprocess.run")
    def test_uv_binary_copy(self, mock_run, orchestrator):
        """Test UV binary is copied if available."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("flavor.packaging.orchestrator.tempfile.TemporaryDirectory") as mock_tempdir:
                mock_tempdir.return_value.__enter__ = Mock(return_value=temp_dir)
                mock_tempdir.return_value.__exit__ = Mock(return_value=None)
                
                with patch("flavor.packaging.orchestrator.ensure_go_binary") as mock_ensure_go:
                    mock_ensure_go.return_value = Path("/fake/flavor-packager")
                    
                    with patch("pathlib.Path.exists") as mock_exists:
                        mock_exists.return_value = True
                        
                        with patch("shutil.copy2") as mock_copy:
                            orchestrator.build_package()
                            
                            # Verify UV was copied
                            mock_copy.assert_called_once_with(
                                "/opt/homebrew/bin/uv",
                                Path(temp_dir) / "uv"
                            )
    
    @patch("flavor.packaging.orchestrator.subprocess.run")
    def test_packager_command_construction(self, mock_run, orchestrator, tmp_path):
        """Test the flavor-packager command is constructed correctly."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("flavor.packaging.orchestrator.tempfile.TemporaryDirectory") as mock_tempdir:
                mock_tempdir.return_value.__enter__ = Mock(return_value=temp_dir)
                mock_tempdir.return_value.__exit__ = Mock(return_value=None)
                
                with patch("flavor.packaging.orchestrator.ensure_go_binary") as mock_ensure_go:
                    packager_path = Path("/fake/flavor-packager")
                    launcher_path = Path("/fake/pspf-launcher")
                    mock_ensure_go.side_effect = [packager_path, launcher_path]
                    
                    orchestrator.build_package()
                    
                    # Find the packager command call
                    packager_call = None
                    for call in mock_run.call_args_list:
                        if str(packager_path) in str(call):
                            packager_call = call
                            break
                    
                    assert packager_call is not None
                    args = packager_call[0][0]
                    
                    # Verify command structure
                    assert str(packager_path) == args[0]
                    assert "build" == args[1]
                    assert "--package-key" in args
                    assert str(tmp_path / "test.key") in args
                    assert "--public-key" in args
                    assert str(tmp_path / "test.pub") in args
                    assert "--out" in args
                    assert str(tmp_path / "output.pspf") in args
                    assert "--payload-dir" in args
                    assert str(Path(temp_dir) / "payload") in args
                    assert "--launcher-bin" in args
                    assert str(launcher_path) in args
    
    @patch("flavor.packaging.orchestrator.subprocess.run")
    def test_build_error_handling(self, mock_run, orchestrator):
        """Test error handling when subprocess fails."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Build failed!")
        
        with pytest.raises(BuildError) as exc_info:
            orchestrator.build_package()
        
        assert "Build failed!" in str(exc_info.value)
    
    @patch("flavor.packaging.orchestrator.subprocess.run")
    def test_tarball_creation_and_content(self, mock_run, orchestrator):
        """Test payload.tgz is created with correct content."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("flavor.packaging.orchestrator.tempfile.TemporaryDirectory") as mock_tempdir:
                mock_tempdir.return_value.__enter__ = Mock(return_value=temp_dir)
                mock_tempdir.return_value.__exit__ = Mock(return_value=None)
                
                with patch("flavor.packaging.orchestrator.ensure_go_binary") as mock_ensure_go:
                    mock_ensure_go.return_value = Path("/fake/flavor-packager")
                    
                    orchestrator.build_package()
                    
                    # Verify payload.tgz exists and has correct structure
                    payload_tgz = Path(temp_dir) / "payload.tgz"
                    assert payload_tgz.exists()
                    
                    # Extract and verify contents
                    with tarfile.open(payload_tgz, "r:gz") as tar:
                        # Check that cache is the root directory
                        members = tar.getmembers()
                        root_dirs = {m.name.split('/')[0] for m in members if m.name}
                        assert "cache" in root_dirs
                        
                        # Extract to verify content
                        extract_dir = Path(temp_dir) / "extracted"
                        tar.extractall(extract_dir)
                        
                        # Verify metadata exists
                        extracted_metadata = extract_dir / "cache" / "metadata"
                        assert extracted_metadata.exists()
                        assert (extracted_metadata / "provider_manifest.json").exists()
                        assert (extracted_metadata / "config.json").exists()


# 📦🍜🧪🪄
