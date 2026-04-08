from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .common import ensure_executable, platform_extension, run_command, run_logged_command, write_json


def install_platform_helpers(
    source_dir: Path, dest_dir: Path, version: str | None, platform: str
) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for existing in dest_dir.iterdir():
        if existing.is_file():
            existing.unlink()
    extension = platform_extension(platform)
    pattern = f"*-{version}-{platform}{extension}" if version else f"*-{platform}{extension}"
    copied: list[str] = []
    for source in sorted(source_dir.glob(pattern)):
        if source.is_file():
            destination = dest_dir / source.name
            shutil.copy2(source, destination)
            ensure_executable(destination)
            copied.append(destination.name)
    return copied


def resolve_flavor_build_assets(
    helpers_dir: Path, wheel_dir: Path, platform: str, version: str
) -> dict[str, str]:
    extension = platform_extension(platform)
    candidates = [
        helpers_dir / f"flavor-rs-launcher-{version}-{platform}{extension}",
        helpers_dir / f"flavor-rs-launcher-{platform}{extension}",
    ]
    launcher = next((candidate for candidate in candidates if candidate.is_file()), None)
    if launcher is None:
        raise FileNotFoundError(f"Launcher not found for {platform} in {helpers_dir}")
    wheel = next(iter(sorted(wheel_dir.glob("**/flavorpack-*.whl"))), None)
    if wheel is None:
        raise FileNotFoundError(f"Wheel not found in {wheel_dir}")
    return {"launcher": str(launcher), "wheel": str(wheel)}


def resolve_taster_build_inputs(
    flavor_dir: Path, helpers_dir: Path, platform: str, version: str
) -> dict[str, str]:
    extension = platform_extension(platform)
    psp = next(
        iter(
            sorted(
                file
                for pattern in (f"flavor-*-{platform}.psp", f"flavor-*-{platform}.exe")
                for file in flavor_dir.glob(pattern)
            )
        ),
        None,
    )
    if psp is None:
        raise FileNotFoundError(f"Flavor PSP not found for {platform} in {flavor_dir}")
    launcher_stem = "flavor-go-launcher" if platform.startswith("windows_") else "flavor-rs-launcher"
    launcher_candidates = [
        helpers_dir / f"{launcher_stem}-{version}-{platform}{extension}",
        helpers_dir / f"{launcher_stem}-{platform}{extension}",
    ]
    launcher = next((candidate for candidate in launcher_candidates if candidate.is_file()), None)
    if launcher is None:
        raise FileNotFoundError(f"Launcher not found for {platform} in {helpers_dir}")
    taster_path = Path.cwd() / "tests" / "taster" / f"taster-{version}-{platform}.psp"
    return {"flavor_psp": str(psp), "launcher": str(launcher), "taster_path": str(taster_path)}


def organize_taster_flavor_artifacts(input_dir: Path, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for source in sorted(input_dir.rglob("*")):
        if source.is_file() and source.suffix in {".psp", ".exe"}:
            destination = output_dir / source.name
            if destination.exists():
                destination.unlink()
            shutil.move(str(source), destination)
            moved.append(destination.name)
    return moved


def verify_wheel_structure(dist_dir: Path) -> None:
    wheel = next(iter(sorted(Path(dist_dir).glob("*.whl"))), None)
    if wheel is None:
        raise FileNotFoundError(f"No wheel found in {dist_dir}")
    listing = run_command([sys.executable, "-m", "zipfile", "-l", str(wheel)]).stdout
    if (
        "flavor/" not in listing
        or "flavor/helpers/bin/" not in listing
        or ".dist-info/METADATA" not in listing
    ):
        raise ValueError("Wheel structure validation failed")


def resolve_workflow_run(specified_run: str, workflow: str) -> str:
    if specified_run:
        return specified_run
    result = run_command(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            workflow,
            "--status",
            "success",
            "--limit",
            "1",
            "--json",
            "databaseId",
            "-q",
            ".[0].databaseId",
        ]
    )
    run_id = result.stdout.strip()
    if not run_id:
        raise RuntimeError(f"No successful runs found for {workflow}")
    return run_id


def setup_test_workenv(dev: bool, sibling: str) -> None:
    run_logged_command(["uv", "venv", "workenv"])
    python_exe = (
        Path("workenv") / ("Scripts" if os.environ.get("RUNNER_OS") == "Windows" else "bin") / "python"
    )
    if dev:
        run_logged_command(["uv", "pip", "install", "--python", str(python_exe), "--group", "dev", "-e", "."])
    else:
        run_logged_command(
            ["uv", "pip", "install", "--python", str(python_exe), "pytest", "pytest-cov", "pytest-xdist"]
        )
        run_logged_command(["uv", "pip", "install", "--python", str(python_exe), "-e", "."])
    sibling_path = Path(sibling)
    if sibling and sibling_path.is_file():
        run_logged_command(
            ["uv", "pip", "install", "--python", str(python_exe), "-e", str(sibling_path.parent)]
        )


def write_taster_result(
    output_path: Path, platform: str, runner: str, status: str, taster_path: str, helper_version: str
) -> None:
    timestamp = subprocess.run(
        ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True, check=True
    ).stdout.strip()
    write_json(
        output_path,
        {
            "platform": platform,
            "runner": runner,
            "status": status,
            "taster_path": taster_path,
            "timestamp": timestamp,
            "helper_version": helper_version,
        },
    )


def find_flavor_location() -> Path:
    result = run_command([sys.executable, "-c", "import flavor, os; print(os.path.dirname(flavor.__file__))"])
    return Path(result.stdout.strip())


def detect_launcher_source() -> dict[str, str]:
    flavor_location = find_flavor_location()
    source = "wheel" if (flavor_location / "helpers" / "bin").is_dir() else "helpers"
    return {"source": source, "flavor_location": str(flavor_location)}


def _run_explicit_launcher(launcher: str, output: str, include_info: bool) -> None:
    launcher_path = Path(launcher)
    if not launcher_path.is_file():
        raise FileNotFoundError(f"Launcher not found: {launcher_path}")
    cwd = Path.cwd()
    run_logged_command(
        [
            "flavor",
            "pack",
            "--manifest",
            "pyproject.toml",
            "--output",
            output,
            "--launcher-bin",
            str(launcher_path),
            "--key-seed",
            "test123",
        ],
        cwd=cwd,
    )
    ensure_executable(Path(output))
    run_logged_command([f"./{output}", "--version"], cwd=cwd)
    if include_info:
        run_logged_command([f"./{output}", "info"], cwd=cwd)


def _run_secondary_launcher(stem: str, output: str, platform: str, launcher_ext: str) -> None:
    launcher_source = os.environ.get("LAUNCHER_SOURCE", "helpers")
    launcher_path = (
        find_flavor_location() / "helpers" / "bin" / f"{stem}-{platform}{launcher_ext}"
        if launcher_source == "wheel"
        else Path("../../helpers/bin") / f"{stem}-{platform}{launcher_ext}"
    )
    if not launcher_path.is_file():
        print(f"Skipping missing launcher: {launcher_path}")
        return
    _run_explicit_launcher(str(launcher_path), output, False)


def _run_pipe_scenario() -> None:
    run_logged_command(
        ["./taster-bundled.psp", "pipe", "stdin"], cwd=Path.cwd(), input_text="Hello from pipe\n"
    )


def _run_signal_scenario() -> None:
    timeout_cmd = shutil.which("timeout")
    if timeout_cmd is None:
        print("Skipping signal test; timeout is unavailable")
        return
    run_logged_command(
        [timeout_cmd, "3", "./taster-bundled.psp", "signals", "--sleep", "1"],
        cwd=Path.cwd(),
        allow_failure=True,
    )


def _run_mmap_scenario() -> None:
    help_output = run_command(["./taster-bundled.psp", "--help"], cwd=Path.cwd()).stdout
    if "mmap" in help_output:
        run_logged_command(["./taster-bundled.psp", "mmap"], cwd=Path.cwd())


def _run_exec_test(platform: str) -> None:
    if not platform.startswith("windows_"):
        run_logged_command(["./taster-bundled.psp", "exec-test", "--verbose"], cwd=Path.cwd())


def run_taster_scenario(
    scenario: str, launcher: str, output: str, platform: str, launcher_ext: str, include_info: bool
) -> None:
    if scenario == "explicit-launcher":
        _run_explicit_launcher(launcher, output, include_info)
        return
    if scenario == "launcher-location":
        print(json.dumps(detect_launcher_source()))
        return
    if scenario == "rust-explicit":
        _run_secondary_launcher("flavor-rs-launcher", output, platform, launcher_ext)
        return
    if scenario == "go-explicit":
        _run_secondary_launcher("flavor-go-launcher", output, platform, launcher_ext)
        return
    if scenario == "pipe":
        _run_pipe_scenario()
        return
    if scenario == "signal":
        _run_signal_scenario()
        return
    if scenario == "mmap":
        _run_mmap_scenario()
        return
    if scenario == "exec-test":
        _run_exec_test(platform)
        return
    raise ValueError(f"Unknown scenario: {scenario}")


def render_flavor_summary(
    test_results_dir: Path,
    wheel_dir: Path,
    flavor_dir: Path,
    helper_version: str,
    test_flavor_psp_result: str,
    repository: str,
    run_id: str,
) -> str:
    lines = [
        "## Flavor Pipeline Summary",
        "",
        f"**Helper Version:** {helper_version}",
        "",
        "### Test Results",
        "",
    ]
    for result_dir in sorted(test_results_dir.glob("test-results-*")):
        test_name = result_dir.name.replace("test-results-", "").replace(f"-{run_id}", "")
        status = "✅ Completed" if (result_dir / "pytest-results.xml").exists() else "⚠️ No results"
        lines.append(f"- **{test_name}**: {status}")
    if wheel_dir.is_dir():
        lines.extend(["", "### Python Wheels", ""])
        for wheel in sorted(wheel_dir.glob("*.whl")):
            lines.append(f"- `{wheel.name}` ({wheel.stat().st_size} bytes)")
    if flavor_dir.is_dir():
        lines.extend(["", "### Flavor & Taster Packages", "", "#### Flavor PSP Packages:"])
        for package in sorted(
            file for pattern in ("flavor-*.psp", "flavor-*.exe") for file in flavor_dir.glob(pattern)
        ):
            lines.append(f"- `{package.name}` ({package.stat().st_size} bytes)")
        lines.extend(["", "#### Taster Test Packages:"])
        for package in sorted(
            file for pattern in ("taster-*.psp", "taster-*.exe") for file in flavor_dir.glob(pattern)
        ):
            lines.append(f"- `{package.name}` ({package.stat().st_size} bytes)")
    lines.extend(["", "### Flavor PSP Self-Contained Tests", ""])
    if test_flavor_psp_result == "success":
        lines.append(
            "✅ All Flavor PSP packages verified successfully (self-contained, no external dependencies)"
        )
    elif test_flavor_psp_result == "skipped":
        lines.append("⏭️ PSP tests were skipped")
    else:
        lines.append("❌ Some PSP self-contained tests failed")
    lines.extend(
        ["", "### Artifacts", f"- [View test results](https://github.com/{repository}/actions/runs/{run_id})"]
    )
    return "\n".join(lines) + "\n"


def render_taster_summary(results_dir: Path, helper_version: str, repository: str, run_id: str) -> str:
    lines = [
        "## Taster Pipeline Summary",
        "",
        f"**Helper Version:** {helper_version}",
        "",
        "### Platform Test Results",
        "",
        "| Platform | Status | Runner | Timestamp |",
        "|----------|--------|--------|-----------|",
    ]
    for json_file in sorted(results_dir.glob("taster-results-*/*.json")):
        payload = json.loads(json_file.read_text(encoding="utf-8"))
        status = payload["status"]
        status_emoji = "✅" if status == "success" else "❌"
        lines.append(
            f"| {payload['platform']} | {status_emoji} {status} | {payload['runner']} | {payload['timestamp']} |"
        )
    lines.extend(
        [
            "",
            "### Test Coverage",
            "",
            "✅ Basic commands (--help, info, env)",
            "✅ Exit codes and error handling",
            "✅ File operations and workenv persistence",
            "✅ Cache management",
            "✅ Argument parsing",
            "✅ Cross-language compatibility",
            "✅ Signal handling",
            "✅ Pipe operations",
            "",
            "### Artifacts",
            f"- [View test results](https://github.com/{repository}/actions/runs/{run_id})",
        ]
    )
    return "\n".join(lines) + "\n"
