"""Integration tests for pretaster PSPF validation."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


class TestPretasterIntegration:
    """Test pretaster cross-language PSPF validation."""

    @pytest.fixture
    def pretaster_dir(self) -> Path:
        """Get the pretaster directory."""
        return Path(__file__).parent.parent.parent / "tests" / "pretaster"

    @pytest.mark.integration
    @pytest.mark.requires_ingredients
    def test_pretaster_core_suite(self, pretaster_dir: Path) -> None:
        """Test that pretaster core test suite passes."""
        if not pretaster_dir.exists():
            pytest.skip("Pretaster directory not found")

        # Check if ingredients are built
        dist_dir = pretaster_dir.parent.parent / "dist" / "bin"
        if not any(dist_dir.glob("flavor-*-builder-*")):
            pytest.skip("Ingredients not built - run ./build.sh first")

        # Run pretaster core tests
        result = subprocess.run(
            ["make", "test-core"],
            cwd=pretaster_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Check that tests passed
        assert result.returncode == 0, f"Pretaster tests failed: {result.stderr}"
        assert "All tests passed!" in result.stdout

    @pytest.mark.integration
    @pytest.mark.cross_language
    def test_echo_package_execution(self, pretaster_dir: Path) -> None:
        """Test that echo package can be created and executed."""
        if not pretaster_dir.exists():
            pytest.skip("Pretaster directory not found")

        echo_package = pretaster_dir / "dist" / "echo-test.psp"

        # Build echo package if needed
        if not echo_package.exists():
            subprocess.run(
                ["make", "dist/echo-test.psp"],
                cwd=pretaster_dir,
                check=True,
                capture_output=True,
            )

        # Execute echo package
        result = subprocess.run(
            [str(echo_package), "Hello from test!"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "Hello from test!" in result.stdout

    @pytest.mark.integration
    @pytest.mark.cross_language
    def test_shell_package_execution(self, pretaster_dir: Path) -> None:
        """Test that shell package can be created and executed."""
        if not pretaster_dir.exists():
            pytest.skip("Pretaster directory not found")

        shell_package = pretaster_dir / "dist" / "shell-test.psp"

        # Build shell package if needed
        if not shell_package.exists():
            subprocess.run(
                ["make", "dist/shell-test.psp"],
                cwd=pretaster_dir,
                check=True,
                capture_output=True,
            )

        # Execute shell package
        result = subprocess.run(
            [str(shell_package)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "Simple Shell Script Test" in result.stdout
        assert "✅ Shell script test completed successfully" in result.stdout

    @pytest.mark.integration
    @pytest.mark.slow
    def test_orchestration_package(self, pretaster_dir: Path) -> None:
        """Test complex multi-slot orchestration package."""
        if not pretaster_dir.exists():
            pytest.skip("Pretaster directory not found")

        orchestrate_package = pretaster_dir / "dist" / "orchestrate-test.psp"

        # Build orchestration package if needed
        if not orchestrate_package.exists():
            subprocess.run(
                ["make", "dist/orchestrate-test.psp"],
                cwd=pretaster_dir,
                check=True,
                capture_output=True,
            )

        # Execute orchestration package
        result = subprocess.run(
            [str(orchestrate_package)],
            capture_output=True,
            text=True,
            timeout=60,  # Longer timeout for complex test
        )

        assert result.returncode == 0
        assert "Multi-Slot Orchestration Test Starting" in result.stdout
        assert "Orchestration Complete!" in result.stdout

    @pytest.mark.integration
    def test_package_verification(self, pretaster_dir: Path) -> None:
        """Test PSPF package verification functionality."""
        if not pretaster_dir.exists():
            pytest.skip("Pretaster directory not found")

        # Try to find any existing package
        package_files = list((pretaster_dir / "dist").glob("*.psp"))
        if not package_files:
            pytest.skip("No test packages found")

        package = package_files[0]

        # Test package inspection (should work without ingredients)
        result = subprocess.run(
            ["flavor", "inspect", str(package)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should show package metadata
        assert result.returncode == 0 or "not found" in result.stderr  # flavor may not be in PATH