# flavor/commands/__init__.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

#
# flavor/commands/__init__.py
#
"""Command modules for the flavor CLI."""

from __future__ import annotations

from flavor.commands.ingredients import ingredient_group
from flavor.commands.inspect import inspect_command
from flavor.commands.keygen import keygen_command
from flavor.commands.package import pack_command
from flavor.commands.utils import clean_command
from flavor.commands.verify import verify_command
from flavor.commands.workenv import workenv_group

__all__ = [
    "clean_command",
    "ingredient_group",
    "inspect_command",
    "keygen_command",
    "pack_command",
    "verify_command",
    "workenv_group",
]
# 🌶️📦📦🪄
