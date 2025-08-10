#!/usr/bin/env python3
"""Fix attrs imports to use direct imports."""

import re
from pathlib import Path


def fix_attrs_in_file(file_path: Path) -> None:
    """Fix attrs imports in a Python file."""
    content = file_path.read_text()
    original_content = content
    
    # Update import statements
    if "import attrs" in content:
        # Check what's being used
        uses_define = "@attrs.define" in content or "attrs.define" in content
        uses_field = "attrs.field" in content
        uses_asdict = "attrs.asdict" in content
        uses_fields = "attrs.fields" in content
        
        # Build import list
        imports = []
        if uses_define:
            imports.append("define")
        if uses_field:
            imports.append("field")
        if uses_asdict:
            imports.append("asdict")
        if uses_fields:
            imports.append("fields")
        
        if imports:
            # Replace import
            content = content.replace("import attrs", f"from attrs import {', '.join(imports)}")
            
            # Replace usages
            content = content.replace("@attrs.define", "@define")
            content = content.replace("attrs.define", "define")
            content = content.replace("attrs.field", "field")
            content = content.replace("attrs.asdict", "asdict")
            content = content.replace("attrs.fields", "fields")
    
    if content != original_content:
        file_path.write_text(content)
        print(f"Fixed attrs imports in {file_path}")


def main():
    """Fix attrs imports in all Python files."""
    src_dir = Path(__file__).parent / "src"
    
    # Find all Python files
    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            fix_attrs_in_file(py_file)


if __name__ == "__main__":
    main()

# 📦🍜📄🪄
