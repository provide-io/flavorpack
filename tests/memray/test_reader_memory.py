# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Memory profiling tests for PSPF reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.memray.conftest import run_memray_stress

pytestmark = [pytest.mark.memray, pytest.mark.slow]


def test_reader_allocations(
    memray_output_dir: Path,
    memray_baseline: dict[str, int],
    memray_baselines_path: Path,
) -> None:
    """Profile memory allocations in PSPF reader hot path."""
    run_memray_stress(
        script="scripts/memray/memray_reader_stress.py",
        baseline_key="reader_total_allocations",
        output_dir=memray_output_dir,
        baselines=memray_baseline,
        baselines_path=memray_baselines_path,
    )
