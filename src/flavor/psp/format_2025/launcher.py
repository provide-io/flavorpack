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

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from provide.foundation import logger
from provide.foundation.file import atomic_write
from provide.foundation.file.directory import ensure_dir, ensure_parent_dir, safe_rmtree

from flavor.config.defaults import DEFAULT_DISK_SPACE_MULTIPLIER
from flavor.config.policy import enforce_policy, load_operator_policy, merge_policy, parse_package_policy
from flavor.config.trust import compute_key_fingerprint, is_key_trusted
from flavor.psp.format_2025.constants import DEFAULT_SLOT_DESCRIPTOR_SIZE, OP_NONE, OPERATION_CHAINS
from flavor.psp.format_2025.operations import pack_operations
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.targets import normalize_workenv_target
from flavor.psp.format_2025.workenv import WorkEnvManager
from flavor.psp.security import verify_package_integrity

# Pre-computed operation chain values — derived from OPERATION_CHAINS (the canonical source).
# Operations field is a packed 64-bit integer: each byte is one operation code.
_OP_NONE = OP_NONE  # 0x00 — raw data, no processing
_OP_TAR = pack_operations(OPERATION_CHAINS["tar"])
_OP_GZIP = pack_operations(OPERATION_CHAINS["gzip"])
_OP_TAR_GZ = pack_operations(OPERATION_CHAINS["tar.gz"])


class PSPFLauncher(PSPFReader):
    """Launch PSPF bundles."""

    def __init__(self, bundle_path: Path | None = None) -> None:
        if bundle_path is None:
            raise ValueError("bundle_path is required")
        super().__init__(bundle_path)
        from flavor.cache import get_cache_dir

        self.cache_dir = get_cache_dir().parent
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

    def extract_slot(self, slot_index: int, workenv_dir: Path, verify_checksum: bool = False) -> Path:  # noqa: C901  # ty: ignore[invalid-method-override]
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
        if slot_entry["operations"] == _OP_NONE:
            data = slot_data
        elif slot_entry["operations"] == _OP_TAR:
            data = slot_data  # Tar archives are extracted later
        elif slot_entry["operations"] == _OP_GZIP:
            logger.debug(f"🗜️ Decompressing slot {slot_index} with gzip")
            import gzip

            data = gzip.decompress(slot_data)
        elif slot_entry["operations"] == _OP_TAR_GZ:
            data = slot_data  # Will be decompressed and extracted later
        else:
            logger.error(f"❌ Unsupported operations: {slot_entry['operations']}")
            raise ValueError(f"Unsupported operations: {slot_entry['operations']}")

        # Get slot name from metadata - use target for extraction path
        metadata = self.read_metadata()
        slot_name = f"slot_{slot_index}"
        slot_meta: dict[str, Any] = {}
        if "slots" in metadata and slot_index < len(metadata["slots"]):
            slot_meta = metadata["slots"][slot_index]
            # Use "target" field for extraction path, fallback to "id" or "name"
            slot_name = slot_meta.get("target", slot_meta.get("id", slot_meta.get("name", slot_name)))
        slot_name = self._normalize_slot_target(str(slot_name))
        logger.debug(f"📝 Slot {slot_index} name: {slot_name}")

        # NOTE: Tarball extraction logic matches Go's tar extraction
        # Check if it's a tarball that needs extraction (by content, not just name)
        import contextlib

        is_tarball = False
        with (
            contextlib.suppress(tarfile.TarError, EOFError, OSError),
            tarfile.open(fileobj=io.BytesIO(data), mode="r:*"),
        ):
            # If we can open it, it's a tarball
            is_tarball = True

        if is_tarball or slot_name.endswith(".tar.gz") or slot_name.endswith(".tgz"):
            logger.debug(f"📤 Extracting tarball {slot_name} to {workenv_dir}")
            try:
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
                    # "data" rejects absolute paths and .. but still allows symlinks;
                    # we additionally strip symlinks to prevent link-based traversal.
                    def _safe_filter(member: tarfile.TarInfo, path: str) -> tarfile.TarInfo | None:
                        result = tarfile.data_filter(member, path)
                        if result is not None and (result.issym() or result.islnk()):
                            logger.warning(f"⚠️ Skipping symlink/hardlink in tarball: {result.name}")
                            return None
                        return result

                    tar.extractall(path=workenv_dir, filter=_safe_filter)  # nosec B202

                if slot_name in {".", "{workenv}"}:
                    return workenv_dir

                return workenv_dir / slot_name
            except (OSError, tarfile.ReadError) as e:
                logger.error(f"❌ Disk or tarball error extracting slot {slot_index} to {workenv_dir}: {e}")
                raise  # Re-raise the exception
        else:
            # Write single file (atomic for safety)
            output_path = workenv_dir / slot_name
            try:
                ensure_parent_dir(output_path)
                atomic_write(output_path, data)
                self._apply_slot_permissions(output_path, slot_meta)
                return output_path
            except OSError as e:
                logger.error(f"❌ Disk error writing slot {slot_index} to {output_path}: {e}")
                raise  # Re-raise the exception

    def _apply_slot_permissions(self, output_path: Path, slot_meta: dict[str, Any]) -> None:
        """Apply metadata-driven permissions after single-file extraction."""
        permissions = slot_meta.get("permissions")
        if not permissions:
            return

        try:
            mode = int(str(permissions), 8) & 0o777  # Strip setuid/setgid/sticky bits
            output_path.chmod(mode)
        except (OSError, ValueError) as e:
            logger.warning(f"⚠️ Failed to apply slot permissions to {output_path}: {e}")

    def _normalize_slot_target(self, slot_target: str) -> str:
        """Normalize slot target metadata to a path relative to the workenv."""
        return normalize_workenv_target(slot_target)

    def setup_workenv(self) -> Path:
        """Setup work environment for bundle execution."""
        return self._workenv_manager.setup_workenv(self.bundle_path)

    def _substitute_slot_references(self, command: str, workenv_dir: Path) -> str:
        """Substitute {slot:N} references in command."""
        return self._workenv_manager.substitute_slot_references(command, workenv_dir)

    def _is_package_key_trusted(self, index: Any | None = None) -> bool:
        """Return whether the package signing key is trusted for operator-policy enforcement."""
        if index is None:
            index = self.read_index()

        public_key = bytes(getattr(index, "public_key", b""))
        if not public_key or set(public_key) == {0}:
            return False

        fingerprint = compute_key_fingerprint(Ed25519PublicKey.from_public_bytes(public_key))
        stored_fingerprint = bytes(getattr(index, "attestation_key_fp", b"")).rstrip(b"\x00")
        if stored_fingerprint:
            try:
                stored_fingerprint_text = stored_fingerprint.decode("ascii")
            except UnicodeDecodeError as exc:
                raise ValueError("attestation key fingerprint is not valid ASCII") from exc
            if stored_fingerprint_text != fingerprint:
                raise ValueError("attestation key fingerprint does not match embedded public key")

        trusted = is_key_trusted(fingerprint)
        return trusted is True

    def _enforce_launch_security(self, metadata: dict[str, Any]) -> None:
        """Verify integrity and enforce launch-time operator/package policy."""
        result = verify_package_integrity(self.bundle_path)
        if not result.get("valid", False):
            raise ValueError("package integrity verification failed")

        index = self.read_index()
        pkg_policy = parse_package_policy(metadata.get("policy", {}))
        op_policy = load_operator_policy()
        effective_policy = merge_policy(pkg_policy, op_policy)
        has_sbom = any(slot.get("lifecycle") == "attestation" for slot in metadata.get("slots", []))
        enforce_policy(
            effective_policy,
            int(getattr(index, "build_timestamp", 0)),
            has_sbom,
            self._is_package_key_trusted(index),
        )

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

            self._enforce_launch_security(metadata)

            # Setup work environment (extracts slots and runs setup commands)
            workenv_dir = self.setup_workenv()

            # Use the executor for actual process execution
            from flavor.psp.format_2025.executor import BundleExecutor

            if logger.is_debug_enabled():
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
