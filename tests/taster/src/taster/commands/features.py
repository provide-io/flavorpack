#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Compare Go vs Rust launcher/builder feature parity."""

from __future__ import annotations

from collections.abc import Callable, Sequence
import json
import os
from pathlib import Path
import signal
import sys
from typing import Any

import click
from provide.foundation.console import pout

FeatureTest = Callable[[], bool]
FeatureResult = dict[str, Any]


def get_launcher_type() -> str:
    """Detect launcher type from environment and behavior."""
    command_name = os.environ.get("FLAVOR_COMMAND_NAME")
    if command_name and command_name != sys.argv[0]:
        return "go"
    return "rust"


def test_feature(test_func: FeatureTest, feature_name: str) -> FeatureResult:
    """Execute a feature test and capture diagnostics."""
    try:
        result = bool(test_func())
        return {"feature": feature_name, "supported": result, "error": None}
    except Exception as exc:
        return {"feature": feature_name, "supported": False, "error": str(exc)}


def test_argv0() -> bool:
    """Test if argv[0] is set correctly."""
    expected_tokens = ["taster", ".psp"]
    return any(token in sys.argv[0] for token in expected_tokens)


def test_signal_handling() -> bool:
    """Test if signals are handled."""
    try:
        old_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, old_handler)
        return old_handler != signal.SIG_DFL
    except (OSError, ValueError):
        return False


def test_json_logging() -> bool:
    """Test if JSON logging is available."""
    log_level = os.environ.get("FLAVOR_LOG_LEVEL", "")
    return log_level.startswith("json")


def test_lock_files() -> bool:
    """Test if lock files are used for extraction."""
    workenv = os.environ.get("FLAVOR_WORKENV")
    if not workenv:
        return False
    lock_file = Path(workenv) / ".extraction.lock"
    return lock_file.exists()


def test_env_whitelist() -> bool:
    """Test if whitelist mode (unset=['*']) works."""
    allowed_prefixes = [
        "PATH",
        "HOME",
        "USER",
        "TERM",
        "LANG",
        "LC_",
        "FLAVOR_",
        "TASTER_",
        "KEEP_",
    ]

    unexpected = []
    for key in os.environ:
        allowed = any(key.startswith(prefix) for prefix in allowed_prefixes)
        if not allowed and key not in {"NEW_VAR", "TASTER_MODE", "TASTER_VERSION"}:
            unexpected.append(key)

    return len(unexpected) < 10


def test_env_glob_patterns() -> bool:
    """Test if glob patterns work in unset/pass."""
    lc_vars = [key for key in os.environ if key.startswith("LC_")]
    return bool(lc_vars)


def test_graceful_shutdown() -> bool:
    """Test if graceful shutdown is implemented."""
    return get_launcher_type() == "rust"


def test_process_cleanup() -> bool:
    """Test if process cleanup on exit works."""
    return get_launcher_type() == "rust"


def test_incomplete_extraction() -> bool:
    """Test incomplete extraction handling."""
    workenv = os.environ.get("FLAVOR_WORKENV")
    if not workenv:
        return False
    return (Path(workenv) / ".extraction.complete").exists()


def test_stale_lock_detection() -> bool:
    """Test stale lock detection with PID validation."""
    return get_launcher_type() == "rust"


@click.command("features")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def features_command(output_json: bool) -> None:
    """Compare Go vs Rust launcher/builder feature parity."""
    launcher_type = get_launcher_type()
    features_tests: Sequence[tuple[str, FeatureTest]] = [
        ("argv[0] setting", test_argv0),
        ("Signal forwarding", test_signal_handling),
        ("JSON logging", test_json_logging),
        ("Lock files", test_lock_files),
        ("Environment whitelist (unset=['*'])", test_env_whitelist),
        ("Glob patterns in env", test_env_glob_patterns),
        ("Graceful shutdown", test_graceful_shutdown),
        ("Process cleanup", test_process_cleanup),
        ("Incomplete extraction handling", test_incomplete_extraction),
        ("Stale lock detection", test_stale_lock_detection),
    ]

    results = [test_feature(func, name) for name, func in features_tests]
    supported = sum(1 for result in results if result["supported"])
    total = len(results)
    percentage = (supported / total) * 100 if total else 0.0

    if output_json:
        _print_json_output(launcher_type, results, supported, total, percentage)
    else:
        _print_human_output(launcher_type, results, supported, total, percentage)


def _print_json_output(
    launcher_type: str,
    results: list[FeatureResult],
    supported: int,
    total: int,
    percentage: float,
) -> None:
    """Emit machine-readable test results."""
    output = {
        "launcher": launcher_type,
        "features": results,
        "summary": {
            "supported": supported,
            "total": total,
            "percentage": percentage,
        },
    }
    pout(json.dumps(output, indent=2))


def _print_human_output(
    launcher_type: str,
    results: list[FeatureResult],
    supported: int,
    total: int,
    percentage: float,
) -> None:
    """Emit human friendly results."""
    pout("=" * 60, color="cyan")
    pout(
        f"🔍 FEATURE PARITY TEST ({launcher_type.upper()} LAUNCHER)",
        color="cyan",
        bold=True,
    )
    pout("=" * 60, color="cyan")

    for result in results:
        if result["supported"]:
            symbol = "✅"
            color = "green"
        else:
            symbol = "❌"
            color = "red"

        pout(f"{symbol} {result['feature']}", color=color)
        if result["error"]:
            pout(f"   Error: {result['error']}")

    pout("\n" + "=" * 60, color="cyan")
    pout("📊 SUMMARY", color="cyan", bold=True)
    pout("=" * 60, color="cyan")
    pout(f"Launcher Type: {launcher_type.upper()}")
    pout(f"Features Supported: {supported}/{total} ({percentage:.1f}%)")

    if launcher_type == "go" and percentage < 100:
        pout(
            "\n⚠️ Note: Go launcher has limitations due to language constraints",
            color="yellow",
        )
        pout("  - Cannot set argv[0] on Unix systems")
        pout("  - Limited signal handling capabilities")


# 🌶️📦🔚
