#!/usr/bin/env python3
"""Fix common indentation errors in Python files."""

from pathlib import Path


def fix_empty_blocks(content: str) -> str:
    """Fix empty if/else/for/while/try/except blocks."""
    lines = content.split("\n")
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Check for control structures that end with :
        if (
            stripped
            and stripped[-1] == ":"
            and any(
                stripped.startswith(k)
                for k in [
                    "if ",
                    "elif ",
                    "else:",
                    "for ",
                    "while ",
                    "try:",
                    "except ",
                    "finally:",
                    "with ",
                    "def ",
                    "class ",
                ]
            )
        ):
            fixed_lines.append(line)

            # Check if next line is empty or another control structure
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_stripped = next_line.lstrip()

                # If next line is empty or starts with another control keyword at same or less indentation
                should_insert_pass = not next_stripped or len(next_line) - len(next_stripped) <= indent
                if should_insert_pass and stripped.startswith(
                    (
                        "else:",
                        "except",
                        "finally:",
                        "elif ",
                        "if ",
                        "for ",
                        "while ",
                        "try:",
                        "with ",
                    )
                ):
                    fixed_lines.append(" " * (indent + 4) + "pass")
            i += 1
        else:
            fixed_lines.append(line)
            i += 1

    return "\n".join(fixed_lines)


def main() -> None:
    # Files with known indentation issues
    problem_files = [
        "src/flavor/commands/helpers.py",
        "src/flavor/commands/package.py",
        "src/flavor/commands/workenv.py",
        "src/flavor/output.py",
        "src/flavor/psp/format_2025/executor.py",
        "src/flavor/psp/format_2025/reader.py",
        "src/flavor/psp/format_2025/workenv.py",
    ]

    for file_path in problem_files:
        path = Path(file_path)
        if path.exists():
            print(f"Fixing {file_path}...")
            try:
                content = path.read_text()
                fixed = fix_empty_blocks(content)
                if fixed != content:
                    path.write_text(fixed)
                    print(f"  ✅ Fixed {file_path}")
                else:
                    print(f"  ⏭️  No changes needed for {file_path}")
            except Exception as e:
                print(f"  ❌ Error fixing {file_path}: {e}")
        else:
            print(f"  ⚠️  File not found: {file_path}")


if __name__ == "__main__":
    main()
