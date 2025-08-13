"""
PSPF 2025 Bundle Launcher

Handles bundle execution, slot extraction, and work environment setup.
"""

import io
import os
import struct
import subprocess
import tarfile
import zlib
from pathlib import Path

from pyvider.telemetry import logger

from flavor.psp.format_2025.reader import PSPFReader


class PSPFLauncher(PSPFReader):
    """Launch PSPF bundles."""

    def __init__(self, bundle_path: Path | None = None):
        super().__init__(bundle_path)
        self.bundle_path = bundle_path
        self.cache_dir = Path.home() / ".cache" / "pspf"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def read_slot_table(self) -> list[dict]:
        """Read the slot table from the bundle.
        
        Returns:
            list: List of slot entries, each containing:
                - offset: Start position of slot data
                - size: Size of uncompressed data
                - checksum: Adler32 checksum
                - encoding: 0=none, 1=gzip, 2=reserved
                - purpose: 0=payload, 1=runtime, 2=tool
                - lifecycle: 0=persistent, 1=volatile, 2=temporary, 3=install
        """
        # NOTE: This logic is unique to Python launcher - Go/Rust have their own implementations
        index = self.read_index()
        
        slot_entries = []
        
        with open(self.bundle_path, 'rb') as f:
            # Seek to slot table
            f.seek(index.slot_table_offset)
            
            # Read each 24-byte slot entry
            for i in range(index.slot_count):
                entry_data = f.read(24)
                if len(entry_data) != 24:
                    raise ValueError(f"Invalid slot table entry {i}: expected 24 bytes, got {len(entry_data)}")
                
                # Parse the 24-byte structure:
                # NOTE: This format must match Go/Rust implementations
                # offset(8), size(8), checksum(4), encoding(1), purpose(1), lifecycle(1), reserved(1)
                offset, size, checksum, encoding, purpose, lifecycle, reserved = struct.unpack(
                    '<QQIBBBB', entry_data
                )
                
                slot_entries.append({
                    'index': i,
                    'offset': offset,
                    'size': size,
                    'checksum': checksum,
                    'encoding': encoding,
                    'purpose': purpose,
                    'lifecycle': lifecycle
                })
        
        return slot_entries
    
    def extract_all_slots(self, workenv_dir: Path) -> dict[int, Path]:
        """Extract all slots to the work environment.
        
        Args:
            workenv_dir: Directory to extract slots into
            
        Returns:
            dict: Mapping of slot index to extracted path
        """
        logger.debug(f"📦 Extracting all slots to {workenv_dir}")
        
        # NOTE: This parallels Go's ExtractAllSlots logic
        slot_table = self.read_slot_table()
        extracted_paths = {}
        
        logger.info(f"📤 Extracting {len(slot_table)} slots")
        for slot_entry in slot_table:
            slot_idx = slot_entry['index']
            logger.debug(f"🔄 Extracting slot {slot_idx}")
            slot_path = self.extract_slot(slot_idx, workenv_dir)
            extracted_paths[slot_idx] = slot_path
        
        logger.info(f"✅ Extracted all {len(extracted_paths)} slots")
        return extracted_paths

    def extract_slot(self, slot_index: int, workenv_dir: Path, verify_checksum: bool = False) -> Path:
        """Extract a single slot.
        
        Args:
            slot_index: Index of the slot to extract
            workenv_dir: Directory to extract into
            verify_checksum: Whether to verify checksum after extraction
            
        Returns:
            Path: Path to the extracted slot content
        """
        logger.debug(f"📦 Extracting slot {slot_index} to {workenv_dir}")
        
        # NOTE: This logic is unique to Python launcher - Go/Rust have their own implementations
        slot_table = self.read_slot_table()
        
        if slot_index < 0 or slot_index >= len(slot_table):
            logger.error(f"❌ Invalid slot index: {slot_index} (have {len(slot_table)} slots)")
            raise ValueError(f"Invalid slot index: {slot_index}")
        
        slot_entry = slot_table[slot_index]
        logger.debug(f"📍 Slot {slot_index}: offset={slot_entry['offset']}, size={slot_entry['size']}, encoding={slot_entry['encoding']}")
        
        # Read slot data from bundle
        with open(self.bundle_path, 'rb') as f:
            f.seek(slot_entry['offset'])
            slot_data = f.read(slot_entry['size'])
            logger.debug(f"📖 Read {len(slot_data)} bytes from slot {slot_index}")
        
        # Verify checksum if requested (checksum is of the data AS STORED IN THE FILE)
        if verify_checksum:
            # NOTE: Use adler32 to match Go/Rust implementations
            # Checksum is of the slot data as it exists in the file (compressed or not)
            actual_checksum = zlib.adler32(slot_data)
            if actual_checksum != slot_entry['checksum']:
                logger.error(f"❌ Checksum mismatch for slot {slot_index}: expected {slot_entry['checksum']}, got {actual_checksum}")
                raise ValueError(f"Checksum mismatch for slot {slot_index}")
            logger.debug(f"✅ Checksum verified for slot {slot_index}")
        
        # NOTE: Decoding logic must match Go/Rust implementations
        # Decode if needed
        if slot_entry['encoding'] == 1:  # gzip
            logger.debug(f"🗜️ Decompressing slot {slot_index} with gzip")
            data = zlib.decompress(slot_data)
            logger.debug(f"✅ Decompressed to {len(data)} bytes")
        elif slot_entry['encoding'] == 2:  # reserved for future encoding methods
            logger.error(f"❌ Encoding method 2 is reserved for future use")
            raise ValueError(f"Unsupported encoding method: {slot_entry['encoding']}")
        else:  # none
            logger.debug(f"📄 Slot {slot_index} is unencoded (raw)")
            data = slot_data
        
        # Get slot name from metadata
        metadata = self.read_metadata()
        slot_name = f"slot_{slot_index}"
        if 'slots' in metadata and slot_index < len(metadata['slots']):
            slot_meta = metadata['slots'][slot_index]
            slot_name = slot_meta.get('name', slot_name)
        logger.debug(f"📝 Slot {slot_index} name: {slot_name}")
        
        # NOTE: Tarball extraction logic matches Go's tar extraction
        # Check if it's a tarball that needs extraction (by content, not just name)
        is_tarball = False
        try:
            # Try to open as tarball
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as tar:
                # If we can open it, it's a tarball
                is_tarball = True
        except:
            pass
        
        if is_tarball or slot_name.endswith('.tar.gz') or slot_name.endswith('.tgz'):
            logger.debug(f"📤 Extracting tarball {slot_name} to {workenv_dir}")
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as tar:
                tar.extractall(path=workenv_dir)
            logger.debug(f"✅ Extracted tarball contents to {workenv_dir}")
            
            # Return the base directory
            return workenv_dir
        else:
            # Write single file
            output_path = workenv_dir / slot_name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(data)
            logger.debug(f"✅ Wrote {len(data)} bytes to {output_path}")
            
            return output_path

    def setup_workenv(self) -> Path:
        """Setup work environment for bundle execution.
        
        Creates a work environment directory, extracts slots, and runs setup commands.
        Uses cache validation to avoid re-extraction when possible.
        
        Returns:
            Path: Path to the work environment directory
        """
        logger.debug(f"🔧 Setting up work environment for {self.bundle_path}")
        
        # NOTE: This matches Go's work environment setup logic
        metadata = self.read_metadata()
        package_name = metadata['package']['name']
        package_version = metadata['package']['version']
        
        # Create work environment directory
        workenv_base = Path.home() / ".cache" / "pspf" / "workenv"
        workenv_dir = workenv_base / f"{package_name}_{package_version}"
        workenv_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Work environment: {workenv_dir}")
        
        # Check cache validity
        cache_valid = False
        if 'cache_validation' in metadata:
            cache_validation = metadata['cache_validation']
            check_file = cache_validation.get('check_file', '')
            expected_content = cache_validation.get('expected_content', '')
            
            # Substitute placeholders
            check_file = check_file.replace('{workenv}', str(workenv_dir))
            check_file = check_file.replace('{version}', package_version)
            
            check_path = Path(check_file)
            logger.debug(f"🔍 Checking cache validity: {check_path}")
            
            if check_path.exists():
                actual_content = check_path.read_text().strip()
                if actual_content == expected_content.replace('{version}', package_version):
                    cache_valid = True
                    logger.debug(f"✅ Cache is valid")
                else:
                    logger.debug(f"❌ Cache content mismatch: expected '{expected_content}', got '{actual_content}'")
            else:
                logger.debug(f"❌ Cache validation file not found: {check_path}")
        
        # Extract slots if cache is invalid
        if not cache_valid:
            logger.info(f"📤 Extracting slots (cache invalid)")
            self.extract_all_slots(workenv_dir)
            
            # Run setup commands
            if 'setup_commands' in metadata:
                self._run_setup_commands(metadata['setup_commands'], workenv_dir, metadata)
        else:
            logger.info(f"✅ Using cached work environment")
        
        return workenv_dir
    
    def _run_setup_commands(self, setup_commands: list, workenv_dir: Path, metadata: dict) -> None:
        """Run setup commands for work environment.
        
        Args:
            setup_commands: List of setup commands to run
            workenv_dir: Work environment directory
            metadata: Package metadata for substitutions
        """
        logger.info(f"🔧 Running {len(setup_commands)} setup commands")
        
        # NOTE: Setup command execution matches Go's implementation
        for i, cmd in enumerate(setup_commands):
            logger.debug(f"🔧 Processing setup command {i}")
            
            if isinstance(cmd, dict):
                cmd_type = cmd.get('type', 'execute')
                
                if cmd_type == 'write_file':
                    # Handle file writing
                    path = cmd.get('path', '')
                    content = cmd.get('content', '')
                    
                    # Substitute placeholders
                    path = path.replace('{workenv}', str(workenv_dir))
                    path = path.replace('{package_name}', metadata['package']['name'])
                    path = path.replace('{version}', metadata['package']['version'])
                    
                    content = content.replace('{workenv}', str(workenv_dir))
                    content = content.replace('{package_name}', metadata['package']['name'])
                    content = content.replace('{version}', metadata['package']['version'])
                    
                    file_path = Path(path)
                    
                    # Handle different path scenarios
                    if file_path.exists() and file_path.is_dir():
                        # Path exists and is a directory - can't write to it directly
                        logger.debug(f"📁 Path is a directory, creating file inside: {file_path}")
                        # Write to a file with the same base name inside the directory
                        file_path = file_path / ".extracted"
                    
                    # Ensure parent directory exists
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)
                    
                    logger.debug(f"✅ Wrote file: {file_path}")
                    
                elif cmd_type == 'execute':
                    # Handle command execution
                    command = cmd.get('command', '')
                    
                    # Substitute placeholders
                    command = command.replace('{workenv}', str(workenv_dir))
                    command = command.replace('{package_name}', metadata['package']['name'])
                    command = command.replace('{version}', metadata['package']['version'])
                    
                    logger.debug(f"🏃 Running: {command}")
                    
                    result = subprocess.run(command, shell=True, cwd=workenv_dir, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.error(f"❌ Command failed: {command}")
                        logger.error(f"❌ Output: {result.stderr}")
                        raise RuntimeError(f"Setup command failed: {command}")
                    
                    logger.debug(f"✅ Command succeeded")
                    
                elif cmd_type == 'enumerate_and_execute':
                    # Handle file enumeration and execution
                    logger.warning(f"⚠️ enumerate_and_execute not yet implemented")
                else:
                    logger.warning(f"⚠️ Unknown setup command type: {cmd_type}")
            else:
                # Legacy string command
                logger.warning(f"⚠️ String setup commands not supported")
    
    def _substitute_slot_references(self, command: str, workenv_dir: Path) -> str:
        """Substitute {slot:N} references in command.
        
        Args:
            command: Command with potential slot references
            workenv_dir: Work environment directory
            
        Returns:
            str: Command with slot references substituted
        """
        # NOTE: Slot substitution logic matches Go implementation
        metadata = self.read_metadata()
        
        for i, slot in enumerate(metadata.get('slots', [])):
            placeholder = f"{{slot:{i}}}"
            if placeholder in command:
                slot_path = workenv_dir / slot['name']
                command = command.replace(placeholder, str(slot_path))
                logger.debug(f"🔄 Substituted {placeholder} -> {slot_path}")
        
        return command

    def execute(self, args: list[str] | None = None) -> dict:
        """Execute the bundle.
        
        Sets up the work environment, extracts slots, and executes the main command
        using the BundleExecutor.
        
        Args:
            args: Command line arguments to pass to the executable
            
        Returns:
            dict: Execution result with exit_code, stdout, stderr, and other metadata
        """
        try:
            logger.info(f"🚀 Executing bundle: {self.bundle_path}")
            
            # Read metadata
            metadata = self.read_metadata()
            
            # Validate execution configuration exists
            if 'execution' not in metadata:
                logger.error("❌ No execution configuration in metadata")
                raise ValueError("Bundle has no execution configuration")
            
            # Setup work environment (extracts slots and runs setup commands)
            logger.debug("📁 Setting up work environment")
            workenv_dir = self.setup_workenv()
            
            # Use the executor for actual process execution
            from flavor.psp.format_2025.executor import BundleExecutor
            executor = BundleExecutor(metadata, workenv_dir)
            
            # Execute and return result
            return executor.execute(args)
            
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "executed": False,
                "command": None,
                "args": args or [],
                "pid": None,
                "working_directory": os.getcwd(),
                "error": str(e)
            }