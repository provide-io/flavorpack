"""
PSPF 2025 Slot Management
"""

from pathlib import Path
from typing import Any
import cattrs
from attrs import define, field, validators

from flavor.psp.format_2025.constants import SLOT_ALIGNMENT


def normalize_purpose(value: str) -> str:
    """Normalize purpose field to spec-compliant values for internal use."""
    # Map additional purpose values to the spec-compliant ones
    purpose_map = {
        "payload": "payload",
        "runtime": "runtime", 
        "tool": "tool",
        # Map additional test values to spec values
        "library": "runtime",  # Libraries are runtime dependencies
        "config": "payload",   # Config files are payload
        "asset": "payload",    # Assets are payload
        "binary": "runtime",   # Binaries are runtime
        "installer": "tool",   # Installers are tools
        "data": "payload",     # Data files are payload
    }
    
    return purpose_map.get(value, "payload")  # Default to payload


@define
class SlotMetadata:
    """Metadata for a single slot."""

    index: int = field(validator=validators.instance_of(int))
    name: str = field(validator=validators.instance_of(str))
    size: int = field(validator=validators.instance_of(int))
    compressed_size: int = field(validator=validators.instance_of(int))
    checksum: str = field(validator=validators.instance_of(str))
    encoding: str = field(validator=validators.in_(["none", "gzip"]))
    purpose: str = field()  # Store original value, normalize when needed
    lifecycle: str = field(validator=validators.in_(["persistent", "volatile", "temporary", "install"]))
    path: Path | None = field(default=None)
    platform: str | None = field(default=None)

    def get_purpose_value(self) -> int:
        """Get the numeric purpose value for binary encoding."""
        normalized = normalize_purpose(self.purpose)
        purpose_map = {"payload": 0, "runtime": 1, "tool": 2}
        return purpose_map.get(normalized, 0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization using cattrs."""
        converter = cattrs.Converter()
        # Register Path to string conversion
        converter.register_unstructure_hook(Path, str)
        return converter.unstructure(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SlotMetadata':
        """Create from dictionary using cattrs."""
        converter = cattrs.Converter()
        # Register string to Path conversion
        converter.register_structure_hook(
            Path,
            lambda v, t: Path(v) if v is not None else None
        )
        return converter.structure(data, cls)


def align_offset(offset: int, alignment: int = SLOT_ALIGNMENT) -> int:
    """Align offset to boundary."""
    return (offset + alignment - 1) & ~(alignment - 1)