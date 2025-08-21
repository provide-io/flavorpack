"""
PSPF 2025 Bundle Launcher

Handles bundle execution, slot extraction, and work environment setup.
"""

from contextlib import contextmanager
import glob
import io
import os
from pathlib import Path
import shlex
import tarfile
import zlib

from pyvider.telemetry import logger

from flavor.psp.format_2025.constants import SLOT_DESCRIPTOR_SIZE
from flavor.psp.format_2025.reader import PSPFReader
from flavor.utils.subprocess import run_command


class PSPFLauncher(PSPFReader):
    """Launch PSPF bundles."""

    def __init__(self, bundle_path: Path | None = None) -> None:
        super().__init__(bundle_path)
        self.bundle_path = bundle_path
        self.cache_dir = Path.home() / ".cache" / "pspf"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def acquire_lock(self, lock_file: Path, timeout: float = 30.0):
        """Acquire a file-based lock for extraction."""
        from flavor.locking import default_lock_manager

        with default_lock_manager.lock(lock_file.name, timeout=timeout) as lock:
            yield lock

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

        with Path(self.bundle_path).open("rb") as f:
            # Seek to slot table
            f.seek(index.slot_table_offset)

            # Read each 64-byte slot descriptor (new format)
            for i in range(index.slot_count):
                entry_data = f.read(SLOT_DESCRIPTOR_SIZE)
                if len(entry_data) != SLOT_DESCRIPTOR_SIZE:
                    raise ValueError(
                        f"Invalid slot table entry {i}: expected {SLOT_DESCRIPTOR_SIZE} bytes, got {len(entry_data)}"
                    )

                # Use SlotDescriptor to unpack
                from flavor.psp.format_2025.slots import SlotDescriptor

                descriptor = SlotDescriptor.unpack(entry_data)

                # Extract the fields we need for launcher
                offset = descriptor.offset
                size = descriptor.size  # Compressed size
                checksum = descriptor.checksum
                encoding = descriptor.encoding
                purpose = descriptor.purpose
                lifecycle = descriptor.lifecycle

                slot_entries.append(
                    {
                        "index": i,
                        "offset": offset,
                        "size": size,
                        "checksum": checksum,
                        "encoding": encoding,
                        "purpose": purpose,
                        "lifecycle": lifecycle,
                    }
                )

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
        try:
            for slot_entry in slot_table:
                slot_idx = slot_entry["index"]
                logger.debug(f"🔄 Extracting slot {slot_idx}")
                slot_path = self.extract_slot(slot_idx, workenv_dir)
                extracted_paths[slot_idx] = slot_path

            logger.info(f"✅ Extracted all {len(extracted_paths)} slots")
            return extracted_paths
        except Exception as e:
            logger.error(
                f"❌ Extraction interrupted or failed: {e}. Cleaning up partial extraction."
            )
            import shutil

            shutil.rmtree(workenv_dir, ignore_errors=True)
            raise  # Re-raise the exception

    def extract_slot(
        self, slot_index: int, workenv_dir: Path, verify_checksum: bool = False
    ) -> Path:
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
            logger.error(
                f"❌ Invalid slot index: {slot_index} (have {len(slot_table)} slots)"
            )
            raise ValueError(f"Invalid slot index: {slot_index}")

        slot_entry = slot_table[slot_index]
        logger.debug(
            f"📍 Slot {slot_index}: offset={slot_entry['offset']}, size={slot_entry['size']}, encoding={slot_entry['encoding']}"
        )

        # Read slot data from bundle
        with Path(self.bundle_path).open("rb") as f:
            f.seek(slot_entry["offset"])
            slot_data = f.read(slot_entry["size"])
            logger.debug(f"📖 Read {len(slot_data)} bytes from slot {slot_index}")

        # Verify checksum if requested (checksum is of the data AS STORED IN THE FILE)
        if verify_checksum:
            # NOTE: Use adler32 to match Go/Rust implementations
            # Checksum is of the slot data as it exists in the file (compressed or not)
            actual_checksum = zlib.adler32(slot_data)
            if actual_checksum != slot_entry["checksum"]:
                logger.error(
                    f"❌ Checksum mismatch for slot {slot_index}: expected {slot_entry['checksum']}, got {actual_checksum}"
                )
                raise ValueError(f"Checksum mismatch for slot {slot_index}")
            logger.debug(f"✅ Checksum verified for slot {slot_index}")

        # NOTE: Decoding logic must match Go/Rust implementations
        # Decode if needed
        if slot_entry["encoding"] == 0:  # raw/none
            logger.debug(f"📄 Slot {slot_index} is unencoded (raw)")
            data = slot_data
        elif slot_entry["encoding"] == 1:  # tar
            logger.debug(f"📦 Slot {slot_index} is a tar archive")
            data = slot_data  # Tar archives are extracted later
        elif slot_entry["encoding"] == 2:  # gzip
            logger.debug(f"🗜️ Decompressing slot {slot_index} with gzip")
            import gzip

            data = gzip.decompress(slot_data)
            logger.debug(f"✅ Decompressed to {len(data)} bytes")
        elif slot_entry["encoding"] == 3:  # tar.gz
            logger.debug(f"📦🗜️ Slot {slot_index} is a tar.gz archive")
            data = slot_data  # Will be decompressed and extracted later
        else:
            logger.error(f"❌ Unsupported encoding method: {slot_entry['encoding']}")
            raise ValueError(f"Unsupported encoding method: {slot_entry['encoding']}")

        # Get slot name from metadata
        metadata = self.read_metadata()
        slot_name = f"slot_{slot_index}"
        if "slots" in metadata and slot_index < len(metadata["slots"]):
            slot_meta = metadata["slots"][slot_index]
            slot_name = slot_meta.get("name", slot_name)
        logger.debug(f"📝 Slot {slot_index} name: {slot_name}")

        # NOTE: Tarball extraction logic matches Go's tar extraction
        # Check if it's a tarball that needs extraction (by content, not just name)
        is_tarball = False
        try:
            # Try to open as tarball
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
                # If we can open it, it's a tarball
                is_tarball = True
        except (tarfile.TarError, EOFError, OSError):
            pass

        if is_tarball or slot_name.endswith(".tar.gz") or slot_name.endswith(".tgz"):
            logger.debug(f"📤 Extracting tarball {slot_name} to {workenv_dir}")
            try:
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
                    # Use the filter parameter to avoid Python 3.14 deprecation warning
                    tar.extractall(path=workenv_dir, filter="data")
                logger.debug(f"✅ Extracted tarball contents to {workenv_dir}")

                # Return the base directory
                return workenv_dir
            except (OSError, PermissionError, tarfile.ReadError) as e:
                logger.error(
                    f"❌ Disk or tarball error extracting slot {slot_index} to {workenv_dir}: {e}"
                )
                raise  # Re-raise the exception
        else:
            # Write single file
            output_path = workenv_dir / slot_name
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(data)
                logger.debug(f"✅ Wrote {len(data)} bytes to {output_path}")
                return output_path
            except (OSError, PermissionError) as e:
                logger.error(
                    f"❌ Disk error writing slot {slot_index} to {output_path}: {e}"
                )
                raise  # Re-raise the exception

    def setup_workenv(self) -> Path:
        """Setup work environment for bundle execution.

        Creates a work environment directory, extracts slots, and runs setup commands.
        Uses cache validation to avoid re-extraction when possible.
        Handles lifecycle-based slot cleanup (e.g., 'init' slots removed after setup).

        Returns:
            Path: Path to the work environment directory
        """
        logger.debug(f"🔧 Setting up work environment for {self.bundle_path}")

        # NOTE: This matches Go's work environment setup logic
        metadata = self.read_metadata()
        package_name = metadata["package"]["name"]
        package_version = metadata["package"]["version"]

        # Create work environment directory
        workenv_base = Path.home() / ".cache" / "pspf" / "workenv"
        workenv_dir = workenv_base / f"{package_name}_{package_version}"
        workenv_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📁 Work environment: {workenv_dir}")

        # Check cache validity
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
                if actual_content == expected_content.replace(
                    "{version}", package_version
                ):
                    cache_valid = True
                    logger.debug("✅ Cache is valid")
                else:
                    logger.debug(
                        f"❌ Cache content mismatch: expected '{expected_content}', got '{actual_content}'"
                    )
            else:
                logger.debug(f"❌ Cache validation file not found: {check_path}")

        # Extract slots if cache is invalid
        if not cache_valid:
            logger.info("📤 Extracting slots (cache invalid)")
            extracted_slots = self.extract_all_slots(workenv_dir)

            # Run setup commands
            if "setup_commands" in metadata:
                self._run_setup_commands(
                    metadata["setup_commands"], workenv_dir, metadata
                )

            # Handle lifecycle-based cleanup
            self._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)
        else:
            logger.info("✅ Using cached work environment")

        return workenv_dir

    def _cleanup_lifecycle_slots(
        self, workenv_dir: Path, metadata: dict, extracted_slots: dict[int, Path]
    ) -> None:
        """Clean up slots based on their lifecycle after setup.

        Args:
            workenv_dir: Work environment directory
            metadata: Package metadata
            extracted_slots: Mapping of slot index to extracted paths
        """
        import shutil

        # Get slot metadata
        slots = metadata.get("slots", [])

        for slot_idx, slot_path in extracted_slots.items():
            if slot_idx < len(slots):
                slot_meta = slots[slot_idx]
                lifecycle = slot_meta.get("lifecycle", "runtime")

                # Handle different lifecycle values
                if lifecycle == "init":
                    # 'init' lifecycle: remove after initialization
                    logger.debug(
                        f"🗑️ Removing 'init' lifecycle slot {slot_idx}: {slot_path}"
                    )
                    if slot_path.exists():
                        if slot_path.is_dir():
                            shutil.rmtree(slot_path, ignore_errors=True)
                        else:
                            slot_path.unlink(missing_ok=True)
                elif lifecycle == "temp":
                    # 'temp' lifecycle: mark for cleanup after session
                    logger.debug(
                        f"🕐 Slot {slot_idx} marked as 'temp' - will be cleaned after session"
                    )
                elif lifecycle in ["volatile"]:  # Handle legacy 'volatile' as 'init'
                    # Legacy support: treat 'volatile' as 'init'
                    logger.debug(
                        f"🗑️ Removing legacy 'volatile' slot {slot_idx}: {slot_path}"
                    )
                    if slot_path.exists():
                        if slot_path.is_dir():
                            shutil.rmtree(slot_path, ignore_errors=True)
                        else:
                            slot_path.unlink(missing_ok=True)

    def _run_setup_commands(
        self, setup_commands: list, workenv_dir: Path, metadata: dict
    ) -> None:
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
                cmd_type = cmd.get("type", "execute")

                if cmd_type == "write_file":
                    # Handle file writing
                    path = cmd.get("path", "")
                    content = cmd.get("content", "")

                    # Substitute placeholders
                    path = path.replace("{workenv}", str(workenv_dir))
                    path = path.replace("{package_name}", metadata["package"]["name"])
                    path = path.replace("{version}", metadata["package"]["version"])

                    content = content.replace("{workenv}", str(workenv_dir))
                    content = content.replace(
                        "{package_name}", metadata["package"]["name"]
                    )
                    content = content.replace(
                        "{version}", metadata["package"]["version"]
                    )

                    file_path = Path(path)

                    # Handle different path scenarios
                    if file_path.exists() and file_path.is_dir():
                        # Path exists and is a directory - can't write to it directly
                        logger.debug(
                            f"📁 Path is a directory, creating file inside: {file_path}"
                        )
                        # Write to a file with the same base name inside the directory
                        file_path = file_path / ".extracted"

                    # Ensure parent directory exists
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)

                    logger.debug(f"✅ Wrote file: {file_path}")

                elif cmd_type == "execute":
                    # Handle command execution
                    command = cmd.get("command", "")

                    # Substitute placeholders
                    command = command.replace("{workenv}", str(workenv_dir))
                    command = command.replace(
                        "{package_name}", metadata["package"]["name"]
                    )
                    command = command.replace(
                        "{version}", metadata["package"]["version"]
                    )

                    # Parse command safely to avoid shell injection
                    args = shlex.split(command)

                    # Use the shared run_command utility
                    try:
                        run_command(
                            args,
                            cwd=workenv_dir,
                            capture_output=True,
                            check=True,
                            log_command=True,
                        )
                        logger.debug("✅ Command succeeded")
                    except Exception as e:
                        logger.error(f"❌ Command failed: {command}")
                        raise RuntimeError(f"Setup command failed: {command}") from e

                    logger.debug("✅ Command succeeded")

                elif cmd_type == "enumerate_and_execute":
                    # Handle file enumeration and execution
                    pattern = cmd.get("pattern", "*")
                    command_template = cmd.get("command", "")

                    # Find matching files
                    search_path = workenv_dir / pattern
                    matches = glob.glob(str(search_path))

                    logger.debug(f"📂 Found {len(matches)} files matching {pattern}")

                    for file_path in matches:
                        # Substitute file path in command
                        command = command_template.replace("{file}", file_path)
                        command = command.replace("{workenv}", str(workenv_dir))

                        # Parse and execute command using shared utility
                        args = shlex.split(command)

                        try:
                            run_command(
                                args,
                                cwd=workenv_dir,
                                capture_output=True,
                                check=True,
                                log_command=True,
                            )
                        except Exception as e:
                            logger.error(
                                f"❌ Command failed for {file_path}: {command}"
                            )
                            logger.error(f"❌ Error: {e}")
                            # Continue with other files instead of failing

                    logger.debug(f"✅ Processed {len(matches)} files")
                else:
                    logger.warning(f"⚠️ Unknown setup command type: {cmd_type}")
            else:
                # Legacy string command
                logger.warning("⚠️ String setup commands not supported")

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

        for i, slot in enumerate(metadata.get("slots", [])):
            placeholder = f"{{slot:{i}}}"
            if placeholder in command:
                slot_path = workenv_dir / slot["name"]
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
            if "execution" not in metadata:
                logger.error("❌ No execution configuration in metadata")
                raise ValueError("Bundle has no execution configuration")

            # Setup work environment (extracts slots and runs setup commands)
            logger.debug("📁 Setting up work environment")
            workenv_dir = self.setup_workenv()

            # Use the executor for actual process execution
            from flavor.psp.format_2025.executor import BundleExecutor

            logger.debug(
                f"🔍 Metadata command: {metadata.get('execution', {}).get('command', 'N/A')}"
            )
            logger.debug(f"🔍 Workenv dir: {workenv_dir}")
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
                "error": str(e),
            }
