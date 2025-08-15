"""
PSPF 2025 Bundle Executor
Handles process execution with environment setup and variable substitution.
"""

import os
import subprocess
from pathlib import Path
from typing import Any

from pyvider.telemetry import logger


class BundleExecutor:
    """Executes PSPF bundles with proper environment and substitution."""
    
    def __init__(self, metadata: dict, workenv_dir: Path):
        """Initialize executor with metadata and work environment.
        
        Args:
            metadata: Bundle metadata containing execution configuration
            workenv_dir: Path to the extracted work environment
        """
        self.metadata = metadata
        self.workenv_dir = workenv_dir
        self.package_name = metadata.get('package', {}).get('name', 'unknown')
        self.package_version = metadata.get('package', {}).get('version', '')
        self.execution_config = metadata.get('execution', {})
    
    def prepare_command(self, base_command: str, args: list[str] | None = None) -> str:
        """Prepare command with substitutions and arguments.
        
        Args:
            base_command: Command template with placeholders
            args: Additional arguments to append
            
        Returns:
            str: Prepared command ready for execution
        """
        # Basic substitutions
        command = base_command.replace('{workenv}', str(self.workenv_dir))
        command = command.replace('{package_name}', self.package_name)
        command = command.replace('{version}', self.package_version)
        
        # Slot substitutions
        command = self._substitute_slots(command)
        
        # Primary slot substitution
        command = self._substitute_primary(command)
        
        # Append user arguments
        if args:
            arg_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in args)
            command = f"{command} {arg_str}"
        
        return command
    
    def _substitute_slots(self, command: str) -> str:
        """Substitute {slot:N} references in command.
        
        Args:
            command: Command with potential slot references
            
        Returns:
            str: Command with slot references substituted
        """
        slots = self.metadata.get('slots', [])
        
        for i, slot in enumerate(slots):
            placeholder = f"{{slot:{i}}}"
            if placeholder in command:
                slot_name = slot['name']
                # For tarballs, the content is extracted directly to workenv
                if slot_name.endswith('.tar.gz') or slot_name.endswith('.tgz'):
                    slot_path = self.workenv_dir
                else:
                    slot_path = self.workenv_dir / slot_name
                command = command.replace(placeholder, str(slot_path))
                logger.trace(f"🔄 Substituted {placeholder} -> {slot_path}")
        
        return command
    
    def _substitute_primary(self, command: str) -> str:
        """Substitute {primary} reference in command.
        
        Args:
            command: Command with potential {primary} reference
            
        Returns:
            str: Command with primary slot substituted
        """
        if '{primary}' not in command:
            return command
        
        primary_slot = self.execution_config.get('primary_slot', 0)
        slots = self.metadata.get('slots', [])
        
        if primary_slot < len(slots):
            primary_path = self.workenv_dir / slots[primary_slot]['name']
            command = command.replace('{primary}', str(primary_path))
            logger.trace(f"🔄 Substituted {{primary}} -> {primary_path}")
        else:
            logger.warning(f"⚠️ Primary slot {primary_slot} not found")
        
        return command
    
    def prepare_environment(self) -> dict[str, str]:
        """Prepare environment variables for execution.
        
        Returns:
            dict: Environment variables including FLAVOR_* vars
        """
        env = os.environ.copy()
        
        # Standard FLAVOR environment variables
        env['FLAVOR_WORKENV'] = str(self.workenv_dir)
        env['FLAVOR_PACKAGE'] = self.package_name
        env['FLAVOR_VERSION'] = self.package_version
        
        # Custom environment variables from metadata
        if 'environment' in self.execution_config:
            for key, value in self.execution_config['environment'].items():
                value = str(value).replace('{workenv}', str(self.workenv_dir))
                value = value.replace('{package_name}', self.package_name)
                value = value.replace('{version}', self.package_version)
                env[key] = value
                logger.trace(f"🌍 Set {key}={value}")
        
        return env
    
    def execute(self, args: list[str] | None = None) -> dict[str, Any]:
        """Execute the bundle command.
        
        Args:
            args: Command line arguments to pass to the executable
            
        Returns:
            dict: Execution result with exit_code, stdout, stderr, etc.
        """
        # Get base command
        command = self.execution_config.get('command', '')
        if not command:
            raise ValueError("No command specified in execution configuration")
        
        # Prepare command with substitutions
        command = self.prepare_command(command, args)
        
        # Prepare environment
        env = self.prepare_environment()
        
        logger.info(f"🏃 Executing: {command}")
        logger.debug(f"📁 Working directory: {self.workenv_dir}")
        
        try:
            # Execute the command
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.workenv_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for completion and get output
            stdout, stderr = process.communicate()
            
            # Log result
            if process.returncode == 0:
                logger.info(f"✅ Execution completed successfully (exit code: 0)")
            else:
                logger.warning(f"⚠️ Execution completed with exit code: {process.returncode}")
                if stderr:
                    logger.debug(f"📝 stderr: {stderr[:500]}")  # Log first 500 chars
            
            return {
                "exit_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "executed": True,
                "command": command,
                "args": args or [],
                "pid": process.pid,
                "working_directory": str(self.workenv_dir),
                "error": None if process.returncode == 0 else f"Process exited with code {process.returncode}"
            }
            
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "executed": False,
                "command": command,
                "args": args or [],
                "pid": None,
                "working_directory": str(self.workenv_dir),
                "error": str(e)
            }