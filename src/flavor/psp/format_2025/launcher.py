#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF 2025 bundle launcher that handles execution, extraction, and workenv setup."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
import io
from pathlib import Path
import tarfile
from typing import Any

from provide.foundation import logger
from provide.foundation.file import atomic_write
from provide.foundation.file.directory import ensure_dir, ensure_parent_dir, safe_rmtree

from flavor.config.defaults import DEFAULT_DISK_SPACE_MULTIPLIER
from flavor.psp.format_2025.constants import DEFAULT_SLOT_DESCRIPTOR_SIZE
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.workenv import WorkEnvManager


class PSPFLauncher(PSPFReader):
    """Launch PSPF bundles."""

    def __init__(self, bundle_path: Path | None = None) -> None:
        if bundle_path is None:
            # Allow None for testing purposes, parent class will handle it
            bundle_path_arg: Path | str = ""
        else:
            bundle_path_arg = bundle_path
        super().__init__(bundle_path_arg)
        self.cache_dir = Path.home() / ".cache" / "flavor"
        ensure_dir(self.cache_dir)
        self._workenv_manager = WorkEnvManager(self)

    @contextmanager
    def acquire_lock(self, lock_file: Path, timeout: float = 30.0) -> Generator[Path, None, None]:
        """Acquire a file-based lock for extraction."""
        from flavor.locking import default_lock_manager

        with default_lock_manager.lock(lock_file.name, timeout=timeout) as lock:
            yield lock

    def read_slot_table(self) -> list[dict[str, Any]]:
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
                entry_data = f.read(DEFAULT_SLOT_DESCRIPTOR_SIZE)
                if len(entry_data) != DEFAULT_SLOT_DESCRIPTOR_SIZE:
                    raise ValueError(
                        f"Invalid slot table entry {i}: expected {DEFAULT_SLOT_DESCRIPTOR_SIZE} bytes, got {len(entry_data)}"
                    )

                # Use SlotDescriptor to unpack
                from flavor.psp.format_2025.slots import SlotDescriptor

                descriptor = SlotDescriptor.unpack(entry_data)

                # Extract the fields we need for launcher
                offset = descriptor.offset
                size = descriptor.size  # Compressed size
                checksum = descriptor.checksum
                operations = descriptor.operations
                purpose = descriptor.purpose
                lifecycle = descriptor.lifecycle

                slot_entries.append(
                    {
                        "index": i,
                        "offset": offset,
                        "size": size,
                        "checksum": checksum,
                        "operations": operations,
                        "purpose": purpose,
                        "lifecycle": lifecycle,
                    }
                )

        return slot_entries

    def check_disk_space(self, workenv_dir: Path) -> None:
        """Check if there's enough disk space for extraction.

        Args:
            workenv_dir: Directory where slots will be extracted

        Raises:
            OSError: If insufficient disk space available
        """
        from provide.foundation.file import check_disk_space

        # Calculate total size needed (compressed size * multiplier for safety)
        slot_table = self.read_slot_table()
        total_needed = sum(slot["size"] * DEFAULT_DISK_SPACE_MULTIPLIER for slot in slot_table)

        # Use the utility function
        check_disk_space(workenv_dir, total_needed)

    def extract_all_slots(self, workenv_dir: Path) -> dict[int, Path]:
        """Extract all slots to the work environment.

        Args:
            workenv_dir: Directory to extract slots into

        Returns:
            dict: Mapping of slot index to extracted path
        """

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

            return extracted_paths
        except Exception as e:
            logger.error(f"❌ Extraction interrupted or failed: {e}. Cleaning up partial extraction.")
            safe_rmtree(workenv_dir)
            raise  # Re-raise the exception

    def extract_slot(self, slot_index: int, workenv_dir: Path, verify_checksum: bool = False) -> Path:  # noqa: C901
        """Extract a single slot.

        Args:
            slot_index: Index of the slot to extract
            workenv_dir: Directory to extract into
            verify_checksum: Whether to verify checksum after extraction

        Returns:
            Path: Path to the extracted slot content
        """

        # NOTE: This logic is unique to Python launcher - Go/Rust have their own implementations
        slot_table = self.read_slot_table()

        if slot_index < 0 or slot_index >= len(slot_table):
            logger.error(f"❌ Invalid slot index: {slot_index} (have {len(slot_table)} slots)")
            raise ValueError(f"Invalid slot index: {slot_index}")

        slot_entry = slot_table[slot_index]
        logger.debug(
            f"📍 Slot {slot_index}: offset={slot_entry['offset']}, size={slot_entry['size']}, operations={slot_entry['operations']}"
        )

        # Read slot data from bundle
        with Path(self.bundle_path).open("rb") as f:
            f.seek(slot_entry["offset"])
            slot_data = f.read(slot_entry["size"])

        # Verify checksum if requested (checksum is of the data AS STORED IN THE FILE)
        if verify_checksum:
            # NOTE: Use SHA-256 (first 8 bytes) to match Go/Rust implementations
            # Checksum is of the slot data as it exists in the file (compressed or not)
            import hashlib

            hash_bytes = hashlib.sha256(slot_data).digest()[:8]
            actual_checksum = int.from_bytes(hash_bytes, byteorder="little")
            if actual_checksum != slot_entry["checksum"]:
                logger.error(
                    f"❌ Checksum mismatch for slot {slot_index}: expected {slot_entry['checksum']:016x}, got {actual_checksum:016x}"
                )
                raise ValueError(f"Checksum mismatch for slot {slot_index}")

        # NOTE: Decoding logic must match Go/Rust implementations
        # Decode if needed
        if slot_entry["operations"] == 0:  # raw/none
            data = slot_data
        elif slot_entry["operations"] == 0x01:  # tar
            data = slot_data  # Tar archives are extracted later
        elif slot_entry["operations"] == 0x10:  # gzip
            logger.debug(f"🗜️ Decompressing slot {slot_index} with gzip")
            import gzip

            data = gzip.decompress(slot_data)
        elif slot_entry["operations"] == 0x1001:  # tar.gz
            data = slot_data  # Will be decompressed and extracted later
        else:
            logger.error(f"❌ Unsupported operations: {slot_entry['operations']}")
            raise ValueError(f"Unsupported operations: {slot_entry['operations']}")

        # Get slot name from metadata - use target for extraction path
        metadata = self.read_metadata()
        slot_name = f"slot_{slot_index}"
        if "slots" in metadata and slot_index < len(metadata["slots"]):
            slot_meta = metadata["slots"][slot_index]
            # Use "target" field for extraction path, fallback to "id" or "name"
            slot_name = slot_meta.get("target", slot_meta.get("id", slot_meta.get("name", slot_name)))
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

                # Return the base directory
                return workenv_dir
            except (OSError, PermissionError, tarfile.ReadError) as e:
                logger.error(f"❌ Disk or tarball error extracting slot {slot_index} to {workenv_dir}: {e}")
                raise  # Re-raise the exception
        else:
            # Write single file (atomic for safety)
            output_path = workenv_dir / slot_name
            try:
                ensure_parent_dir(output_path)
                atomic_write(output_path, data)
                return output_path
            except (OSError, PermissionError) as e:
                logger.error(f"❌ Disk error writing slot {slot_index} to {output_path}: {e}")
                raise  # Re-raise the exception

    def setup_workenv(self) -> Path:
        """Setup work environment for bundle execution."""
        return self._workenv_manager.setup_workenv(self.bundle_path)

    def _substitute_slot_references(self, command: str, workenv_dir: Path) -> str:
        """Substitute {slot:N} references in command."""
        return self._workenv_manager.substitute_slot_references(command, workenv_dir)

    def execute(self, args: list[str] | None = None) -> dict[str, Any]:
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
            workenv_dir = self.setup_workenv()

            # Use the executor for actual process execution
            from flavor.psp.format_2025.executor import BundleExecutor

            logger.debug(f"🔍 Metadata command: {metadata.get('execution', {}).get('command', 'N/A')}")
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
                "working_directory": str(Path.cwd()),
                "error": str(e),
            }

    def verify_integrity(self) -> dict[str, bool]:
        """
        Verify package integrity including signatures and checksums.

        Returns:
            Dictionary with verification results:
            - valid: Overall validity
            - signature_valid: Signature verification result
            - tamper_detected: Whether tampering was detected
        """
        from flavor.psp.protocols import IntegrityResult
        from flavor.psp.security import verify_package_integrity

        if not self.bundle_path:
            return {"valid": False, "signature_valid": False, "tamper_detected": True}

        result: IntegrityResult = verify_package_integrity(self.bundle_path)
        # IntegrityResult is a TypedDict with bool values, which is compatible with dict[str, bool]
        return dict(result)  # type: ignore[arg-type]


# 🌶️📦🔚
