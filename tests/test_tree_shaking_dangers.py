#!/usr/bin/env python3
"""Demonstrates why 'it runs' doesn't mean tree-shaking worked."""

# This might run fine initially...
def main():
    print("App started!")
    user_input = input("Enter command: ")
    
    # But breaks when user enters 'analyze'
    if user_input == "analyze":
        import pandas as pd  # Lazy import - tree-shaker missed this!
        df = pd.DataFrame([1, 2, 3])
        print(df)
    
    # Or breaks in production when error occurs
    try:
        risky_operation()
    except Exception as e:
        import traceback  # Only imported on error
        import logging    # Tree-shaker might remove these
        logging.error(traceback.format_exc())

def risky_operation():
    """Works 99% of the time."""
    import random
    if random.random() < 0.01:  # 1% chance
        raise ValueError("Rare error!")
    return "success"

# Tree-shaker won't see these:
PLUGINS = {
    'json': 'import json',
    'yaml': 'import yaml',
    'xml': 'import xml.etree.ElementTree'
}

def load_format(fmt):
    """Dynamic import based on runtime data."""
    exec(PLUGINS[fmt])  # Completely invisible to static analysis

# Even worse - imports triggered by environment
import os
if os.environ.get('DEBUG'):
    import pdb  # Only in debug mode
    import cProfile  # Tree-shaker might strip these

if os.name == 'nt':
    import msvcrt  # Windows only
else:
    import termios  # Unix only