from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_MAKEFILE = REPO_ROOT / "Makefile"
QUALITY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "05-code-quality.yml"
RUST_MAKEFILE = REPO_ROOT / "src" / "flavor-rs" / "Makefile"
RUST_FUZZ_CARGO = REPO_ROOT / "src" / "flavor-rs" / "fuzz" / "Cargo.toml"


def test_root_makefile_defines_quality_targets() -> None:
    content = ROOT_MAKEFILE.read_text()

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


def test_quality_workflow_includes_observability_jobs_and_paths() -> None:
    workflow = yaml.load(QUALITY_WORKFLOW.read_text(), Loader=yaml.BaseLoader)
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
    rust_makefile = RUST_MAKEFILE.read_text()
    fuzz_manifest = RUST_FUZZ_CARGO.read_text()

    assert "coverage:" in rust_makefile
    assert "proptest:" in rust_makefile
    assert "mutation:" in rust_makefile
    assert "cargo +nightly fuzz run pspf_operations_roundtrip" in rust_makefile
    assert "cargo +nightly fuzz run pspf_reader_no_panic" in rust_makefile

    assert 'name = "pspf_operations_roundtrip"' in fuzz_manifest
    assert 'name = "pspf_reader_no_panic"' in fuzz_manifest
