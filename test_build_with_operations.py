#!/usr/bin/env python3
"""Build a test package using the new operations system."""

import json
import tempfile
from pathlib import Path

from flavor.packaging.orchestrator import Orchestrator


def build_test_package():
    """Build a minimal test package."""
    print("🔨 Building test package with operations...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test Python script
        test_script = tmpdir / "hello.py"
        test_script.write_text("""
#!/usr/bin/env python3
import sys
print(f"Hello from operations! Python {sys.version}")
print("Operations test successful!")
""")
        
        # Create pyproject.toml
        pyproject = tmpdir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "hello-operations"
version = "1.0.0"
description = "Test package with operations"

[project.scripts]
hello = "hello:main"

[tool.flavor]
entry_point = "hello:main"
""")
        
        # Create __init__.py with main function
        init_file = tmpdir / "hello.py"
        init_file.write_text("""
def main():
    import sys
    print(f"Hello from operations! Python {sys.version}")
    print("Operations test successful!")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
""")
        
        # Build the package
        output_path = tmpdir / "hello.psp"
        
        try:
            orchestrator = Orchestrator(
                manifest_path=pyproject,
                output_path=output_path,
                launcher_path=None,  # Will auto-select
                key_seed="test123",
                python_version="3.11",
            )
            
            result = orchestrator.build()
            
            if output_path.exists():
                size = output_path.stat().st_size
                print(f"✅ Package built: {output_path} ({size:,} bytes)")
                
                # Copy to a known location for testing
                test_output = Path("test_operations.psp")
                import shutil
                shutil.copy2(output_path, test_output)
                print(f"📦 Copied to: {test_output}")
                
                return test_output
            else:
                print("❌ Package build failed")
                return None
                
        except Exception as e:
            print(f"❌ Build error: {e}")
            import traceback
            traceback.print_exc()
            return None


def test_package_execution():
    """Test running the package."""
    package_path = Path("test_operations.psp")
    
    if not package_path.exists():
        print("❌ Package not found")
        return False
    
    print("\n🚀 Testing package execution...")
    
    import subprocess
    import os
    
    # Make executable
    os.chmod(package_path, 0o755)
    
    # Run the package
    result = subprocess.run(
        [str(package_path)],
        capture_output=True,
        text=True,
        env={**os.environ, "FLAVOR_INSECURE": "1"}
    )
    
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"Output:\n{result.stdout}")
    if result.stderr:
        print(f"Errors:\n{result.stderr}")
    
    return result.returncode == 0


def main():
    """Main test function."""
    print("🚀 Starting operations package build test")
    print("=" * 60)
    
    # Build the package
    package_path = build_test_package()
    
    if package_path:
        # Test execution
        success = test_package_execution()
        
        print("=" * 60)
        if success:
            print("✨ All tests passed!")
            return 0
        else:
            print("❌ Execution test failed")
            return 1
    else:
        print("❌ Build failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())