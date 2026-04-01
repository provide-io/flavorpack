"""Memory profiling tests for XOR cipher."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.memray.conftest import run_memray_stress

pytestmark = [pytest.mark.memray, pytest.mark.slow]


def test_xor_allocations(
    memray_output_dir: Path,
    memray_baseline: dict[str, int],
    memray_baselines_path: Path,
) -> None:
    """Profile memory allocations in XOR cipher hot path."""
    run_memray_stress(
        script="scripts/memray/memray_xor_stress.py",
        baseline_key="xor_total_allocations",
        output_dir=memray_output_dir,
        baselines=memray_baseline,
        baselines_path=memray_baselines_path,
    )
