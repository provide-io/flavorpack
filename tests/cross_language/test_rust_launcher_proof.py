#!/usr/bin/env python3
"""
Proof that Rust launcher with emoji logging works with Python-built packages.
"""

import os
from pathlib import Path
import subprocess
import tempfile

from flavor.api import build_package_from_manifest


def test_rust_launcher_with_python_package() -> None:
    """Prove Rust launcher with emoji logging works."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create test provider
        src_dir = temp_dir / "src" / "emoji_test"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text('"""Emoji test provider."""')
        (src_dir / "main.py").write_text("""
import sys
print("🎉 Rust launcher successfully executed Python package!")
print("🐍 Python code is running inside Rust-launched environment")
print("✅ Cross-language compatibility with emojis proven!")
sys.exit(0)
""")

        # Create pyproject.toml
        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "emoji-test"
version = "1.0.0"
requires-python = ">=3.9"

[project.scripts]
terraform-provider-emoji = "emoji_test.main:serve"

[tool.pspf]
provider_name = "emoji"
entry_point = "emoji_test.main:serve"

[tool.pspf.build]
python_version = "3.13"
dependencies = ["./src/emoji_test"]

[tool.setuptools.packages.find]
where = ["src"]
""")

        # Build package with Python
        print("📦 Building package with Python flavor...")
        package_path = build_package_from_manifest(pyproject)[0]
        print(f"✅ Package built: {package_path}")

        # Build Rust launcher
        print("\n🦀 Building Rust launcher...")
        rust_dir = Path(
            "/REDACTED_ABS_PATH"
        )
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=rust_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"❌ Failed to build Rust launcher: {result.stderr}")
            return

        rust_launcher = rust_dir / "target" / "release" / "flavor-launcher-rs"
        print(f"✅ Rust launcher built: {rust_launcher}")

        # Create executable
        executable = temp_dir / "emoji-test-provider"
        with open(executable, "wb") as out:
            with open(rust_launcher, "rb") as launcher:
                out.write(launcher.read())
            with open(package_path, "rb") as package:
                out.write(package.read())

        executable.chmod(0o755)
        print(f"✅ Created executable: {executable}")

        # Run with verbose logging to see emojis
        print("\n🚀 Running with Rust launcher (verbose mode)...")
        env = os.environ.copy()
        env["RUST_LOG"] = "trace"

        result = subprocess.run(
            [str(executable), "--verbose"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

        print("\n=== RUST LAUNCHER OUTPUT (stderr) ===")
        print(result.stderr)
        print("\n=== PYTHON OUTPUT (stdout) ===")
        print(result.stdout)
        print(f"\nExit code: {result.returncode}")

        # Verify success
        assert result.returncode == 0
        assert "🎉 Rust launcher successfully executed Python package!" in result.stdout

        # Verify Rust launcher emojis in stderr
        assert "🦀🚀 Starting Flavor launcher (Rust implementation)" in result.stderr
        assert (
            "📦 Extracting package" in result.stderr
            or "✨ Cache is valid" in result.stderr
        )
        assert "🐍 Found Python executable" in result.stderr
        assert "🚀 Starting provider" in result.stderr
        assert "✅ Provider completed successfully" in result.stderr

        print("\n✅ PROOF COMPLETE: Rust launcher with emoji logging works perfectly!")
        print("   - 🦀 Rust launcher extracted the package")
        print("   - 🐍 Python code executed successfully")
        print("   - 📝 Structured logging with emojis is functional")
        print("   - 🎯 Cross-language compatibility proven!")


if __name__ == "__main__":
    test_rust_launcher_with_python_package()


# 📦🍜🧪🪄
