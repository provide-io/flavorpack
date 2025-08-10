#!/usr/bin/env python3
"""Add headers and footers to all Python files in the flavor package."""

import os
import random
from pathlib import Path


# Emoji sets for different file types/purposes
PACKAGER_EMOJIS = ["📦", "🏗️", "🔨", "⚙️", "🛠️", "📐", "🎁"]
LAUNCHER_EMOJIS = ["🚀", "🎯", "⚡", "🏃", "🌟", "💫", "🔥"]
API_EMOJIS = ["🔌", "🔗", "🌐", "📡", "🔧", "🎛️", "⚖️"]
MODEL_EMOJIS = ["📊", "📈", "🗂️", "📋", "🏛️", "🎨", "📝"]
CLI_EMOJIS = ["💻", "⌨️", "🖥️", "📟", "🎮", "🕹️", "🖱️"]
TEST_EMOJIS = ["🧪", "🔬", "🧬", "🧫", "🔍", "🌡️", "⚗️"]
UTIL_EMOJIS = ["🔧", "🛠️", "⚙️", "🔩", "🪛", "🔨", "🪚"]
SECURITY_EMOJIS = ["🔐", "🔒", "🔑", "🛡️", "🚨", "🔓", "🗝️"]
ERROR_EMOJIS = ["❌", "🚫", "⚠️", "🚨", "💥", "🆘", "📛"]
CONFIG_EMOJIS = ["⚙️", "🎛️", "🔧", "📐", "📏", "🗃️", "🎚️"]


def get_emojis_for_file(file_path: Path) -> list[str]:
    """Get appropriate emojis based on file name and path."""
    name = file_path.stem.lower()
    path_str = str(file_path).lower()
    
    # Determine file type
    if "test" in name:
        return random.sample(TEST_EMOJIS, 3)
    elif "launcher" in name or "launch" in path_str:
        return random.sample(LAUNCHER_EMOJIS, 3)
    elif "packager" in name or "package" in name or "build" in name:
        return random.sample(PACKAGER_EMOJIS, 3)
    elif "api" in name:
        return random.sample(API_EMOJIS, 3)
    elif "model" in name or "schema" in name:
        return random.sample(MODEL_EMOJIS, 3)
    elif "cli" in name or "command" in name:
        return random.sample(CLI_EMOJIS, 3)
    elif "security" in name or "crypto" in name or "sign" in name:
        return random.sample(SECURITY_EMOJIS, 3)
    elif "error" in name or "exception" in name:
        return random.sample(ERROR_EMOJIS, 3)
    elif "config" in name or "setting" in name:
        return random.sample(CONFIG_EMOJIS, 3)
    elif "util" in name or "helper" in name:
        return random.sample(UTIL_EMOJIS, 3)
    else:
        # Mix from different categories
        all_emojis = (PACKAGER_EMOJIS + LAUNCHER_EMOJIS + API_EMOJIS + 
                     MODEL_EMOJIS + CLI_EMOJIS + UTIL_EMOJIS)
        return random.sample(all_emojis, 3)


def add_header_and_footer_to_file(file_path: Path, src_dir: Path) -> None:
    """Add header and footer to a Python file."""
    # Calculate relative path from src directory
    try:
        relative_path = file_path.relative_to(src_dir)
    except ValueError:
        # File is not under src directory
        return
    
    # Read existing content
    content = file_path.read_text()
    
    # Check if header already exists
    if content.startswith("#\n# ") and "# " in content[-20:]:
        print(f"Skipping {file_path} - already has header/footer")
        return
    
    # Create header
    header = f"#\n# {relative_path}\n#\n\n"
    
    # Create footer with emojis
    emojis = get_emojis_for_file(file_path)
    footer = f"\n# {' '.join(emojis)}\n"
    
    # Handle content
    if content.startswith("#!"):
        # Skip shebang
        lines = content.split('\n', 1)
        if len(lines) > 1:
            new_content = lines[0] + '\n' + header + lines[1].rstrip() + footer
        else:
            new_content = lines[0] + '\n' + header + footer
    else:
        new_content = header + content.rstrip() + footer
    
    # Write back
    file_path.write_text(new_content)
    print(f"Added header/footer to {file_path} with emojis: {' '.join(emojis)}")


def main():
    """Add headers and footers to all Python files."""
    src_dir = Path(__file__).parent / "src"
    
    # Find all Python files
    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            add_header_and_footer_to_file(py_file, src_dir)


if __name__ == "__main__":
    main()

# 📦🍜📄🪄
