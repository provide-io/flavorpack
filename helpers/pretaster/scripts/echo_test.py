#!/usr/bin/env python3
"""Simple echo test to verify basic packaging and execution."""
import sys
import os

print(f"🎯 Echo Test Script")
print(f"Python: {sys.executable}")
print(f"Arguments: {sys.argv[1:]}")
print(f"Working Directory: {os.getcwd()}")
print(f"FLAVOR_WORKENV: {os.environ.get('FLAVOR_WORKENV', 'not set')}")
print(f"FLAVOR_COMMAND_NAME: {os.environ.get('FLAVOR_COMMAND_NAME', 'not set')}")

# Echo back arguments
if len(sys.argv) > 1:
    print(f"\n📢 Echoing: {' '.join(sys.argv[1:])}")
else:
    print("\n📢 Echo test ready (no arguments provided)")
sys.exit(0)