from __future__ import annotations

from pathlib import Path
import tomllib

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
ROOT_MAKEFILE = REPO_ROOT / "Makefile"
QUALITY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "code-quality.yml"


def test_pyproject_registers_shared_test_taxonomy_markers() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text())
    markers = pyproject["tool"]["pytest"]["ini_options"]["markers"]
    registered = {marker.split(":", 1)[0].strip() for marker in markers}

    for marker in {
        "unit",
        "integration",
        "cross_language",
        "security",
        "adversarial",
        "property",
        "fuzz",
        "smoke",
        "fast",
        "slow",
        "ci",
        "parity",
    }:
        assert marker in registered


def test_root_makefile_defines_intent_targets() -> None:
    content = ROOT_MAKEFILE.read_text(encoding="utf-8")

    for target in (
        "test-unit:",
        "test-integration:",
        "test-cross-language:",
        "test-security:",
        "test-adversarial:",
        "test-property:",
        "test-fuzz:",
        "test-mutation:",
        "test-smoke:",
        "test-fast:",
        "test-slow:",
        "test-security-fast:",
        "test-adversarial-fast:",
    ):
        assert target in content


def test_quality_workflow_mentions_intent_categories_in_observability_report() -> None:
    workflow = yaml.load(QUALITY_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    report_job = workflow["jobs"]["quality-observability-report"]
    run_script = report_job["steps"][0]["run"]

    for phrase in (
        "Intent Categories",
        "Unit / Integration / Cross-Language",
        "Security / Adversarial / Property",
        "Fuzz / Mutation",
    ):
        assert phrase in run_script
