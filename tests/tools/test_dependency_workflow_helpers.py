from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


def _find_repo_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "VERSION").is_file() and (candidate / "ci").is_dir():
            return candidate

    raise FileNotFoundError(f"Could not locate repository root from {start}")


def _load_module(module_name: str, relative_path: str) -> ModuleType:
    repo_root = _find_repo_root(Path(__file__))
    script_path = repo_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_REPORTING = _load_module("dependency_workflow_reporting", "ci/dependency_workflow_lib/reporting.py")


def test_render_dependency_report_marks_vulnerabilities_and_updates() -> None:
    markdown, summary = _REPORTING.render_dependency_report(
        repository="provide-io/flavorpack",
        run_id="12345",
        timestamp="2026-04-07 12:00:00 UTC",
        iso_timestamp="2026-04-07T12:00:00Z",
        python_report={
            "total_dependencies": 10,
            "vulnerabilities": {"pip_audit": 1, "safety": 0},
            "updates_available": 3,
            "licenses": {"copyleft": 0},
        },
        go_has_report=True,
        go_vulnerable=True,
        go_has_updates=False,
        rust_has_report=True,
        rust_vulnerable=False,
        rust_has_updates=True,
    )

    assert "Total vulnerabilities: 2" in markdown
    assert "Python: 3 packages can be updated" in markdown
    assert summary["summary"]["total_vulnerabilities"] == 2
    assert summary["summary"]["updates_available"] == 4
