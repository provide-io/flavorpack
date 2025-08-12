#!/usr/bin/env python3
"""Wrapper script to run Flavor CLI from PSPF bundle."""

import sys
from flavor.cli import cli

if __name__ == "__main__":
    # Call the CLI with sys.argv
    cli()