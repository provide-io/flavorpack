#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Fix relative links in FlavorPack documentation."""

from pathlib import Path
import re


def fix_relative_links(file_path: Path) -> bool:
    """Fix relative links in a markdown file based on its directory depth."""

    # Calculate depth from docs root
    rel_path = file_path.relative_to(Path("docs"))
    depth = len(rel_path.parts) - 1  # -1 because the file itself doesn't count

    # Read the file
    content = file_path.read_text()
    original_content = content

    # Patterns to fix based on file location
    if "api/" in str(rel_path):
        if depth == 2:  # api/python/index.md, api/native/index.md
            # Fix links like ../guide/index.md -> ../../guide/index.md
            content = re.sub(r"\]\(\.\./guide/", "](../../guide/", content)
            content = re.sub(r"\]\(\.\./cookbook/", "](../../cookbook/", content)
            content = re.sub(r"\]\(\.\./development/", "](../../development/", content)
            content = re.sub(r"\]\(\.\./getting-started/", "](../../getting-started/", content)
            content = re.sub(r"\]\(\.\./api/", "](../../api/", content)
            content = re.sub(r"\]\(\.\./troubleshooting/", "](../../troubleshooting/", content)
        elif depth == 3:  # api/python/packaging/index.md, api/python/psp/index.md
            # Fix links to go up three levels
            content = re.sub(r"\]\(\.\./guide/", "](../../../guide/", content)
            content = re.sub(r"\]\(\.\./cookbook/", "](../../../cookbook/", content)
            content = re.sub(r"\]\(\.\./development/", "](../../../development/", content)
            content = re.sub(r"\]\(\.\./getting-started/", "](../../../getting-started/", content)
            content = re.sub(r"\]\(\.\./api/", "](../../../api/", content)
            content = re.sub(r"\]\(\.\./troubleshooting/", "](../../../troubleshooting/", content)

    elif "cookbook/" in str(rel_path):
        if depth == 2:  # cookbook/examples/index.md, cookbook/recipes/index.md
            # Fix links like ../getting-started/index.md -> ../../getting-started/index.md
            content = re.sub(r"\]\(\.\./getting-started/", "](../../getting-started/", content)
            content = re.sub(r"\]\(\.\./guide/", "](../../guide/", content)
            content = re.sub(r"\]\(\.\./api/", "](../../api/", content)
            content = re.sub(r"\]\(\.\./development/", "](../../development/", content)
            content = re.sub(r"\]\(\.\./troubleshooting/", "](../../troubleshooting/", content)

    elif "development/testing/" in str(rel_path):
        if depth == 2:  # development/testing/index.md
            # Fix links like ../getting-started/index.md -> ../../getting-started/index.md
            content = re.sub(r"\]\(\.\./getting-started/", "](../../getting-started/", content)
            content = re.sub(r"\]\(\.\./guide/", "](../../guide/", content)
            content = re.sub(r"\]\(\.\./api/", "](../../api/", content)

    elif "guide/" in str(rel_path):
        if depth == 2:  # guide/concepts/index.md, guide/advanced/index.md, etc.
            # Fix links like ../getting-started/index.md -> ../../getting-started/index.md
            content = re.sub(r"\]\(\.\./getting-started/", "](../../getting-started/", content)
            content = re.sub(r"\]\(\.\./api/", "](../../api/", content)
            content = re.sub(r"\]\(\.\./troubleshooting/", "](../../troubleshooting/", content)
            content = re.sub(r"\]\(\.\./cookbook/", "](../../cookbook/", content)
            content = re.sub(r"\]\(\.\./development/", "](../../development/", content)

    elif "troubleshooting/platforms/" in str(rel_path):
        if depth == 2:  # troubleshooting/platforms/macos.md
            # Fix links like ../getting-started/index.md -> ../../getting-started/index.md
            content = re.sub(r"\]\(\.\./getting-started/", "](../../getting-started/", content)
            content = re.sub(r"\]\(\.\./guide/", "](../../guide/", content)
            content = re.sub(r"\]\(\.\./api/", "](../../api/", content)

    # Write back if changed
    if content != original_content:
        file_path.write_text(content)
        return True
    return False


def main():
    """Fix all documentation links."""
    docs_dir = Path("docs")
    fixed_count = 0

    # Find all markdown files
    for md_file in docs_dir.rglob("*.md"):
        if fix_relative_links(md_file):
            print(f"Fixed: {md_file.relative_to(docs_dir)}")
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
# 🌶️📦🔚
