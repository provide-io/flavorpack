#!/usr/bin/env python3
"""Fix duplicate headers and __future__ import issues."""

from pathlib import Path


def fix_file_header(content):
    """Fix duplicate headers and __future__ import placement."""
    lines = content.split("\n")

    # Check if the file has the problematic pattern
    if not (
        "# \n# SPDX-FileCopyrightText" in content
        or (
            '"""TODO: Add module docstring."""' in content
            and content.count('"""TODO: Add module docstring."""') > 1
        )
    ):
        return content

    # Find the first copyright header
    copyright_start = -1
    for i, line in enumerate(lines):
        if line.startswith("# SPDX-FileCopyrightText") or line.startswith("#\n# SPDX-FileCopyrightText"):
            copyright_start = i - 1 if i > 0 and lines[i - 1] in ["#", "# "] else i
            break

    if copyright_start == -1:
        return content

    # Find where the first copyright block ends
    copyright_end = copyright_start
    for i in range(copyright_start, len(lines)):
        if lines[i].startswith("#"):
            copyright_end = i
        else:
            break

    # Find the first real docstring (not TODO)
    real_docstring = None
    real_docstring_start = -1

    for i in range(copyright_end + 1, min(copyright_end + 50, len(lines))):
        if '"""' in lines[i]:
            if "TODO: Add module docstring" not in lines[i]:
                # Found a real docstring
                real_docstring_start = i
                if lines[i].count('"""') == 2:
                    # Single line docstring
                    real_docstring = lines[i]
                else:
                    # Multi-line docstring
                    for j in range(i + 1, len(lines)):
                        if '"""' in lines[j]:
                            real_docstring = "\n".join(lines[i : j + 1])
                            break
                break

    # Find __future__ import
    future_import = None
    for i, line in enumerate(lines):
        if line.strip() == "from __future__ import annotations":
            future_import = line
            break

    # Reconstruct the file
    new_lines = []

    # Add copyright header (just the first one)
    new_lines.extend(lines[copyright_start : copyright_end + 1])
    new_lines.append("")

    # Add the real docstring or a default one
    if real_docstring:
        new_lines.append(real_docstring)
    else:
        new_lines.append('"""Module for flavorpack."""')
    new_lines.append("")

    # Add __future__ import
    if future_import:
        new_lines.append("from __future__ import annotations")
        new_lines.append("")

    # Add the rest of the file, skipping duplicate headers and imports
    skip_until_imports = True
    for line in lines:
        if skip_until_imports:
            # Skip until we find the first import statement that's not __future__
            if line.startswith("import ") or (line.startswith("from ") and "__future__" not in line):
                skip_until_imports = False
                new_lines.append(line)
        else:
            new_lines.append(line)

    return "\n".join(new_lines)


def main():
    # Find all Python files in src
    src_path = Path("src")

    for py_file in src_path.rglob("*.py"):
        try:
            content = py_file.read_text()
            fixed = fix_file_header(content)

            if fixed != content:
                py_file.write_text(fixed)
                print(f"✅ Fixed {py_file}")
        except Exception as e:
            print(f"❌ Error processing {py_file}: {e}")


if __name__ == "__main__":
    main()
