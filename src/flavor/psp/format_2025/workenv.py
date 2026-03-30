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
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flavor.psp.format_2025.reader import PSPFReader

from provide.foundation import logger
from provide.foundation.file import atomic_write_text
from provide.foundation.file.directory import ensure_dir, ensure_parent_dir, safe_rmtree
from provide.foundation.process import run

from flavor.config.defaults import DEFAULT_EXECUTABLE_PERMS
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
        from flavor.cache import get_cache_dir

        workenv_base = get_cache_dir()
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

            # Substitute placeholders (use POSIX paths; Path() handles forward slashes on Windows)
            check_file = check_file.replace("{workenv}", workenv_dir.as_posix())
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
                    if slot_path.resolve() == workenv_dir.resolve():
                        logger.warning(
                            "⚠️ Refusing to remove workenv root during init-slot cleanup",
                            slot_index=slot_idx,
                            slot_path=str(slot_path),
                        )
                        continue
                    if slot_path.exists():
                        if slot_path.is_dir():
                            safe_rmtree(slot_path)
                        else:
                            slot_path.unlink(missing_ok=True)
                elif lifecycle == "temporary":
                    # 'temporary' lifecycle: mark for cleanup after session
                    logger.debug(f"🕐 Slot {slot_idx} marked as 'temporary' - will be cleaned after session")

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

        if logger.is_debug_enabled():
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
                    self._run_enumerate_execute_command(cmd, workenv_dir, metadata, setup_env)
                elif cmd_type == "chmod":
                    self._run_chmod_command(cmd, workenv_dir, metadata)
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
        self, cmd: dict[str, Any], workenv_dir: Path, metadata: dict[str, Any], env: dict[str, str]
    ) -> None:
        """Handle file enumeration and execution command.

        Args:
            cmd: Command dictionary
            workenv_dir: Work environment directory
            metadata: Package metadata
            env: Isolated environment dictionary
        """
        enumerate_config = cmd.get("enumerate")
        if not isinstance(enumerate_config, dict):
            raise RuntimeError("enumerate_and_execute setup command requires an 'enumerate' object")

        enum_path = self._substitute_placeholders(
            enumerate_config.get("path", "{workenv}"), workenv_dir, metadata
        )
        pattern = enumerate_config.get("pattern", "*")
        command_template = self._substitute_placeholders(cmd.get("command", ""), workenv_dir, metadata)

        # Find matching files
        matches = sorted(Path(enum_path).glob(pattern))

        logger.debug(f"📂 Found {len(matches)} files matching {pattern} in {enum_path}")

        for file_path in matches:
            # Use POSIX paths to avoid shlex.split mangling backslashes on Windows
            if "{file}" in command_template:
                args = shlex.split(command_template.replace("{file}", file_path.as_posix()))
            else:
                args = [*shlex.split(command_template), file_path.as_posix()]

            try:
                run(
                    args,
                    cwd=workenv_dir,
                    capture_output=True,
                    check=True,
                    env=env,
                )
            except Exception as e:
                logger.error(f"❌ Command failed for {file_path}: {' '.join(args)}")
                logger.error(f"❌ Error: {e}")
                raise RuntimeError(f"Enumerated setup command failed for {file_path}: {e}") from e

    def _run_chmod_command(self, cmd: dict[str, Any], workenv_dir: Path, metadata: dict[str, Any]) -> None:
        """Apply metadata-driven permissions to matching files."""
        path_pattern = self._substitute_placeholders(cmd.get("path", ""), workenv_dir, metadata)
        mode_str = str(cmd.get("mode", format(DEFAULT_EXECUTABLE_PERMS, "o")))

        try:
            mode = int(mode_str, 8)
        except ValueError as e:
            raise RuntimeError(f"Invalid chmod mode '{mode_str}'") from e

        path_pattern_path = Path(path_pattern)
        matched_paths = sorted(path_pattern_path.parent.glob(path_pattern_path.name))
        if not matched_paths:
            logger.debug(f"⚠️ chmod matched no files for pattern: {path_pattern}")
            return

        for matched_path in matched_paths:
            if not matched_path.exists() or matched_path.is_dir():
                continue
            try:
                matched_path.chmod(mode)
            except OSError as e:
                raise RuntimeError(f"Failed to chmod {matched_path}: {e}") from e

    def _substitute_placeholders(self, text: str, workenv_dir: Path, metadata: dict[str, Any]) -> str:
        """Substitute common placeholders in text.

        Args:
            text: Text with placeholders
            workenv_dir: Work environment directory
            metadata: Package metadata

        Returns:
            Text with placeholders substituted
        """
        is_win = sys.platform == "win32"
        bin_dir = "Scripts" if is_win else "bin"
        python_exe = "python.exe" if is_win else "python3"
        python_bin = (workenv_dir / bin_dir / python_exe).as_posix()

        # Use POSIX (forward-slash) paths: shlex.split treats backslashes as
        # escape characters, so OS-native Windows paths get silently mangled.
        text = text.replace("{workenv}", workenv_dir.as_posix())
        text = text.replace("{package_name}", metadata["package"]["name"])
        text = text.replace("{version}", metadata["package"]["version"])
        text = text.replace("{bin}", bin_dir)
        text = text.replace("{python}", python_exe)
        text = text.replace("{python_bin}", python_bin)
        return text

    def _normalize_slot_target(self, slot_target: str) -> str:
        """Normalize slot target metadata to a path relative to the workenv."""
        if slot_target == "{workenv}":
            return "{workenv}"
        if slot_target.startswith("{workenv}/"):
            return slot_target.removeprefix("{workenv}/")
        return slot_target

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
                slot_name = self._normalize_slot_target(slot.get("target", slot.get("id", f"slot_{i}")))
                slot_path = workenv_dir if slot_name in {".", "{workenv}"} else workenv_dir / slot_name
                command = command.replace(placeholder, str(slot_path))
                logger.debug(f"🔄 Substituted {placeholder} -> {slot_path}")

        return command


# 🌶️📦🔚
