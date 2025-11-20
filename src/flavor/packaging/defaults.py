#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Default configuration values for packaging."""

# Default environment variables to unset for Python/UV isolation
# These prevent host virtual environment and Python configuration from interfering
# with packaged applications
DEFAULT_ENV_ISOLATION_UNSET = [
    "PYTHONPATH",
    "UV_PROJECT_ENVIRONMENT",
    "PYTHONHOME",
    "UV_CACHE_DIR",
    "VIRTUAL_ENV",
]
