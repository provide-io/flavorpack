#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Echo command for testing arguments"""

import click
from provide.foundation.console import pout


@click.command("echo")
@click.argument("args", nargs=-1)
def echo_command(args: tuple[str, ...]) -> None:
    """📢 Echo arguments for testing"""
    if args:
        pout(" ".join(args))
    else:
        pout("(no arguments provided)")


# 🌶️📦🔚
