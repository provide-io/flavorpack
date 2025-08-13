#!/usr/bin/env python3
"""Bootstrap script for Flavor execution."""
import os
import subprocess
import sys
import tempfile

# This will be run by UV's managed Python
cache_dir = os.environ.get("FLAVOR_CACHE", "/tmp/pspf/cache")

# Check if flavor is installed
try:
    import flavor
except ImportError:
    # Install all wheels
    uv = os.path.join(cache_dir, "bin", "uv")
    import glob
    wheels = glob.glob(os.path.join(cache_dir, "wheels", "*.whl"))
    
    # Use UV to install the wheels into the venv's site-packages
    # Since {cache} is the venv root, site-packages is at lib/python3.11/site-packages
    site_packages = os.path.join(cache_dir, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
    os.makedirs(site_packages, exist_ok=True)
    
    subprocess.run([
        uv, "pip", "install",
        "--python", sys.executable,
        "--target", site_packages,
        "--no-deps"
    ] + wheels, check=True)

# Run the module
import runpy
module = sys.argv[1] if len(sys.argv) > 1 else "flavor.cli"
sys.argv = [module] + sys.argv[2:]  # Fix argv for the module
try:
    runpy.run_module(module, run_name="__main__", alter_sys=True)
except Exception as e:
    print(f"Error running module {module}: {e}", file=sys.stderr)
    raise