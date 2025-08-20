"""
Slot handling utilities for PSPF launcher.

Handles slot table reading and slot reference substitution.
"""

from pathlib import Path

from pyvider.telemetry import logger

from flavor.psp.format_2025.constants import SLOT_DESCRIPTOR_SIZE


def read_slot_table(reader_instance) -> list[dict]:
    """Read the slot table from the bundle.
    
    Args:
        reader_instance: PSPFReader or PSPFLauncher instance with bundle_path
    
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
    index = reader_instance.read_index()
    
    slot_entries = []
    
    with Path(reader_instance.bundle_path).open("rb") as f:
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


def substitute_slot_references(command: str, workenv_dir: Path, metadata: dict) -> str:
    """Substitute {slot:N} references in command.
    
    Args:
        command: Command with potential slot references
        workenv_dir: Work environment directory  
        metadata: Package metadata containing slot information
        
    Returns:
        str: Command with slot references substituted
    """
    # NOTE: Slot substitution logic matches Go implementation
    for i, slot in enumerate(metadata.get("slots", [])):
        placeholder = f"{{slot:{i}}}"
        if placeholder in command:
            slot_path = workenv_dir / slot["name"]
            command = command.replace(placeholder, str(slot_path))
            logger.debug(f"🔄 Substituted {placeholder} -> {slot_path}")
    
    return command