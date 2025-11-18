#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF Work Environment Management

Handles work environment setup, caching, lifecycle management, and setup commands."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flavor.psp.format_2025.reader import PSPFReader

from provide.foundation import logger
from provide.foundation.file import atomic_write_text
from provide.foundation.file.directory import ensure_dir, ensure_parent_dir, safe_rmtree
from provide.foundation.process import run

from flavor.psp.format_2025.environment import apply_environment_layers


class WorkEnvManager:
    """Manages PSPF work environments."""

    def __init__(self, reader: PSPFReader) -> None:
        """Initialize with reference to PSPFReader."""
        self.reader = reader

    def setup_workenv(self, bundle_path: Path) -> Path:
        """Setup work environment for bundle execution.

        Creates a work environment directory, extracts slots, and runs setup commands.
        Uses cache validation to avoid re-extraction when possible.
        Handles lifecycle-based slot cleanup (e.g., 'init' slots removed after setup).

        Args:
            bundle_path: Path to the bundle

        Returns:
            Path: Path to the work environment directory
        """

        # NOTE: This matches Go's work environment setup logic
        metadata = self.reader.read_metadata()
        package_name = metadata["package"]["name"]
        package_version = metadata["package"]["version"]

        # Create work environment directory
        workenv_base = Path.home() / ".cache" / "flavor" / "workenv"
        workenv_dir = workenv_base / f"{package_name}_{package_version}"
        ensure_dir(workenv_dir)

        # Check cache validity
        cache_valid = self._check_cache_validity(metadata, workenv_dir, package_version)

        # Extract slots if cache is invalid
        if not cache_valid:
            logger.info("📤 Extracting slots (cache invalid)")
            # Extract all slots by iterating through slot count
            extracted_slots: dict[int, Path] = {}
            assert self.reader._index is not None
            slot_count = self.reader._index.slot_count
            for slot_idx in range(slot_count):
                slot_path = self.reader.extract_slot(slot_idx, workenv_dir)
                extracted_slots[slot_idx] = slot_path

            # Run setup commands
            if "setup_commands" in metadata:
                self._run_setup_commands(metadata["setup_commands"], workenv_dir, metadata)

            # Handle lifecycle-based cleanup
            self._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)
        else:
            pass

        return workenv_dir

    def _check_cache_validity(self, metadata: dict[str, Any], workenv_dir: Path, package_version: str) -> bool:
        """Check if work environment cache is valid.

        Args:
            metadata: Package metadata
            workenv_dir: Work environment directory
            package_version: Package version

        Returns:
            True if cache is valid
        """
        cache_valid = False
        if "cache_validation" in metadata:
            cache_validation = metadata["cache_validation"]
            check_file = cache_validation.get("check_file", "")
            expected_content = cache_validation.get("expected_content", "")

            # Substitute placeholders
            check_file = check_file.replace("{workenv}", str(workenv_dir))
            check_file = check_file.replace("{version}", package_version)

            check_path = Path(check_file)
            logger.debug(f"🔍 Checking cache validity: {check_path}")

            if check_path.exists():
                actual_content = check_path.read_text().strip()
                if actual_content == expected_content.replace("{version}", package_version):
                    cache_valid = True
                else:
                    logger.debug(
                        f"❌ Cache content mismatch: expected '{expected_content}', got '{actual_content}'"
                    )
            else:
                logger.debug(f"❌ Cache validation file not found: {check_path}")

        return cache_valid

    def _cleanup_lifecycle_slots(
        self, workenv_dir: Path, metadata: dict[str, Any], extracted_slots: dict[int, Path]
    ) -> None:
        """Clean up slots based on their lifecycle after setup.

        Args:
            workenv_dir: Work environment directory
            metadata: Package metadata
            extracted_slots: Mapping of slot index to extracted paths
        """
        # Get slot metadata
        slots = metadata.get("slots", [])

        for slot_idx, slot_path in extracted_slots.items():
            if slot_idx < len(slots):
                slot_meta = slots[slot_idx]
                lifecycle = slot_meta.get("lifecycle", "runtime")

                # Handle different lifecycle values
                if lifecycle == "init":
                    # 'init' lifecycle: remove after initialization
                    logger.debug(f"🗑️ Removing 'init' lifecycle slot {slot_idx}: {slot_path}")
                    if slot_path.exists():
                        if slot_path.is_dir():
                            safe_rmtree(slot_path)
                        else:
                            slot_path.unlink(missing_ok=True)
                elif lifecycle == "temp":
                    # 'temp' lifecycle: mark for cleanup after session
                    logger.debug(f"🕐 Slot {slot_idx} marked as 'temp' - will be cleaned after session")

    def _prepare_setup_environment(self, workenv_dir: Path, runtime_env: dict[str, Any]) -> dict[str, str]:
        """Prepare isolated environment for setup command execution.

        Applies environment isolation to prevent host venv interference with PSPF setup.

        Args:
            workenv_dir: Work environment directory
            runtime_env: Runtime environment configuration from metadata

        Returns:
            Filtered environment dictionary for setup commands
        """
        # Start with current environment
        base_env = dict(os.environ)

        # Prepare workenv-specific environment variables
        workenv_env = {
            "PATH": f"{workenv_dir}/bin:{base_env.get('PATH', '')}",
        }

        # Apply environment layers with isolation
        isolated_env = apply_environment_layers(
            base_env=base_env,
            runtime_env=runtime_env,
            workenv_env=workenv_env,
        )

        logger.debug(f"🧹 Prepared isolated environment for setup commands ({len(isolated_env)} vars)")
        return isolated_env

    def _run_setup_commands(
        self, setup_commands: list[Any], workenv_dir: Path, metadata: dict[str, Any]
    ) -> None:
        """Run setup commands for work environment.

        Args:
            setup_commands: List of setup commands to run
            workenv_dir: Work environment directory
            metadata: Package metadata for substitutions
        """

        # NOTE: Setup command execution matches Go's implementation
        # Extract runtime environment config from metadata and prepare isolated environment
        runtime_env = metadata.get("runtime", {}).get("env", {})
        setup_env = self._prepare_setup_environment(workenv_dir, runtime_env)

        for _i, cmd in enumerate(setup_commands):
            pass

            if isinstance(cmd, dict):
                cmd_type = cmd.get("type", "execute")

                if cmd_type == "write_file":
                    self._run_write_file_command(cmd, workenv_dir, metadata)
                elif cmd_type == "execute":
                    self._run_execute_command(cmd, workenv_dir, metadata, setup_env)
                elif cmd_type == "enumerate_and_execute":
                    self._run_enumerate_execute_command(cmd, workenv_dir, setup_env)
                else:
                    logger.warning(f"⚠️ Unknown setup command type: {cmd_type}")
            else:
                logger.warning("⚠️ String setup commands not supported")

    def _run_write_file_command(
        self, cmd: dict[str, Any], workenv_dir: Path, metadata: dict[str, Any]
    ) -> None:
        """Handle file writing command.

        Args:
            cmd: Command dictionary
            workenv_dir: Work environment directory
            metadata: Package metadata
        """
        path = cmd.get("path", "")
        content = cmd.get("content", "")

        # Substitute placeholders
        path = self._substitute_placeholders(path, workenv_dir, metadata)
        content = self._substitute_placeholders(content, workenv_dir, metadata)

        file_path = Path(path)

        # Handle different path scenarios
        if file_path.exists() and file_path.is_dir():
            # Path exists and is a directory - can't write to it directly
            # Write to a file with the same base name inside the directory
            file_path = file_path / ".extracted"

        # Ensure parent directory exists and write file (atomic for safety)
        ensure_parent_dir(file_path)
        atomic_write_text(file_path, content)

    def _run_execute_command(
        self, cmd: dict[str, Any], workenv_dir: Path, metadata: dict[str, Any], env: dict[str, str]
    ) -> None:
        """Handle command execution.

        Args:
            cmd: Command dictionary
            workenv_dir: Work environment directory
            metadata: Package metadata
            env: Isolated environment dictionary
        """
        command = cmd.get("command", "")

        # Substitute placeholders
        command = self._substitute_placeholders(command, workenv_dir, metadata)

        # Parse command safely to avoid shell injection
        args = shlex.split(command)

        # Use the shared run utility with isolated environment
        try:
            run(
                args,
                cwd=workenv_dir,
                capture_output=True,
                check=True,
                env=env,
            )
        except Exception as e:
            logger.error(f"❌ Command failed: {command}")
            logger.error(f"❌ Error details: {e!s}")
            raise RuntimeError(f"Setup command failed: {command}. Error: {e!s}") from e

    def _run_enumerate_execute_command(
        self, cmd: dict[str, Any], workenv_dir: Path, env: dict[str, str]
    ) -> None:
        """Handle file enumeration and execution command.

        Args:
            cmd: Command dictionary
            workenv_dir: Work environment directory
            env: Isolated environment dictionary
        """
        pattern = cmd.get("pattern", "*")
        command_template = cmd.get("command", "")

        # Find matching files
        matches = list(workenv_dir.glob(pattern))

        logger.debug(f"📂 Found {len(matches)} files matching {pattern}")

        for file_path in matches:
            # Substitute file path in command
            command = command_template.replace("{file}", str(file_path))
            command = command.replace("{workenv}", str(workenv_dir))

            # Parse and execute command using shared utility with isolated environment
            args = shlex.split(command)

            try:
                run(
                    args,
                    cwd=workenv_dir,
                    capture_output=True,
                    check=True,
                    env=env,
                )
            except Exception as e:
                logger.error(f"❌ Command failed for {file_path}: {command}")
                logger.error(f"❌ Error: {e}")
                # Continue with other files instead of failing

    def _substitute_placeholders(self, text: str, workenv_dir: Path, metadata: dict[str, Any]) -> str:
        """Substitute common placeholders in text.

        Args:
            text: Text with placeholders
            workenv_dir: Work environment directory
            metadata: Package metadata

        Returns:
            Text with placeholders substituted
        """
        text = text.replace("{workenv}", str(workenv_dir))
        text = text.replace("{package_name}", metadata["package"]["name"])
        text = text.replace("{version}", metadata["package"]["version"])
        return text

    def substitute_slot_references(self, command: str, workenv_dir: Path) -> str:
        """Substitute {slot:N} references in command.

        Args:
            command: Command with potential slot references
            workenv_dir: Work environment directory

        Returns:
            str: Command with slot references substituted
        """
        # NOTE: Slot substitution logic matches Go implementation
        metadata = self.reader.read_metadata()

        for i, slot in enumerate(metadata.get("slots", [])):
            placeholder = f"{{slot:{i}}}"
            if placeholder in command:
                slot_name = slot.get("id", f"slot_{i}")
                slot_path = workenv_dir / slot_name
                command = command.replace(placeholder, str(slot_path))
                logger.debug(f"🔄 Substituted {placeholder} -> {slot_path}")

        return command


# 🌶️📦🔚
