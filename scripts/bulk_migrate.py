#!/usr/bin/env python3
"""Bulk migrate click.echo/secho to pout/perr for remaining files."""

from pathlib import Path
import re

files_to_migrate = [
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
    "/REDACTED_ABS_PATH",
]


def migrate_file(file_path: Path) -> tuple[int, int]:
    """Migrate a single file. Returns (changes, errors)."""
    content = file_path.read_text()
    original = content
    changes = 0

    # Add imports if not present
    if "from provide.foundation.console import" not in content:
        # Find where to add import (after click import)
        if "import click" in content:
            content = content.replace(
                "import click\n", "import click\nfrom provide.foundation.console import perr, pout\n"
            )
            changes += 1

    # Replace click.echo(..., err=True) → perr(...)
    pattern = r"click\.echo\(([^,)]+),\s*err=True\)"
    matches = re.findall(pattern, content)
    content = re.sub(pattern, r"perr(\1)", content)
    changes += len(matches)

    # Replace click.echo(...) → pout(...)
    pattern = r"click\.echo\(([^)]+)\)"
    matches = re.findall(pattern, content)
    content = re.sub(pattern, r"pout(\1)", content)
    changes += len(matches)

    # Replace click.secho with err=True
    pattern = r"click\.secho\(([^,)]+),\s*fg=([^,)]+),?\s*err=True"
    matches = re.findall(pattern, content)
    content = re.sub(pattern, r"perr(\1, color=\2", content)
    changes += len(matches)

    # Replace click.secho(..., fg=..., bold=True) → pout(..., color=..., bold=True)
    pattern = r"click\.secho\(([^,)]+),\s*fg=([^,)]+),\s*bold=True\)"
    matches = re.findall(pattern, content)
    content = re.sub(pattern, r"pout(\1, color=\2, bold=True)", content)
    changes += len(matches)

    # Replace click.secho(..., fg=...) → pout(..., color=...)
    pattern = r"click\.secho\(([^,)]+),\s*fg=([^,)]+)\)"
    matches = re.findall(pattern, content)
    content = re.sub(pattern, r"pout(\1, color=\2)", content)
    changes += len(matches)

    # Replace simple click.secho(...) → pout(...)
    pattern = r"click\.secho\(([^)]+)\)"
    matches = re.findall(pattern, content)
    content = re.sub(pattern, r"pout(\1)", content)
    changes += len(matches)

    if content != original:
        file_path.write_text(content)
        print(f"✅ {file_path.name}: {changes} replacements")
        return (changes, 0)
    else:
        print(f"⚠️ {file_path.name}: No changes")
        return (0, 0)


def main():
    total_changes = 0
    total_errors = 0

    for file_str in files_to_migrate:
        file_path = Path(file_str)
        if not file_path.exists():
            print(f"❌ Not found: {file_path}")
            total_errors += 1
            continue

        changes, errors = migrate_file(file_path)
        total_changes += changes
        total_errors += errors

    print(f"\n{'=' * 60}")
    print(f"Total replacements: {total_changes}")
    print(f"Total errors: {total_errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
