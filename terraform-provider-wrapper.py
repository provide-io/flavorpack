#!/usr/bin/env python3
"""
Wrapper for terraform-provider-pyvider to demonstrate PSPF bundling.
This imports the pyvider CLI and runs it.
"""

import sys
import os

# Add the pyvider source directory to Python path
pyvider_src = os.path.join(os.path.dirname(__file__), "..", "pyvider", "src")
if os.path.exists(pyvider_src):
    sys.path.insert(0, pyvider_src)

try:
    from pyvider.cli.__main__ import main
    main()
except ImportError as e:
    print(f"Error: Could not import pyvider: {e}")
    print("This is a demonstration wrapper. In production, pyvider would be properly installed.")
    sys.exit(1)