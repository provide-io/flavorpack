"""
PSPF Package Writer Module.

Handles the actual writing of PSPF packages to disk, including launcher,
index, metadata, slots, and magic footer.
"""

import gzip
import io
import json
import struct
import tarfile
import tempfile
from pathlib import Path

from pyvider.telemetry import logger

from flavor.exceptions import BuildError
from flavor.psp.format_2025.checksums import calculate_checksum
from flavor.psp.format_2025.constants import (
    EMOJI_MAGIC_SIZE,
    INDEX_SIZE,
    MAGIC_WAND_EMOJI,
    SLOT_DESCRIPTOR_SIZE,
)
from flavor.psp.format_2025.crypto import sign_data
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.spec import BuildOptions, BuildResult, BuildSpec, PreparedSlot


def write_package(
    output_path: Path,
    launcher_path: Path,
    index: PSPFIndex,
    metadata: dict,
    slots: list[PreparedSlot],
    signature: bytes | None,
    options: BuildOptions,
) -> BuildResult:
    """
    Write complete PSPF package to disk.
    
    This function assembles the final package:
    1. Launcher binary (platform executable)
    2. Index block at launcher_size offset
    3. Metadata archive (gzipped tar with psp.json)
    4. Slot table (array of slot descriptors)
    5. Slot data (actual slot contents)
    6. Magic emoji footer
    
    Args:
        output_path: Where to write the package
        launcher_path: Path to launcher binary
        index: Prepared index block
        metadata: Package metadata dictionary
        slots: List of prepared slots
        signature: Optional package signature
        options: Build options
        
    Returns:
        BuildResult indicating success or failure
    """
    try:
        logger.info(f"📝 Writing package to {output_path}")
        
        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            # 1. Write launcher
            logger.debug("🚀 Writing launcher")
            launcher_data = launcher_path.read_bytes()
            f.write(launcher_data)
            
            # 2. Write index at launcher_size offset
            logger.debug(f"📋 Writing index at offset {len(launcher_data)}")
            index_data = index.pack()
            f.write(index_data)
            
            # 3. Write metadata archive
            logger.debug("📄 Writing metadata archive")
            metadata_archive = _create_metadata_archive(metadata, signature)
            f.write(metadata_archive)
            
            # 4. Write slot table
            logger.debug(f"📊 Writing slot table ({len(slots)} entries)")
            for slot in slots:
                descriptor_data = slot.descriptor.pack()
                f.write(descriptor_data)
            
            # 5. Write slot data
            logger.debug("💾 Writing slot data")
            for i, slot in enumerate(slots):
                logger.debug(
                    f"  Slot {i}: {slot.metadata.name} "
                    f"({len(slot.data)} bytes at offset {f.tell()})"
                )
                f.write(slot.data)
            
            # 6. Write magic footer
            logger.debug("🪄 Writing magic footer")
            f.write(MAGIC_WAND_EMOJI.encode("utf-8"))
            
            final_size = f.tell()
        
        # Make executable on Unix
        if hasattr(output_path, "chmod"):
            output_path.chmod(0o755)
        
        logger.info(
            f"✅ Package created: {output_path} ({final_size:,} bytes)"
        )
        
        return BuildResult(
            success=True,
            package_path=output_path,
            metadata={
                "size": final_size,
                "slots": len(slots),
                "launcher_size": len(launcher_data),
                "metadata_size": len(metadata_archive),
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to write package: {e}")
        
        # Clean up partial file
        if output_path.exists():
            output_path.unlink()
        
        return BuildResult(
            success=False,
            errors=[str(e)],
        )


def _create_metadata_archive(metadata: dict, signature: bytes | None) -> bytes:
    """
    Create metadata archive (gzipped tar containing psp.json).
    
    The metadata archive is a tar.gz file containing:
    - psp.json: Main metadata file
    - signature.bin: Optional signature file
    
    Args:
        metadata: Metadata dictionary to serialize
        signature: Optional signature bytes
        
    Returns:
        Gzipped tar archive bytes
    """
    # Create tar archive in memory
    tar_buffer = io.BytesIO()
    
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add psp.json
        json_data = json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8")
        json_info = tarfile.TarInfo(name="psp.json")
        json_info.size = len(json_data)
        json_info.mtime = 0 if metadata.get("build", {}).get("deterministic") else None
        tar.addfile(json_info, io.BytesIO(json_data))
        
        # Add signature if present
        if signature:
            sig_info = tarfile.TarInfo(name="signature.bin")
            sig_info.size = len(signature)
            sig_info.mtime = 0 if metadata.get("build", {}).get("deterministic") else None
            tar.addfile(sig_info, io.BytesIO(signature))
    
    return tar_buffer.getvalue()


def calculate_package_checksum(package_path: Path) -> str:
    """
    Calculate checksum of complete package.
    
    Args:
        package_path: Path to package file
        
    Returns:
        Hex-encoded SHA256 checksum
    """
    return calculate_checksum(package_path)