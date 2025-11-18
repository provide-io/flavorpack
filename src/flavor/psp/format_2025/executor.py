#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF 2025 Bundle Executor
Handles process execution with environment setup and variable substitution.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
from typing import Any

from provide.foundation import logger
from provide.foundation.process import run

from flavor.psp.format_2025.environment import apply_environment_layers


class BundleExecutor:
    """Executes PSPF bundles with proper environment and substitution."""

    def __init__(self, metadata: dict[str, Any], workenv_dir: Path) -> None:
        """Initialize executor with metadata and work environment.

        Args:
            metadata: Bundle metadata containing execution configuration
            workenv_dir: Path to the extracted work environment
        """
        self.metadata = metadata
        self.workenv_dir = workenv_dir
        self.package_name = metadata.get("package", {}).get("name", "unknown")
        self.package_version = metadata.get("package", {}).get("version", "")
        self.execution_config = metadata.get("execution", {})

    def prepare_command(self, base_command: str, args: list[str] | None = None) -> str:
        """Prepare command with substitutions and arguments.

        Args:
            base_command: Command template with placeholders
            args: Additional arguments to append

        Returns:
            str: Prepared command ready for execution
        """
        logger.debug(f"🔍 prepare_command input: {base_command}")

        # Primary slot substitution
        command = self._substitute_primary(base_command)
        logger.debug(f"🔍 after primary substitution: {command}")

        # Slot substitution - {slot:N} references
        command = self._substitute_slots(command)
        logger.debug(f"🔍 after slot substitution: {command}")

        # Basic substitutions - only {workenv}, {package_name}, and {version} as per spec
        command = command.replace("{workenv}", str(self.workenv_dir))
        command = command.replace("{package_name}", self.package_name)
        command = command.replace("{version}", self.package_version)
        logger.debug(f"🔍 after basic substitutions: {command}")

        # Append user arguments
        if args:
            arg_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in args)
            command = f"{command} {arg_str}"

        return command

    def _substitute_primary(self, command: str) -> str:
        """Substitute {primary} reference in command.

        Args:
            command: Command with potential {primary} reference

        Returns:
            str: Command with primary slot substituted
        """
        if "{primary}" not in command:
            return command

        primary_slot = self.execution_config.get("primary_slot", 0)
        slots = self.metadata.get("slots", [])

        if primary_slot < len(slots):
            # Use "target" field for actual file path, fallback to "id" or "name"
            slot_name = slots[primary_slot].get(
                "target",
                slots[primary_slot].get("id", slots[primary_slot].get("name", f"slot_{primary_slot}")),
            )
            # For tarballs, use {workenv} placeholder
            if slot_name.endswith(".tar.gz") or slot_name.endswith(".tgz"):
                primary_path = "{workenv}"
            else:
                # For non-tarballs, use relative path
                primary_path = slot_name
            command = command.replace("{primary}", str(primary_path))
            logger.trace(f"🔄 Substituted {{primary}} -> {primary_path}")
        else:
            logger.warning(f"⚠️ Primary slot {primary_slot} not found")

        return command

    def _substitute_slots(self, command: str) -> str:
        """Substitute {slot:N} references in command.

        Args:
            command: Command with potential {slot:N} references

        Returns:
            str: Command with slot references substituted
        """

        def replace_slot(match: re.Match[str]) -> str:
            slot_idx = int(match.group(1))
            slots = self.metadata.get("slots", [])

            if slot_idx < len(slots):
                # Use "target" field for actual file path, fallback to "id" or "name"
                slot_name = slots[slot_idx].get(
                    "target",
                    slots[slot_idx].get("id", slots[slot_idx].get("name", f"slot_{slot_idx}")),
                )
                # Build the path to the extracted slot
                slot_path = self.workenv_dir / slot_name
                return str(slot_path)
            else:
                logger.warning(f"⚠️ Slot {slot_idx} not found")
                return match.group(0)  # Keep original if not found

        # Replace all {slot:N} patterns
        return re.sub(r"\{slot:(\d+)\}", replace_slot, command)

    def prepare_environment(self) -> dict[str, str]:
        """Prepare environment variables for execution.

        Applies environment isolation layers:
        1. Runtime security layer (unset/pass/map/set from metadata)
        2. Workenv layer (FLAVOR_* variables)
        3. Execution layer (custom variables from metadata)
        4. Platform layer (automatic, added by apply_environment_layers)

        Returns:
            dict: Isolated environment variables for execution
        """
        # Start with current environment
        base_env = dict(os.environ)

        # Extract runtime environment config from metadata
        runtime_env = self.metadata.get("runtime", {}).get("env", {})

        # Prepare workenv-specific environment variables
        workenv_env = {
            "FLAVOR_WORKENV": str(self.workenv_dir),
            "FLAVOR_PACKAGE": self.package_name,
            "FLAVOR_VERSION": self.package_version,
        }

        # Prepare execution-specific environment variables from metadata
        execution_env = {}
        if "env" in self.execution_config:
            for key, value in self.execution_config["env"].items():
                value = str(value).replace("{workenv}", str(self.workenv_dir))
                value = value.replace("{package_name}", self.package_name)
                value = value.replace("{version}", self.package_version)
                execution_env[key] = value

        # Apply all environment layers with proper isolation
        env = apply_environment_layers(
            base_env=base_env,
            runtime_env=runtime_env,
            workenv_env=workenv_env,
            execution_env=execution_env,
        )

        logger.debug(f"🧹 Prepared isolated execution environment ({len(env)} vars)")
        return env

    def execute(self, args: list[str] | None = None) -> dict[str, Any]:
        """Execute the bundle command.

        Args:
            args: Command line arguments to pass to the executable

        Returns:
            dict: Execution result with exit_code, stdout, stderr, etc.
        """
        # Get base command
        command = self.execution_config.get("command", "")
        if not command:
            raise ValueError("No command specified in execution configuration")

        # Prepare command with substitutions
        command = self.prepare_command(command, args)

        # Prepare environment
        env = self.prepare_environment()

        logger.info(f"🏃 Executing: {command}")

        try:
            # Parse command into arguments (safely handles quotes and spaces)
            command_args = shlex.split(command)

            # Execute the command using shared utility (no shell=True for security)
            result = run(
                command_args,
                cwd=self.workenv_dir,
                env=env,
                capture_output=True,
                check=False,  # We want to handle the exit code ourselves
            )

            # Log result
            if result.returncode == 0:
                pass
            else:
                logger.warning(f"⚠️ Execution completed with exit code: {result.returncode}")
                if result.stderr:
                    logger.debug(f"📝 stderr: {result.stderr[:500]}")  # Log first 500 chars

            crashed = result.returncode < 0  # Negative return codes often indicate a crash due to a signal
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "executed": True,
                "command": command,
                "args": args or [],  # Return the original user args, not the parsed command
                "pid": os.getpid(),  # Current process PID since we don't have access to subprocess PID
                "working_directory": str(self.workenv_dir),
                "error": None if result.returncode == 0 else f"Process exited with code {result.returncode}",
                "crashed": crashed,
            }

        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "executed": False,
                "command": command,
                "args": args or [],  # Return the original user args
                "pid": None,
                "working_directory": str(self.workenv_dir),
                "error": str(e),
                "returncode": 1,  # Add returncode for consistency
            }


# 🌶️📦🔚
