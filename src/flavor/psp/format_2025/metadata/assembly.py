#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Metadata assembly for PSPF packages."""

from __future__ import annotations

import datetime
from pathlib import Path
import socket
from typing import Any

from provide.foundation.crypto import format_checksum as calculate_checksum
from provide.foundation.platform import get_arch_name, get_os_name, get_platform_string
from provide.foundation.utils import get_version

from flavor.psp.format_2025.spec import BuildSpec
from flavor.psp.metadata.paths import validate_metadata_dict

# Default version for launcher when extraction fails
DEFAULT_LAUNCHER_VERSION = "unknown"


def get_flavor_version() -> str:
    """Get the version of flavor-python from VERSION file or package metadata."""
    return get_version("flavorpack", caller_file=__file__)


def load_launcher_binary(launcher_type: str) -> bytes:
    """Load launcher binary for the specified type."""
    import os

    platform_str = get_platform_string()

    # Map launcher types to binary names
    launcher_map = {
        "rust": "flavor-rs-launcher",
        "go": "flavor-go-launcher",
        "python": "flavor-rs-launcher",  # Python uses Rust launcher
        "node": "flavor-rs-launcher",  # Node uses Rust launcher
    }

    launcher_base = launcher_map.get(launcher_type, "flavor-rs-launcher")

    # Try both platform-specific and generic names
    launcher_names = [
        f"{launcher_base}-{platform_str}",  # Platform-specific first
        launcher_base,  # Generic fallback
    ]

    # Get XDG_CACHE_HOME with fallback to ~/.cache
    xdg_cache = os.environ.get("XDG_CACHE_HOME", str(Path("~/.cache").expanduser()))

    # Search paths - prioritize helpers/bin first, then XDG cache location
    base_search_paths = [
        Path.cwd() / "dist" / "bin",  # Built binaries (make build-helpers)
        Path.cwd() / "helpers" / "bin",
        Path.cwd().parent / "helpers" / "bin",
        Path.cwd().parent.parent / "helpers" / "bin",  # For tests
        Path(xdg_cache) / "flavor" / "helpers" / "bin",  # XDG cache location
        Path.home() / ".cache" / "flavor" / "helpers" / "bin",  # Fallback cache
        Path.cwd() / "workenv" / "flavors" / platform_str,
        Path.cwd() / "helpers" / "bin",  # Development helpers
        Path.cwd() / "src" / "flavor" / "helpers" / "bin",  # Installed helpers
        Path.cwd(),
    ]

    # Try each launcher name in each search path
    for base_path in base_search_paths:
        for launcher_name in launcher_names:
            path = base_path / launcher_name
            if path.exists():
                data = path.read_bytes()
                assert isinstance(data, bytes)
                return data

    # Build helpful error message showing all searched paths
    searched_paths = []
    for base_path in base_search_paths:
        for launcher_name in launcher_names:
            searched_paths.append(str(base_path / launcher_name))

    raise FileNotFoundError(
        f"❌ Could not find {launcher_base} binary!\n"
        "\n"
        "   • cd helpers && ./build.sh     (build both Go and Rust launchers)\n"
        "   • make build-helpers           (if using make)\n"
        "   • flavor helpers build         (if flavor CLI is available)\n"
        "\n"
        "💡 Or specify a custom launcher with:\n"
        "   • --launcher-bin /path/to/launcher (command line)\n"
        "   • FLAVOR_LAUNCHER_BIN=/path/to/launcher (environment variable)\n"
        "\n"
        f"🔍 Searched {len(searched_paths)} locations including:\n"
        f"   • {searched_paths[0] if searched_paths else 'No paths'}\n"
        f"   • {searched_paths[1] if len(searched_paths) > 1 else '...'}\n"
        f"   • {searched_paths[2] if len(searched_paths) > 2 else '...'}\n"
        f"   • ... and {len(searched_paths) - 3} more"
        if len(searched_paths) > 3
        else ""
    )


def extract_launcher_version(launcher_data: bytes) -> str:
    """Extract version from launcher binary.

    Looks for common version string patterns in the binary.
    """
    import re

    # Try to find version strings in the binary
    # Look for patterns like "flavor-go-launcher 0.3.0" or "flavor-rs-launcher/1.0.0"
    patterns = [
        rb"flavor-[\w-]+launcher[\s/]+([\d.]+)",  # flavor-go-launcher 0.3.0
        rb"version[:\s]+([\d.]+)",  # version: 1.0.0
        rb"v([\d.]+)",  # v1.0.0
    ]

    # Search in first 100KB of binary to avoid scanning entire file
    search_data = launcher_data[:102400] if len(launcher_data) > 102400 else launcher_data

    for pattern in patterns:
        match = re.search(pattern, search_data, re.IGNORECASE)
        if match:
            version = match.group(1).decode("utf-8", errors="ignore")
            # Validate it looks like a version
            if re.match(r"^\d+\.\d+(\.\d+)?", version):
                return version

    # Fallback to unknown version
    return DEFAULT_LAUNCHER_VERSION


def get_launcher_capabilities(launcher_type: str) -> list[str]:
    """Get capabilities for launcher type."""
    capabilities_map = {
        "rust": ["mmap", "async", "sandbox"],
        "go": ["mmap", "async"],
        "python": ["mmap", "async", "sandbox"],
        "node": ["mmap", "async", "sandbox"],
    }
    return capabilities_map.get(launcher_type, ["mmap"])


def get_launcher_info(launcher_type: str) -> dict[str, Any]:
    """Get launcher binary and metadata."""
    launcher_data = load_launcher_binary(launcher_type)

    # Map launcher types to tool names
    launcher_map = {
        "rust": "flavor-rs-launcher",
        "go": "flavor-go-launcher",
        "python": "flavor-rs-launcher",
        "node": "flavor-rs-launcher",
    }

    tool_name = launcher_map.get(launcher_type, "flavor-rs-launcher")
    checksum = calculate_checksum(launcher_data, "sha256")

    return {
        "data": launcher_data,
        "tool": tool_name,
        "tool_version": extract_launcher_version(launcher_data),
        "checksum": checksum,
        "capabilities": get_launcher_capabilities(launcher_type),
    }


def create_build_metadata(deterministic: bool = False) -> dict[str, Any]:
    """Create build section metadata."""
    platform_info: dict[str, Any] = {
        "os": get_os_name(),
        "arch": get_arch_name(),
    }

    build_meta: dict[str, Any] = {
        "tool": "flavor-python",
        "tool_version": get_flavor_version(),
        "deterministic": deterministic,
        "platform": platform_info,
    }

    # Only add non-deterministic fields if not in deterministic mode
    if not deterministic:
        build_meta["timestamp"] = datetime.datetime.now(datetime.UTC).isoformat()
        platform_info["host"] = socket.gethostname()
    else:
        # Use fixed timestamp for deterministic builds
        build_meta["timestamp"] = "2025-01-01T00:00:00+00:00"
        platform_info["host"] = "deterministic-build"

    return build_meta


def create_launcher_metadata(launcher_info: dict[str, Any]) -> dict[str, Any]:
    """Create launcher section metadata from launcher info."""
    return {
        "tool": launcher_info["tool"],
        "tool_version": launcher_info["tool_version"],
        "size": len(launcher_info["data"]),
        "checksum": f"sha256:{launcher_info['checksum']}",
        "capabilities": launcher_info["capabilities"],
    }


def create_verification_metadata(spec: BuildSpec) -> dict[str, Any]:
    """Create verification section metadata."""
    # Always require verification - use FLAVOR_VALIDATION environment variable to control behavior
    verification = {
        "integrity_seal": {"required": True, "algorithm": "ed25519"},
        "signed": True,
        "require_verification": True,
    }

    # If trust_signatures was provided in spec metadata, include it
    if "verification" in spec.metadata and "trust_signatures" in spec.metadata["verification"]:
        verification["trust_signatures"] = spec.metadata["verification"]["trust_signatures"]

    return verification


def detect_features_used(spec: BuildSpec) -> list[str]:
    """Detect which PSPF features are used in this package."""
    features = []

    if "workenv" in spec.metadata and "directories" in spec.metadata["workenv"]:
        features.append("workenv_dirs")

    if "runtime" in spec.metadata and "env" in spec.metadata["runtime"]:
        features.append("runtime_env")

    if spec.metadata.get("setup_commands"):
        features.append("setup_commands")

    if "cache_validation" in spec.metadata:
        features.append("cache_validation")

    # Check for volatile slots
    for slot in spec.slots:
        if hasattr(slot, "lifecycle") and slot.lifecycle == "volatile":
            features.append("volatile_slots")
            break

    return features


def assemble_metadata(spec: BuildSpec, slots: list[Any], launcher_info: dict[str, Any]) -> dict[str, Any]:
    """Assemble complete metadata structure."""
    # Core metadata
    metadata = {
        "format": "PSPF/2025",
        "format_version": "1.0.0",
        "package": spec.metadata.get("package", {}),
        "slots": [slot.metadata.to_dict() for slot in slots],
        "execution": spec.metadata.get("execution", {}),
        "verification": create_verification_metadata(spec),
        "build": create_build_metadata(deterministic=spec.keys.key_seed is not None),
        "launcher": create_launcher_metadata(launcher_info),
        "compatibility": {
            "min_format_version": "1.0.0",
            "features": detect_features_used(spec),
        },
    }

    # Add optional sections if present
    for section in ["cache_validation", "setup_commands", "runtime", "workenv"]:
        if section in spec.metadata:
            metadata[section] = spec.metadata[section]

    # Validate all paths use {workenv}
    return validate_metadata_dict(metadata)


# 🌶️📦🔚
