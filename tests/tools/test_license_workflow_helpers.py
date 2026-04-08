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


_ANALYSIS = _load_module("license_workflow_analysis", "ci/license_workflow_lib/analysis.py")
_REPORTING = _load_module("license_workflow_reporting", "ci/license_workflow_lib/reporting.py")


def test_detect_license_type_maps_common_license_text() -> None:
    assert _ANALYSIS.detect_license_type("MIT License\nPermission is hereby granted...") == "MIT"
    assert _ANALYSIS.detect_license_type("Apache License\nVersion 2.0, January 2004") == "Apache-2.0"
    assert _ANALYSIS.detect_license_type("Mozilla Public License Version 2.0") == "MPL-2.0"
    assert _ANALYSIS.detect_license_type("completely custom terms") == "Unknown"


def test_analyze_python_licenses_separates_allowed_unknown_and_violations() -> None:
    report = _ANALYSIS.analyze_python_licenses(
        [
            {"Name": "safe-lib", "License": "MIT"},
            {"Name": "copyleft-lib", "License": "GPL-3.0-only"},
            {"Name": "mystery-lib", "License": "UNKNOWN"},
            {"Name": "pip-licenses", "License": "MIT"},
        ]
    )

    assert report.compliant == ["safe-lib: MIT"]
    assert report.violations == ["copyleft-lib: GPL-3.0-only"]
    assert report.unknown == ["mystery-lib: UNKNOWN"]


def test_render_compliance_report_marks_overall_failure_when_inputs_have_issues() -> None:
    markdown, summary = _REPORTING.render_compliance_report(
        repository="provide-io/flavorpack",
        run_id="12345",
        strict_mode=False,
        project_license="MIT",
        has_license=False,
        python_compliant=False,
        python_violations=2,
        go_compliant=True,
        rust_compliant=False,
        sbom_generated=True,
        timestamp="2026-04-07 12:00:00 UTC",
        iso_timestamp="2026-04-07T12:00:00Z",
    )

    assert "License compliance issues require attention" in markdown
    assert summary["compliance"]["overall"] is False
    assert summary["violations"]["python"] == 2
    assert summary["sbom_generated"] is True
