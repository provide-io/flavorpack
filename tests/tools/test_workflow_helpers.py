from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import yaml


def _find_repo_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "VERSION").is_file() and (candidate / "ci" / "workflow_helpers.py").is_file():
            return candidate

    raise FileNotFoundError(f"Could not locate repository root from {start}")


def _load_workflow_helpers_module() -> ModuleType:
    repo_root = _find_repo_root(Path(__file__))
    script_path = repo_root / "ci" / "workflow_helpers.py"
    spec = importlib.util.spec_from_file_location("workflow_helpers", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["workflow_helpers"] = module
    spec.loader.exec_module(module)
    return module


_WORKFLOW_HELPERS = _load_workflow_helpers_module()


def test_helper_matrix_filters_requested_platforms() -> None:
    matrix = _WORKFLOW_HELPERS.build_helper_matrix("linux_amd64,windows_arm64", act=False)

    assert matrix == {
        "include": [
            {
                "platform": "linux_amd64",
                "os": "ubuntu-24.04",
                "rust_target": "x86_64-unknown-linux-musl",
                "use_musl": True,
                "emoji": "🐧",
            },
            {
                "platform": "windows_arm64",
                "os": "windows-11-arm",
                "rust_target": "aarch64-pc-windows-msvc",
                "use_musl": False,
                "emoji": "🪟",
            },
        ]
    }


def test_release_checksums_groups_wheels_and_psp(tmp_path: Path) -> None:
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "flavorpack-1.2.3-py3-none-any.whl").write_bytes(b"wheel")
    (release_dir / "flavor-1.2.3-linux_amd64.psp").write_bytes(b"psp")

    checksum_path = _WORKFLOW_HELPERS.write_release_checksums(release_dir)
    content = checksum_path.read_text(encoding="utf-8")

    assert "# SHA256 Checksums" in content
    assert "## Python Wheels" in content
    assert "## PSP Packages" in content
    assert "flavorpack-1.2.3-py3-none-any.whl" in content
    assert "flavor-1.2.3-linux_amd64.psp" in content


def test_release_notes_include_version_and_repository() -> None:
    notes = _WORKFLOW_HELPERS.render_release_notes("1.2.3", "provide-io/flavorpack")

    assert "# Flavor Pack 1.2.3" in notes
    assert "pip install flavorpack==1.2.3" in notes
    assert "https://github.com/provide-io/flavorpack/releases/download/v1.2.3/checksums.txt" in notes


def test_stage_release_directory_collects_known_artifacts(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    release_dir = tmp_path / "release"
    (artifacts_dir / "release-wheels").mkdir(parents=True)
    (artifacts_dir / "release-psp").mkdir(parents=True)
    (artifacts_dir / "release-assets").mkdir(parents=True)
    (artifacts_dir / "release-wheels" / "demo.whl").write_text("wheel", encoding="utf-8")
    (artifacts_dir / "release-psp" / "demo.psp").write_text("psp", encoding="utf-8")
    (artifacts_dir / "release-assets" / "checksums.txt").write_text("sum", encoding="utf-8")
    (artifacts_dir / "release-assets" / "release-notes.md").write_text("notes", encoding="utf-8")

    summary = _WORKFLOW_HELPERS.stage_release_directory(artifacts_dir, release_dir)

    assert summary == {"wheels": 1, "psp_packages": 1, "other": 2}
    assert (release_dir / "demo.whl").is_file()
    assert (release_dir / "demo.psp").is_file()
    assert (release_dir / "checksums.txt").is_file()
    assert (release_dir / "release-notes.md").is_file()


def test_install_platform_helpers_keeps_only_current_platform(tmp_path: Path) -> None:
    source_dir = tmp_path / "helpers"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()
    (source_dir / "flavor-go-launcher-1.2.3-linux_amd64").write_text("go", encoding="utf-8")
    (source_dir / "flavor-rs-launcher-1.2.3-linux_amd64").write_text("rs", encoding="utf-8")
    (source_dir / "flavor-rs-launcher-1.2.3-windows_amd64.exe").write_text("bad", encoding="utf-8")

    copied = _WORKFLOW_HELPERS.install_platform_helpers(
        source_dir=source_dir,
        dest_dir=dest_dir,
        version="1.2.3",
        platform="linux_amd64",
    )

    assert copied == [
        "flavor-go-launcher-1.2.3-linux_amd64",
        "flavor-rs-launcher-1.2.3-linux_amd64",
    ]
    assert sorted(path.name for path in dest_dir.iterdir()) == copied


def test_release_and_pipeline_workflows_limit_inline_shell_blocks() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflow_paths = [
        repo_root / ".github" / "workflows" / "release.yml",
        repo_root / ".github" / "workflows" / "helper-prep.yml",
        repo_root / ".github" / "workflows" / "flavor-pipeline.yml",
        repo_root / ".github" / "workflows" / "taster-pipeline.yml",
        repo_root / ".github" / "workflows" / "license-compliance.yml",
        repo_root / ".github" / "workflows" / "dependency-audit.yml",
    ]

    offenders: dict[str, list[tuple[str, int]]] = {}
    for workflow_path in workflow_paths:
        workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        workflow_offenders: list[tuple[str, int]] = []
        for _job_name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                run_block = step.get("run")
                if not isinstance(run_block, str):
                    continue
                non_empty = [line for line in run_block.splitlines() if line.strip()]
                if len(non_empty) > 5:
                    workflow_offenders.append((step.get("name", "<unnamed>"), len(non_empty)))
        if workflow_offenders:
            offenders[str(workflow_path.relative_to(repo_root))] = workflow_offenders

    assert offenders == {}


def test_flavor_and_taster_matrices_are_json_serializable() -> None:
    flavor_matrix = _WORKFLOW_HELPERS.build_flavor_test_matrix()
    taster_matrix = _WORKFLOW_HELPERS.build_taster_test_matrix()

    assert json.loads(json.dumps(flavor_matrix)) == flavor_matrix
    assert json.loads(json.dumps(taster_matrix)) == taster_matrix
