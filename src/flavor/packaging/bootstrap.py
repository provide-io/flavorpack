#!/usr/bin/env python3
"""Bootstrap script for Flavor execution."""
import os
import subprocess
import sys

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
    
    # Use UV to install the wheels
    subprocess.run([
        uv, "pip", "install",
        "--python", sys.executable,
        "--no-deps"
    ] + wheels, check=True)

# Run the module
import runpy
module = sys.argv[1] if len(sys.argv) > 1 else "flavor.cli"
sys.argv = [module] + sys.argv[2:]  # Fix argv for the module
runpy.run_module(module, run_name="__main__", alter_sys=True)