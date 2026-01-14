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


def validate_metadata(metadata: dict[str, Any]) -> list[str]:  # noqa: C901
    """
    Validate package metadata.

    Ensures required fields are present and valid.
    """
    errors = []

    # Check for package name (required)
    has_name = False
    name = None

    # Check various possible locations for name
    if "name" in metadata:
        has_name = True
        name = metadata["name"]
    elif "package" in metadata and isinstance(metadata["package"], dict):
        if "name" in metadata["package"]:
            has_name = True
            name = metadata["package"]["name"]

    if not has_name:
        errors.append("📛 Package name is required but not found in metadata")
    elif not name or not str(name).strip():
        errors.append("📛 Package name cannot be empty")

    # Validate version if present
    version = None
    if "version" in metadata:
        version = metadata["version"]
    elif "package" in metadata and isinstance(metadata["package"], dict) and "version" in metadata["package"]:
        version = metadata["package"]["version"]

    if version and not str(version).strip():
        errors.append("🏷️ Package version cannot be empty if provided")

    # Validate format if specified
    if "format" in metadata:
        format_str = metadata["format"]
        if format_str not in ["PSPF/2025", "PSPF/2024"]:
            errors.append(f"📐 Invalid format '{format_str}', expected 'PSPF/2025'")

    return errors


def validate_slots(slots: list[SlotMetadata]) -> list[str]:  # noqa: C901
    """
    Validate slot configurations.

    Checks for:
    - Unique indices
    - Valid paths
    - Valid codec
    - Valid sizes
    - Valid names
    """
    errors: list[str] = []

    if not slots:
        return errors  # Empty slots is valid

    seen_indices = set()
    seen_names = set()

    for _i, slot in enumerate(slots):
        # Check index uniqueness
        if slot.index in seen_indices:
            errors.append(f"🔢 Duplicate slot index {slot.index} for slot '{slot.id}'")
        seen_indices.add(slot.index)

        # Check name validity
        if not slot.id or not slot.id.strip():
            errors.append(f"📝 Slot at index {slot.index} has empty name")
        elif slot.id in seen_names:
            errors.append(f"📝 Duplicate slot name '{slot.id}'")
        seen_names.add(slot.id)

        # Check size validity
        if slot.size < 0:
            errors.append(f"📏 Slot '{slot.id}' has negative size: {slot.size}")

        # Check operations validity
        # Operations field is a string like "tar.gz" or "TAR|GZIP"
        if not isinstance(slot.operations, str):
            errors.append(
                f"🗜️ Slot '{slot.id}' has invalid operations type: expected string, got {type(slot.operations).__name__}"
            )

        # Check source path existence if provided
        if slot.source:
            source_path = Path(slot.source)
            if not source_path.exists():
                errors.append(f"🔍 Slot {slot.id}: Source path does not exist: {slot.source}")
            elif not source_path.is_file() and not source_path.is_dir():
                errors.append(f"🔍 Slot {slot.id}: Source path is not a file or directory: {slot.source}")

        # Check purpose validity
        valid_purposes = [
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
        if slot.purpose not in valid_purposes:
            errors.append(
                f"🎯 Slot '{slot.id}' has invalid purpose '{slot.purpose}'. "
                f"Valid options: {', '.join(valid_purposes)}"
            )

        # Check lifecycle validity
        valid_lifecycles = [
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
            "temporary",  # New names
        ]
        if slot.lifecycle not in valid_lifecycles:
            errors.append(
                f"♻️ Slot '{slot.id}' has invalid lifecycle '{slot.lifecycle}'. "
                f"Valid options: {', '.join(valid_lifecycles)}"
            )

        # Check checksum format if provided
        if slot.checksum and not isinstance(slot.checksum, str):
            errors.append(f"🔐 Slot '{slot.id}' checksum must be a string")

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
