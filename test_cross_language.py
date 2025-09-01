#!/usr/bin/env python3
"""Test cross-language compatibility of the new format."""

import subprocess
import tempfile
from pathlib import Path
import sys

def run_command(cmd):
    """Run a command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(f"Success: {result.stdout[:100]}..." if len(result.stdout) > 100 else f"Success: {result.stdout}")
    return True

def test_builder_launcher_combo(builder, launcher, name):
    """Test a specific builder/launcher combination."""
    print(f"\n{'='*60}")
    print(f"Testing {name}: {builder} builder + {launcher} launcher")
    print('='*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test config (different format for Rust vs Go)
        config = tmpdir / "test.json"
        if builder == "rs":
            # Rust builder format
            config.write_text("""{
    "package": {
        "name": "test-package",
        "version": "1.0.0"
    },
    "execution": {
        "engine": "shell",
        "entrypoint": "echo 'Hello from test package'"
    },
    "slots": []
}""")
        else:
            # Go builder format
            config.write_text("""{
    "name": "test-package",
    "version": "1.0.0",
    "entrypoint": "echo 'Hello from test package'",
    "engine": "shell"
}""")
        
        # Build package
        output = tmpdir / f"test_{name}.psp"
        builder_bin = f"ingredients/bin/flavor-{builder}-builder-darwin_arm64"
        launcher_bin = f"ingredients/bin/flavor-{launcher}-launcher-darwin_arm64"
        
        if not Path(builder_bin).exists():
            print(f"Builder not found: {builder_bin}")
            return False
            
        if not Path(launcher_bin).exists():
            print(f"Launcher not found: {launcher_bin}")
            return False
        
        # Build command
        build_cmd = [
            builder_bin,
            "--manifest", str(config),
            "--launcher-bin", launcher_bin,
            "--output", str(output),
            "--key-seed", "test123"
        ]
        
        if not run_command(build_cmd):
            print(f"Build failed for {name}")
            return False
        
        if not output.exists():
            print(f"Output file not created: {output}")
            return False
            
        print(f"✅ Package built: {output} ({output.stat().st_size} bytes)")
        
        # Verify MagicTrailer structure
        with open(output, "rb") as f:
            # Read last 8200 bytes
            f.seek(-8200, 2)
            trailer = f.read(8200)
            
            # Check emojis
            if trailer[:4] != b'\xf0\x9f\x93\xa6':  # 📦
                print(f"Missing 📦 at start: {trailer[:4].hex()}")
                return False
            print("✅ Found 📦 at trailer start")
            
            if trailer[-4:] != b'\xf0\x9f\xaa\x84':  # 🪄
                print(f"Missing 🪄 at end: {trailer[-4:].hex()}")
                return False
            print("✅ Found 🪄 at trailer end")
            
            # Check version at start of index
            import struct
            version = struct.unpack("<I", trailer[4:8])[0]
            if version != 0x20250001:
                print(f"Wrong version: 0x{version:08x}")
                return False
            print(f"✅ Correct version: 0x{version:08x}")
        
        # Test execution (if same language launcher)
        if builder == launcher:
            print("\nTesting execution...")
            env = {"FLAVOR_INSECURE": "1", "FLAVOR_LOG_LEVEL": "error"}
            result = subprocess.run([str(output), "info"], 
                                  capture_output=True, 
                                  text=True,
                                  env={**env})
            if "test-package" in result.stdout or "1.0.0" in result.stdout:
                print("✅ Package executes correctly")
            else:
                print(f"Execution output unexpected: {result.stdout}")
                print(f"Stderr: {result.stderr}")
        
        return True

def main():
    """Test all builder/launcher combinations."""
    print("Testing cross-language compatibility with new format")
    print("=" * 60)
    
    combinations = [
        ("go", "go", "go-go"),
        ("go", "rs", "go-rust"),
        ("rs", "rs", "rust-rust"),
        ("rs", "go", "rust-go"),
    ]
    
    results = []
    for builder, launcher, name in combinations:
        success = test_builder_launcher_combo(builder, launcher, name)
        results.append((name, success))
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:20} {status}")
    
    if all(success for _, success in results):
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())