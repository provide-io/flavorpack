#!/usr/bin/env python3
#
# flavor/helpers.py
#
"""Helper management system for Flavor launchers and builders."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import platform
import shutil
from typing import Any

from pyvider.telemetry import logger

from flavor.utils.subprocess import run_command


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

    def __init__(self) -> None:
        """Initialize the helper manager."""
        self.flavor_root = Path(__file__).parent.parent.parent
        self.helpers_dir = self.flavor_root / "helpers"
        self.helpers_bin = self.helpers_dir / "bin"

        # Also check XDG cache location for installed helpers
        xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        self.installed_helpers_bin = Path(xdg_cache) / "flavor" / "helpers" / "bin"

        # Source directories are in helpers/<language>
        self.go_src_dir = self.helpers_dir / "flavor-go"
        self.rust_src_dir = self.helpers_dir / "flavor-rs"

        # Ensure helpers directories exist
        self.helpers_dir.mkdir(exist_ok=True)
        self.helpers_bin.mkdir(exist_ok=True)

        # Detect current platform
        self.current_platform = self._get_current_platform()

    def _get_current_platform(self) -> str:
        """Get the current platform identifier (e.g., 'linux_amd64', 'darwin_arm64')."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normalize OS names
        os_map = {
            "linux": "linux",
            "darwin": "darwin",
            "windows": "windows",
        }

        # Normalize architecture names
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }

        os_name = os_map.get(system, system)
        arch_name = arch_map.get(machine, machine)

        return f"{os_name}_{arch_name}"

    def list_helpers(
        self, platform_filter: bool = False
    ) -> dict[str, list[HelperInfo]]:
        """List all available helpers.

        Args:
            platform_filter: If True, only return helpers compatible with current platform

        Returns:
            Dictionary with 'launchers' and 'builders' lists
        """
        helpers = {
            "launchers": [],
            "builders": [],
        }

        # Check both local development and installed locations
        search_dirs = []
        if self.helpers_bin.exists():
            search_dirs.append(self.helpers_bin)
        if self.installed_helpers_bin.exists():
            search_dirs.append(self.installed_helpers_bin)

        # Track seen helpers to avoid duplicates
        seen = set()

        for search_dir in search_dirs:
            # Find all launchers (match both with and without platform suffix)
            for launcher in search_dir.glob("flavor-*-launcher*"):
                if launcher.is_file() and launcher.name not in seen:
                    # Check platform compatibility if filtering is enabled
                    if platform_filter and not self._is_platform_compatible(
                        launcher.name
                    ):
                        continue

                    info = self._get_helper_info(launcher)
                    if info:
                        helpers["launchers"].append(info)
                        seen.add(launcher.name)

            # Find all builders (match both with and without platform suffix)
            for builder in search_dir.glob("flavor-*-builder*"):
                if builder.is_file() and builder.name not in seen:
                    # Check platform compatibility if filtering is enabled
                    if platform_filter and not self._is_platform_compatible(
                        builder.name
                    ):
                        continue

                    info = self._get_helper_info(builder)
                    if info:
                        helpers["builders"].append(info)
                        seen.add(builder.name)

        return helpers

    def _is_platform_compatible(self, filename: str) -> bool:
        """Check if a helper binary is compatible with the current platform.

        Args:
            filename: Name of the helper binary file

        Returns:
            True if compatible with current platform, False otherwise
        """
        # Binaries without platform suffix are assumed to be for the current platform
        # (e.g., locally built binaries)
        if not any(platform in filename for platform in ["linux", "darwin", "windows"]):
            return True

        # Check if the current platform is in the filename
        # Handle both underscore and hyphen separators
        current_parts = self.current_platform.split("_")
        os_name = current_parts[0]
        arch_name = current_parts[1] if len(current_parts) > 1 else ""

        # Check OS match
        if os_name not in filename.lower():
            return False

        # Check architecture match (if specified in filename)
        if arch_name and any(
            arch in filename.lower() for arch in ["amd64", "arm64", "x86_64", "aarch64"]
        ):
            # Map architecture names for comparison
            arch_variants = {
                "amd64": ["amd64", "x86_64"],
                "arm64": ["arm64", "aarch64"],
            }

            valid_archs = arch_variants.get(arch_name, [arch_name])
            if not any(arch in filename.lower() for arch in valid_archs):
                return False

        return True

    def _get_helper_info(self, path: Path) -> HelperInfo | None:
        """Get information about a helper binary."""
        if not path.exists():
            return None

        name = path.name
        parts = name.split("-")

        if len(parts) < 3:
            return None

        # Extract language and type from filename
        # Format: flavor-<lang>-<type> or flavor-<lang>-<type>-<platform>
        lang = parts[1]

        # Helper type might have platform suffix (e.g., launcher-darwin_arm64)
        helper_type_full = parts[2]
        # Remove platform suffix if present (e.g., "launcher-darwin_arm64" -> "launcher")
        helper_type = helper_type_full.split("_")[0]  # Split by underscore for platform
        if helper_type not in ["launcher", "builder"]:
            # Try without any suffix
            helper_type = helper_type_full

        # Get file info
        stat = path.stat()
        size = stat.st_size

        # Compute checksum
        checksum = None
        try:
            hasher = hashlib.sha256()
            with path.open("rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            checksum = hasher.hexdigest()[:16]  # First 16 chars
        except Exception:
            pass

        # Try to get version
        version = None
        try:
            result = run_command(
                [str(path), "--version"],
                capture_output=True,
                check=False,
                timeout=2,
                env={**os.environ, "FLAVOR_LAUNCHER_CLI": "true"},
                log_command=False,
            )
            if result.returncode == 0:
                # Parse version from output
                output = result.stdout.strip()
                if "version" in output.lower():
                    # Try to extract version number
                    import re

                    match = re.search(r"(\d+\.\d+\.\d+)", output)
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
            built_from = helpers_dir / "flavor-rs"

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

    def build_helpers(
        self, language: str | None = None, force: bool = False
    ) -> list[Path]:
        """Build helper binaries from source.

        Args:
            language: Build only helpers for this language (go/rust), or all if None
            force: Force rebuild even if binaries exist

        Returns:
            List of paths to built binaries
        """
        built = []

        languages = []
        languages = [language] if language else ["go", "rust"]

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
                run_command(
                    ["go", "build", "-o", str(launcher_out), "."],
                    cwd=launcher_src,
                    check=True,
                    capture_output=True,
                )
                launcher_out.chmod(0o755)
                built.append(launcher_out)
                logger.info(f"✅ Built Go launcher: {launcher_out}")
            except Exception as e:
                logger.error(f"Failed to build Go launcher: {e}")

        # Build builder
        builder_src = self.go_src_dir / "cmd" / "flavor-go-builder"
        builder_out = self.helpers_bin / "flavor-go-builder"

        if force or not builder_out.exists():
            logger.info("Building Go builder...")
            try:
                run_command(
                    ["go", "build", "-o", str(builder_out), "."],
                    cwd=builder_src,
                    check=True,
                    capture_output=True,
                )
                builder_out.chmod(0o755)
                built.append(builder_out)
                logger.info(f"✅ Built Go builder: {builder_out}")
            except Exception as e:
                logger.error(f"Failed to build Go builder: {e}")

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
                run_command(
                    ["cargo", "build", "--release"],
                    cwd=self.rust_src_dir,
                    check=True,
                    capture_output=True,
                )

                # Copy launcher binary to helpers/bin
                launcher_binary = (
                    self.rust_src_dir / "target" / "release" / "flavor-rs-launcher"
                )
                if launcher_binary.exists():
                    shutil.copy2(launcher_binary, launcher_out)
                    launcher_out.chmod(0o755)
                    built.append(launcher_out)
                    logger.info(f"✅ Built Rust launcher: {launcher_out}")
                else:
                    logger.error("Rust launcher binary not found after build")

                # Copy builder binary to helpers/bin
                builder_binary = (
                    self.rust_src_dir / "target" / "release" / "flavor-rs-builder"
                )
                if builder_binary.exists():
                    shutil.copy2(builder_binary, builder_out)
                    builder_out.chmod(0o755)
                    built.append(builder_out)
                    logger.info(f"✅ Built Rust builder: {builder_out}")
                else:
                    logger.error("Rust builder binary not found after build")

            except Exception as e:
                logger.error(f"Failed to build Rust helpers: {e}")

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
            patterns = ["flavor-rs-*", "flavor-rs-*"]
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
                    results["failed"].append(
                        {"name": helper.name, "error": "Binary not found"}
                    )
                    continue

                if not os.access(helper.path, os.X_OK):
                    results["failed"].append(
                        {"name": helper.name, "error": "Binary not executable"}
                    )
                    continue

                # Try to run with --version
                try:
                    env = {**os.environ}
                    if helper.type == "launcher":
                        env["FLAVOR_LAUNCHER_CLI"] = "true"

                    result = run_command(
                        [str(helper.path), "--version"],
                        capture_output=True,
                        check=False,
                        timeout=5,
                        env=env,
                        log_command=False,
                    )

                    if result.returncode == 0:
                        results["passed"].append(helper.name)
                    else:
                        results["failed"].append(
                            {
                                "name": helper.name,
                                "error": f"Exit code {result.returncode}",
                                "stderr": result.stderr[:200]
                                if result.stderr
                                else None,
                            }
                        )
                except Exception as e:
                    results["failed"].append({"name": helper.name, "error": str(e)})

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

    def get_helper(self, name: str) -> Path:
        """Get path to a helper binary.

        Args:
            name: Helper name (e.g., "flavor-rs-launcher")

        Returns:
            Path to the helper binary

        Raises:
            FileNotFoundError: If helper not found
        """
        # 1. Check bundled with package (for PyPI wheels)
        bundled_path = Path(__file__).parent / "helpers" / self.current_platform / name
        if bundled_path.exists():
            return bundled_path

        # 2. Check local development helpers
        local_path = self.helpers_bin / name
        if local_path.exists():
            return local_path

        # 3. Check installed helpers cache (legacy)
        installed_path = self.installed_helpers_bin / self.current_platform / name
        if installed_path.exists():
            return installed_path

        # Not found
        raise FileNotFoundError(
            f"Helper '{name}' not found for platform {self.current_platform}.\n"
            f"Searched: {bundled_path}, {local_path}, {installed_path}"
        )


# 🔧🏗️🤖
