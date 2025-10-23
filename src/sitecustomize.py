# sitecustomize.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Auto-load setproctitle blocker.

Importing pytest_plugin installs the blocker at module-level.
"""

import contextlib

with contextlib.suppress(ImportError):
    import provide.testkit.pytest_plugin  # noqa: F401


# <3 🧱🤝🧪🪄
