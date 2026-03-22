#!/usr/bin/env python3
"""
Memray stress test: PSPFBuilder full build cycle.

Profiles allocation patterns in:
- PSPFBuilder.create().with_keys().metadata().add_slot().build()
- Full end-to-end package construction
- Mocks load_launcher_binary since real binaries may not be available
"""

import os

os.environ.setdefault("LOG_LEVEL", "ERROR")

from pathlib import Path
import tempfile
from unittest.mock import patch

from flavor.psp.format_2025.pspf_builder import PSPFBuilder

# Mock launcher binary - must be realistic size for PE header processing
MOCK_LAUNCHER_SIZE = 124
MOCK_LAUNCHER_DATA = b"FAKE_LAUNCHER_FOR_TEST" + b"\x00" * (MOCK_LAUNCHER_SIZE - 22)


def _build_one_package(output_path: Path, iteration: int) -> None:
    """Build a single package and verify success."""
    result = (
        PSPFBuilder.create()
        .with_keys(seed="memray_stress")
        .metadata(
            format="PSPF/2025",
            package={"name": f"stress-test-{iteration}", "version": "1.0.0"},
            build={"builder": "memray/stress"},
        )
        .add_slot(
            id="test-data",
            data=f"stress test payload {iteration}" * 100,
            purpose="data",
            operations="gzip",
        )
        .build(output_path=output_path)
    )

    if not result.success:
        raise RuntimeError(f"Build failed on iteration {iteration}: {result.errors}")


def stress_builder() -> None:
    """Stress test PSPFBuilder full build cycles."""
    with (
        patch(
            "flavor.psp.format_2025.metadata.assembly.load_launcher_binary",
            return_value=MOCK_LAUNCHER_DATA,
        ),
        patch(
            "flavor.psp.format_2025.writer.load_launcher_binary",
            return_value=MOCK_LAUNCHER_DATA,
        ),
    ):
        # Warmup - separate import-time allocations
        with tempfile.TemporaryDirectory() as tmpdir:
            warmup_path = Path(tmpdir) / "warmup.pspf"
            _build_one_package(warmup_path, 0)

        # 500 full build cycles
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(1, 501):
                output_path = Path(tmpdir) / f"stress_{i:04d}.pspf"
                _build_one_package(output_path, i)

                # Clean up each output file to avoid disk pressure
                if output_path.exists():
                    output_path.unlink()

    print("Builder stress test complete: 500 full build cycles")


def main() -> None:
    """Entry point."""
    stress_builder()


if __name__ == "__main__":
    main()
