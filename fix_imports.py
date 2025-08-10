#!/usr/bin/env python3
"""Fix imports to use Python 3.11+ native features."""

import re
from pathlib import Path


def fix_imports_in_file(file_path: Path) -> None:
    """Fix imports in a Python file."""
    content = file_path.read_text()
    original_content = content
    
    # Remove tomli imports and use native tomllib
    content = re.sub(
        r'try:\s*import tomllib\s*except ImportError:\s*import tomli as tomllib',
        'import tomllib',
        content,
        flags=re.MULTILINE | re.DOTALL
    )
    
    # Simpler tomli import
    content = content.replace('import tomli as tomllib', 'import tomllib')
    content = content.replace('import tomli', 'import tomllib')
    
    # Update typing imports to use native types
    # Dict -> dict, List -> list, etc.
    type_replacements = [
        (r'from typing import Dict\b', 'from typing import '),
        (r'from typing import List\b', 'from typing import '),
        (r'from typing import Set\b', 'from typing import '),
        (r'from typing import Tuple\b', 'from typing import '),
        (r'from typing import Optional\b', 'from typing import '),
        (r'from typing import Union\b', 'from typing import '),
        (r'Dict\[([^]]+)\]', r'dict[\1]'),
        (r'List\[([^]]+)\]', r'list[\1]'),
        (r'Set\[([^]]+)\]', r'set[\1]'),
        (r'Tuple\[([^]]+)\]', r'tuple[\1]'),
        (r'Optional\[([^]]+)\]', r'\1 | None'),
        (r'Union\[([^,]+),\s*None\]', r'\1 | None'),
    ]
    
    for pattern, replacement in type_replacements:
        content = re.sub(pattern, replacement, content)
    
    # Clean up empty imports
    content = re.sub(r'from typing import\s*\n', '', content)
    content = re.sub(r'from typing import\s*,', 'from typing import', content)
    
    # Remove tomli from requirements
    content = content.replace('"tomli; python_version < \'3.11\'"', '')
    content = content.replace('\'tomli; python_version < "3.11"\'', '')
    content = re.sub(r',\s*"tomli[^"]*"', '', content)
    content = re.sub(r'"tomli[^"]*",\s*', '', content)
    
    if content != original_content:
        file_path.write_text(content)
        print(f"Fixed imports in {file_path}")


def main():
    """Fix imports in all Python files."""
    src_dir = Path(__file__).parent / "src"
    
    # Find all Python files
    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            fix_imports_in_file(py_file)


if __name__ == "__main__":
    main()

# 📦🍜📄🪄
