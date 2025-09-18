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
