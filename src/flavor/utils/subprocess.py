#!/usr/bin/env python3
"""Subprocess utilities for Flavor - thin wrapper for BuildError compatibility.

For new code, prefer importing directly from provide.foundation.process.
"""

import os
from pathlib import Path
import subprocess

from provide.foundation.process import run, run_simple, ProcessError
from flavor.exceptions import BuildError


def run_command(
    command: list[str],
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    capture_output: bool = True,
    check: bool = True,
    timeout: int | None = None,
    log_command: bool = True,
) -> subprocess.CompletedProcess:
    """Run command with BuildError on failure."""
    # Add NO_COVERAGE for build commands
    build_env = dict(env) if env is not None else os.environ.copy()
    build_env["NO_COVERAGE"] = "1"
    
    try:
        result = run(command, cwd=cwd, env=build_env, capture_output=capture_output, 
                    check=check, timeout=timeout)
        # Convert to stdlib CompletedProcess
        return subprocess.CompletedProcess(
            args=result.args,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except ProcessError as e:
        raise BuildError(str(e)) from e


def run_command_simple(command: list[str], cwd: Path | str | None = None) -> str:
    """Run command and return stdout, raising BuildError on failure."""
    try:
        # Add NO_COVERAGE
        env = os.environ.copy()
        env["NO_COVERAGE"] = "1"
        return run_simple(command, cwd=cwd, env=env)
    except ProcessError as e:
        raise BuildError(str(e)) from e