# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest helpers for the standalone taster test lane."""

from __future__ import annotations

from pathlib import Path
import sys

TASTER_SRC = Path(__file__).resolve().parents[1] / "src"

if str(TASTER_SRC) not in sys.path:
    sys.path.insert(0, str(TASTER_SRC))
