#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""
A script to enforce header and footer conformance on Python source files.
"""

import ast
from pathlib import Path
import sys

# --- Protocol Specification ---

HEADER_SHEBANG = "#!/usr/bin/env python3"
HEADER_LIBRARY = "# "
SPDX_BLOCK = [
    "# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.",
    "# SPDX-License-Identifier: Apache-2.0",
    "#",
]
DOCSTRING_PLACEHOLDER = '"""TODO: Add module docstring."""'
FOOTER_COMMENT = "# 🌶️📦🔚"
OLD_FOOTER_PATTERNS = ["# 🌶️📦", "# 🐍🏗️🔚"]

# --- Implementation Logic ---

def get_module_docstring(source_code: str) -> str | None:
    """Safely extracts the module-level docstring from source code."""
    try:
        tree = ast.parse(source_code)
        return ast.get_docstring(tree)
    except (SyntaxError, IndexError):
        # If the file has syntax errors, we can't parse it.
        # Return None and the script will have to guess.
        return None

def conform_file(filepath: Path) -> None:
    """
    Applies the header/footer protocol to a single Python file.
    """
    try:
        original_content = filepath.read_text(encoding='utf-8')
        lines = original_content.splitlines()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}", file=sys.stderr)
        return
    except UnicodeDecodeError:
        print(f"Error: Could not decode file {filepath} as UTF-8.", file=sys.stderr)
        return


    # 1. Analyze existing content
    is_executable = lines and lines[0].startswith("#!")
    existing_docstring = get_module_docstring(original_content)

    # 2. Strip old header, docstring, footers, and whitespace
    start_of_code_index = 0
    if lines:
        # Find where the actual code begins, skipping shebang, comments, and the module docstring
        in_docstring = False
        docstring_quotes = ''
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith(('"""', "'''")):
                # This logic is imperfect but a decent heuristic for finding the end of the docstring
                if in_docstring or stripped_line.count('"""') > 1 or stripped_line.count("'''") > 1:
                    start_of_code_index = i + 1
                    in_docstring = False
                    break
                else:
                    in_docstring = True
                    docstring_quotes = '"""' if '"""' in stripped_line else "'''"
            elif in_docstring and docstring_quotes in stripped_line:
                start_of_code_index = i + 1
                in_docstring = False
                break
            elif not stripped_line or stripped_line.startswith("#"):
                start_of_code_index = i + 1
            else:
                 # It's the first real line of code
                 start_of_code_index = i
                 break

    # If we couldn't find code, reset to 0 to be safe
    if start_of_code_index >= len(lines):
         start_of_code_index = 0


    # Heuristic to find the start of the "real" code after potential headers
    # This is tricky; we'll assume the first non-comment, non-docstring line is it.
    body_lines = lines[start_of_code_index:]
    body_content = "\n".join(body_lines).strip()

    # Remove any old footers from the body
    for pattern in OLD_FOOTER_PATTERNS:
        body_content = "\n".join(
            line for line in body_content.splitlines() if pattern not in line
        )
    body_content = body_content.strip()


    # 3. Construct the new file content
    final_header = []
    final_header.append(HEADER_SHEBANG if is_executable else HEADER_LIBRARY)
    final_header.extend(SPDX_BLOCK)
    final_header.append("")  # Blank line before docstring

    docstring_to_use = f'"""{existing_docstring}"""' if existing_docstring else DOCSTRING_PLACEHOLDER

    # Final assembly
    new_content_parts = []
    new_content_parts.extend(final_header)
    new_content_parts.append(docstring_to_use)
    if body_content: # only add a blank line if there's code
        new_content_parts.append("")
        new_content_parts.append(body_content)

    final_content = "\n".join(new_content_parts).strip()

    # 4. Append the new footer
    final_content += f"\n\n{FOOTER_COMMENT}\n"

    # 5. Write the conformed content back to the file
    filepath.write_text(final_content, encoding='utf-8')
    # print(f"Conformed: {filepath}")

def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python conform.py <file1.py> <file2.py> ...", file=sys.stderr)
        sys.exit(1)

    for file_path_str in sys.argv[1:]:
        file_path = Path(file_path_str)
        if not file_path.is_file() or not file_path.name.endswith(".py"):
            print(f"Skipping non-Python file: {file_path}", file=sys.stderr)
            continue
        conform_file(file_path)

if __name__ == "__main__":
    main()
