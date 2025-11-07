#!/usr/bin/env python3
"""Migration script to replace click.echo/secho with pout/perr.

This script automates the conversion of click output functions to the
provide-foundation pout/perr API across the taster test suite.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Tuple

# Migration patterns
PATTERNS = [
    # click.echo with err=True → perr
    (
        r'click\.echo\(([^,)]+),\s*err=True(?:,\s*nl=(True|False))?\)',
        lambda m: f'perr({m.group(1)}' + (f', nl={m.group(2)}' if m.group(2) else '') + ')',
    ),
    # click.echo → pout
    (
        r'click\.echo\(([^)]+)\)',
        lambda m: f'pout({m.group(1)})',
    ),
    # click.secho with err=True → perr with color
    (
        r'click\.secho\(([^,)]+),\s*fg=([^,)]+)(?:,\s*err=True)?(?:,\s*bold=(True|False))?(?:,\s*dim=(True|False))?(?:,\s*nl=(True|False))?\)',
        lambda m: (
            f'perr({m.group(1)}, color={m.group(2)}'
            + (f', bold={m.group(3)}' if m.group(3) else '')
            + (f', dim={m.group(4)}' if m.group(4) else '')
            + (f', nl={m.group(5)}' if m.group(5) else '')
            + ')'
            if 'err=True' in m.group(0)
            else f'pout({m.group(1)}, color={m.group(2)}'
            + (f', bold={m.group(3)}' if m.group(3) else '')
            + (f', dim={m.group(4)}' if m.group(4) else '')
            + (f', nl={m.group(5)}' if m.group(5) else '')
            + ')'
        ),
    ),
    # click.secho without fg → pout/perr
    (
        r'click\.secho\(([^,)]+)(?:,\s*err=True)?(?:,\s*bold=(True|False))?(?:,\s*dim=(True|False))?(?:,\s*nl=(True|False))?\)',
        lambda m: (
            f'perr({m.group(1)}'
            + (f', bold={m.group(2)}' if m.group(2) else '')
            + (f', dim={m.group(3)}' if m.group(3) else '')
            + (f', nl={m.group(4)}' if m.group(4) else '')
            + ')'
            if 'err=True' in m.group(0)
            else f'pout({m.group(1)}'
            + (f', bold={m.group(2)}' if m.group(2) else '')
            + (f', dim={m.group(3)}' if m.group(3) else '')
            + (f', nl={m.group(4)}' if m.group(4) else '')
            + ')'
        ),
    ),
]


def add_imports(content: str) -> str:
    """Add pout/perr imports if not present."""
    if 'from provide.foundation.console import' in content:
        # Already has provide.foundation imports
        if 'pout' not in content or 'perr' not in content:
            # Need to add pout/perr to existing import
            content = re.sub(
                r'from provide\.foundation\.console import ([^\n]+)',
                lambda m: f'from provide.foundation.console import {m.group(1)}, pout, perr'
                if 'pout' not in m.group(1)
                else m.group(0),
                content,
            )
    elif 'import click' in content:
        # Add after click import
        content = re.sub(
            r'(import click\n)',
            r'\1from provide.foundation.console import pout, perr\n',
            content,
        )
    else:
        # Add at top after imports
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_end = i + 1
        lines.insert(import_end, 'from provide.foundation.console import pout, perr')
        content = '\n'.join(lines)

    return content


def migrate_file(file_path: Path, dry_run: bool = True) -> Tuple[str, str, int]:
    """Migrate a single file from click.echo/secho to pout/perr.

    Args:
        file_path: Path to the file to migrate
        dry_run: If True, only show changes without applying

    Returns:
        Tuple of (original_content, new_content, change_count)
    """
    content = file_path.read_text()
    original_content = content
    change_count = 0

    # Apply all patterns
    for pattern, replacement in PATTERNS:
        matches = list(re.finditer(pattern, content))
        if matches:
            content = re.sub(pattern, replacement, content)
            change_count += len(matches)

    # Add imports if we made changes
    if change_count > 0:
        content = add_imports(content)

    if not dry_run and content != original_content:
        file_path.write_text(content)

    return original_content, content, change_count


def show_diff(file_path: Path, original: str, new: str) -> None:
    """Show a simple diff of changes."""
    print(f"\n{'='*80}")
    print(f"File: {file_path}")
    print('='*80)

    orig_lines = original.split('\n')
    new_lines = new.split('\n')

    for i, (orig, new) in enumerate(zip(orig_lines, new_lines), 1):
        if orig != new:
            print(f"{i:4d} - {orig}")
            print(f"{i:4d} + {new}")


def main() -> int:
    """Main migration script."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate click.echo/secho to pout/perr')
    parser.add_argument(
        'files',
        nargs='+',
        type=Path,
        help='Files to migrate',
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes (default is dry-run)',
    )
    parser.add_argument(
        '--no-diff',
        action='store_true',
        help='Do not show diffs',
    )

    args = parser.parse_args()

    total_changes = 0

    for file_path in args.files:
        if not file_path.exists():
            print(f"❌ File not found: {file_path}", file=sys.stderr)
            continue

        original, new, change_count = migrate_file(file_path, dry_run=not args.apply)

        if change_count > 0:
            total_changes += change_count
            if not args.no_diff:
                show_diff(file_path, original, new)

            status = "✅ Applied" if args.apply else "📝 Would apply"
            print(f"\n{status} {change_count} changes to {file_path}")
        else:
            print(f"✨ No changes needed for {file_path}")

    print(f"\n{'='*80}")
    print(f"Total changes: {total_changes}")
    if not args.apply:
        print("Run with --apply to apply changes")
    print('='*80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
