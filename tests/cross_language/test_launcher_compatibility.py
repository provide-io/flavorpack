"""
Cross-language compatibility tests for flavor launchers.

Tests that flavor-launcher-go and flavor-launcher-rs can both run
packages created by any packager.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import pytest

from flavor.api import build_package_from_manifest
from flavor.compiler import ensure_go_binary


@pytest.fixture(scope="module")
def packager_binaries(request):
    """Ensure all packager binaries are available."""
    binaries = {}
    skip_rust = request.config.getoption("--skip-rust", False)
    skip_go = request.config.getoption("--skip-go", False)
    
    import sys
    
    # Python flavor is available via module
    binaries["python"] = [sys.executable, "-m", "flavor"]
    
    # Ensure Go packager is built
    if not skip_go:
        go_packager = ensure_go_binary("flavor-go")
        binaries["go"] = [str(go_packager)]
    
    # Build Rust packager if Rust is available and not skipped
    if not skip_rust:
        rust_dir = (
            Path(__file__).parent.parent.parent
            / "src"
            / "flavor"
            / "rust"
            / "flavor-packager-rs"
        )
        if shutil.which("cargo") and rust_dir.exists():
            try:
                # Build Rust packager
                subprocess.run(
                    ["cargo", "build", "--release"],
                    cwd=rust_dir,
                    check=True,
                    capture_output=True,
                )
                rust_binary = rust_dir / "target" / "release" / "flavor-rs"
                if rust_binary.exists():
                    binaries["rust"] = [str(rust_binary)]
            except subprocess.CalledProcessError:
                # Rust build failed, skip it
                pass
    
    return binaries


@pytest.fixture(scope="module")
def launcher_binaries():
    """Ensure all launcher binaries are available."""
    binaries = {}

    # Ensure Go launcher is built
    go_launcher = ensure_go_binary("flavor-launcher-go")
    binaries["go"] = str(go_launcher)

    # Build Rust launcher if Rust is available
    rust_dir = (
        Path(__file__).parent.parent.parent
        / "src"
        / "flavor"
        / "rust"
        / "flavor-launcher-rs"
    )
    if shutil.which("cargo") and rust_dir.exists():
        # Build Rust launcher
        subprocess.run(
            ["cargo", "build", "--release"],
            cwd=rust_dir,
            check=True,
            capture_output=True,
        )
        rust_binary = rust_dir / "target" / "release" / "flavor-launcher-rs"
        if rust_binary.exists():
            binaries["rust"] = str(rust_binary)

    return binaries


@pytest.fixture
def test_package(tmp_path):
    """Create a test package using Python packager."""
    # Create a simple provider
    src_dir = tmp_path / "src" / "test_provider"
    src_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text('"""Test provider."""')
    (src_dir / "main.py").write_text("""
import sys
import json

def serve():
    # Simple test - output a marker and exit
    output = {
        "status": "success",
        "provider": "test_provider",
        "version": "1.0.0"
    }
    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    serve()
""")

    # Create pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "test-provider"
version = "1.0.0"
requires-python = ">=3.9"

[project.scripts]
terraform-provider-test = "test_provider.main:serve"

[tool.flavor]
provider_name = "test"
entry_point = "test_provider.main:serve"

[tool.flavor.build]
python_version = "3.13"
dependencies = ["./src/test_provider"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["test_provider*"]
""")

    # Build the package
    artifacts = build_package_from_manifest(pyproject)
    assert len(artifacts) == 1

    return artifacts[0]


class TestLauncherCompatibility:
    """Test that all launchers can run packages from any packager."""

    def test_launchers_can_run_package(self, test_package, launcher_binaries) -> None:
        """Test that both Go and Rust launchers can run a test package."""
        if len(launcher_binaries) == 0:
            pytest.skip("No launcher implementations available")

        for launcher_name, launcher_path in launcher_binaries.items():
            # Create a temporary copy of the package as the launcher binary
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                test_binary = temp_dir / "test-provider"

                # Concatenate launcher + package
                with open(test_binary, "wb") as out:
                    # Write launcher
                    with open(launcher_path, "rb") as launcher_file:
                        out.write(launcher_file.read())
                    # Write package
                    with open(test_package, "rb") as package_file:
                        out.write(package_file.read())

                # Make executable
                os.chmod(test_binary, 0o755)

                # Run the package
                result = subprocess.run(
                    [str(test_binary)], capture_output=True, text=True, timeout=30
                )

                # Should exit with status 0 and output JSON
                assert result.returncode == 0, (
                    f"{launcher_name} launcher failed to run package: {result.stderr}"
                )

                # Verify output
                try:
                    output = json.loads(result.stdout)
                    assert output["status"] == "success"
                    assert output["provider"] == "test_provider"
                    assert output["version"] == "1.0.0"
                except json.JSONDecodeError:
                    pytest.fail(
                        f"{launcher_name} launcher produced invalid output: {result.stdout}"
                    )

    def test_launcher_caching(self, test_package, launcher_binaries) -> None:
        """Test that launchers properly cache extracted packages."""
        if len(launcher_binaries) == 0:
            pytest.skip("No launcher implementations available")

        for launcher_name, launcher_path in launcher_binaries.items():
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                test_binary = temp_dir / "test-provider"

                # Create test binary
                with open(test_binary, "wb") as out:
                    with open(launcher_path, "rb") as launcher_file:
                        out.write(launcher_file.read())
                    with open(test_package, "rb") as package_file:
                        out.write(package_file.read())

                os.chmod(test_binary, 0o755)

                # Run twice and measure time
                times = []
                for _i in range(2):
                    start = time.time()
                    result = subprocess.run(
                        [str(test_binary)], capture_output=True, text=True, timeout=30
                    )
                    end = time.time()
                    times.append(end - start)

                    assert result.returncode == 0

                # Second run should be significantly faster due to caching
                # (at least 50% faster)
                assert times[1] < times[0] * 0.5, (
                    f"{launcher_name} launcher doesn't seem to cache properly. "
                    f"First run: {times[0]:.2f}s, Second run: {times[1]:.2f}s"
                )

    def test_launcher_force_extract(self, test_package, launcher_binaries) -> None:
        """Test that launchers respect the --force-extract flag."""
        if len(launcher_binaries) == 0:
            pytest.skip("No launcher implementations available")

        for _launcher_name, launcher_path in launcher_binaries.items():
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                test_binary = temp_dir / "test-provider"

                # Create test binary
                with open(test_binary, "wb") as out:
                    with open(launcher_path, "rb") as launcher_file:
                        out.write(launcher_file.read())
                    with open(test_package, "rb") as package_file:
                        out.write(package_file.read())

                os.chmod(test_binary, 0o755)

                # Run once to cache
                subprocess.run([str(test_binary)], capture_output=True, timeout=30)

                # Run with --force-extract
                result = subprocess.run(
                    [str(test_binary), "--force-extract"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "FLAVOR_LOG_LEVEL": "trace"},
                )

                assert result.returncode == 0
                # Check that it actually re-extracted (would be in trace logs)
                assert (
                    "extracting" in result.stderr.lower()
                    or "extract" in result.stderr.lower()
                )


class TestCrossCompatibility:
    """Test all combinations of packagers and launchers."""

    @pytest.mark.parametrize("packager", ["python", "go", "rust"])
    @pytest.mark.parametrize("launcher", ["go", "rust"])
    def test_packager_launcher_matrix(
        self, tmp_path, packager_binaries, launcher_binaries, packager, launcher
    ) -> None:
        """Test each packager with each launcher."""
        if packager not in packager_binaries:
            pytest.skip(f"{packager} packager not available")
        if launcher not in launcher_binaries:
            pytest.skip(f"{launcher} launcher not available")

        # Create a simple test provider
        src_dir = tmp_path / "src" / "matrix_test"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text('"""Matrix test provider."""')
        (src_dir / "main.py").write_text(f"""
import json

def serve():
    output = {{
        "packager": "{packager}",
        "launcher": "{launcher}",
        "status": "success"
    }}
    print(json.dumps(output))

if __name__ == "__main__":
    serve()
""")

        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(f"""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "matrix-test"
version = "1.0.0"
requires-python = ">=3.9"

[project.scripts]
terraform-provider-matrix = "matrix_test.main:serve"

[tool.pspf]
provider_name = "matrix_{packager}_{launcher}"
entry_point = "matrix_test.main:serve"

[tool.pspf.build]
python_version = "3.13"
dependencies = ["./src/matrix_test"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["matrix_test*"]
""")

        # Build with specified packager
        if packager == "python":
            artifacts = build_package_from_manifest(pyproject)
            package_path = artifacts[0]
        else:
            # Use Go or Rust packager
            output_path = tmp_path / "matrix.flavor"
            cmd = packager_binaries[packager] + [
                "build",
                "--out",
                str(output_path),
                "--payload-dir",
                str(tmp_path),
                "--package-key",
                str(tmp_path / "keys" / "provider-private.key"),
                "--public-key",
                str(tmp_path / "keys" / "provider-public.key"),
                "--launcher-bin",
                str(ensure_go_binary("flavor-launcher-go")),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            package_path = output_path

        # Create executable with specified launcher
        test_binary = tmp_path / "test-matrix"
        with open(test_binary, "wb") as out:
            with open(launcher_binaries[launcher], "rb") as launcher_file:
                out.write(launcher_file.read())
            with open(package_path, "rb") as package_file:
                out.write(package_file.read())

        os.chmod(test_binary, 0o755)

        # Run and verify
        result = subprocess.run(
            [str(test_binary)], capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, (
            f"Failed {packager} packager + {launcher} launcher: {result.stderr}"
        )

        output = json.loads(result.stdout)
        assert output["packager"] == packager
        assert output["launcher"] == launcher
        assert output["status"] == "success"


# 📦🍜🧪🪄
