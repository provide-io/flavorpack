"""Memory profiling tests for slot descriptor."""

from __future__ import annotations

from pathlib import Path

import pytest
from wrknv.memray.runner import run_memray_stress  # ty: ignore[unresolved-import]

pytestmark = [pytest.mark.memray, pytest.mark.slow]


def test_slot_descriptor_allocations(
    memray_output_dir: Path,
    memray_baseline: dict,
    memray_baselines_path: Path,
) -> None:
    """Profile memory allocations in slot descriptor parsing."""
    run_memray_stress(
        script="scripts/memray/memray_slot_descriptor_stress.py",
        baseline_key="slot_descriptor_total_allocations",
        output_dir=memray_output_dir,
        baselines=memray_baseline,
        baselines_path=memray_baselines_path,
    )
