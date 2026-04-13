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

# Windows system environment variables that must always be preserved.
# The PSP launcher strips the host environment for isolation, but these
# variables are required by Windows itself for DLL loading, process
# creation, temp file handling, and user-profile resolution.
# They are added to the manifest `pass` list when building on Windows.
WINDOWS_SYSTEM_PASS = [
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "SYSTEMDRIVE",
    "PATH",
    "PATHEXT",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "TEMP",
    "TMP",
    "COMPUTERNAME",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "COMMONPROGRAMFILES",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
]
