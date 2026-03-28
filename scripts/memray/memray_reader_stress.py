#!/usr/bin/env python3
"""
Memray stress test: PSPFReader full read cycle.

Profiles allocation patterns in:
- PSPFReader context manager entry/exit
- read_index(), read_metadata(), read_slot_descriptors(), read_slot()
- Builds ONE bundle, then reads it 2000 times
- Mocks load_launcher_binary since real binaries may not be available
"""

import os

os.environ.setdefault("LOG_LEVEL", "ERROR")

from pathlib import Path
import tempfile
from unittest.mock import patch

from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader

# Mock launcher binary - must match builder stress test
MOCK_LAUNCHER_SIZE = 124
MOCK_LAUNCHER_DATA = b"FAKE_LAUNCHER_FOR_TEST" + b"\x00" * (MOCK_LAUNCHER_SIZE - 22)


def _build_test_bundle(output_path: Path) -> None:
    """Build a single test bundle for reader stress testing."""
    result = (
        PSPFBuilder.create()
        .with_keys(seed="memray_reader_stress")
        .metadata(
            format="PSPF/2025",
            package={"name": "reader-stress-test", "version": "1.0.0"},
            build={"builder": "memray/reader-stress"},
        )
        .add_slot(
            id="test-payload",
            data="reader stress test data " * 200,
            purpose="data",
            operations="gzip",
        )
        .build(output_path=output_path)
    )

    if not result.success:
        raise RuntimeError(f"Failed to build test bundle: {result.errors}")


def stress_reader() -> None:
    """Stress test PSPFReader full read cycles."""
    with (
        patch(
            "flavor.psp.format_2025.metadata.assembly.load_launcher_binary",
            return_value=MOCK_LAUNCHER_DATA,
        ),
        patch(
            "flavor.psp.format_2025.writer.load_launcher_binary",
            return_value=MOCK_LAUNCHER_DATA,
        ),
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        bundle_path = Path(tmpdir) / "reader_stress.pspf"

        # Build ONE bundle
        _build_test_bundle(bundle_path)

        # Warmup - separate import-time allocations
        with PSPFReader(bundle_path) as reader:
            reader.read_index()
            reader.read_metadata()
            reader.read_slot_descriptors()
            reader.read_slot(0)

        # 2000 full read cycles
        for _ in range(2_000):
            with PSPFReader(bundle_path) as reader:
                reader.read_index()
                reader.read_metadata()
                reader.read_slot_descriptors()
                reader.read_slot(0)

    print("Reader stress test complete: 2000 full read cycles")


def main() -> None:
    """Entry point."""
    stress_reader()


if __name__ == "__main__":
    main()
