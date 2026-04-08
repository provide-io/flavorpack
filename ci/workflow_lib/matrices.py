from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

HELPER_MATRIX = [
    {
        "platform": "linux_amd64",
        "os": "ubuntu-24.04",
        "rust_target": "x86_64-unknown-linux-musl",
        "use_musl": True,
        "emoji": "🐧",
    },
    {
        "platform": "linux_arm64",
        "os": "ubuntu-24.04-arm",
        "rust_target": "aarch64-unknown-linux-musl",
        "use_musl": True,
        "emoji": "🐧",
    },
    {
        "platform": "darwin_amd64",
        "os": "macos-15-intel",
        "rust_target": "x86_64-apple-darwin",
        "use_musl": False,
        "emoji": "🍎",
    },
    {
        "platform": "darwin_arm64",
        "os": "macos-15",
        "rust_target": "aarch64-apple-darwin",
        "use_musl": False,
        "emoji": "🍎",
    },
    {
        "platform": "windows_amd64",
        "os": "windows-2022",
        "rust_target": "x86_64-pc-windows-msvc",
        "use_musl": False,
        "emoji": "🪟",
    },
    {
        "platform": "windows_arm64",
        "os": "windows-11-arm",
        "rust_target": "aarch64-pc-windows-msvc",
        "use_musl": False,
        "emoji": "🪟",
    },
]

HELPER_MATRIX_ACT = [HELPER_MATRIX[0]]

FLAVOR_TEST_MATRIX = {
    "include": [
        {"name": "unit", "runner": "ubuntu-24.04", "marker": "unit", "timeout": 10},
        {"name": "integration", "runner": "ubuntu-24.04", "marker": "integration", "timeout": 20},
        {"name": "security", "runner": "ubuntu-24.04", "marker": "security", "timeout": 15},
        {"name": "format-2025", "runner": "ubuntu-24.04", "path": "tests/format_2025", "timeout": 30},
        {"name": "packaging", "runner": "ubuntu-24.04", "path": "tests/packaging", "timeout": 25},
        {"name": "cross-language", "runner": "ubuntu-24.04", "marker": "cross_language", "timeout": 30},
        {"name": "parity", "runner": "ubuntu-24.04", "marker": "parity", "timeout": 10, "parity_report": True},
    ]
}

TASTER_TEST_MATRIX = {
    "include": [
        {"name": "linux-amd64", "runner": "ubuntu-24.04", "platform": "linux_amd64"},
        {"name": "linux-arm64", "runner": "ubuntu-24.04-arm", "platform": "linux_arm64"},
        {"name": "darwin-amd64", "runner": "macos-15-intel", "platform": "darwin_amd64"},
        {"name": "darwin-arm64", "runner": "macos-15", "platform": "darwin_arm64"},
        {"name": "windows-amd64", "runner": "windows-2025", "platform": "windows_amd64"},
        {"name": "windows-arm64", "runner": "windows-11-arm", "platform": "windows_arm64"},
    ]
}


def build_helper_matrix(platforms: str, act: bool) -> dict[str, list[dict[str, Any]]]:
    selected = HELPER_MATRIX_ACT if act else HELPER_MATRIX
    requested = [item.strip() for item in platforms.split(",") if item.strip()]
    if not requested:
        return {"include": selected}
    requested_set = set(requested)
    return {"include": [item for item in selected if item["platform"] in requested_set]}


def build_flavor_test_matrix() -> dict[str, list[dict[str, Any]]]:
    return FLAVOR_TEST_MATRIX


def build_taster_test_matrix() -> dict[str, list[dict[str, Any]]]:
    return TASTER_TEST_MATRIX


def hash_matching_files(root: Path, suffixes: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        candidate
        for candidate in root.rglob("*")
        if candidate.is_file() and (candidate.suffix in suffixes or candidate.name in {"go.mod", "Cargo.toml"})
    ):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
