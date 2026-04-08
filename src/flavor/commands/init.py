#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""flavor init — one-shot host setup for Flavorpack."""

from __future__ import annotations

import json
from pathlib import Path

import click
from provide.foundation.console import pout

from flavor.config.dirs import get_config_dir, get_system_config_dir
from flavor.config.policy import POLICY_VERSION
from flavor.console import get_command_logger

log = get_command_logger("init")

_POLICY_JSON_SCAFFOLD = {
    "version": POLICY_VERSION,
    "trust": {
        "require_trusted_key": False,
        "use_os_keychain": False,
    },
    "execution": {
        "refuse_root": False,
        "allow_platforms": [],
    },
    "attestation": {
        "require_sbom": False,
    },
    "enforcement": {
        "default": "deny",
    },
}


@click.command("init")
@click.option(
    "--global",
    "global_",
    is_flag=True,
    default=False,
    help="Set up system-wide config under /etc/flavor (requires root/sudo).",
)
def init_command(global_: bool) -> None:
    """Set up Flavorpack config directory structure on this host.

    Creates the trusted-keys directory and a default policy.json.
    Safe to run multiple times — existing files are never overwritten.
    """
    config_root: Path = get_system_config_dir() if global_ else get_config_dir()
    scope = "system" if global_ else "user"

    log.debug("Initializing Flavorpack config", scope=scope, root=str(config_root))

    # Create trusted-keys directory
    trusted_keys_dir = config_root / "trusted-keys"
    trusted_keys_dir.mkdir(parents=True, exist_ok=True)
    pout(f"✓ {trusted_keys_dir}")

    # Scaffold policy.json (never overwrite)
    policy_file = config_root / "policy.json"
    if not policy_file.exists():
        policy_file.write_text(json.dumps(_POLICY_JSON_SCAFFOLD, indent=2) + "\n", encoding="utf-8")
        pout(f"✓ {policy_file}  (scaffolded)")
    else:
        pout(f"  {policy_file}  (already exists, not modified)")

    pout(f"\nFlavorpack {scope} config initialised at {config_root}")
    if not global_:
        pout("  Add trusted keys with: flavor trust add <key.pub>")
        pout(f"  Edit policy:           {policy_file}")
    else:
        pout("  Add trusted keys with: sudo flavor trust add <key.pub> --global")
        pout(f"  Edit policy:           {policy_file}")


# 🌶️📦🔚
