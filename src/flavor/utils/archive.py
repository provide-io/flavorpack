#!/usr/bin/env python3
"""Archive utility functions."""

import tarfile


def deterministic_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    """A tarfile filter to ensure deterministic output."""
    # Reset user/group info
    tarinfo.uid = 0
    tarinfo.gid = 0
    tarinfo.uname = "root"
    tarinfo.gname = "root"

    # Reset modification time
    tarinfo.mtime = 0

    return tarinfo
