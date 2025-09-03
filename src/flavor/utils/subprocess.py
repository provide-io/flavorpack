#!/usr/bin/env python3
#
# flavor/utils/subprocess.py
#
"""Unified subprocess execution utilities for the Flavor project.

This module now wraps provide.foundation.process for backward compatibility.
All new code should import directly from provide.foundation.process.
"""

from collections.abc import Mapping
import os
from pathlib import Path
import subprocess

from provide.foundation import logger
from provide.foundation.process import run, run_simple
from flavor.exceptions import BuildError


def run_command(
    command: list[str],
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    capture_output: bool = True,
    check: bool = True,
    timeout: int | None = None,
    log_command: bool = True,
) -> subprocess.CompletedProcess:
    """Run a subprocess command with consistent error handling and logging.

    This is the primary subprocess execution function that should be used
    throughout the Flavor codebase for consistency.

    Args:
        command: Command and arguments as a list
        cwd: Working directory for the command
        env: Environment variables (if None, uses current environment)
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        timeout: Command timeout in seconds
        log_command: Whether to log the command being run

    Returns:
        CompletedProcess with stdout/stderr as strings

    Raises:
        BuildError: If command fails and check=True
        subprocess.TimeoutExpired: If timeout is exceeded
    """
    if log_command:
        logger.info(f"🗣️ Running command: {' '.join(command)}")

    # Add NO_COVERAGE to environment for build commands
    build_env = dict(env) if env is not None else os.environ.copy()
    build_env["NO_COVERAGE"] = "1"
    
    try:
        # Use foundation's run function
        result = run(
            command,
            cwd=cwd,
            env=build_env,
            capture_output=capture_output,
            check=check,
            timeout=timeout,
        )
        
        # Convert foundation's CompletedProcess to stdlib's
        return subprocess.CompletedProcess(
            args=result.args,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except Exception as e:
        # Convert ProcessError to BuildError for backward compatibility
        if check and "exit code" in str(e):
            raise BuildError(str(e)) from e
        raise


def run_command_simple(
    command: list[str],
    cwd: Path | str | None = None,
) -> str:
    """Simple wrapper for run_command that returns stdout as a string.

    Use this for simple commands where you just need the output.

    Args:
        command: Command and arguments as a list
        cwd: Working directory for the command

    Returns:
        Stdout as a stripped string

    Raises:
        BuildError: If command fails
    """
    try:
        return run_simple(command, cwd=cwd)
    except Exception as e:
        raise BuildError(str(e)) from e
