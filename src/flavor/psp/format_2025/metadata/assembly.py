#!/usr/bin/env python3
"""Metadata assembly for PSPF packages."""

import datetime
from pathlib import Path
import socket
from typing import Any

from flavor.psp.format_2025.checksums import calculate_checksum
from flavor.psp.format_2025.spec import BuildSpec
from flavor.psp.metadata.paths import validate_metadata_dict
from flavor.utils import get_arch_name, get_os_name, get_platform_string


def get_flavor_version() -> str:
    """Get the version of flavor-python."""
    # TODO: Get from package version
    return "1.0.0"


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
    xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))

    # Search paths - prioritize helpers/bin first, then XDG cache location
    base_search_paths = [
        Path.cwd() / "helpers" / "bin",
        Path.cwd().parent / "helpers" / "bin",
        Path.cwd().parent.parent / "helpers" / "bin",  # For tests
        Path(xdg_cache) / "flavor" / "helpers" / "bin",  # XDG cache location
        Path.home() / ".cache" / "flavor" / "helpers" / "bin",  # Fallback cache
        Path.cwd() / "workenv" / "flavors" / platform_str,
        Path.cwd(),
    ]

    # Try each launcher name in each search path
    for base_path in base_search_paths:
        for launcher_name in launcher_names:
            path = base_path / launcher_name
            if path.exists():
                return path.read_bytes()

    # Build helpful error message showing all searched paths
    searched_paths = []
    for base_path in base_search_paths:
        for launcher_name in launcher_names:
            searched_paths.append(str(base_path / launcher_name))

    raise FileNotFoundError(
        f"Could not find {launcher_base} binary. "
        f"Build it first with 'flavor helpers build'. "
        f"Searched paths: {', '.join(searched_paths[:3])}..."
    )


def extract_launcher_version(launcher_data: bytes) -> str:
    """Extract version from launcher binary."""
    # TODO: Implement actual version extraction from binary
    # Could look for version strings or embedded metadata
    return "1.0.0"


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
    build_meta = {
        "tool": "flavor-python",
        "tool_version": get_flavor_version(),
        "deterministic": deterministic,
        "platform": {
            "os": get_os_name(),
            "arch": get_arch_name(),
        },
    }

    # Only add non-deterministic fields if not in deterministic mode
    if not deterministic:
        build_meta["timestamp"] = datetime.datetime.now(datetime.UTC).isoformat()
        build_meta["platform"]["host"] = socket.gethostname()
    else:
        # Use fixed timestamp for deterministic builds
        build_meta["timestamp"] = "2025-01-01T00:00:00+00:00"
        build_meta["platform"]["host"] = "deterministic-build"

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
    # Check if insecure mode is enabled
    insecure = getattr(spec.options, "insecure_mode", False)

    # Start with base verification metadata
    verification = {
        "integrity_seal": {"required": True, "algorithm": "ed25519"},
        "signed": True,
        "require_verification": not insecure,
    }

    # If trust_signatures was provided in spec metadata, include it
    if (
        "verification" in spec.metadata
        and "trust_signatures" in spec.metadata["verification"]
    ):
        verification["trust_signatures"] = spec.metadata["verification"][
            "trust_signatures"
        ]

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


def assemble_metadata(
    spec: BuildSpec, slots: list[Any], launcher_info: dict[str, Any]
) -> dict[str, Any]:
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

    # Handle backward compatibility for tests (if old format exists)
    if "builder" in spec.metadata:
        metadata["builder"] = spec.metadata["builder"]

    if "launcher" in spec.metadata and isinstance(spec.metadata["launcher"], dict):
        # Merge old launcher metadata (for tests)
        for key, value in spec.metadata["launcher"].items():
            if key not in metadata["launcher"]:
                metadata["launcher"][key] = value

    # Validate all paths use {workenv}
    return validate_metadata_dict(metadata)
