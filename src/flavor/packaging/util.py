#
# flavor/packaging/util.py
#
"""Utility functions for the packaging module."""

import os
import subprocess
from pathlib import Path

from pyvider.telemetry import logger

from flavor.exceptions import BuildError


def run_subprocess(command: list[str], cwd: Path | str | None = None, 
                  capture_output: bool = False, text: bool = False) -> str | subprocess.CompletedProcess:
    """Run a subprocess command."""
    logger.info(f"Running command: {' '.join(command)}")
    env = os.environ.copy()
    env["NO_COVERAGE"] = "1"
    
    # If caller wants the raw result, use their settings
    if capture_output and text:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
            env=env,
        )
        if result.returncode != 0:
            raise BuildError(
                f"Command failed: {' '.join(command)}\nStderr: {result.stderr.strip()}"
            )
        return result
    
    # Otherwise use default behavior
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise BuildError(
            f"Command failed: {' '.join(command)}\nStderr: {result.stderr.strip()}"
        )
    return result.stdout.strip()
