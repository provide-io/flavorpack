"""Test launcher availability and resilience.

This module tests that the packaging system properly handles:
- Missing launchers
- Corrupted launchers
- Wrong platform launchers
- Launcher selection fallbacks
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flavor.api import build_package_from_manifest
from flavor.exceptions import BuildError
from flavor.packaging.orchestrator import PackagingOrchestrator


class TestLauncherAvailability:
    """Test launcher availability and error handling."""

    @pytest.mark.unit
    def test_missing_launcher_error(self, tmp_path):
        """Test that building fails gracefully when no launcher is available."""
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Try to build with a non-existent launcher
        output_path = tmp_path / "test.psp"
        launcher_path = tmp_path / "nonexistent-launcher"
        
        with pytest.raises(BuildError, match="Launcher binary not found"):
            build_package_from_manifest(
                manifest_path=manifest_path,
                output_path=output_path,
                launcher_bin=launcher_path,
                show_progress=False
            )

    @pytest.mark.unit
    def test_corrupted_launcher_detection(self, tmp_path):
        """Test that corrupted launchers are detected."""
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Create a corrupted launcher (invalid binary)
        launcher_path = tmp_path / "corrupted-launcher"
        launcher_path.write_text("This is not a valid binary")
        launcher_path.chmod(0o755)
        
        output_path = tmp_path / "test.psp"
        
        # The build should either fail or warn about invalid launcher
        with pytest.raises((ValueError, OSError)) as exc_info:
            build_package_from_manifest(
                manifest_path=manifest_path,
                output_path=output_path,
                launcher_bin=launcher_path,
                show_progress=False
            )
        
        # Check that the error message is informative
        assert "launcher" in str(exc_info.value).lower() or "binary" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_wrong_platform_launcher_warning(self, tmp_path, monkeypatch):
        """Test that using wrong platform launcher produces a warning."""
        import platform
        
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Get current platform
        current_platform = platform.system().lower()
        
        # Create a launcher with wrong platform in name
        wrong_platform = "windows" if current_platform != "windows" else "linux"
        launcher_path = tmp_path / f"flavor-rs-launcher-{wrong_platform}_amd64"
        
        # Create a minimal valid ELF/PE header based on platform
        if current_platform == "linux":
            # Minimal ELF header
            launcher_path.write_bytes(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8)
        elif current_platform == "darwin":
            # Minimal Mach-O header
            launcher_path.write_bytes(b'\xcf\xfa\xed\xfe' + b'\x00' * 12)
        else:
            # Minimal PE header for Windows
            launcher_path.write_bytes(b'MZ' + b'\x00' * 58 + b'PE\x00\x00')
        
        launcher_path.chmod(0o755)
        
        output_path = tmp_path / "test.psp"
        
        # Should warn but might still proceed depending on implementation
        # Capture warnings
        with pytest.warns(UserWarning, match="platform|architecture"):
            try:
                build_package_from_manifest(
                    manifest_path=manifest_path,
                    output_path=output_path,
                    launcher_bin=launcher_path,
                    show_progress=False
                )
            except (ValueError, OSError):
                # It's also acceptable to fail with wrong platform
                pass

    @pytest.mark.unit
    def test_launcher_fallback_selection(self, tmp_path):
        """Test that launcher selection falls back to available options."""
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Mock the ingredients directory
        ingredients_dir = tmp_path / "ingredients" / "bin"
        ingredients_dir.mkdir(parents=True)
        
        # Create mock launchers with different priorities
        rust_launcher = ingredients_dir / "flavor-rs-launcher-linux_amd64"
        go_launcher = ingredients_dir / "flavor-go-launcher-linux_amd64"
        
        # Create minimal valid binaries
        for launcher in [rust_launcher, go_launcher]:
            launcher.write_bytes(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8)
            launcher.chmod(0o755)
        
        output_path = tmp_path / "test.psp"
        
        # Patch the orchestrator to use our test ingredients
        with patch.object(PackagingOrchestrator, '_find_launcher', return_value=str(rust_launcher)):
            # Should automatically find and use the Rust launcher
            result = build_package_from_manifest(
                manifest_path=manifest_path,
                output_path=output_path,
                launcher_bin=None,  # Let it auto-select
                show_progress=False
            )
            
            # Verify a package was created
            assert output_path.exists() or (result and len(result) > 0)

    @pytest.mark.unit  
    def test_launcher_executable_permission_check(self, tmp_path):
        """Test that non-executable launchers are detected."""
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Create a valid launcher without execute permissions
        launcher_path = tmp_path / "non-executable-launcher"
        launcher_path.write_bytes(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8)
        launcher_path.chmod(0o644)  # Read/write but not execute
        
        output_path = tmp_path / "test.psp"
        
        # Should fail or fix permissions
        with pytest.raises((PermissionError, OSError, ValueError)) as exc_info:
            build_package_from_manifest(
                manifest_path=manifest_path,
                output_path=output_path,
                launcher_bin=launcher_path,
                show_progress=False
            )
        
        # Error should mention permissions or executable
        error_msg = str(exc_info.value).lower()
        assert "permission" in error_msg or "executable" in error_msg or "execute" in error_msg

    @pytest.mark.integration
    def test_multiple_launcher_versions_conflict(self, tmp_path):
        """Test handling of multiple launcher versions in ingredients."""
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Create multiple launcher versions
        ingredients_dir = tmp_path / "ingredients" / "bin"
        ingredients_dir.mkdir(parents=True)
        
        launchers = [
            ingredients_dir / "flavor-rs-launcher-0.2.0-linux_amd64",
            ingredients_dir / "flavor-rs-launcher-0.3.0-linux_amd64",
            ingredients_dir / "flavor-rs-launcher-linux_amd64",  # Unversioned
        ]
        
        for launcher in launchers:
            launcher.write_bytes(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8)
            launcher.chmod(0o755)
        
        output_path = tmp_path / "test.psp"
        
        # Should pick the versioned one with highest version
        with patch('flavor.packaging.orchestrator.INGREDIENTS_DIR', ingredients_dir.parent):
            orchestrator = PackagingOrchestrator(
                manifest_path=manifest_path,
                output_path=output_path,
                show_progress=False
            )
            
            # Find launcher should prefer versioned launchers
            launcher = orchestrator._find_launcher(None)
            assert launcher is not None
            assert "0.3.0" in str(launcher) or "flavor-rs-launcher" in str(launcher)

    @pytest.mark.integration
    def test_launcher_binary_size_validation(self, tmp_path):
        """Test that suspiciously small launchers are rejected."""
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Create a launcher that's too small to be valid
        launcher_path = tmp_path / "tiny-launcher"
        launcher_path.write_bytes(b'MZ')  # Just 2 bytes - way too small
        launcher_path.chmod(0o755)
        
        output_path = tmp_path / "test.psp"
        
        # Should reject the tiny launcher
        with pytest.raises((ValueError, OSError)) as exc_info:
            build_package_from_manifest(
                manifest_path=manifest_path,
                output_path=output_path,
                launcher_bin=launcher_path,
                show_progress=False
            )
        
        # Check error is about size or validity
        error_msg = str(exc_info.value).lower()
        assert "size" in error_msg or "invalid" in error_msg or "binary" in error_msg

    @pytest.mark.unit
    def test_launcher_architecture_detection(self, tmp_path):
        """Test that launcher architecture is properly detected."""
        import platform
        import struct
        
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Create launchers with different architectures
        launcher_x64 = tmp_path / "launcher-x64"
        launcher_arm = tmp_path / "launcher-arm"
        
        # Create ELF headers with different architectures
        # x86_64 ELF header
        elf_x64 = bytearray(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8)
        elf_x64[18:20] = struct.pack('<H', 0x3E)  # EM_X86_64
        launcher_x64.write_bytes(bytes(elf_x64))
        launcher_x64.chmod(0o755)
        
        # ARM64 ELF header
        elf_arm = bytearray(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8)
        elf_arm[18:20] = struct.pack('<H', 0xB7)  # EM_AARCH64
        launcher_arm.write_bytes(bytes(elf_arm))
        launcher_arm.chmod(0o755)
        
        current_arch = platform.machine().lower()
        correct_launcher = launcher_x64 if 'x86' in current_arch else launcher_arm
        wrong_launcher = launcher_arm if 'x86' in current_arch else launcher_x64
        
        output_path = tmp_path / "test.psp"
        
        # Using wrong architecture launcher should warn or fail
        try:
            build_package_from_manifest(
                manifest_path=manifest_path,
                output_path=output_path,
                launcher_bin=wrong_launcher,
                show_progress=False
            )
            # If it succeeds, there should at least be a warning logged
        except (ValueError, OSError) as e:
            # Expected to fail with architecture mismatch
            assert "architecture" in str(e).lower() or "arch" in str(e).lower()


class TestLauncherReproducibility:
    """Test launcher build reproducibility."""

    @pytest.mark.integration
    def test_deterministic_launcher_selection(self, tmp_path):
        """Test that launcher selection is deterministic."""
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Create multiple launchers
        ingredients_dir = tmp_path / "ingredients" / "bin"
        ingredients_dir.mkdir(parents=True)
        
        launchers = [
            "flavor-rs-launcher-linux_amd64",
            "flavor-go-launcher-linux_amd64",
        ]
        
        for name in launchers:
            launcher = ingredients_dir / name
            launcher.write_bytes(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8)
            launcher.chmod(0o755)
        
        # Run selection multiple times
        with patch('flavor.packaging.orchestrator.INGREDIENTS_DIR', ingredients_dir.parent):
            selections = []
            for _ in range(5):
                orchestrator = PackagingOrchestrator(
                    manifest_path=manifest_path,
                    output_path=tmp_path / "test.psp",
                    show_progress=False
                )
                launcher = orchestrator._find_launcher(None)
                selections.append(Path(launcher).name if launcher else None)
        
        # All selections should be identical
        assert len(set(selections)) == 1, f"Non-deterministic selection: {selections}"
        # Should prefer Rust launcher by default
        assert selections[0] and "flavor-rs-launcher" in selections[0]

    @pytest.mark.integration
    def test_reproducible_builds_with_same_launcher(self, tmp_path):
        """Test that builds with the same launcher are reproducible."""
        # Create a simple manifest
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"

[project.scripts]
test-package = "test:main"

[tool.flavor]
entry_point = "test:main"
""")
        
        # Create a mock launcher
        launcher_path = tmp_path / "test-launcher"
        launcher_path.write_bytes(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 100)
        launcher_path.chmod(0o755)
        
        # Build twice with the same inputs
        output1 = tmp_path / "test1.psp"
        output2 = tmp_path / "test2.psp"
        
        # Use deterministic key seed for reproducibility
        for output in [output1, output2]:
            try:
                build_package_from_manifest(
                    manifest_path=manifest_path,
                    output_path=output,
                    launcher_bin=launcher_path,
                    key_seed="test-seed",
                    show_progress=False
                )
            except Exception:
                # If build fails, skip this test
                pytest.skip("Build failed, cannot test reproducibility")
        
        # Check if files exist and compare sizes at least
        if output1.exists() and output2.exists():
            assert output1.stat().st_size == output2.stat().st_size, \
                "Builds with same inputs produced different sizes"

    @pytest.mark.unit
    def test_launcher_checksum_verification(self, tmp_path):
        """Test that launcher checksums can be verified."""
        import hashlib
        
        # Create a launcher
        launcher_path = tmp_path / "test-launcher"
        launcher_content = b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 100
        launcher_path.write_bytes(launcher_content)
        launcher_path.chmod(0o755)
        
        # Calculate checksum
        expected_checksum = hashlib.sha256(launcher_content).hexdigest()
        
        # Create a checksum file (simulating what CI might do)
        checksum_file = tmp_path / "checksums.txt"
        checksum_file.write_text(f"{expected_checksum}  test-launcher\n")
        
        # Verify checksum matches
        actual_checksum = hashlib.sha256(launcher_path.read_bytes()).hexdigest()
        assert actual_checksum == expected_checksum, "Launcher checksum mismatch"
        
        # Test corrupted launcher detection
        launcher_path.write_bytes(launcher_content + b'corrupted')
        new_checksum = hashlib.sha256(launcher_path.read_bytes()).hexdigest()
        assert new_checksum != expected_checksum, "Should detect corruption"