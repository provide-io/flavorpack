#!/usr/bin/env python3
"""Update all Python file footers with consistent project emojis."""

from pathlib import Path
import re


def get_file_emoji(file_path: Path) -> str:
    """Determine the appropriate emoji for a file based on its name and content."""
    name = file_path.name.lower()
    
    # Read file content for better classification
    try:
        content = file_path.read_text().lower()
    except:
        content = ""
    
    # CLI files
    if "cli" in name or "click" in content:
        return "🖥️"
    
    # API/Interface files
    if "api" in name or "interface" in name:
        return "🔌"
    
    # Build/Compiler files
    if "build" in name or "compiler" in name or "compile" in content:
        return "🔨"
    
    # Key/Crypto files
    if "key" in name or "crypto" in name or "sign" in content:
        return "🔑"
    
    # Metadata files
    if "metadata" in name or "meta" in name:
        return "📋"
    
    # Exception/Error files
    if "exception" in name or "error" in name:
        return "⚠️"
    
    # Reader/Parser files
    if "reader" in name or "parser" in name or "read" in name:
        return "📖"
    
    # Model/Data structure files
    if "model" in name or "schema" in name or "data" in name:
        return "📊"
    
    # Packaging files
    if "packag" in name or "orchestrator" in name:
        return "📦"
    
    # Test files
    if "test" in name or "test_" in name:
        return "🧪"
    
    # Config files
    if "config" in name or "conf" in name:
        return "⚙️"
    
    # Init files or main modules
    if "__init__" in name or "main" in name:
        return "🚀"
    
    # Default for other files
    return "📄"


def update_footer(file_path: Path) -> None:
    """Update the footer of a Python file with project-specific emojis."""
    try:
        content = file_path.read_text()
    except:
        return
    
    # Find the last occurrence of the magic emoji pattern (3 emojis + 🪄)
    # This regex looks for a line with # followed by 3 emojis and 🪄
    magic_pattern = re.compile(r'\n# [^\n]*🪄\s*\n*$', re.MULTILINE | re.DOTALL)
    
    # Remove existing magic footer if it exists
    match = magic_pattern.search(content)
    if match:
        # Remove from the match to the end of file
        content = content[:match.start()]
    else:
        # If no magic footer found, just strip trailing whitespace
        content = content.rstrip()
    
    # Add new footer
    file_emoji = get_file_emoji(file_path)
    footer = f"\n\n# 📦🍜{file_emoji}🪄\n"
    
    # Write updated content
    new_content = content + footer
    file_path.write_text(new_content)
    print(f"Updated {file_path.name} with footer: 📦🍜{file_emoji}🪄")


def main():
    """Update all Python files in the src directory."""
    src_dir = Path(__file__).parent / "src"
    
    if not src_dir.exists():
        print(f"Source directory not found: {src_dir}")
        return
    
    # Find all Python files
    python_files = list(src_dir.rglob("*.py"))
    
    print(f"Found {len(python_files)} Python files to update")
    
    for file_path in sorted(python_files):
        update_footer(file_path)
    
    print("\nFooter update complete!")


if __name__ == "__main__":
    main()

# 📦🍜🖥️🪄
