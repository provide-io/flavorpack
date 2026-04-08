#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from ci.license_workflow_lib.analysis import (
    GO_IGNORE_MODULES,
    RUST_DENY_TOML,
    analyze_python_licenses,
    evaluate_go_compliance,
    license_distribution,
    load_python_licenses,
    scan_project_license,
)
from ci.license_workflow_lib.reporting import (
    render_compliance_report,
    render_go_compliance,
    render_go_report,
    render_project_license_summary,
    render_python_compliance,
    render_python_distribution,
    render_python_report,
    render_rust_compliance,
    render_rust_report,
    render_sbom_generation,
    render_sbom_validation,
)
from ci.workflow_lib.common import append_step_summary, run_command, write_github_output, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Helpers for thin license compliance workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("project-license-scan")
    subparsers.add_parser("python-license-report")
    python_check = subparsers.add_parser("python-license-check")
    python_check.add_argument("--allowed-licenses", required=True)
    python_check.add_argument("--strict-mode", action="store_true")
    subparsers.add_parser("python-license-stats")
    subparsers.add_parser("go-license-report")
    go_check = subparsers.add_parser("go-license-check")
    go_check.add_argument("--strict-mode", action="store_true")
    subparsers.add_parser("rust-license-report")
    rust_check = subparsers.add_parser("rust-license-check")
    rust_check.add_argument("--strict-mode", action="store_true")
    subparsers.add_parser("sbom-generate")
    subparsers.add_parser("sbom-validate")
    compliance = subparsers.add_parser("compliance-report")
    for name in (
        "repository",
        "run_id",
        "project_license",
        "has_license",
        "python_compliant",
        "python_violations",
        "go_compliant",
        "rust_compliant",
        "sbom_generated",
        "timestamp",
        "iso_timestamp",
    ):
        compliance.add_argument(f"--{name.replace('_', '-')}", default="")
    compliance.add_argument("--strict-mode", action="store_true")
    return parser.parse_args()


def _tool_path(name: str) -> str:
    venv_bin = Path(".venv") / ("Scripts" if sys.platform.startswith("win") else "bin") / name
    if venv_bin.exists():
        return str(venv_bin)
    resolved = shutil.which(name)
    if resolved:
        return resolved
    raise FileNotFoundError(f"Could not locate required command: {name}")


def _write_command_output(cmd: list[str], output_path: Path, cwd: Path | None = None) -> int:
    completed = run_command(cmd, cwd=cwd, check=False)
    output_path.write_text((completed.stdout or "") + (completed.stderr or ""), encoding="utf-8")
    return completed.returncode


def _timestamp(format_string: str) -> str:
    return subprocess.run(
        ["date", "-u", format_string], capture_output=True, text=True, check=True
    ).stdout.strip()


def _to_bool(value: str) -> bool:
    return value.lower() == "true"


def handle_project_license_scan() -> None:
    scan = scan_project_license(Path.cwd())
    append_step_summary(render_project_license_summary(scan))
    write_github_output(
        project_license=scan.primary_license,
        has_license=str(scan.has_license).lower(),
    )


def handle_python_license_report() -> None:
    command = _tool_path("pip-licenses")
    summary_path = Path("python-license-summary.txt")
    _write_command_output(
        [command, "--format=json", "--output-file=python-licenses.json"], Path("python-licenses.json.log")
    )
    _write_command_output(
        [command, "--format=csv", "--output-file=python-licenses.csv"], Path("python-licenses.csv.log")
    )
    _write_command_output(
        [command, "--format=markdown", "--output-file=python-licenses.md"], Path("python-licenses.md.log")
    )
    _write_command_output(
        [command, "--format=plain", "--output-file=python-licenses.txt"], Path("python-licenses.txt.log")
    )
    run_command([command, "--summary", "--output-file", str(summary_path)])
    append_step_summary(render_python_report(summary_path.read_text(encoding="utf-8")))


def handle_python_license_check(allowed_licenses: str, strict_mode: bool) -> None:
    report = analyze_python_licenses(load_python_licenses(Path("python-licenses.json")))
    Path("license-analysis.txt").write_text(report.as_text(), encoding="utf-8")
    markdown, outputs, should_fail = render_python_compliance(report, allowed_licenses, strict_mode)
    append_step_summary(markdown)
    write_github_output(**outputs)
    if should_fail:
        raise SystemExit(1)


def handle_python_license_stats() -> None:
    rows = license_distribution(load_python_licenses(Path("python-licenses.json")))
    append_step_summary(render_python_distribution(rows))


def handle_go_license_report() -> None:
    repo = Path("src/flavor-go")
    report_args = ["go-licenses", "report", "./..."]
    csv_args = ["go-licenses", "csv", "./..."]
    for module in GO_IGNORE_MODULES:
        report_args.extend(["--ignore", module])
        csv_args.extend(["--ignore", module])
    _write_command_output(report_args, repo / "go-licenses.txt", cwd=repo)
    _write_command_output(csv_args, repo / "go-licenses.csv", cwd=repo)
    append_step_summary(render_go_report((repo / "go-licenses.txt").read_text(encoding="utf-8")))


def handle_go_license_check(strict_mode: bool) -> None:
    report_text = (Path("src/flavor-go") / "go-licenses.txt").read_text(encoding="utf-8", errors="ignore")
    markdown, compliant, should_fail = render_go_compliance(*evaluate_go_compliance(report_text), strict_mode)
    append_step_summary(markdown)
    write_github_output(compliant=compliant)
    if should_fail:
        raise SystemExit(1)


def handle_rust_license_report() -> None:
    repo = Path("src/flavor-rs")
    _write_command_output(["cargo", "license", "--json"], repo / "rust-licenses.json", cwd=repo)
    _write_command_output(["cargo", "license"], repo / "rust-licenses.txt", cwd=repo)
    append_step_summary(
        render_rust_report((repo / "rust-licenses.txt").read_text(encoding="utf-8", errors="ignore"))
    )


def handle_rust_license_check(strict_mode: bool) -> None:
    repo = Path("src/flavor-rs")
    (repo / "deny.toml").write_text(RUST_DENY_TOML, encoding="utf-8")
    returncode = _write_command_output(
        ["cargo", "deny", "check", "licenses"], repo / "cargo-deny-licenses.log", cwd=repo
    )
    log_text = (repo / "cargo-deny-licenses.log").read_text(encoding="utf-8", errors="ignore")
    markdown, compliant, should_fail = render_rust_compliance(log_text, returncode == 0, strict_mode)
    append_step_summary(markdown)
    write_github_output(compliant=compliant)
    if should_fail:
        raise SystemExit(1)


def handle_sbom_generate() -> None:
    package_count: int | None = None
    python_sbom = False
    for format_name, output_name in (
        ("json", "sbom-syft.json"),
        ("spdx-json", "sbom-spdx.json"),
        ("cyclonedx-json", "sbom-cyclonedx.json"),
        ("table", "sbom-table.txt"),
    ):
        output = run_command(["syft", ".", "-o", format_name]).stdout
        Path(output_name).write_text(output, encoding="utf-8")
    if Path("requirements.txt").is_file():
        run_command(
            [
                _tool_path("cyclonedx-py"),
                "-r",
                "requirements.txt",
                "-o",
                "sbom-python.json",
                "--format",
                "json",
            ],
            check=False,
        )
        python_sbom = Path("sbom-python.json").is_file()
    elif Path("pyproject.toml").is_file():
        run_command(
            [_tool_path("cyclonedx-py"), "-p", "pyproject.toml", "-o", "sbom-python.json", "--format", "json"],
            check=False,
        )
        python_sbom = Path("sbom-python.json").is_file()
    syft_payload = json.loads(Path("sbom-syft.json").read_text(encoding="utf-8"))
    package_count = len(syft_payload.get("artifacts", []))
    preview = "\n".join(Path("sbom-table.txt").read_text(encoding="utf-8").splitlines()[:50])
    append_step_summary(render_sbom_generation(package_count, preview, python_sbom))


def handle_sbom_validate() -> None:
    spdx_valid = False
    try:
        json.loads(Path("sbom-spdx.json").read_text(encoding="utf-8"))
        spdx_valid = True
    except (FileNotFoundError, json.JSONDecodeError):
        spdx_valid = False
    cyclonedx_message = "⚠️ CycloneDX CLI unavailable"
    cyclonedx_cli = shutil.which("cyclonedx")
    if cyclonedx_cli and Path("sbom-cyclonedx.json").is_file():
        completed = run_command(
            [cyclonedx_cli, "validate", "--input-file", "sbom-cyclonedx.json", "--input-format", "json"],
            check=False,
        )
        log_text = (completed.stdout or "") + (completed.stderr or "")
        Path("cyclonedx-validation.log").write_text(log_text, encoding="utf-8")
        cyclonedx_message = (
            "✅ CycloneDX SBOM is valid"
            if "valid" in log_text.lower()
            else "⚠️ CycloneDX SBOM validation warnings"
        )
    else:
        Path("cyclonedx-validation.log").write_text("cyclonedx CLI unavailable\n", encoding="utf-8")
    append_step_summary(render_sbom_validation(spdx_valid, cyclonedx_message))


def handle_compliance_report(args: argparse.Namespace) -> None:
    markdown, summary = render_compliance_report(
        repository=args.repository or _require_env("LICENSE_REPOSITORY"),
        run_id=args.run_id or _require_env("LICENSE_RUN_ID"),
        strict_mode=args.strict_mode,
        project_license=args.project_license or _require_env("LICENSE_PROJECT_LICENSE"),
        has_license=_to_bool(args.has_license or _require_env("LICENSE_HAS_LICENSE")),
        python_compliant=_to_bool(args.python_compliant or _require_env("LICENSE_PYTHON_COMPLIANT")),
        python_violations=int(args.python_violations or _require_env("LICENSE_PYTHON_VIOLATIONS")),
        go_compliant=_to_bool(args.go_compliant or _require_env("LICENSE_GO_COMPLIANT")),
        rust_compliant=_to_bool(args.rust_compliant or _require_env("LICENSE_RUST_COMPLIANT")),
        sbom_generated=_to_bool(args.sbom_generated or _require_env("LICENSE_SBOM_GENERATED")),
        timestamp=args.timestamp or _require_env("LICENSE_TIMESTAMP"),
        iso_timestamp=args.iso_timestamp or _require_env("LICENSE_ISO_TIMESTAMP"),
    )
    append_step_summary(markdown)
    write_json(Path("compliance-summary.json"), summary)
    if args.strict_mode and not summary["compliance"]["overall"]:
        raise SystemExit(1)


def main() -> None:
    args = parse_args()
    handlers = {
        "project-license-scan": handle_project_license_scan,
        "python-license-report": handle_python_license_report,
        "python-license-check": lambda: handle_python_license_check(args.allowed_licenses, args.strict_mode),
        "python-license-stats": handle_python_license_stats,
        "go-license-report": handle_go_license_report,
        "go-license-check": lambda: handle_go_license_check(args.strict_mode),
        "rust-license-report": handle_rust_license_report,
        "rust-license-check": lambda: handle_rust_license_check(args.strict_mode),
        "sbom-generate": handle_sbom_generate,
        "sbom-validate": handle_sbom_validate,
        "compliance-report": lambda: handle_compliance_report(args),
    }
    handlers[args.command]()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required value for {name}")
    return value


if __name__ == "__main__":
    main()
