# flavor/config/defaults.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Centralized default values for Flavorpack configuration.
All defaults are defined here instead of inline in field definitions.
import sys

# =================================
# PSPF Format defaults
# =================================
PSPF_VERSION = 0x20250001  # Format version v1
DEFAULT_HEADER_SIZE = 8192  # Future-proof 8KB index block
DEFAULT_SLOT_DESCRIPTOR_SIZE = 64  # Descriptor size
DEFAULT_MAGIC_TRAILER_SIZE = 8200  # Index block with markers
DEFAULT_SLOT_ALIGNMENT = 8  # Minimum alignment

# Magic bytes for format markers (replacing emoji bytes)
TRAILER_START_MAGIC = bytes([0xF0, 0x9F, 0x93, 0xA6])  # Start marker (was 📦)
# 🌶️📦⚙️🪄
