#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF Fluent Builder - Immutable builder pattern for PSPF packages.

Provides a chainable API for constructing build specifications.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

import attrs

from flavor.exceptions import BuildError

# Avoid circular import - import build_package in build method
from flavor.psp.format_2025.slots import SlotMetadata
from flavor.psp.format_2025.spec import BuildResult, BuildSpec, KeyConfig


class PSPFBuilder:
    """
    Immutable fluent builder interface for PSPF packages.

    Provides a chainable API for constructing build specifications.
    """

    def __init__(self, spec: BuildSpec | None = None) -> None:
        """Initialize with optional starting specification."""
        self._spec = spec or BuildSpec()

    @classmethod
    def create(cls) -> PSPFBuilder:
        """Create a new builder instance."""
        return cls()

    def metadata(self, **kwargs: Any) -> PSPFBuilder:
        """
        Set metadata fields.

        Merges provided kwargs with existing metadata.
        """
        new_spec = self._spec.with_metadata(**kwargs)
        return PSPFBuilder(new_spec)

    def add_slot(
        self,
        id: str,
        data: bytes | str | Path,
        purpose: str = "data",
        lifecycle: str = "runtime",
        operations: str = "gzip",
        target: str | None = None,
        permissions: str | None = None,
    ) -> PSPFBuilder:
        """
        Add a slot to the package.

        Args:
            id: Slot identifier
            data: Slot data (bytes, string, or path to file/directory)
            purpose: Slot purpose (data, code, config, media)
            lifecycle: Slot lifecycle (runtime, cached, temporary)
            operations: Operation chain (e.g., "tar.gz", "TAR|GZIP")
            target: Target location relative to workenv (default: None)
            permissions: Unix permissions as octal string (e.g., "0755")
        """
        # Determine path and size
        if isinstance(data, bytes):
            # Write to temp file securely
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(data)
                temp_path = Path(temp_file.name)
            path = temp_path
            size = len(data)
        elif isinstance(data, str):
            # Write string to temp file securely
            with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as temp_file:
                temp_file.write(data)
                temp_path = Path(temp_file.name)
            path = temp_path
            size = len(data.encode("utf-8"))
        elif isinstance(data, Path):
            path = data
            size = path.stat().st_size if path.exists() else 0
        else:
            raise BuildError(f"Invalid data type: {type(data)}")

        # Create slot metadata
        slot = SlotMetadata(
            index=len(self._spec.slots),
            id=id,
            source=str(path) if path else "",
            target=target or id,
            size=size,
            checksum="",  # Will be calculated during build
            operations=operations,
            purpose=purpose,
            lifecycle=lifecycle,
            permissions=permissions,
        )

        new_spec = self._spec.with_slot(slot)
        return PSPFBuilder(new_spec)

    def with_keys(
        self,
        seed: str | None = None,
        private: bytes | None = None,
        public: bytes | None = None,
        path: Path | None = None,
    ) -> PSPFBuilder:
        """
        Configure signing keys.

        Args:
            seed: Seed for deterministic key generation
            private: Explicit private key bytes
            public: Explicit public key bytes
            path: Path to load keys from
        """
        key_config = KeyConfig(private_key=private, public_key=public, key_seed=seed, key_path=path)
        new_spec = self._spec.with_keys(key_config)
        return PSPFBuilder(new_spec)

    def with_options(self, **kwargs: Any) -> PSPFBuilder:
        """
        Set build options.

        Supported options:
        - enable_mmap: Enable memory-mapped access
        - page_aligned: Align slots to page boundaries
        - strip_binaries: Strip debug symbols from binaries
        - compression: Compression type (none, gzip)
        - compression_level: Compression level (0-9)
        - launcher_bin: Path to launcher binary
        - reproducible: Enable reproducible builds
        """
        # Create new options with updates
        current_options = self._spec.options
        new_options = attrs.evolve(current_options, **kwargs)
        new_spec = self._spec.with_options(new_options)
        return PSPFBuilder(new_spec)

    def build(self, output_path: str | Path) -> BuildResult:
        """
        Build the package.

        Args:
            output_path: Path where package should be written

        Returns:
            BuildResult with success status and any errors
        """
        if isinstance(output_path, str):
            output_path = Path(output_path)

        try:
            # Import here to avoid circular import
            from flavor.psp.format_2025.builder import build_package

            return build_package(self._spec, output_path)
        except (BuildError, ValueError) as e:
            # Convert exceptions to BuildResult format
            from flavor.psp.format_2025.spec import BuildResult

            return BuildResult(success=False, errors=[str(e)])


# 🌶️📦🔚
