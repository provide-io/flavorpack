"""Memray test fixtures and runner stub (replaces wrknv.memray dependency)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Runner implementation
# ---------------------------------------------------------------------------


def _run_memray_stress(
    script: str,
    baseline_key: str,
    output_dir: Path,
    baselines: dict,
    baselines_path: Path,
) -> None:
    """Run a memray stress script and compare .bin file size against baseline."""
    name = Path(script).stem
    output_bin = Path(output_dir) / f"{name}.bin"

    result = subprocess.run(
        ["uv", "run", "memray", "run", "--force", "-o", str(output_bin), script],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"Stress script failed:\n{result.stderr[-500:]}"
    assert output_bin.exists(), "memray output .bin not created"

    current_size = output_bin.stat().st_size
    update_baseline = os.environ.get("MEMRAY_UPDATE_BASELINE") == "1"

    if baseline_key in baselines and not update_baseline:
        baseline_size = baselines[baseline_key]
        if baseline_size > 0:
            increase_pct = (current_size - baseline_size) / baseline_size * 100
            assert increase_pct <= 10, (
                f"Memory regression in {name}: {increase_pct:.1f}% increase "
                f"({baseline_size:,} → {current_size:,} bytes)"
            )
    else:
        baselines[baseline_key] = current_size
        baselines_path.write_text(json.dumps(baselines, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Stub wrknv.memray.runner so test files can import from it unchanged
# ---------------------------------------------------------------------------

_runner_mod = types.ModuleType("wrknv.memray.runner")
_runner_mod.run_memray_stress = _run_memray_stress  # type: ignore[attr-defined]

_memray_mod = types.ModuleType("wrknv.memray")
_memray_mod.runner = _runner_mod  # type: ignore[attr-defined]

_wrknv_mod = types.ModuleType("wrknv")
_wrknv_mod.memray = _memray_mod  # type: ignore[attr-defined]

sys.modules.setdefault("wrknv", _wrknv_mod)
sys.modules.setdefault("wrknv.memray", _memray_mod)
sys.modules.setdefault("wrknv.memray.runner", _runner_mod)

# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def memray_output_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Temporary directory for memray .bin output files."""
    return tmp_path_factory.mktemp("memray_output")


@pytest.fixture(scope="session")
def memray_baselines_path() -> Path:
    """Path to the persistent baselines JSON file."""
    return Path(__file__).parent / "baselines.json"


@pytest.fixture(scope="session")
def memray_baseline(memray_baselines_path: Path) -> dict:
    """Loaded baseline dict (empty dict if file is missing or empty)."""
    if memray_baselines_path.exists():
        text = memray_baselines_path.read_text().strip()
        if text:
            return json.loads(text)
    return {}
