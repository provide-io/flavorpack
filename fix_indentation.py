#!/usr/bin/env python3
"""Fix common indentation errors in Python files."""

from pathlib import Path


def fix_empty_blocks(content):
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
                if not next_stripped or (next_stripped and len(next_line) - len(next_stripped) <= indent):
                    # Add a pass statement
                    if (
                        stripped.startswith("else:")
                        or stripped.startswith("except")
                        or stripped.startswith("finally:")
                        or stripped.startswith("elif ")
                        or stripped.startswith("if ")
                        or stripped.startswith("for ")
                        or stripped.startswith("while ")
                        or stripped.startswith("try:")
                        or stripped.startswith("with ")
                    ):
                        fixed_lines.append(" " * (indent + 4) + "pass")
            i += 1
        else:
            fixed_lines.append(line)
            i += 1

    return "\n".join(fixed_lines)


def main():
    # Files with known indentation issues
    problem_files = [
        "src/flavor/commands/helpers.py",
        "src/flavor/commands/package.py",
        "src/flavor/commands/workenv.py",
        "src/flavor/output.py",
        "src/flavor/psp/format_2025/executor.py",
        "src/flavor/psp/format_2025/reader.py",
        "src/flavor/psp/format_2025/workenv.py",
        "scripts/export_protobuf_spec.py",
        "scripts/generate_test_vectors.py",
        "scripts/verify_operations.py",
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
