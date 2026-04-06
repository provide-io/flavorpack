from __future__ import annotations

from pathlib import Path
import tomllib

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_MAKEFILE = REPO_ROOT / "Makefile"
QUALITY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "code-quality.yml"
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
RUST_MAKEFILE = REPO_ROOT / "src" / "flavor-rs" / "Makefile"
RUST_FUZZ_CARGO = REPO_ROOT / "src" / "flavor-rs" / "fuzz" / "Cargo.toml"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_root_makefile_defines_quality_targets() -> None:
    content = ROOT_MAKEFILE.read_text(encoding="utf-8")

    for target in (
        "quality-python-fast:",
        "quality-python-deep:",
        "quality-go-fast:",
        "quality-go-deep:",
        "quality-rust-fast:",
        "quality-rust-deep:",
        "quality-ci:",
    ):
        assert target in content

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
    ):
        assert target in content


def test_quality_workflow_includes_observability_jobs_and_paths() -> None:
    workflow = yaml.load(QUALITY_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    pull_request_paths = workflow["on"]["pull_request"]["paths"]

    for job_name in (
        "python-quality-observability",
        "go-quality-observability",
        "rust-quality-observability",
        "quality-observability-report",
    ):
        assert job_name in jobs

    for workflow_path in (
        "Makefile",
        "src/flavor-go/Makefile",
        "src/flavor-rs/Makefile",
        "src/flavor-rs/fuzz/**",
        "src/flavor-go/go.mod",
        "src/flavor-rs/Cargo.toml",
        "src/flavor-rs/fuzz/Cargo.toml",
    ):
        assert workflow_path in pull_request_paths


def test_rust_quality_surface_defines_real_fuzz_targets() -> None:
    rust_makefile = RUST_MAKEFILE.read_text(encoding="utf-8")
    fuzz_manifest = RUST_FUZZ_CARGO.read_text(encoding="utf-8")

    assert "coverage:" in rust_makefile
    assert "proptest:" in rust_makefile
    assert "mutation:" in rust_makefile
    assert "cargo +nightly fuzz run pspf_operations_roundtrip" in rust_makefile
    assert "cargo +nightly fuzz run pspf_reader_no_panic" in rust_makefile

    assert 'name = "pspf_operations_roundtrip"' in fuzz_manifest
    assert 'name = "pspf_reader_no_panic"' in fuzz_manifest


def test_release_workflow_uses_trusted_publishing_for_pypi() -> None:
    workflow = yaml.load(RELEASE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    publish_testpypi = workflow["jobs"]["publish-testpypi"]
    publish_pypi = workflow["jobs"]["publish-pypi"]

    assert publish_testpypi["permissions"]["id-token"] == "write"
    assert publish_pypi["permissions"]["id-token"] == "write"

    testpypi_publish = publish_testpypi["steps"][-1]
    pypi_publish = publish_pypi["steps"][-1]

    assert testpypi_publish["uses"] == "pypa/gh-action-pypi-publish@release/v1"
    assert pypi_publish["uses"] == "pypa/gh-action-pypi-publish@release/v1"

    assert testpypi_publish["with"]["password"] == "${{ secrets.TEST_PYPI_API_TOKEN }}"
    assert "password" not in pypi_publish["with"]


def test_quality_workflow_avoids_broken_python_heredoc_summary_snippet() -> None:
    content = QUALITY_WORKFLOW.read_text(encoding="utf-8")

    assert "python3 - <<'PY' >> $GITHUB_STEP_SUMMARY" not in content
    assert "python3 -c " in content


def test_mutmut_copies_cross_language_and_workflow_support_files() -> None:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    also_copy = set(config["tool"]["mutmut"]["also_copy"])

    assert {
        "VERSION",
        "Makefile",
        "scripts",
        "tools",
        ".github/workflows",
        "src/flavor-go",
        "src/flavor-rs",
    }.issubset(also_copy)
