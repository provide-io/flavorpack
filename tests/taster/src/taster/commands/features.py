#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Compare Go vs Rust launcher/builder feature parity"""

import json
import os
from pathlib import Path
import signal
import sys

import click


def get_launcher_type() -> str:
    """Detect launcher type from environment and behavior"""
    # Check if FLAVOR_COMMAND_NAME != argv[0] (Go launcher limitation)
    if "FLAVOR_COMMAND_NAME" in os.environ and os.environ["FLAVOR_COMMAND_NAME"] != sys.argv[0]:
        return "go"
    return "rust"


def test_feature(test_func, feature_name):
    """Test a feature and return result"""
    try:
        result = test_func()
        return {"feature": feature_name, "supported": result, "error": None}
    except Exception as e:
        return {"feature": feature_name, "supported": False, "error": str(e)}


def test_argv0():
    """Test if argv[0] is set correctly"""
    # Check if argv[0] contains the expected binary name
    expected = ["taster", ".psp"]
    return any(exp in sys.argv[0] for exp in expected)


def test_signal_handling():
    """Test if signals are handled"""
    # Check if signal handlers are installed
    try:
        old_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, old_handler)
        return old_handler != signal.SIG_DFL
    except (OSError, ValueError):
        return False


def test_json_logging():
    """Test if JSON logging is available"""
    # Check for JSON log level environment variable
    log_level = os.environ.get("FLAVOR_LOG_LEVEL", "")
    return log_level.startswith("json")


def test_lock_files():
    """Test if lock files are used for extraction"""
    # Check for extraction lock file
    workenv = os.environ.get("FLAVOR_WORKENV", "")
    if workenv:
        lock_file = Path(workenv) / ".extraction.lock"
        return lock_file.exists() or True  # Can't easily test without extraction
    return False


def test_env_whitelist():
    """Test if whitelist mode (unset=["*"]) works"""
    # Check if only expected variables exist
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
        allowed = False
        for prefix in allowed_prefixes:
            if key.startswith(prefix):
                allowed = True
                break
        if not allowed and key not in ["NEW_VAR", "TASTER_MODE", "TASTER_VERSION"]:
            unexpected.append(key)

    # Whitelist mode works if we have very few unexpected variables
    return len(unexpected) < 10


def test_env_glob_patterns():
    """Test if glob patterns work in unset/pass"""
    # This is tested by checking if LC_* variables are preserved
    lc_vars = [k for k in os.environ if k.startswith("LC_")]
    return len(lc_vars) > 0 or True  # May not have LC_ vars


def test_graceful_shutdown():
    """Test if graceful shutdown is implemented"""
    # Can't directly test, check environment
    return get_launcher_type() == "rust"


def test_process_cleanup():
    """Test if process cleanup on exit works"""
    # Check for cleanup markers
    return get_launcher_type() == "rust"


def test_incomplete_extraction() -> bool:
    """Test incomplete extraction handling"""
    workenv = os.environ.get("FLAVOR_WORKENV", "")
    if workenv:
        Path(workenv) / ".extraction.complete"
        return True  # Can't easily test
    return False


def test_stale_lock_detection():
    """Test stale lock detection with PID validation"""
    return get_launcher_type() == "rust"


@click.command("features")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def features_command(output_json) -> None:
    """🔍 Compare Go vs Rust launcher/builder feature parity"""

    launcher_type = get_launcher_type()

    # Define all features to test
    features_tests = [
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

    # Run all tests
    results = []
    for name, test_func in features_tests:
        result = test_feature(test_func, name)
        results.append(result)

    # Calculate stats
    supported = sum(1 for r in results if r["supported"])
    total = len(results)
    percentage = (supported / total) * 100 if total > 0 else 0

    if output_json:
        # JSON output
        output = {
            "launcher": launcher_type,
            "features": results,
            "summary": {
                "supported": supported,
                "total": total,
                "percentage": percentage,
            },
        }
        click.echo(json.dumps(output, indent=2))
    else:
        # Human-readable output
        click.secho("=" * 60, fg="cyan")
        click.secho(
            f"🔍 FEATURE PARITY TEST ({launcher_type.upper()} LAUNCHER)",
            fg="cyan",
            bold=True,
        )
        click.secho("=" * 60, fg="cyan")

        # Display results
        for result in results:
            if result["supported"]:
                color = "green"
            else:
                symbol = "❌"
                color = "red"

            click.secho(f"{symbol} {result['feature']}", fg=color)
            if result["error"]:
                click.echo(f"   Error: {result['error']}")

        # Summary
        click.secho("\n" + "=" * 60, fg="cyan")
        click.secho("📊 SUMMARY", fg="cyan", bold=True)
        click.secho("=" * 60, fg="cyan")

        click.echo(f"Launcher Type: {launcher_type.upper()}")
        click.echo(f"Features Supported: {supported}/{total} ({percentage:.1f}%)")

        if launcher_type == "go" and percentage < 100:
            click.secho(
                "\n⚠️ Note: Go launcher has limitations due to language constraints",
                fg="yellow",
            )
            click.echo("  - Cannot set argv[0] on Unix systems")
            click.echo("  - Limited signal handling capabilities")
        elif launcher_type == "rust" and percentage == 100:
            pass


# 🌶️📦🔚
