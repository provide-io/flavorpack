#!/usr/bin/env python3
"""Fix duplicate headers and __future__ import issues."""

from collections.abc import Iterable
from pathlib import Path


def _needs_fix(content: str) -> bool:
    """Return True when the file contains duplicated headers/docstrings."""
    return "# \n# SPDX-FileCopyrightText" in content or (
        '"""TODO: Add module docstring."""' in content
        and content.count('"""TODO: Add module docstring."""') > 1
    )


def _find_copyright_block(lines: list[str]) -> tuple[int, int] | None:
    """Return the start/end indexes of the first copyright block."""
    for i, line in enumerate(lines):
        if line.startswith("# SPDX-FileCopyrightText") or line.startswith("#\n# SPDX-FileCopyrightText"):
            start = i - 1 if i > 0 and lines[i - 1] in {"#", "# "} else i
            end = start
            for j in range(start, len(lines)):
                if lines[j].startswith("#"):
                    end = j
                else:
                    break
            return start, end
    return None


def _extract_real_docstring(lines: list[str], search_start: int) -> str | None:
    """Grab the first non-placeholder docstring after search_start."""
    search_stop = min(search_start + 50, len(lines))
    for i in range(search_start, search_stop):
        line = lines[i]
        if '"""' in line and "TODO: Add module docstring" not in line:
            if line.count('"""') == 2:
                return line
            for j in range(i + 1, len(lines)):
                if '"""' in lines[j]:
                    return "\n".join(lines[i : j + 1])
            break
    return None


def _has_future_import(lines: Iterable[str]) -> bool:
    """Check whether the file already imports __future__.annotations."""
    return any(line.strip() == "from __future__ import annotations" for line in lines)


def _append_remaining_lines(lines: Iterable[str], new_lines: list[str]) -> None:
    """Copy the body of the file back while skipping duplicate headers."""
    skip_until_imports = True
    for line in lines:
        if skip_until_imports and (
            line.startswith("import ") or (line.startswith("from ") and "__future__" not in line)
        ):
            skip_until_imports = False
            new_lines.append(line)
        elif not skip_until_imports:
            new_lines.append(line)


def fix_file_header(content: str) -> str:
    """Fix duplicate headers and __future__ import placement."""
    if not _needs_fix(content):
        return content

    lines = content.split("\n")
    copyright_block = _find_copyright_block(lines)
    if not copyright_block:
        return content

    start, end = copyright_block
    real_docstring = _extract_real_docstring(lines, end + 1)
    has_future_import = _has_future_import(lines)

    new_lines: list[str] = []
    new_lines.extend(lines[start : end + 1])
    new_lines.append("")
    new_lines.append(real_docstring or '"""Module for flavorpack."""')
    new_lines.append("")

    if has_future_import:
        new_lines.append("from __future__ import annotations")
        new_lines.append("")

    _append_remaining_lines(lines, new_lines)

    return "\n".join(new_lines)


def main() -> None:
    """Apply header fixes to all Python files under src/."""
    src_path = Path("src")

    for py_file in src_path.rglob("*.py"):
        try:
            content = py_file.read_text()
            fixed = fix_file_header(content)

            if fixed != content:
                py_file.write_text(fixed)
                print(f"✅ Fixed {py_file}")
        except Exception as exc:
            print(f"❌ Error processing {py_file}: {exc}")


if __name__ == "__main__":
    main()
