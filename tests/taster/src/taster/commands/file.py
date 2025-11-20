#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""File operations for testing."""

import os
from pathlib import Path
import sys

import click


@click.group("file")
def file_command() -> None:
    pass


@file_command.command("write")
@click.argument("path")
@click.argument("content")
def write_file(path: str, content: str) -> None:
    """Write content to a file"""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)


@file_command.command("read")
@click.argument("path")
def read_file(path: str) -> None:
    """Read and display file content"""
    try:
        content = Path(path).read_text()
        print(content)
    except FileNotFoundError:
        print(f"❌ File not found: {path}", file=sys.stderr)
        sys.exit(1)


@file_command.command("exists")
@click.argument("path")
def check_exists(path: str) -> None:
    """Check if file/directory exists"""
    exists = Path(path).exists()
    sys.exit(0 if exists else 1)


@file_command.command("workenv-test")
def test_workenv() -> None:
    """Test workenv persistence by writing/reading files"""
    workenv = os.environ.get("FLAVOR_WORKENV", "/tmp")
    test_file = Path(workenv) / "test_persistence.txt"

    if test_file.exists():
        content = test_file.read_text()
        counter = int(content.strip()) + 1
    else:
        counter = 1
        print("📝 Creating new persistence file")

    test_file.write_text(str(counter))
    print(f"💾 Workenv: {workenv}")
    print(f"📊 Run count: {counter}")


# 🌶️📦🔚
