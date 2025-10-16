#!/usr/bin/env python3
"""Export protobuf definitions to JSON/YAML specifications.

This script reads the compiled protobuf definitions and exports them
to JSON and YAML formats for language-agnostic reference.
"""

import json
import logging
from pathlib import Path
import sys

import yaml

# Import our generated protobuf modules
from flavor.psp.format_2025.generated.modules import operations_pb2

# Configure logging with emojis
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)


def log_info(msg: str):
    logger.info(f"📊 [INFO] {msg}")


def log_success(msg: str):
    logger.info(f"✅ [SUCCESS] {msg}")


def log_debug(msg: str):
    logger.debug(f"🐛 [DEBUG] {msg}")


def log_trace(msg: str):
    logger.debug(f"🔍 [TRACE] {msg}")


def extract_enum_values(enum_descriptor):
    """Extract enum values from a protobuf enum descriptor."""
    values = {}
    for value in enum_descriptor.values:
        values[f"0x{value.number:02X}"] = {
            "name": value.name,
            "number": value.number,
            "decimal": value.number,
            "hex": f"0x{value.number:02X}",
            "binary": f"0b{value.number:08b}",
        }
    return values


def categorize_operations(operations):
    """Categorize operations by their numeric ranges."""
    categories = {
        "none": {},
        "bundle": {},
        "compression": {},
        "encryption": {},
        "encoding": {},
        "hash": {},
        "signature": {},
        "transform": {},
        "custom": {},
        "reserved": {},
        "terminal": {},
    }

    for hex_key, op in operations.items():
        num = op["number"]

        if num == 0x00:
            categories["none"][hex_key] = op
        elif 0x01 <= num <= 0x0F:
            categories["bundle"][hex_key] = op
        elif 0x10 <= num <= 0x2F:
            categories["compression"][hex_key] = op
        elif 0x30 <= num <= 0x4F:
            categories["encryption"][hex_key] = op
        elif 0x50 <= num <= 0x6F:
            categories["encoding"][hex_key] = op
        elif 0x70 <= num <= 0x8F:
            categories["hash"][hex_key] = op
        elif 0x90 <= num <= 0xAF:
            categories["signature"][hex_key] = op
        elif 0xB0 <= num <= 0xCF:
            categories["transform"][hex_key] = op
        elif 0xD0 <= num <= 0xEF:
            categories["custom"][hex_key] = op
        elif 0xF0 <= num <= 0xFE:
            categories["reserved"][hex_key] = op
        elif num == 0xFF:
            categories["terminal"][hex_key] = op

    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def build_operation_spec():
    """Build the complete operation specification from protobuf."""
    log_info("🔧 Building operation specification from protobuf")

    # Get the Operation enum descriptor
    operation_enum = operations_pb2.Operation.DESCRIPTOR

    # Extract all enum values
    all_operations = {}
    for value in operation_enum.values:
        log_trace(f"Processing operation: {value.name} = 0x{value.number:02X}")
        all_operations[f"0x{value.number:02X}"] = {
            "name": value.name,
            "number": value.number,
            "decimal": value.number,
            "hex": f"0x{value.number:02X}",
            "binary": f"0b{value.number:08b}",
        }

    log_success(f"Extracted {len(all_operations)} operations")

    # Categorize operations
    categorized = categorize_operations(all_operations)

    # Build the complete specification
    spec = {
        "version": "2025.1.0",
        "source": "protobuf",
        "protobuf_package": "pspf_2025.operations",
        "description": "PSPF/2025 Operation Chain Specification (Auto-generated from protobuf)",
        "metadata": {
            "max_operations_per_chain": 8,
            "bits_per_operation": 8,
            "chain_storage_bits": 64,
            "packing_format": "Little-endian, 8 operations × 8 bits each",
            "total_operations": len(all_operations),
            "categories": list(categorized.keys()),
        },
        "operations_flat": all_operations,
        "operations_by_category": categorized,
        "operation_chains": {
            "examples": [
                {
                    "name": "raw",
                    "description": "No operations (raw data)",
                    "operations": [],
                    "packed_hex": "0x0000000000000000",
                    "packed_decimal": 0,
                },
                {
                    "name": "gzip",
                    "description": "Simple gzip compression",
                    "operations": ["OP_GZIP"],
                    "operation_numbers": [0x10],
                    "packed_hex": "0x0000000000000010",
                    "packed_decimal": 16,
                },
                {
                    "name": "tar.gz",
                    "description": "TAR archive compressed with gzip",
                    "operations": ["OP_TAR", "OP_GZIP"],
                    "operation_numbers": [0x01, 0x10],
                    "packed_hex": "0x0000000000001001",
                    "packed_decimal": 4097,
                },
                {
                    "name": "tar.bz2",
                    "description": "TAR archive compressed with bzip2",
                    "operations": ["OP_TAR", "OP_BZIP2"],
                    "operation_numbers": [0x01, 0x13],
                    "packed_hex": "0x0000000000001301",
                    "packed_decimal": 4865,
                },
                {
                    "name": "tar.zst",
                    "description": "TAR archive compressed with zstandard",
                    "operations": ["OP_TAR", "OP_ZSTD"],
                    "operation_numbers": [0x01, 0x1B],
                    "packed_hex": "0x0000000000001b01",
                    "packed_decimal": 6913,
                },
                {
                    "name": "encrypted_archive",
                    "description": "Encrypted compressed TAR archive",
                    "operations": ["OP_TAR", "OP_GZIP", "OP_AES256_GCM"],
                    "operation_numbers": [0x01, 0x10, 0x31],
                    "packed_hex": "0x0000000000311001",
                    "packed_decimal": 3215361,
                },
            ],
            "packing_algorithm": {
                "description": "Pack up to 8 operations into a 64-bit integer",
                "formula": "packed = sum(op[i] << (i * 8) for i in range(min(8, len(ops))))",
                "example": {
                    "input": [0x01, 0x10, 0x31],
                    "calculation": "0x01 | (0x10 << 8) | (0x31 << 16)",
                    "result": "0x311001",
                },
            },
            "unpacking_algorithm": {
                "description": "Extract operations from a 64-bit integer",
                "formula": "ops = [(packed >> (i*8)) & 0xFF for i in range(8) if ((packed >> (i*8)) & 0xFF) != 0]",
                "example": {
                    "input": "0x311001",
                    "calculation": "[0x311001 & 0xFF, (0x311001 >> 8) & 0xFF, (0x311001 >> 16) & 0xFF]",
                    "result": [0x01, 0x10, 0x31],
                },
            },
        },
        "implementation_status": {
            "python": {
                "module": "flavor.psp.format_2025.operations",
                "functions": ["pack_operations", "unpack_operations"],
                "status": "complete",
            },
            "go": {
                "package": "github.com/provide-io/flavorpack/pkg/psp/format_2025",
                "functions": ["PackOperations", "UnpackOperations"],
                "status": "complete",
            },
            "rust": {
                "module": "psp::format_2025::operations",
                "functions": ["pack_operations", "unpack_operations"],
                "status": "pending",
            },
        },
    }

    return spec


def export_to_json(spec: dict, output_path: Path):
    """Export specification to JSON format."""
    log_info(f"📝 Exporting to JSON: {output_path}")

    with open(output_path, "w") as f:
        json.dump(spec, f, indent=2, sort_keys=False)

    log_success(f"Wrote {output_path.stat().st_size} bytes to {output_path}")


def export_to_yaml(spec: dict, output_path: Path):
    """Export specification to YAML format."""
    log_info(f"📝 Exporting to YAML: {output_path}")

    with open(output_path, "w") as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False, width=120)

    log_success(f"Wrote {output_path.stat().st_size} bytes to {output_path}")


def export_operation_names_only():
    """Export just the operation names and numbers for quick reference."""
    log_info("📋 Exporting operation names reference")

    names = {}
    for value in operations_pb2.Operation.DESCRIPTOR.values:
        names[value.name] = {"value": value.number, "hex": f"0x{value.number:02X}"}

    output_path = Path("spec/pspf_2025/operation_names.json")
    with open(output_path, "w") as f:
        json.dump(names, f, indent=2, sort_keys=True)

    log_success(f"Exported {len(names)} operation names to {output_path}")

    # Also create a simple mapping file
    mapping = {value.name: value.number for value in operations_pb2.Operation.DESCRIPTOR.values}
    mapping_path = Path("spec/pspf_2025/operation_mapping.json")
    with open(mapping_path, "w") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)

    log_success(f"Exported operation mapping to {mapping_path}")


def main():
    """Generate operation specifications from protobuf."""
    log_info("🚀 Starting protobuf specification export")
    log_info("=" * 60)

    # Build the specification
    spec = build_operation_spec()

    # Create output directory
    output_dir = Path("spec/pspf_2025")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export to JSON
    json_path = output_dir / "operations_protobuf_spec.json"
    export_to_json(spec, json_path)

    # Export to YAML
    yaml_path = output_dir / "operations_protobuf_spec.yaml"
    export_to_yaml(spec, yaml_path)

    # Export simplified versions
    export_operation_names_only()

    # Print summary
    log_info("=" * 60)
    log_success("✨ Protobuf specification export complete!")
    log_info("📁 Generated files:")
    log_info(f"   • {json_path}")
    log_info(f"   • {yaml_path}")
    log_info("   • spec/pspf_2025/operation_names.json")
    log_info("   • spec/pspf_2025/operation_mapping.json")

    # Print some statistics
    log_info("📊 Statistics:")
    log_info(f"   • Total operations: {len(spec['operations_flat'])}")
    log_info(f"   • Categories: {len(spec['operations_by_category'])}")
    log_info(f"   • Example chains: {len(spec['operation_chains']['examples'])}")


if __name__ == "__main__":
    main()
