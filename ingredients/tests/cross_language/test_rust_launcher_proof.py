#!/usr/bin/env python3
"""
Proof that Rust launcher with emoji logging works with Python-built packages.
"""

from pathlib import Path
import subprocess
import tempfile

import pytest

from flavor.api import build_package_from_manifest
from flavor.helpers.manager import HelperManager


# This test requires the rust launcher to be built
@pytest.mark.requires_helpers
def test_rust_launcher_with_python_package() -> None:
    """Prove Rust launcher can execute a Python package built by the Python builder."""
    helper_manager = HelperManager()
    try:
        # Find the Rust launcher binary
        rust_launcher_path = helper_manager.get_helper("flavor-rs-launcher")
    except FileNotFoundError:
        pytest.skip("Rust launcher helper binary not found. Run 'flavor helpers build'.")

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # Create a simple Python application to be packaged
        src_dir = temp_dir / "src" / "my_app"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").touch()
        (src_dir / "main.py").write_text(
            """
import sys
print("🎉 Rust launcher successfully executed Python package!")
print("🐍 Python code is running inside a Rust-launched environment.")
print("✅ Cross-language compatibility proven!")
sys.exit(0)
"""
        )

        # Create pyproject.toml manifest
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path.write_text(
            """
[project]
name = "cross-lang-test-app"
version = "1.0.0"

[project.scripts]
my_app = "my_app.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.flavor]
entry_point = "my_app.main:main"
"""
        )

        # Build the package using the Python builder, but specify the Rust launcher
        print("📦 Building package with Python builder and Rust launcher...")
        built_artifacts = build_package_from_manifest(
            manifest_path=pyproject_path,
            launcher_bin=rust_launcher_path,
            show_progress=True,
        )
        assert built_artifacts, "Package build did not produce any artifacts."
        package_path = built_artifacts[0]
        print(f"✅ Package built: {package_path}")
        assert package_path.exists(), "Built package file does not exist."
        
        # Make the package executable (required on Unix-like systems)
        package_path.chmod(0o755)

        # Execute the built package
        print(f"🚀 Executing package with Rust launcher: {package_path}")
        result = subprocess.run(
            [str(package_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        # Print output for debugging
        print("\n=== RUST LAUNCHER STDOUT ===")
        print(result.stdout)
        print("\n=== RUST LAUNCHER STDERR ===")
        print(result.stderr)
        print(f"\nExit code: {result.returncode}")

        # --- Assertions ---
        assert result.returncode == 0, "Package execution failed with a non-zero exit code."

        # Verify the output from the Python script
        stdout = result.stdout
        assert "🎉 Rust launcher successfully executed Python package!" in stdout
        assert "🐍 Python code is running inside a Rust-launched environment." in stdout
        assert "✅ Cross-language compatibility proven!" in stdout

        print("\n✅ PROOF COMPLETE: Rust launcher successfully executed a Python-built package.")


if __name__ == "__main__":
    pytest.main([__file__])
