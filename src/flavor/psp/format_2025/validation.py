#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF build validation helpers.

All validation functions are pure and return lists of error messages.
"""

from pathlib import Path
from typing import Any

from flavor.psp.format_2025.slots import SlotMetadata
from flavor.psp.format_2025.spec import BuildSpec


def validate_spec(spec: BuildSpec) -> list[str]:
    """
    Validate a complete build specification.

    Returns list of validation errors, empty if valid.
    """
    errors = []

    # Validate metadata
    metadata_errors = validate_metadata(spec.metadata)
    errors.extend(metadata_errors)

    # Validate slots
    slot_errors = validate_slots(spec.slots)
    errors.extend(slot_errors)

    # Validate that we have at least something to package
    if not spec.slots and not spec.metadata.get("allow_empty", False):
        errors.append("📦 Package must have at least one slot unless allow_empty is set")

    return errors


def _extract_metadata_field(metadata: dict[str, Any], field: str) -> tuple[bool, Any]:
    """Extract a field from metadata, checking both root and nested 'package' locations."""
    if field in metadata:
        return True, metadata[field]
    pkg = metadata.get("package")
    if isinstance(pkg, dict) and field in pkg:
        return True, pkg[field]
    return False, None


def validate_metadata(metadata: dict[str, Any]) -> list[str]:
    """
    Validate package metadata.

    Ensures required fields are present and valid.
    """
    errors: list[str] = []

    # Check for package name (required)
    has_name, name = _extract_metadata_field(metadata, "name")
    if not has_name:
        errors.append("📛 Package name is required but not found in metadata")
    elif not name or not str(name).strip():
        errors.append("📛 Package name cannot be empty")

    # Validate version if present
    has_version, version = _extract_metadata_field(metadata, "version")
    if has_version and version and not str(version).strip():
        errors.append("🏷️ Package version cannot be empty if provided")

    # Validate format if specified
    if "format" in metadata:
        format_str = metadata["format"]
        if format_str not in ["PSPF/2025", "PSPF/2024"]:
            errors.append(f"📐 Invalid format '{format_str}', expected 'PSPF/2025'")

    return errors


_VALID_PURPOSES = frozenset(
    [
        "data",
        "payload",
        "code",
        "runtime",
        "config",
        "tool",
        "media",
        "asset",
        "library",
        "binary",
        "installer",
    ]
)

_VALID_LIFECYCLES = frozenset(
    [
        "init",
        "startup",
        "runtime",
        "shutdown",
        "cache",
        "temp",
        "lazy",
        "eager",
        "dev",
        "config",
        "platform",
        "persistent",
        "volatile",
        "temporary",
    ]
)


def _validate_slot_identity(slot: SlotMetadata, seen_indices: set[int], seen_names: set[str]) -> list[str]:
    """Validate slot index and name uniqueness."""
    errors: list[str] = []
    if slot.index in seen_indices:
        errors.append(f"🔢 Duplicate slot index {slot.index} for slot '{slot.id}'")
    seen_indices.add(slot.index)

    if not slot.id or not slot.id.strip():
        errors.append(f"📝 Slot at index {slot.index} has empty name")
    elif slot.id in seen_names:
        errors.append(f"📝 Duplicate slot name '{slot.id}'")
    seen_names.add(slot.id)
    return errors


def _validate_slot_source(slot: SlotMetadata) -> list[str]:
    """Validate slot source path if provided."""
    if not slot.source:
        return []
    source_path = Path(slot.source)
    if not source_path.exists():
        return [f"🔍 Slot {slot.id}: Source path does not exist: {slot.source}"]
    if not source_path.is_file() and not source_path.is_dir():
        return [f"🔍 Slot {slot.id}: Source path is not a file or directory: {slot.source}"]
    return []


def _validate_single_slot(slot: SlotMetadata, seen_indices: set[int], seen_names: set[str]) -> list[str]:
    """Validate a single slot and return list of errors."""
    errors: list[str] = []

    errors.extend(_validate_slot_identity(slot, seen_indices, seen_names))

    if slot.size < 0:
        errors.append(f"📏 Slot '{slot.id}' has negative size: {slot.size}")

    if not isinstance(slot.operations, str):
        errors.append(
            f"🗜️ Slot '{slot.id}' has invalid operations type: expected string, got {type(slot.operations).__name__}"
        )

    errors.extend(_validate_slot_source(slot))

    if slot.purpose not in _VALID_PURPOSES:
        errors.append(
            f"🎯 Slot '{slot.id}' has invalid purpose '{slot.purpose}'. "
            f"Valid options: {', '.join(sorted(_VALID_PURPOSES))}"
        )

    if slot.lifecycle not in _VALID_LIFECYCLES:
        errors.append(
            f"♻️ Slot '{slot.id}' has invalid lifecycle '{slot.lifecycle}'. "
            f"Valid options: {', '.join(sorted(_VALID_LIFECYCLES))}"
        )

    if slot.checksum and not isinstance(slot.checksum, str):
        errors.append(f"🔐 Slot '{slot.id}' checksum must be a string")

    return errors


def validate_slots(slots: list[SlotMetadata]) -> list[str]:
    """
    Validate slot configurations.

    Checks for:
    - Unique indices
    - Valid paths
    - Valid codec
    - Valid sizes
    - Valid names
    """
    if not slots:
        return []

    errors: list[str] = []
    seen_indices: set[int] = set()
    seen_names: set[str] = set()

    for slot in slots:
        errors.extend(_validate_single_slot(slot, seen_indices, seen_names))

    return errors


def validate_key_config(spec: BuildSpec) -> list[str]:
    """
    Validate key configuration.

    Checks that key configuration is consistent and valid.
    """
    errors = []
    key_config = spec.keys

    # If explicit keys provided, both must be present
    if key_config.private_key or key_config.public_key:
        if not (key_config.private_key and key_config.public_key):
            errors.append("🔑 When providing explicit keys, both private and public keys are required")

        # Check key sizes (Ed25519 keys)
        if key_config.private_key and len(key_config.private_key) != 32:
            errors.append(f"🔑 Private key must be 32 bytes for Ed25519, got {len(key_config.private_key)}")
        if key_config.public_key and len(key_config.public_key) != 32:
            errors.append(f"🔑 Public key must be 32 bytes for Ed25519, got {len(key_config.public_key)}")

    # If key path provided, check it exists
    if key_config.key_path:
        if not key_config.key_path.exists():
            errors.append(f"🔑 Key path does not exist: {key_config.key_path}")
        elif not key_config.key_path.is_dir():
            errors.append(f"🔑 Key path must be a directory: {key_config.key_path}")

    return errors


def validate_build_options(spec: BuildSpec) -> list[str]:
    """
    Validate build options.

    Checks that build options are consistent and valid.
    """
    errors = []
    options = spec.options

    # Check compression level
    if options.compression_level < 0 or options.compression_level > 9:
        errors.append(f"🗜️ Compression level must be 0-9, got {options.compression_level}")

    # Check page alignment consistency
    if options.page_aligned and not options.enable_mmap:
        errors.append("⚠️ Page-aligned option should be used with memory mapping enabled")

    return errors


def validate_complete(spec: BuildSpec) -> list[str]:
    """
    Complete validation of build specification.

    Runs all validation checks and returns combined errors.
    """
    errors = []

    # Run all validations
    errors.extend(validate_spec(spec))
    errors.extend(validate_key_config(spec))
    errors.extend(validate_build_options(spec))

    return errors


# 🌶️📦🔚
