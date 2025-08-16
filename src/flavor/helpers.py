#!/usr/bin/env python3
#
# flavor/helpers.py
#
"""Helper management system for Flavor launchers and builders."""

import hashlib
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyvider.telemetry import logger


@dataclass
class HelperInfo:
    """Information about a helper binary."""
    name: str
    path: Path
    type: str  # "launcher" or "builder"
    language: str  # "go" or "rust"
    size: int
    checksum: str | None = None
    version: str | None = None
    built_from: Path | None = None  # Source directory


class HelperManager:
    """Manages Flavor helper binaries (launchers and builders)."""
    
    def __init__(self):
        """Initialize the helper manager."""
        self.flavor_root = Path(__file__).parent.parent.parent
        self.helpers_dir = self.flavor_root / "helpers"
        self.helpers_bin = self.helpers_dir / "bin"
        # Source directories are in helpers/<language>
        self.go_src_dir = self.helpers_dir / "flavor-go"
        self.rust_src_dir = self.helpers_dir / "flavor-rust"
        
        # Ensure helpers directories exist
        self.helpers_dir.mkdir(exist_ok=True)
        self.helpers_bin.mkdir(exist_ok=True)
    
    def list_helpers(self) -> dict[str, list[HelperInfo]]:
        """List all available helpers."""
        helpers = {
            "launchers": [],
            "builders": [],
        }
        
        if not self.helpers_bin.exists():
            return helpers
        
        # Find all launchers
        for launcher in self.helpers_bin.glob("flavor-*-launcher"):
            if launcher.is_file():
                info = self._get_helper_info(launcher)
                if info:
                    helpers["launchers"].append(info)
        
        # Find all builders
        for builder in self.helpers_bin.glob("flavor-*-builder"):
            if builder.is_file():
                info = self._get_helper_info(builder)
                if info:
                    helpers["builders"].append(info)
        
        return helpers
    
    def _get_helper_info(self, path: Path) -> HelperInfo | None:
        """Get information about a helper binary."""
        if not path.exists():
            return None
        
        name = path.name
        parts = name.split("-")
        
        if len(parts) < 3:
            return None
        
        # Extract language and type from filename
        # Format: flavor-<lang>-<type>
        lang = parts[1]
        helper_type = parts[2]
        
        # Get file info
        stat = path.stat()
        size = stat.st_size
        
        # Compute checksum
        checksum = None
        try:
            hasher = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            checksum = hasher.hexdigest()[:16]  # First 16 chars
        except Exception:
            pass
        
        # Try to get version
        version = None
        try:
            result = subprocess.run(
                [str(path), "--version"],
                capture_output=True,
                text=True,
                timeout=2,
                env={**os.environ, "FLAVOR_LAUNCHER_CLI": "true"}
            )
            if result.returncode == 0:
                # Parse version from output
                output = result.stdout.strip()
                if "version" in output.lower():
                    # Try to extract version number
                    import re
                    match = re.search(r'(\d+\.\d+\.\d+)', output)
                    if match:
                        version = match.group(1)
        except Exception:
            pass
        
        # Determine source directory
        built_from = None
        helpers_dir = Path(__file__).parent.parent.parent / "helpers"
        if lang == "go":
            if helper_type == "launcher":
                built_from = helpers_dir / "flavor-go" / "cmd" / "flavor-go-launcher"
            elif helper_type == "builder":
                built_from = helpers_dir / "flavor-go" / "cmd" / "flavor-go-builder"
        elif lang in ["rs", "rust"]:
            # Rust uses a workspace structure
            built_from = helpers_dir / "flavor-rust"
        
        return HelperInfo(
            name=name,
            path=path,
            type=helper_type,
            language="rust" if lang == "rs" else lang,
            size=size,
            checksum=checksum,
            version=version,
            built_from=built_from,
        )
    
    def build_helpers(self, language: str | None = None, force: bool = False) -> list[Path]:
        """Build helper binaries from source.
        
        Args:
            language: Build only helpers for this language (go/rust), or all if None
            force: Force rebuild even if binaries exist
            
        Returns:
            List of paths to built binaries
        """
        built = []
        
        languages = []
        if language:
            languages = [language]
        else:
            languages = ["go", "rust"]
        
        for lang in languages:
            if lang == "go":
                built.extend(self._build_go_helpers(force))
            elif lang == "rust":
                built.extend(self._build_rust_helpers(force))
            else:
                logger.warning(f"Unknown language: {lang}")
        
        return built
    
    def _build_go_helpers(self, force: bool = False) -> list[Path]:
        """Build Go helpers."""
        built = []
        
        # Check if Go is available
        if not shutil.which("go"):
            logger.warning("Go compiler not found, skipping Go helpers")
            return built
        
        # Build launcher
        launcher_src = self.go_src_dir / "cmd" / "flavor-go-launcher"
        launcher_out = self.helpers_bin / "flavor-go-launcher"
        
        if force or not launcher_out.exists():
            logger.info("Building Go launcher...")
            try:
                subprocess.run(
                    ["go", "build", "-o", str(launcher_out), "."],
                    cwd=launcher_src,
                    check=True,
                    capture_output=True,
                )
                launcher_out.chmod(0o755)
                built.append(launcher_out)
                logger.info(f"✅ Built Go launcher: {launcher_out}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to build Go launcher: {e}")
                if e.stderr:
                    logger.error(e.stderr.decode())
        
        # Build builder
        builder_src = self.go_src_dir / "cmd" / "flavor-go-builder"
        builder_out = self.helpers_bin / "flavor-go-builder"
        
        if force or not builder_out.exists():
            logger.info("Building Go builder...")
            try:
                subprocess.run(
                    ["go", "build", "-o", str(builder_out), "."],
                    cwd=builder_src,
                    check=True,
                    capture_output=True,
                )
                builder_out.chmod(0o755)
                built.append(builder_out)
                logger.info(f"✅ Built Go builder: {builder_out}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to build Go builder: {e}")
                if e.stderr:
                    logger.error(e.stderr.decode())
        
        return built
    
    def _build_rust_helpers(self, force: bool = False) -> list[Path]:
        """Build Rust helpers."""
        built = []
        
        # Check if Rust is available
        if not shutil.which("cargo"):
            logger.warning("Cargo not found, skipping Rust helpers")
            return built
        
        # The Rust helpers are in a workspace, build both at once
        launcher_out = self.helpers_bin / "flavor-rs-launcher"
        builder_out = self.helpers_bin / "flavor-rs-builder"
        
        if force or not launcher_out.exists() or not builder_out.exists():
            logger.info("Building Rust helpers...")
            try:
                # Build in release mode (builds all workspace members)
                subprocess.run(
                    ["cargo", "build", "--release"],
                    cwd=self.rust_src_dir,
                    check=True,
                    capture_output=True,
                )
                
                # Copy launcher binary to helpers/bin
                launcher_binary = self.rust_src_dir / "target" / "release" / "flavor-rs-launcher"
                if launcher_binary.exists():
                    shutil.copy2(launcher_binary, launcher_out)
                    launcher_out.chmod(0o755)
                    built.append(launcher_out)
                    logger.info(f"✅ Built Rust launcher: {launcher_out}")
                else:
                    logger.error("Rust launcher binary not found after build")
                
                # Copy builder binary to helpers/bin
                builder_binary = self.rust_src_dir / "target" / "release" / "flavor-rs-builder"
                if builder_binary.exists():
                    shutil.copy2(builder_binary, builder_out)
                    builder_out.chmod(0o755)
                    built.append(builder_out)
                    logger.info(f"✅ Built Rust builder: {builder_out}")
                else:
                    logger.error("Rust builder binary not found after build")
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to build Rust helpers: {e}")
                if e.stderr:
                    logger.error(e.stderr.decode())
        
        return built
    
    def clean_helpers(self, language: str | None = None) -> list[Path]:
        """Remove built helper binaries.
        
        Args:
            language: Clean only helpers for this language, or all if None
            
        Returns:
            List of removed files
        """
        removed = []
        
        if not self.helpers_bin.exists():
            return removed
        
        patterns = []
        if language == "go":
            patterns = ["flavor-go-*"]
        elif language == "rust":
            patterns = ["flavor-rs-*", "flavor-rust-*"]
        else:
            patterns = ["flavor-*"]
        
        for pattern in patterns:
            for helper in self.helpers_bin.glob(pattern):
                if helper.is_file():
                    try:
                        helper.unlink()
                        removed.append(helper)
                        logger.info(f"Removed: {helper.name}")
                    except Exception as e:
                        logger.error(f"Failed to remove {helper}: {e}")
        
        return removed
    
    def test_helpers(self, language: str | None = None) -> dict[str, Any]:
        """Test helper binaries.
        
        Args:
            language: Test only helpers for this language, or all if None
            
        Returns:
            Dictionary with test results
        """
        results = {
            "passed": [],
            "failed": [],
            "skipped": [],
        }
        
        helpers = self.list_helpers()
        
        for helper_list in [helpers["launchers"], helpers["builders"]]:
            for helper in helper_list:
                if language and helper.language != language:
                    results["skipped"].append(helper.name)
                    continue
                
                # Test if binary exists and is executable
                if not helper.path.exists():
                    results["failed"].append({
                        "name": helper.name,
                        "error": "Binary not found"
                    })
                    continue
                
                if not os.access(helper.path, os.X_OK):
                    results["failed"].append({
                        "name": helper.name,
                        "error": "Binary not executable"
                    })
                    continue
                
                # Try to run with --version
                try:
                    env = {**os.environ}
                    if helper.type == "launcher":
                        env["FLAVOR_LAUNCHER_CLI"] = "true"
                    
                    result = subprocess.run(
                        [str(helper.path), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        env=env,
                    )
                    
                    if result.returncode == 0:
                        results["passed"].append(helper.name)
                    else:
                        results["failed"].append({
                            "name": helper.name,
                            "error": f"Exit code {result.returncode}",
                            "stderr": result.stderr[:200] if result.stderr else None,
                        })
                except subprocess.TimeoutExpired:
                    results["failed"].append({
                        "name": helper.name,
                        "error": "Timeout running --version"
                    })
                except Exception as e:
                    results["failed"].append({
                        "name": helper.name,
                        "error": str(e)
                    })
        
        return results
    
    def get_helper_info(self, name: str) -> HelperInfo | None:
        """Get detailed information about a specific helper.
        
        Args:
            name: Helper name (e.g., "flavor-go-launcher")
            
        Returns:
            HelperInfo object or None if not found
        """
        helper_path = self.helpers_bin / name
        if helper_path.exists():
            return self._get_helper_info(helper_path)
        
        # Try to find by partial name
        helpers = self.list_helpers()
        for helper_list in [helpers["launchers"], helpers["builders"]]:
            for helper in helper_list:
                if name in helper.name:
                    return helper
        
        return None
    
    def install_prebuilt(self, version: str = "latest") -> list[Path]:
        """Install pre-built helpers from GitHub releases.
        
        Args:
            version: Version to install ("latest" or specific version like "v1.0.0")
            
        Returns:
            List of installed helper paths
        """
        # This would download pre-built binaries from GitHub releases
        # For now, this is a placeholder
        logger.warning("Pre-built binary installation not yet implemented")
        logger.info("Please build from source using: flavor helper build")
        return []


# 🔧🏗️🤖