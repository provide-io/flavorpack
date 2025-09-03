#!/usr/bin/env python3
#
# flavor/utils/subprocess.py
#
"""Unified subprocess execution utilities for the Flavor project.

This module now wraps provide.foundation.process for backward compatibility.
All new code should import directly from provide.foundation.process.
"""

from collections.abc import Mapping
from pathlib import Path
import subprocess

from provide.foundation.process.runner import (
    run_command as _run_command,
    run_command_simple as _run_command_simple,
    run_build_command,
    BuildError,
)


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
    # Use foundation's run_build_command for build operations
    try:
        result = run_build_command(
            command,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            timeout=timeout,
            quiet=not log_command,
        )
        
        # Convert foundation's CompletedProcess to stdlib's
        return subprocess.CompletedProcess(
            args=result.args,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except BuildError:
        # Re-raise as-is for compatibility
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
    result = run_command(command, cwd=cwd, capture_output=True, check=True)
    return result.stdout.strip()
