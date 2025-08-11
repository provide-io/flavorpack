#!/usr/bin/env python3
"""Update all Go and Rust file footers with consistent project emojis."""

from pathlib import Path
import re


def get_file_emoji(file_path: Path, lang: str) -> str:
    """Determine the appropriate emoji for a file based on its name and content."""
    name = file_path.name.lower()
    
    # Read file content for better classification
    try:
        content = file_path.read_text().lower()
    except:
        content = ""
    
    # Main/Entry point files
    if "main" in name or (lang == "go" and "func main(" in content):
        return "🚀"
    
    # CLI files
    if "cli" in name or "cobra" in content or "clap" in content:
        return "🖥️"
    
    # Build/Compiler files
    if "build" in name or "compile" in name:
        return "🔨"
    
    # Packager files
    if "packag" in name:
        return "📦"
    
    # Launcher files
    if "launch" in name:
        return "🚀"
    
    # Crypto/Security files
    if "crypto" in name or "sign" in name or "verify" in name:
        return "🔑"
    
    # Test files
    if "_test" in name or "test_" in name:
        return "🧪"
    
    # Config files
    if "config" in name:
        return "⚙️"
    
    # Default for other files
    return "📄"


def update_go_footer(file_path: Path) -> None:
    """Update the footer of a Go file with project-specific emojis."""
    try:
        content = file_path.read_text()
    except:
        return
    
    # Find the last occurrence of the magic emoji pattern
    # Go comments use // 
    magic_pattern = re.compile(r'\n// [^\n]*🪄\s*\n*$', re.MULTILINE | re.DOTALL)
    
    # Remove existing magic footer if it exists
    match = magic_pattern.search(content)
    if match:
        content = content[:match.start()]
    else:
        content = content.rstrip()
    
    # Add new footer
    file_emoji = get_file_emoji(file_path, "go")
    footer = f"\n\n// 📦🍜{file_emoji}🪄\n"
    
    # Write updated content
    new_content = content + footer
    file_path.write_text(new_content)
    print(f"Updated {file_path.name} with footer: 📦🍜{file_emoji}🪄")


def update_rust_footer(file_path: Path) -> None:
    """Update the footer of a Rust file with project-specific emojis."""
    try:
        content = file_path.read_text()
    except:
        return
    
    # Find the last occurrence of the magic emoji pattern
    # Rust comments use // 
    magic_pattern = re.compile(r'\n// [^\n]*🪄\s*\n*$', re.MULTILINE | re.DOTALL)
    
    # Remove existing magic footer if it exists
    match = magic_pattern.search(content)
    if match:
        content = content[:match.start()]
    else:
        content = content.rstrip()
    
    # Add new footer
    file_emoji = get_file_emoji(file_path, "rust")
    footer = f"\n\n// 📦🍜{file_emoji}🪄\n"
    
    # Write updated content
    new_content = content + footer
    file_path.write_text(new_content)
    print(f"Updated {file_path.name} with footer: 📦🍜{file_emoji}🪄")


def main():
    """Update all Go and Rust files in the src directory."""
    # Look for Go files in the go subdirectory
    go_dir = Path(__file__).parent / "src" / "flavor" / "go"
    rust_dir = Path(__file__).parent / "src" / "flavor" / "rust"
    
    # Find all Go files
    go_files = []
    if go_dir.exists():
        go_files = list(go_dir.rglob("*.go"))
        print(f"Found {len(go_files)} Go files to update")
        
        for file_path in sorted(go_files):
            update_go_footer(file_path)
    else:
        print(f"Go directory not found: {go_dir}")
    
    # Find all Rust files
    rust_files = []
    if rust_dir.exists():
        rust_files = list(rust_dir.rglob("*.rs"))
        print(f"\nFound {len(rust_files)} Rust files to update")
        
        for file_path in sorted(rust_files):
            update_rust_footer(file_path)
    else:
        print(f"\nRust directory not found: {rust_dir}")
    
    print("\nGo and Rust footer update complete!")


if __name__ == "__main__":
    main()

# 📦🍜📄🪄
