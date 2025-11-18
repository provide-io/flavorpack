#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Exit with a specific code for testing."""

import sys

import click


@click.command("exit")
@click.argument("code", type=int, default=0)
@click.option("--message", "-m", help="Print message before exiting")
def exit_command(code: int, message: str | None) -> None:
    """🚪 Exit with a specific code (for testing error handling)"""
    if message:
        print(message, file=sys.stderr if code != 0 else sys.stdout)
    sys.exit(code)


# 🌶️📦🔚
