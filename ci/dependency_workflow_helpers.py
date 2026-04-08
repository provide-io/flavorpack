#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from ci.dependency_workflow_lib.reporting import render_dependency_report
from ci.license_workflow_lib.analysis import GO_IGNORE_MODULES, analyze_python_licenses, evaluate_go_compliance
from ci.license_workflow_lib.reporting import render_go_compliance
from ci.workflow_lib.common import append_step_summary, run_command, write_github_output, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Helpers for thin dependency audit workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "python-tree",
        "python-vulns",
        "python-licenses",
        "python-updates",
        "python-unused",
        "python-report",
        "go-analysis",
        "go-vulns",
        "go-licenses",
        "go-updates",
        "go-tidiness",
        "rust-analysis",
        "rust-security",
        "rust-licenses",
        "rust-updates",
        "rust-unused",
        "dependency-report",
    ):
        subparsers.add_parser(command)
    return parser.parse_args()


def _tool_path(name: str) -> str:
    venv_bin = Path(".venv") / ("Scripts" if sys.platform.startswith("win") else "bin") / name
    if venv_bin.exists():
        return str(venv_bin)
    resolved = shutil.which(name)
    if resolved:
        return resolved
    raise FileNotFoundError(f"Could not locate required command: {name}")


def _run_capture(
    cmd: list[str], cwd: Path | None = None, check: bool = False
) -> subprocess.CompletedProcess[str]:
    return run_command(cmd, cwd=cwd, check=check)


def _run_combined_to_file(cmd: list[str], output_path: Path, cwd: Path | None = None) -> int:
    completed = _run_capture(cmd, cwd=cwd, check=False)
    output_path.write_text((completed.stdout or "") + (completed.stderr or ""), encoding="utf-8")
    return completed.returncode


def _load_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _timestamp(format_string: str) -> str:
    return subprocess.run(
        ["date", "-u", format_string], capture_output=True, text=True, check=True
    ).stdout.strip()


def handle_python_tree() -> None:
    pipdeptree = _tool_path("pipdeptree")
    summary_tree = _run_capture([pipdeptree, "--warn", "silence"], check=True).stdout
    circular = _run_capture([pipdeptree, "--warn", "fail"], check=False).stdout
    tree_json = _run_capture([pipdeptree, "--json"], check=True).stdout
    Path("python-dependency-tree.json").write_text(tree_json, encoding="utf-8")
    lines = [
        "## 🐍 Python Dependency Analysis",
        "",
        "### Dependency Tree",
        "```",
        "\n".join(summary_tree.splitlines()[:100]),
        "```",
        "### Circular Dependencies Check",
        "⚠️ Circular dependencies detected!"
        if "circular" in circular.lower()
        else "✅ No circular dependencies",
    ]
    if "circular" in circular.lower():
        lines.extend(circular.splitlines()[:10])
    append_step_summary("\n".join(lines) + "\n")


def handle_python_vulns() -> None:
    pip_audit = _tool_path("pip-audit")
    safety = _tool_path("safety")
    pip_audit_run = _run_capture([pip_audit, "--format", "json"], check=False)
    Path("pip-audit-deps.json").write_text(pip_audit_run.stdout or "[]", encoding="utf-8")
    Path("pip-audit-deps.log").write_text(
        (pip_audit_run.stdout or "") + (pip_audit_run.stderr or ""), encoding="utf-8"
    )
    freeze = _run_capture([_tool_path("pip"), "freeze"], check=True).stdout
    Path("requirements-audit.txt").write_text(freeze, encoding="utf-8")
    safety_run = _run_capture([safety, "check", "--json"], check=False)
    Path("safety-deps.json").write_text(safety_run.stdout or "{}", encoding="utf-8")
    Path("safety-deps.log").write_text((safety_run.stdout or "") + (safety_run.stderr or ""), encoding="utf-8")
    pip_vulns = _count_pip_audit_vulnerabilities(Path("pip-audit-deps.json"))
    safety_vulns = _count_safety_vulnerabilities(Path("safety-deps.json"))
    lines = [
        "### Vulnerability Scan",
        "",
        "#### pip-audit Results",
        (
            f"🚨 **{pip_vulns} vulnerabilities found**"
            if pip_vulns
            else "✅ No vulnerabilities found by pip-audit"
        ),
        "#### Safety Results",
        (
            f"⚠️ **{safety_vulns} vulnerabilities found by Safety**"
            if safety_vulns
            else "✅ No vulnerabilities found by Safety"
        ),
    ]
    append_step_summary("\n".join(lines) + "\n")


def handle_python_licenses() -> None:
    pip_licenses = _tool_path("pip-licenses")
    _run_capture([pip_licenses, "--format=json", "--output-file=python-licenses.json"], check=True)
    _run_capture([pip_licenses, "--format=markdown", "--output-file=python-licenses.md"], check=True)
    _run_capture([pip_licenses, "--summary", "--output-file=license-summary.txt"], check=True)
    report = analyze_python_licenses(json.loads(Path("python-licenses.json").read_text(encoding="utf-8")))
    unknown_count = len(report.unknown)
    lines = [
        "### License Analysis",
        "",
        "#### License Summary",
        "```",
        "\n".join(Path("license-summary.txt").read_text(encoding="utf-8").splitlines()[:20]),
        "```",
        "| License Type | Count | Status |",
        "|--------------|-------|--------|",
        f"| Copyleft (GPL/AGPL/LGPL) | {len(report.violations)} | {'✅' if not report.violations else '⚠️'} |",
        f"| Unknown | {unknown_count} | {'✅' if unknown_count == 0 else '⚠️'} |",
        "",
    ]
    append_step_summary("\n".join(lines))


def handle_python_updates() -> None:
    outdated = (
        _run_capture([_tool_path("pip"), "list", "--outdated", "--format=json"], check=False).stdout or "[]"
    )
    Path("outdated-python.json").write_text(outdated, encoding="utf-8")
    updates = _load_json(Path("outdated-python.json")) or []
    count = len(updates)
    write_github_output(has_updates="true" if count else "false", update_count=str(count))
    lines = ["### Dependency Updates", ""]
    if count:
        lines.extend(
            [
                f"📦 **{count} packages have updates available**",
                "",
                "| Package | Current | Latest | Type |",
                "|---------|---------|--------|------|",
            ]
        )
        for item in updates[:20]:
            lines.append(
                f"| {item['name']} | {item['version']} | {item['latest_version']} | {item['latest_filetype']} |"
            )
    else:
        lines.append("✅ All packages are up to date")
    append_step_summary("\n".join(lines) + "\n")


def handle_python_report() -> None:
    licenses = analyze_python_licenses(_load_json(Path("python-licenses.json")) or [])
    payload = {
        "timestamp": _timestamp("+%Y-%m-%dT%H:%M:%SZ"),
        "total_dependencies": len(_load_json(Path("python-dependency-tree.json")) or []),
        "direct_dependencies": _direct_dependency_count(),
        "vulnerabilities": {
            "pip_audit": _count_pip_audit_vulnerabilities(Path("pip-audit-deps.json")),
            "safety": _count_safety_vulnerabilities(Path("safety-deps.json")),
        },
        "updates_available": len(_load_json(Path("outdated-python.json")) or []),
        "licenses": {"copyleft": len(licenses.violations), "unknown": len(licenses.unknown)},
    }
    write_json(Path("python-deps-report.json"), payload)


def handle_python_unused() -> None:
    append_step_summary(
        "\n".join(
            [
                "### Unused Dependencies Analysis",
                "",
                "⚠️ Manual review recommended for unused dependencies",
                "Consider using tools like `vulture` or `pycln` for dead code detection",
                "",
            ]
        )
    )


def handle_go_analysis() -> None:
    repo = Path("src/flavor-go")
    deps = _run_capture(["go", "list", "-m", "all"], cwd=repo, check=True).stdout
    Path("src/flavor-go/go-mod-graph.txt").write_text(
        _run_capture(["go", "mod", "graph"], cwd=repo, check=True).stdout, encoding="utf-8"
    )
    _run_capture(["go", "mod", "download"], cwd=repo, check=True)
    append_step_summary(
        "\n".join(
            [
                "## 🐹 Go Dependency Analysis",
                "",
                "### Direct Dependencies",
                "```",
                "\n".join(deps.splitlines()[:30]),
                "```",
                "",
            ]
        )
    )


def handle_go_vulns() -> None:
    repo = Path("src/flavor-go")
    _run_capture(["go", "install", "golang.org/x/vuln/cmd/govulncheck@latest"], cwd=repo, check=True)
    _run_capture(["go", "install", "github.com/sonatype-nexus-community/nancy@latest"], cwd=repo, check=True)
    govuln_json = _run_capture(["govulncheck", "-json", "./..."], cwd=repo, check=False)
    Path(repo / "govulncheck-deps.json").write_text(govuln_json.stdout or "", encoding="utf-8")
    _run_combined_to_file(["govulncheck", "./..."], repo / "govulncheck-deps.log", cwd=repo)
    deps_json = _run_capture(["go", "list", "-json", "-deps", "./..."], cwd=repo, check=True).stdout
    nancy = subprocess.run(
        ["nancy", "sleuth"],
        cwd=repo,
        input=deps_json,
        text=True,
        capture_output=True,
        check=False,
    )
    Path(repo / "nancy-deps.log").write_text((nancy.stdout or "") + (nancy.stderr or ""), encoding="utf-8")
    govuln_log = (repo / "govulncheck-deps.log").read_text(encoding="utf-8", errors="ignore")
    lines = ["### Go Vulnerability Scan", ""]
    if "vulnerability" in govuln_log.lower():
        lines.extend(["🚨 Vulnerabilities detected:", "```", govuln_log.strip(), "```"])
    else:
        lines.append("✅ No vulnerabilities detected")
    if "vulnerable" in (repo / "nancy-deps.log").read_text(encoding="utf-8", errors="ignore").lower():
        lines.extend(
            [
                "### Nancy Vulnerability Report",
                "```",
                "\n".join((repo / "nancy-deps.log").read_text(encoding="utf-8").splitlines()[:20]),
                "```",
            ]
        )
    append_step_summary("\n".join(lines) + "\n")


def handle_go_licenses() -> None:
    repo = Path("src/flavor-go")
    _run_capture(["go", "install", "github.com/google/go-licenses@latest"], cwd=repo, check=True)
    command = ["go-licenses", "report", "./..."]
    for module in GO_IGNORE_MODULES:
        command.extend(["--ignore", module])
    _run_combined_to_file(command, repo / "go-licenses.txt", cwd=repo)
    markdown, _, _ = render_go_compliance(
        *evaluate_go_compliance((repo / "go-licenses.txt").read_text(encoding="utf-8", errors="ignore")),
        False,
    )
    append_step_summary(
        "\n".join(
            [
                "### Go License Analysis",
                "",
                "#### License Report",
                "```",
                "\n".join(
                    (repo / "go-licenses.txt").read_text(encoding="utf-8", errors="ignore").splitlines()[:50]
                ),
                "```",
                markdown.strip(),
                "",
            ]
        )
    )


def handle_go_updates() -> None:
    repo = Path("src/flavor-go")
    _run_combined_to_file(["go", "list", "-u", "-m", "all"], repo / "go-updates.txt", cwd=repo)
    updates = [
        line
        for line in (repo / "go-updates.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
        if "[" in line
    ]
    write_github_output(has_updates="true" if updates else "false")
    lines = ["### Go Module Updates", ""]
    if updates:
        lines.extend(
            [f"📦 **{len(updates)} module updates available**", "```", "\n".join(updates[:20]), "```"]
        )
    else:
        lines.append("✅ All modules are up to date")
    append_step_summary("\n".join(lines) + "\n")


def handle_go_tidiness() -> None:
    repo = Path("src/flavor-go")
    _run_combined_to_file(["go", "mod", "tidy", "-v"], repo / "go-mod-tidy.log", cwd=repo)
    log_text = (repo / "go-mod-tidy.log").read_text(encoding="utf-8", errors="ignore")
    lines = ["### Module Tidiness", ""]
    if "unused" in log_text:
        lines.extend(["⚠️ Unused dependencies found:", "```", log_text.strip(), "```"])
    else:
        lines.append("✅ go.mod is tidy")
    append_step_summary("\n".join(lines) + "\n")


def handle_rust_analysis() -> None:
    repo = Path("src/flavor-rs")
    tree_preview = _run_capture(["cargo", "tree", "--depth", "2"], cwd=repo, check=True).stdout
    Path(repo / "cargo-tree-full.txt").write_text(
        _run_capture(["cargo", "tree", "--all-features"], cwd=repo, check=True).stdout,
        encoding="utf-8",
    )
    duplicates = _run_capture(["cargo", "tree", "--duplicates"], cwd=repo, check=False).stdout
    Path(repo / "cargo-duplicates.txt").write_text(duplicates, encoding="utf-8")
    lines = [
        "## 🦀 Rust Dependency Analysis",
        "",
        "### Dependency Tree",
        "```",
        "\n".join(tree_preview.splitlines()[:50]),
        "```",
        "### Duplicate Dependencies",
    ]
    if duplicates.strip():
        lines.extend(["⚠️ Duplicate dependencies found:", "```", duplicates.strip(), "```"])
    else:
        lines.append("✅ No duplicate dependencies")
    append_step_summary("\n".join(lines) + "\n")


def handle_rust_security() -> None:
    repo = Path("src/flavor-rs")
    audit_json = _run_capture(["cargo", "audit", "--json"], cwd=repo, check=False)
    Path(repo / "cargo-audit-deps.json").write_text(audit_json.stdout or "", encoding="utf-8")
    _run_combined_to_file(["cargo", "audit"], repo / "cargo-audit-deps.log", cwd=repo)
    log_text = (repo / "cargo-audit-deps.log").read_text(encoding="utf-8", errors="ignore")
    lines = ["### Rust Security Audit", ""]
    if "vulnerabilities found" in log_text.lower():
        lines.extend(["🚨 Vulnerabilities found:", "```", log_text.strip(), "```"])
    else:
        lines.append("✅ No known vulnerabilities")
    append_step_summary("\n".join(lines) + "\n")


def handle_rust_licenses() -> None:
    repo = Path("src/flavor-rs")
    license_json = _run_capture(["cargo", "license", "--json"], cwd=repo, check=False)
    Path(repo / "cargo-licenses.json").write_text(license_json.stdout or "", encoding="utf-8")
    _run_combined_to_file(["cargo", "license"], repo / "cargo-licenses.txt", cwd=repo)
    log_text = (repo / "cargo-licenses.txt").read_text(encoding="utf-8", errors="ignore")
    lines = [
        "### Rust License Analysis",
        "",
        "#### License Summary",
        "```",
        "\n".join(log_text.splitlines()[:30]),
        "```",
    ]
    if any(token in log_text for token in ("GPL", "AGPL", "LGPL")):
        lines.append("⚠️ Copyleft licenses detected")
    if "unknown" in log_text.lower():
        lines.append("⚠️ Unknown licenses detected")
    append_step_summary("\n".join(lines) + "\n")


def handle_rust_updates() -> None:
    repo = Path("src/flavor-rs")
    outdated_json = _run_capture(["cargo", "outdated", "--format", "json"], cwd=repo, check=False)
    Path(repo / "cargo-outdated.json").write_text(outdated_json.stdout or "", encoding="utf-8")
    _run_combined_to_file(["cargo", "outdated"], repo / "cargo-outdated.log", cwd=repo)
    payload = _load_json(repo / "cargo-outdated.json") or {}
    count = len(payload.get("dependencies", [])) if isinstance(payload, dict) else 0
    write_github_output(has_updates="true" if count else "false")
    lines = ["### Rust Crate Updates", ""]
    if count:
        lines.extend(
            [
                f"📦 **{count} crate updates available**",
                "```",
                "\n".join(
                    (repo / "cargo-outdated.log")
                    .read_text(encoding="utf-8", errors="ignore")
                    .splitlines()[:30]
                ),
                "```",
            ]
        )
    else:
        lines.append("✅ All crates are up to date")
    append_step_summary("\n".join(lines) + "\n")


def handle_rust_unused() -> None:
    repo = Path("src/flavor-rs")
    _run_combined_to_file(["cargo", "machete"], repo / "cargo-machete.log", cwd=repo)
    log_text = (repo / "cargo-machete.log").read_text(encoding="utf-8", errors="ignore")
    lines = ["### Unused Dependencies", ""]
    if "unused" in log_text.lower():
        lines.extend(["⚠️ Unused dependencies found:", "```", log_text.strip(), "```"])
    else:
        lines.append("✅ No unused dependencies")
    append_step_summary("\n".join(lines) + "\n")


def handle_dependency_report() -> None:
    reports = Path("dependency-reports")
    python_report = _load_json(reports / "python-dependency-reports" / "python-deps-report.json")
    go_log = _read_optional(reports / "go-dependency-reports" / "govulncheck-deps.log")
    rust_log = _read_optional(reports / "rust-dependency-reports" / "cargo-audit-deps.log")
    markdown, summary = render_dependency_report(
        repository=_require_env("DEPENDENCY_REPOSITORY"),
        run_id=_require_env("DEPENDENCY_RUN_ID"),
        timestamp=_require_env("DEPENDENCY_TIMESTAMP"),
        iso_timestamp=_require_env("DEPENDENCY_ISO_TIMESTAMP"),
        python_report=python_report if isinstance(python_report, dict) else None,
        go_has_report=(reports / "go-dependency-reports").is_dir(),
        go_vulnerable="vulnerability" in go_log.lower(),
        go_has_updates=_require_env("DEPENDENCY_GO_HAS_UPDATES") == "true",
        rust_has_report=(reports / "rust-dependency-reports").is_dir(),
        rust_vulnerable="vulnerabilities found" in rust_log.lower(),
        rust_has_updates=_require_env("DEPENDENCY_RUST_HAS_UPDATES") == "true",
    )
    append_step_summary(markdown)
    write_json(Path("dependency-summary.json"), summary)


def _direct_dependency_count() -> int:
    requirements = Path("requirements-audit.txt")
    if not requirements.is_file():
        return 0
    return len(
        [
            line
            for line in requirements.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    )


def _count_pip_audit_vulnerabilities(path: Path) -> int:
    payload = _load_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("vulnerabilities"), list):
        return len(payload["vulnerabilities"])
    if isinstance(payload, list):
        return sum(len(item.get("vulns", [])) for item in payload if isinstance(item, dict))
    return 0


def _count_safety_vulnerabilities(path: Path) -> int:
    payload = _load_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("vulnerabilities"), list):
        return len(payload["vulnerabilities"])
    if isinstance(payload, list):
        return len(payload)
    return 0


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required value for {name}")
    return value


def main() -> None:
    handlers = {
        "python-tree": handle_python_tree,
        "python-vulns": handle_python_vulns,
        "python-licenses": handle_python_licenses,
        "python-updates": handle_python_updates,
        "python-unused": handle_python_unused,
        "python-report": handle_python_report,
        "go-analysis": handle_go_analysis,
        "go-vulns": handle_go_vulns,
        "go-licenses": handle_go_licenses,
        "go-updates": handle_go_updates,
        "go-tidiness": handle_go_tidiness,
        "rust-analysis": handle_rust_analysis,
        "rust-security": handle_rust_security,
        "rust-licenses": handle_rust_licenses,
        "rust-updates": handle_rust_updates,
        "rust-unused": handle_rust_unused,
        "dependency-report": handle_dependency_report,
    }
    handlers[parse_args().command]()


if __name__ == "__main__":
    main()
