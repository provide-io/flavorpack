#
# flavor/packaging/util.py
#
"""Utility functions for the packaging module."""

import os
import subprocess
from pathlib import Path
from typing import Mapping

from pyvider.telemetry import logger

from flavor.exceptions import BuildError


def run_subprocess(
    command: list[str],
    cwd: Path | str | None = None,
    capture_output: bool = False,
    text: bool = False,
    env: Mapping[str, str] | None = None,
) -> str | subprocess.CompletedProcess:
    """Run a subprocess command with a controlled environment."""
    logger.info(f"Running command: {' '.join(command)}")
    
    # Use provided environment or create a new one from the current process
    run_env = env if env is not None else os.environ.copy()
    run_env["NO_COVERAGE"] = "1"

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
        env=run_env,
    )

    if result.returncode != 0:
        raise BuildError(
            f"Command failed: {' '.join(command)}\nStderr: {result.stderr.strip()}"
        )

    # If the caller wants the raw CompletedProcess object, return it.
    if capture_output and text:
        return result

    return result.stdout.strip()
