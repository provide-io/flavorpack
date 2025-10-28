import ast
import sys

# 🌶️📦🔚


def conform_file(filepath):
    """
    Conforms a Python file to the specified header and footer protocol.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}", file=sys.stderr)
        return

    # Determine if it's an executable
    is_executable = content.startswith("#!/usr/bin/env python3")

    # Extract module docstring
    original_docstring = ""
    try:
        tree = ast.parse(content)
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
            original_docstring = ast.get_docstring(tree)
    except SyntaxError:
        # Ignore syntax errors for now, will be caught by ruff/mypy
        pass

    # Construct the new header
    header_lines = []
    if is_executable:
        header_lines.append("#!/usr/bin/env python3")
    else:
        header_lines.append("# ")

    header_lines.extend(
        [
            "# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.",
            "# SPDX-License-Identifier: Apache-2.0",
            "#",
        ]
    )

    if original_docstring:
        header_lines.append(f'"""{original_docstring}"""')
    else:
        header_lines.append('"""TODO: Add module docstring."""')

    new_header = "\n".join(header_lines)

    # Strip existing header and footer
    lines = content.split("\n")

    # Find the start of the code
    start_of_code = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.strip().startswith("#") and not line.strip().startswith('"""'):
            start_of_code = i
            break

    # If the file is only comments/docstrings, we might not find a code start.
    # In that case, we will just append the new header.
    if start_of_code > 0:
        # Check if there is a docstring on the line before the code starts
        if '"""' in lines[start_of_code - 1]:
            body_content = "\n".join(lines[start_of_code - 1 :])
        else:
            body_content = "\n".join(lines[start_of_code:])
    elif original_docstring:
        body_content = ""
    else:
        body_content = "\n".join(lines)

    # Remove old footers and trailing whitespace
    body_content = body_content.strip()
    body_lines = body_content.split("\n")
    body_lines = [line for line in body_lines if "# 🌶️📦" not in line]
    body_content = "\n".join(body_lines)

    # Construct the final content
    final_content = f"{new_header}\n\n{body_content}\n\n# 🌶️📦🔚\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_content)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for filepath in sys.argv[1:]:
            conform_file(filepath)
    else:
        print("Usage: python conform.py <file1.py> <file2.py> ...", file=sys.stderr)
