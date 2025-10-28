
import ast
import sys

# 🌶️📦🔚

def conform_file(filepath):
    """
    Conforms a Python file to the specified header and footer protocol.
    """
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}", file=sys.stderr)
        return

    # Determine if it's an executable
    is_executable = content.startswith('#!/usr/bin/env python3')

    # Extract module docstring
    original_docstring = ""
    docstring_end_line = -1
    try:
        tree = ast.parse(content)
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
            original_docstring = ast.get_docstring(tree)
            docstring_node = tree.body[0]
            docstring_end_line = docstring_node.lineno + len(docstring_node.value.s.splitlines()) -1

    except SyntaxError:
        # Ignore syntax errors for now, will be caught by ruff/mypy
        pass

    # Extract __future__ imports
    future_imports = []
    lines = content.split('\n')
    for line in lines:
        if line.strip().startswith('from __future__ import'):
            future_imports.append(line)

    # Construct the new header
    header_lines = []
    if is_executable:
        header_lines.append('#!/usr/bin/env python3')
    else:
        header_lines.append('# ')

    header_lines.extend([
        '# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.',
        '# SPDX-License-Identifier: Apache-2.0',
        '#',
    ])

    if future_imports:
        header_lines.extend(future_imports)

    if original_docstring:
        header_lines.append(f'"""{original_docstring}"""')
    else:
        header_lines.append('"""TODO: Add module docstring."""')

    new_header = '\n'.join(header_lines)

    # Find the start of the code
    start_of_code = 0
    if docstring_end_line != -1:
        start_of_code = docstring_end_line
    else:
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""') and not line.strip().startswith('from __future__ import'):
                start_of_code = i
                break

    body_content = '\n'.join(lines[start_of_code:])

    # Remove old docstring from body
    if original_docstring:
        body_content = body_content.replace(f'"""{original_docstring}"""', '')


    # Remove old footers and trailing whitespace
    body_content = body_content.strip()
    body_lines = body_content.split('\n')
    body_lines = [line for line in body_lines if '# 🌶️📦' not in line]
    body_content = '\n'.join(body_lines)

    # Construct the final content
    final_content = f"{new_header}\n\n{body_content}\n\n# 🌶️📦🔚\n"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_content)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for filepath in sys.argv[1:]:
            conform_file(filepath)
    else:
        print("Usage: python conform.py <file1.py> <file2.py> ...", file=sys.stderr)
