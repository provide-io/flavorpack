#!/usr/bin/env python3
#
# flavor/utils/subprocess.py
#
"""Unified subprocess execution utilities for the Flavor project."""

from collections.abc import Mapping
import os
from pathlib import Path
import subprocess

from pyvider.telemetry import logger

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

    # Use provided environment or copy current
    run_env = dict(env) if env is not None else os.environ.copy()
    run_env["NO_COVERAGE"] = "1"  # Disable coverage for subprocesses

    try:
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            cwd=cwd,
            check=False,  # We'll handle the check ourselves
            env=run_env,
            timeout=timeout,
        )

        if check and result.returncode != 0:
            error_msg = f"Command failed with exit code {result.returncode}: {' '.join(command)}"
            if capture_output and result.stderr:
                error_msg += f"\nStderr: {result.stderr.strip()}"
            raise BuildError(error_msg)

        return result

    except subprocess.TimeoutExpired:
        logger.error(f"❌ Command timed out after {timeout}s: {' '.join(command)}")
        raise
    except Exception as e:
        logger.error(f"❌ Command execution failed: {e}")
        raise BuildError(f"Failed to execute command: {' '.join(command)}") from e


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


def run_command_with_progress(
    command: list[str],
    description: str,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a command with a progress indicator.

    Args:
        command: Command and arguments as a list
        description: Description to show in progress
        cwd: Working directory for the command
        env: Environment variables

    Returns:
        CompletedProcess result

    Raises:
        BuildError: If command fails
    """
    from flavor.progress import ProgressIndicator

    with ProgressIndicator() as progress:
        with progress.task(description=description) as task:
            result = run_command(
                command,
                cwd=cwd,
                env=env,
                capture_output=True,
                check=True,
                log_command=False,  # Don't double-log
            )
            task.finish()

    return result


# Backward compatibility alias
def run_subprocess(
    command: list[str],
    cwd: Path | str | None = None,
    capture_output: bool = False,
    text: bool = False,
    env: Mapping[str, str] | None = None,
) -> str | subprocess.CompletedProcess:
    """Backward compatibility wrapper for existing code.

    This maintains the old interface while using the new implementation.
    """
    logger.info(f"Running command: {' '.join(command)}")

    result = run_command(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        check=True,
        log_command=False,  # Already logged above
    )

    # Match old behavior
    if capture_output and text:
        return result
    return result.stdout.strip()
