#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Key generation command for the flavor CLI."""

from __future__ import annotations

from pathlib import Path

import click
from provide.foundation.console import perr, pout

from flavor.console import get_command_logger
from flavor.exceptions import BuildError
from flavor.packaging.keys import generate_key_pair

# Get structured logger for this command
log = get_command_logger("keygen")


@click.command("keygen")
@click.option(
    "--out-dir",
    default="keys",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    help="Directory to save the Ed25519 key pair.",
)
def keygen_command(out_dir: str) -> None:
    """Generates an Ed25519 key pair for package integrity signing."""
    log.debug("Generating key pair", out_dir=out_dir)

    try:
        generate_key_pair(Path(out_dir))
        log.info("Key pair generated successfully", out_dir=out_dir)
        pout(f"✅ Package integrity key pair generated in '{out_dir}'.")
    except BuildError as e:
        log.error("Keygen failed", error=str(e), out_dir=out_dir)
        perr(f"❌ Keygen failed: {e}")
        raise click.Abort() from e


# 🌶️📦🔚
