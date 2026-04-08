#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Pre-process plating templates and provider guides to inject global partials.

This script is maintained in provide-foundry and extracted to provider projects.

Implements a hybrid approach:
1. AUTOMATIC INJECTION: Injects global_header after first heading and global_footer at end
   - Unless opted-out via frontmatter (skip_global_header: true / skip_global_footer: true)
2. MANUAL INJECTION: Also processes {{ global('partial_name') }} syntax

Usage:
    ./scripts/inject_partials.py                    # Process provider guides (default)
    ./scripts/inject_partials.py --guides          # Process provider guides only
    ./scripts/inject_partials.py --components      # Process component docs only
    ./scripts/inject_partials.py --dry-run         # Preview changes without writing
"""

from __future__ import annotations

from pathlib import Path
import re
from re import Pattern
import sys
from typing import Any

try:
    import yaml
except ImportError:
    print("❌ Error: PyYAML not installed. Run: uv add pyyaml")
    sys.exit(1)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and remaining content.

    Returns:
        (frontmatter_dict, body_without_frontmatter)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the second --- delimiter
    lines = content.split("\n")
    if len(lines) < 2:
        return {}, content

    # Find closing ---
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        return {}, content

    # Parse YAML frontmatter
    frontmatter_text = "\n".join(lines[1:close_idx])
    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        frontmatter = {}

    # Reconstruct body (keep the closing --- and everything after)
    body = "\n".join(lines[close_idx:])

    return frontmatter, body


def should_skip_header(frontmatter: dict[str, Any]) -> bool:
    """Check if global_header should be skipped."""
    return bool(frontmatter.get("skip_global_header", False))


def should_skip_footer(frontmatter: dict[str, Any]) -> bool:
    """Check if global_footer should be skipped."""
    return bool(frontmatter.get("skip_global_footer", False))


def remove_old_injections(body: str) -> str:
    """Remove old HTML-comment based injections to prepare for new ones."""
    header_pattern = (
        r"\n*<!-- Injected from global partial: _global_header\.md -->\n.*?\n"
        r"<!-- End global partial -->\n*"
    )
    footer_pattern = (
        r"\n*<!-- Injected from global partial: _global_footer\.md -->\n.*?\n"
        r"<!-- End global partial -->"
    )
    body = re.sub(header_pattern, "", body, flags=re.DOTALL)
    body = re.sub(footer_pattern, "", body, flags=re.DOTALL)
    return body


def inject_global_partials(
    docs_dir: Path,
    partials_dir: Path,
    dry_run: bool = False,
    file_pattern: str = "*.tmpl.md",
    fallback_partials_dir: Path | None = None,
) -> int:
    """Inject global partials into documentation files.

    Implements hybrid approach:
    - Auto-inject header after first heading and footer at end
    - Allow opt-out via frontmatter flags
    - Still process manual {{ global(...) }} syntax

    Args:
        docs_dir: Directory containing documentation files
        partials_dir: Directory for project-specific mkdocs overrides (docs/_partials/)
        dry_run: If True, only print what would be changed
        file_pattern: Pattern to match files (default: "*.tmpl.md", can also use "*.md")
        fallback_partials_dir: Foundry defaults (.provide/foundry/docs/_partials/)

    Returns:
        Number of files processed
    """
    doc_files = list(docs_dir.rglob(file_pattern))
    if not doc_files:
        print(f"⚠️  No documentation files found in {docs_dir}")
        return 0

    global_header_content, global_footer_content = _load_global_partials(partials_dir, fallback_partials_dir)
    manual_pattern = re.compile(r"\{\{\s*global\(['\"]([^'\"]+)['\"]\)\s*\}\}")
    files_changed = 0

    for doc_file in doc_files:
        result = _process_document(
            doc_file,
            partials_dir,
            global_header_content,
            global_footer_content,
            manual_pattern,
        )
        if result is None:
            continue

        updated_content, change_descriptions = result
        if dry_run:
            print(f"Would update: {doc_file}")
            if change_descriptions:
                print(f"  Changes: {', '.join(change_descriptions)}")
        else:
            try:
                doc_file.write_text(updated_content, encoding="utf-8")
                print(f"✅ Updated: {doc_file}")
            except Exception as exc:
                print(f"❌ Error writing {doc_file}: {exc}")
                continue

        files_changed += 1

    return files_changed


def main() -> int:
    # Paths - relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Partials hierarchy for mkdocs documentation:
    # 1. docs/_partials/ - project-specific overrides (checked first)
    # 2. .provide/foundry/docs/_partials/ - foundry defaults (fallback)
    # NOTE: plating/partials/ is for Terraform docs only, NEVER used here
    project_partials_dir = project_root / "docs" / "_partials"
    foundry_partials_dir = project_root / ".provide" / "foundry" / "docs" / "_partials"

    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    process_guides = "--guides" in sys.argv or "--provider-guides" in sys.argv
    process_components = "--components" in sys.argv

    total_files_changed = 0

    # Process provider guides if requested or if no target specified
    if process_guides or not any(arg in sys.argv for arg in ["--components", "--guides", "--provider-guides"]):
        provider_guides_dir = project_root / "plating" / "guides"

        if provider_guides_dir.exists():
            print("=" * 60)
            print("🔧 Processing Provider Guides")
            print("=" * 60)
            print(f"🔍 Scanning for guides in: {provider_guides_dir}")
            print(f"📚 Project overrides: {project_partials_dir}")
            print(f"📚 Foundry defaults: {foundry_partials_dir}")
            print()

            if not foundry_partials_dir.exists():
                print("⚠️  Foundry partials not found. Run 'we run docs.setup' first.")
                return 1

            files_changed = inject_global_partials(
                provider_guides_dir,
                project_partials_dir,
                dry_run,
                file_pattern="*.md",
                fallback_partials_dir=foundry_partials_dir,
            )
            total_files_changed += files_changed
            print()

    # Process component documentation if requested
    if process_components:
        docs_dir = project_root / "docs"

        if docs_dir.exists():
            print("=" * 60)
            print("🔧 Processing Component Documentation")
            print("=" * 60)
            print(f"🔍 Scanning for docs in: {docs_dir}")
            print(f"📚 Project overrides: {project_partials_dir}")
            print(f"📚 Foundry defaults: {foundry_partials_dir}")
            print()

            if not foundry_partials_dir.exists():
                print("⚠️  Foundry partials not found. Run 'we run docs.setup' first.")
                return 1

            files_changed = inject_global_partials(
                docs_dir,
                project_partials_dir,
                dry_run,
                file_pattern="*.md",
                fallback_partials_dir=foundry_partials_dir,
            )
            total_files_changed += files_changed
            print()

    if dry_run:
        print(f"📋 Dry run: {total_files_changed} files would be updated")
        return 0
    else:
        if total_files_changed == 0:
            print("✅ Complete: No files needed updating")
        else:
            print(f"✅ Complete: {total_files_changed} files updated")
        return 0


if __name__ == "__main__":
    sys.exit(main())


def _load_global_partials(primary_dir: Path, fallback_dir: Path | None = None) -> tuple[str, str]:
    """Return the contents of the global header and footer partials.

    Checks primary_dir first (project overrides), then fallback_dir (foundry defaults).
    """
    header = _read_partial_with_fallback("_global_header.md", primary_dir, fallback_dir)
    footer = _read_partial_with_fallback("_global_footer.md", primary_dir, fallback_dir)
    return header, footer


def _read_partial_with_fallback(filename: str, primary_dir: Path, fallback_dir: Path | None) -> str:
    """Read a partial file, checking primary dir first, then fallback."""
    primary_path = primary_dir / filename
    if primary_path.exists():
        return primary_path.read_text(encoding="utf-8").strip()
    if fallback_dir:
        fallback_path = fallback_dir / filename
        if fallback_path.exists():
            return fallback_path.read_text(encoding="utf-8").strip()
    return ""


def _read_partial(path: Path) -> str:
    """Read and strip a partial file, returning an empty string if missing."""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _process_document(
    doc_file: Path,
    partials_dir: Path,
    header_content: str,
    footer_content: str,
    manual_pattern: Pattern[str],
) -> tuple[str, list[str]] | None:
    """Process a single documentation file and return updated content."""
    try:
        original_content = doc_file.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - filesystem issue
        print(f"❌ Error reading {doc_file}: {exc}")
        return None

    frontmatter, body_with_delim = parse_frontmatter(original_content)
    body = remove_old_injections(body_with_delim)
    changes: list[str] = []

    skip_header = should_skip_header(frontmatter)
    skip_footer = should_skip_footer(frontmatter)

    body, header_added = _auto_inject_header(body, header_content, skip_header)
    if header_added:
        changes.append("auto-inject header")

    body, footer_added = _auto_inject_footer(body, footer_content, skip_footer)
    if footer_added:
        changes.append("auto-inject footer")

    body, manual_changes = _inject_manual_partials(body, partials_dir, manual_pattern)
    if manual_changes:
        changes.append(f"manual inject: {', '.join(manual_changes)}")

    updated_content = _rebuild_content(original_content, body, bool(frontmatter))
    if updated_content == original_content:
        return None

    return updated_content, changes


def _auto_inject_header(body: str, header_content: str, skip_header: bool) -> tuple[str, bool]:
    """Insert the global header after the first heading/description."""
    if not header_content or skip_header or _has_header(body):
        return body, False

    heading_pattern = re.compile(r"^# .+$", re.MULTILINE)
    heading_match = heading_pattern.search(body)
    if not heading_match:
        return body, False

    insert_pos = heading_match.end()
    remaining = body[insert_pos:]
    lines = remaining.split("\n")

    desc_end = 0
    for index, line in enumerate(lines):
        if line.strip() and not line.startswith("#"):
            desc_end = index + 1
            break
    if desc_end:
        insert_pos += len("\n".join(lines[:desc_end])) + 1

    header_injection = f"\n\n{header_content}\n"
    updated_body = body[:insert_pos] + header_injection + body[insert_pos:]
    return updated_body, True


def _auto_inject_footer(body: str, footer_content: str, skip_footer: bool) -> tuple[str, bool]:
    """Append the global footer if needed."""
    if not footer_content or skip_footer or _has_footer(body):
        return body, False

    footer_injection = f"\n\n{footer_content}"
    return body.rstrip() + footer_injection, True


def _inject_manual_partials(
    body: str,
    partials_dir: Path,
    pattern: Pattern[str],
) -> tuple[str, list[str]]:
    """Replace manual {{ global(...) }} markers with their content."""
    changes: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        partial_name = match.group(1)
        partial_file = partials_dir / f"_{partial_name}.md"
        if not partial_file.exists():
            print(f"⚠️  Warning: Global partial '{partial_name}' not found at {partial_file}")
            return match.group(0)
        try:
            partial_content = partial_file.read_text(encoding="utf-8").strip()
        except Exception as exc:  # pragma: no cover - filesystem issue
            print(f"❌ Error reading partial {partial_file}: {exc}")
            return match.group(0)

        changes.append(partial_name)
        start_marker = f"<!-- Injected from global partial: _{partial_name}.md -->"
        end_marker = "<!-- End global partial -->"
        return f"{start_marker}\n{partial_content}\n{end_marker}"

    updated_body = pattern.sub(replacer, body)
    return updated_body, changes


def _rebuild_content(original: str, body: str, has_frontmatter: bool) -> str:
    """Reconstruct the document, preserving frontmatter delimiters."""
    if not has_frontmatter or not original.startswith("---"):
        return body

    close_idx = original.find("---", 3)
    if close_idx == -1:
        return body

    frontmatter_section = original[: close_idx + 3]
    body_lines = body.split("\n", 1)
    if body_lines and body_lines[0].strip() == "---":
        body_without_delim = body_lines[1] if len(body_lines) > 1 else ""
    else:
        body_without_delim = body

    return frontmatter_section + "\n" + body_without_delim


def _has_header(body: str) -> bool:
    """Return True if a global header already exists."""
    return (
        "<!-- Injected from global partial: _global_header.md -->" in body or "POC (proof-of-concept)" in body
    )


def _has_footer(body: str) -> bool:
    """Return True if a global footer already exists."""
    return "<!-- Injected from global partial: _global_footer.md -->" in body
