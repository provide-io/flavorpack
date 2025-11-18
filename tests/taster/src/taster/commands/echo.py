#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Echo command for testing arguments"""

import click


@click.command("echo")
@click.argument("args", nargs=-1)
def echo_command(args) -> None:
    """📢 Echo arguments for testing"""
    if args:
        click.echo(" ".join(args))
    else:
        click.echo("(no arguments provided)")


# 🌶️📦🔚
