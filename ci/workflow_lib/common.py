from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess


def run_command(
    cmd: list[str], cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def run_logged_command(
    cmd: list[str],
    cwd: Path | None = None,
    input_text: str | None = None,
    allow_failure: bool = False,
) -> int:
    completed = subprocess.run(cmd, cwd=cwd, input=input_text, text=True)
    if completed.returncode != 0 and not allow_failure:
        raise subprocess.CalledProcessError(completed.returncode, cmd)
    return completed.returncode


def ensure_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_github_output(**values: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    lines = [f"{key}={value}" for key, value in values.items()]
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


def write_github_env(**values: str) -> None:
    env_path = os.environ.get("GITHUB_ENV")
    lines = [f"{key}={value}" for key, value in values.items()]
    if env_path:
        with Path(env_path).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


def append_step_summary(content: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write(content)
    else:
        print(content, end="")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def platform_extension(platform: str) -> str:
    return ".exe" if platform.startswith("windows_") else ""
