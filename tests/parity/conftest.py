# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Parity test framework -- generates cross-language behavior reports."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest


def pytest_configure(config: Any) -> None:
    config.addinivalue_line("markers", "parity: cross-language parity test")
    config.addinivalue_line("markers", "parity_category(name): parity test category")
    config.addinivalue_line("markers", "parity_go(status): expected Go behavior (PASS/FAIL/N_A/SKIP)")
    config.addinivalue_line("markers", "parity_rust(status): expected Rust behavior (PASS/FAIL/N_A/SKIP)")
    config._parity_items = {}


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Capture marker info from items at collection time (items are available here)."""
    store: dict[str, dict[str, str]] = getattr(config, "_parity_items", {})
    for item in items:
        if not list(item.iter_markers("parity")):
            continue
        cat_markers = list(item.iter_markers("parity_category"))
        go_markers = list(item.iter_markers("parity_go"))
        rust_markers = list(item.iter_markers("parity_rust"))
        store[item.nodeid] = {
            "category": cat_markers[0].args[0] if cat_markers else "Uncategorized",
            "behavior": item.name.replace("test_", "").replace("_", " "),
            "go": go_markers[0].args[0] if go_markers else "N/A",
            "rust": rust_markers[0].args[0] if rust_markers else "N/A",
        }
    config._parity_items = store


def _overall_status(py_status: str, go_status: str, rust_status: str) -> str:
    """Compute overall parity status from the three language statuses."""
    real = [s for s in (py_status, go_status, rust_status) if s not in ("N/A", "SKIP")]
    if all(s == "PASS" for s in real):
        return "all-pass"
    if "FAIL" in real:
        return "has-fail"
    return "warning"


def _render_report(categories: dict[str, list[dict[str, str]]]) -> str:
    """Render collected parity data into Markdown."""
    now = datetime.now(tz=UTC).isoformat()
    lines = [
        "# PSPF Cross-Language Parity Report",
        f"Generated: {now}",
        "",
    ]
    for category, tests in sorted(categories.items()):
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| Behavior | Python | Go | Rust | Status |")
        lines.append("|----------|--------|----|------|--------|")
        for t in tests:
            lines.append(f"| {t['behavior']} | {t['python']} | {t['go']} | {t['rust']} | {t['status']} |")
        lines.append("")
    return "\n".join(lines)


def pytest_terminal_summary(terminalreporter: Any, config: Any) -> None:
    if not config.getoption("--parity-report", False):
        return

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / "parity-report.md"

    parity_items: dict[str, dict[str, str]] = getattr(config, "_parity_items", {})

    all_reports = (
        terminalreporter.stats.get("passed", [])
        + terminalreporter.stats.get("failed", [])
        + terminalreporter.stats.get("skipped", [])
    )

    categories: dict[str, list[dict[str, str]]] = {}
    seen: set[str] = set()

    for report in all_reports:
        # Only consider the "call" phase to avoid duplicates from setup/teardown
        if getattr(report, "when", None) != "call":
            continue
        nodeid = report.nodeid
        if nodeid in seen or nodeid not in parity_items:
            continue
        seen.add(nodeid)

        info = parity_items[nodeid]
        if report.passed:
            py_status = "PASS"
        elif report.failed:
            py_status = "FAIL"
        else:
            py_status = "SKIP"

        entry = {
            **info,
            "python": py_status,
            "status": _overall_status(py_status, info["go"], info["rust"]),
        }
        categories.setdefault(info["category"], []).append(entry)

    report_path.write_text(_render_report(categories), encoding="utf-8")
    terminalreporter.write_sep("=", f"Parity report written to {report_path}")
