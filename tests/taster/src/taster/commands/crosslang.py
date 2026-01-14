#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-language compatibility testing command for PSPF packages."""

from __future__ import annotations

from collections.abc import Sequence
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
from typing import Any

import click
from provide.foundation import logger
from provide.foundation.console import perr, pout
from provide.foundation.process import run as run_command

from flavor.helpers.manager import HelperInfo, HelperManager


class CrossLangTester:
    """Cross-language compatibility tester."""

    def __init__(self, verbose: bool = False, json_output: bool = False) -> None:
        self.verbose = verbose
        self.json_output = json_output
        self.results: dict[str, Any] = {
            "build_tests": [],
            "verify_tests": [],
            "launch_tests": [],
            "cli_tests": [],
            "reproducible_tests": [],
            "summary": {},
        }

        self.helper_manager = HelperManager()
        logger.debug(
            "Initializing CrossLangTester",
            cwd=str(Path.cwd()),
            initial_helpers_bin=str(self.helper_manager.helpers_bin),
            initial_helpers_dir=str(self.helper_manager.helpers_dir),
        )
        self._configure_helper_paths()
        self.taster_dir: Path = self._discover_taster_directory()

    def _configure_helper_paths(self) -> None:
        """Configure helper binary locations based on environment."""
        helpers_dir = os.environ.get("FLAVOR_HELPERS_DIR")
        if helpers_dir:
            helpers_path = Path(helpers_dir)
            logger.debug(
                "Found FLAVOR_HELPERS_DIR env var",
                path=helpers_dir,
                exists=helpers_path.exists(),
            )
            if helpers_path.exists():
                self.helper_manager.helpers_bin = helpers_path / "bin"
                self.helper_manager.helpers_dir = helpers_path
                logger.info(
                    "Using helpers from FLAVOR_HELPERS_DIR",
                    helpers_bin=str(self.helper_manager.helpers_bin),
                    helpers_dir=str(self.helper_manager.helpers_dir),
                )
        else:
            logger.debug("No FLAVOR_HELPERS_DIR env var, searching directory tree")
            current = Path.cwd()
            for parent in [current, *current.parents]:
                dist_bin = parent / "dist" / "bin"
                logger.trace("Checking for dist/bin", path=str(dist_bin))
                if dist_bin.exists():
                    self.helper_manager.helpers_bin = dist_bin
                    self.helper_manager.helpers_dir = parent / "dist"
                    logger.info(
                        "Found helpers in directory tree",
                        helpers_bin=str(dist_bin),
                        helpers_dir=str(parent / "dist"),
                    )
                    break
            else:
                logger.warning("No dist/bin directory found in directory tree")

        logger.debug(
            "Final helper paths",
            helpers_bin=str(self.helper_manager.helpers_bin),
            helpers_dir=str(self.helper_manager.helpers_dir),
            bin_exists=self.helper_manager.helpers_bin.exists(),
        )

        if self.helper_manager.helpers_bin.exists():
            files = list(self.helper_manager.helpers_bin.glob("*"))
            logger.debug(
                "Helpers bin contents",
                file_count=len(files),
                files=[f.name for f in files],
            )

    def _discover_taster_directory(self) -> Path:
        """Locate the taster workspace that contains pyproject metadata."""
        current = Path.cwd()

        if (current / "pyproject.toml").exists() and "taster" in str(current):
            return current

        for parent in [current, *list(current.parents)]:
            taster_path = parent / "tests/taster"
            if taster_path.exists() and (taster_path / "pyproject.toml").exists():
                return taster_path

        return current

    def log(self, message: str, level: str = "info") -> None:
        """Log a message."""
        if not self.json_output:
            if level == "error":
                perr(message, color="red")
            elif level == "success":
                pout(message, color="green")
            elif level == "warning":
                pout(message, color="yellow")
            else:
                pout(message)

    def build_with_launcher(self, launcher_info: HelperInfo, key_seed: str = "test123") -> Path | None:
        """Build package using Python builder with specified launcher."""
        # Extract language from launcher name (e.g., "flavor-go-launcher" -> "go")
        launcher_lang = launcher_info.language
        output = self.taster_dir / f"test-{launcher_lang}.psp"

        # Create a temporary test package
        temp_dir = Path(tempfile.mkdtemp(prefix="crosslang_test_"))

        # Create a simple Python module
        test_module = temp_dir / "crosslang_test.py"
        test_module.write_text("""#!/usr/bin/env python3
import sys

def main():
    print("Cross-language test successful!")
    sys.exit(0)

if __name__ == "__main__":
    main()
""")

        # Create the manifest
        manifest_path = temp_dir / "pyproject.toml"
        manifest_path.write_text("""[project]
name = "crosslang-test"
version = "1.0.0"
dependencies = []

[project.scripts]
crosslang-test = "crosslang_test:main"

[tool.flavor]
name = "crosslang-test"
version = "1.0.0"
entry_point = "crosslang_test:main"
""")

        # Build command using Python module
        cmd = [
            sys.executable,
            "-m",
            "flavor",
            "pack",  # Changed from 'package' to 'pack'
            "--manifest",
            str(manifest_path),
            "--output",
            str(output),
            "--key-seed",
            key_seed,
            "--launcher-bin",
            str(launcher_info.path),
        ]

        try:
            # Run the build command from the test directory
            result = run_command(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                check=False,
                log_command=self.verbose,
            )
            success = result.returncode == 0 and output.exists()

            # Capture detailed error information
            if not success:
                error = f"Exit code: {result.returncode}\n"
                if result.stderr:
                    error += f"Stderr: {result.stderr[:1000]}\n"
                if result.stdout:
                    error += f"Stdout: {result.stdout[:1000]}"
            else:
                error = None

            # Make the built package executable
            if success:
                output.chmod(0o755)
        except Exception as e:
            success = False
            error = str(e)

        self.results["build_tests"].append(
            {
                "launcher": launcher_info.name,
                "language": launcher_lang,
                "success": success,
                "output": str(output) if success else None,
                "error": error,
            }
        )

        return output if success else None

    def verify_with_python(self, package_path: Path) -> bool:
        """Verify package with Python."""
        try:
            # Import here to avoid dependency issues
            from flavor.psp.format_2025 import PSPFReader
            from flavor.verification import FlavorVerifier

            # First try the verifier
            try:
                verify_result = FlavorVerifier.verify_package(package_path)
                success = verify_result.get("signature_valid", False)

                self.results["verify_tests"].append(
                    {
                        "package": str(package_path.name),
                        "verifier": "python",
                        "success": success,
                        "details": verify_result,
                    }
                )

                # If verification failed, get more details
                if not success and self.verbose:
                    self.log(
                        f"    Verification details: {json.dumps(verify_result, indent=2)}",
                        "warning",
                    )

                return success

            except Exception as e:
                # Fallback to basic reader check
                with PSPFReader(package_path) as reader:
                    result = reader.verify_integrity()
                    success = result.get("valid", False)

                    self.results["verify_tests"].append(
                        {
                            "package": str(package_path.name),
                            "verifier": "python_reader",
                            "success": success,
                            "details": result,
                            "verifier_error": str(e),
                        }
                    )

                    return success

        except Exception as e:
            self.results["verify_tests"].append(
                {
                    "package": str(package_path.name),
                    "verifier": "python",
                    "success": False,
                    "error": str(e),
                }
            )

            # Log detailed error in verbose mode
            if self.verbose:
                self.log(f"    Error verifying {package_path.name}: {e}", "error")
                self.log(f"    Traceback: {traceback.format_exc()}", "error")

            return False

    def verify_with_launcher_cli(self, package_path: Path, launcher_name: str) -> bool:
        """Verify package using launcher CLI."""
        # Make package executable
        package_path.chmod(0o755)

        env = os.environ.copy()
        env["FLAVOR_LAUNCHER_CLI"] = "true"

        # Use info command to verify the package works
        cmd = [str(package_path), "info"]
        result = run_command(cmd, capture_output=True, check=False, env=env)
        success = result.returncode == 0

        self.results["verify_tests"].append(
            {
                "package": str(package_path.name),
                "verifier": f"{launcher_name}_cli",
                "success": success,
                "error": result.stderr if not success else None,
            }
        )

        return success

    def test_cli_command(self, package_path: Path, command: str) -> bool:
        """Test a CLI command."""
        cmd = [str(package_path), *command.split()]
        result = run_command(cmd, capture_output=True, check=False)

        # Some commands exit non-zero intentionally (like --help)
        success = result.returncode in [0, 1, 2]  # Allow common exit codes

        self.results["cli_tests"].append(
            {
                "package": str(package_path.name),
                "command": command,
                "success": success,
                "exit_code": result.returncode,
                "output": result.stdout[:100] if success else result.stderr[:100],
            }
        )

        return success

    def test_reproducible_build(self, launcher_info: HelperInfo) -> bool:
        """Test if builds are reproducible."""
        # Build twice with same seed
        pkg1 = self.build_with_launcher(launcher_info, key_seed="repro999")
        pkg2 = self.build_with_launcher(launcher_info, key_seed="repro999")

        if pkg1 and pkg2:
            # Compare files (excluding timestamps in launcher)
            try:
                # Read both files
                data1 = pkg1.read_bytes()
                data2 = pkg2.read_bytes()

                # Find where index starts (after launcher)
                from flavor.psp.format_2025 import PSPFReader

                with PSPFReader(pkg1) as r:
                    launcher_size = r.read_index().launcher_size

                # Compare everything after launcher
                identical = data1[launcher_size:] == data2[launcher_size:]

                self.results["reproducible_tests"].append(
                    {
                        "launcher": launcher_info.name,
                        "success": identical,
                        "note": "Compared data after launcher" if identical else "Packages differ",
                    }
                )

                # Clean up
                pkg1.unlink()
                pkg2.unlink()

                return identical
            except Exception as e:
                self.results["reproducible_tests"].append(
                    {"launcher": launcher_info.name, "success": False, "error": str(e)}
                )
                return False
        else:
            self.results["reproducible_tests"].append(
                {
                    "launcher": launcher_info.name,
                    "success": False,
                    "error": "Failed to build test packages",
                }
            )
            return False

    def _resolve_launchers(self) -> list[HelperInfo]:
        """Resolve launchers compatible with the current platform."""
        helpers = self.helper_manager.list_helpers(platform_filter=True)
        available_launchers: list[HelperInfo] = helpers.get("launchers", [])

        current_platform = self.helper_manager.current_platform
        self.log(f"\n🖥️  Current platform: {current_platform}")

        if not available_launchers:
            self.log("❌ No platform-compatible launchers found!", "error")
            self.log(f"   Looking for launchers compatible with: {current_platform}", "error")
            all_helpers = self.helper_manager.list_helpers(platform_filter=False)
            all_launchers: list[HelperInfo] = all_helpers.get("launchers", [])
            if all_launchers:
                self.log(
                    f"   Found {len(all_launchers)} total launchers (all platforms):",
                    "warning",
                )
                for launcher in all_launchers[:5]:
                    self.log(f"     - {launcher.name}", "warning")
        else:
            for launcher in available_launchers:
                self.log(f"  • {launcher.name} ({launcher.language})")

        return available_launchers

    def _build_packages(self, launchers: Sequence[HelperInfo]) -> list[tuple[Path, HelperInfo]]:
        """Build sample packages for each launcher."""
        self.log("\n🔨 Building packages with each launcher...")
        built_packages: list[tuple[Path, HelperInfo]] = []

        for launcher_info in launchers:
            self.log(f"  Building with {launcher_info.name}...")
            pkg = self.build_with_launcher(launcher_info)
            if pkg:
                built_packages.append((pkg, launcher_info))
                continue

            self.log("    ❌ Failed", "error")
            for test in self.results["build_tests"]:
                if test["launcher"] == launcher_info.name and test.get("error"):
                    self.log(f"      Error: {test['error'][:200]}", "error")

        return built_packages

    def _verify_with_python_suite(self, packages: Sequence[tuple[Path, HelperInfo]]) -> None:
        """Verify built packages using Python tooling."""
        self.log("\n🔍 Testing Python verification of all packages...")
        for pkg, _ in packages:
            if not self.verify_with_python(pkg):
                self.log(f"  ❌ {pkg.name}", "error")

    def _verify_with_launcher_cli_suite(self, packages: Sequence[tuple[Path, HelperInfo]]) -> None:
        """Verify built packages using launcher CLI binaries."""
        self.log("\n🔍 Testing launcher CLI verification...")
        for pkg, launcher_info in packages:
            if not self.verify_with_launcher_cli(pkg, launcher_info.language):
                self.log(f"  ❌ {pkg.name} (CLI)", "error")

    def _exercise_cli_commands(self, packages: Sequence[tuple[Path, HelperInfo]]) -> None:
        """Run a subset of CLI commands to ensure behavior parity."""
        if not packages:
            return

        self.log("\n🎮 Testing CLI command consistency...")
        test_commands = ["--help", "--version", "info", "echo test"]
        for pkg, _launcher_info in packages[:2]:
            self.log(f"  Testing {pkg.name}:")
            for cmd in test_commands:
                if not self.test_cli_command(pkg, cmd):
                    self.log(f"    ⚠️ {cmd}", "warning")

    def _check_reproducible_builds(self, launchers: Sequence[HelperInfo]) -> None:
        """Ensure launchers can create reproducible bundles."""
        self.log("\n🔄 Testing reproducible builds...")
        for launcher_info in launchers:
            if not self.test_reproducible_build(launcher_info):
                self.log(f"  ⚠️ {launcher_info.name} not fully reproducible", "warning")

    def _cleanup_packages(self, packages: Sequence[tuple[Path, HelperInfo]]) -> None:
        """Remove temporary package artifacts."""
        for pkg, _ in packages:
            if pkg.exists():
                pkg.unlink()

    def _summarize_and_report(self) -> bool:
        """Summarize collected results and report them to the user."""
        build_success = sum(1 for t in self.results["build_tests"] if t["success"])
        build_total = len(self.results["build_tests"])

        verify_success = sum(1 for t in self.results["verify_tests"] if t["success"])
        verify_total = len(self.results["verify_tests"])

        cli_success = sum(1 for t in self.results["cli_tests"] if t["success"])
        cli_total = len(self.results["cli_tests"])

        repro_success = sum(1 for t in self.results["reproducible_tests"] if t["success"])
        repro_total = len(self.results["reproducible_tests"])

        overall_success = build_success > 0 and verify_success > 0 and cli_success > 0
        self.results["summary"] = {
            "builds": f"{build_success}/{build_total}",
            "verifications": f"{verify_success}/{verify_total}",
            "cli_tests": f"{cli_success}/{cli_total}",
            "reproducible": f"{repro_success}/{repro_total}",
            "overall_success": overall_success,
        }

        if self.json_output:
            print(json.dumps(self.results, indent=2))
        else:
            self.log("\n" + "=" * 60)
            self.log("SUMMARY", "warning")
            self.log("=" * 60)
            self.log(f"Builds: {self.results['summary']['builds']}")
            self.log(f"Verifications: {self.results['summary']['verifications']}")
            self.log(f"CLI Tests: {self.results['summary']['cli_tests']}")
            self.log(f"Reproducible: {self.results['summary']['reproducible']}")

            if not overall_success:
                self.log("\n❌ Cross-language compatibility: FAILED", "error")

        return overall_success

    def run_all_tests(self) -> int:
        """Run all cross-language tests."""
        self.log("=" * 60)
        self.log("CROSS-LANGUAGE COMPATIBILITY TESTS", "warning")
        self.log("=" * 60)

        # Change to taster directory
        original_cwd = Path.cwd()
        os.chdir(self.taster_dir)

        try:
            available_launchers = self._resolve_launchers()
            if not available_launchers:
                return 1

            built_packages = self._build_packages(available_launchers)
            self._verify_with_python_suite(built_packages)
            self._verify_with_launcher_cli_suite(built_packages)
            self._exercise_cli_commands(built_packages)
            self._check_reproducible_builds(available_launchers)
            success = self._summarize_and_report()
            self._cleanup_packages(built_packages)

            return 0 if success else 1
        finally:
            os.chdir(original_cwd)


@click.command("crosslang")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
@click.option("--output-file", "-o", type=click.Path(), help="Write output to file")
def crosslang_command(verbose: bool, json_output: bool, output_file: str | None) -> None:
    """Execute the cross-language compatibility test suite."""
    tester = CrossLangTester(verbose=verbose, json_output=json_output)
    exit_code = tester.run_all_tests()

    if output_file and json_output:
        output_path = Path(output_file)
        output_path.write_text(json.dumps(tester.results, indent=2), encoding="utf-8")

    sys.exit(exit_code)


# 🌶️📦🔚
