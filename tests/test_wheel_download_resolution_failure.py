#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""A missing wheel for the target platform must fail the build, not fall back.

The download chain is pip, then UV's offline cache, then UV over the network.
Those fallbacks exist for a transport problem -- urllib3 failing on a Windows
runner -- and they can substitute for each other because each is another way to
fetch the same file.

They cannot substitute for a wheel that does not exist. `pip download
--platform <target>` reporting "No matching distribution found" is a statement
about the index, and asking UV to install for the *build host* instead answers
a different question: it resolves for the machine doing the packaging rather
than the one the package is for.

terraform-provider-pyvider hit this. cryptography publishes no macOS x86_64
wheel from 49.0.0 on; pip said so, the fallback ran, and the build exited 0
with a package that had no `pyvider` in it. The binary died with
`ModuleNotFoundError: No module named 'pyvider'` the first time an engine
launched it -- and it had been shipping that way, because the only check on
the collected set was that it was not empty.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pytest

from flavor.exceptions import WheelResolutionError
from flavor.packaging.python.wheel_builder import WheelBuilder


class _Pip:
    """Stands in for the pip manager, failing the way pip does."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def download_wheels_from_requirements(self, *_: Any, **__: Any) -> None:
        raise self.error


class _Uv:
    """Records whether a fallback was reached."""

    def __init__(self) -> None:
        self.offline_calls = 0
        self.network_calls = 0

    def download_wheels_offline(self, *_: Any, **__: Any) -> bool:
        self.offline_calls += 1
        return False

    def download_wheels_network(self, *_: Any, **__: Any) -> bool:
        self.network_calls += 1
        return True


def _builder(error: Exception) -> tuple[WheelBuilder, _Uv]:
    builder = WheelBuilder.__new__(WheelBuilder)
    uv = _Uv()
    builder.pypapip = _Pip(error)  # type: ignore[assignment]
    builder.uv = uv  # type: ignore[assignment]
    return builder, uv


def test_a_missing_wheel_stops_the_build_without_trying_the_fallbacks(tmp_path: Path) -> None:
    """No fallback can conjure a wheel the index does not have."""
    builder, uv = _builder(
        WheelResolutionError(
            "Failed to download required wheels: ERROR: Could not find a version "
            "that satisfies the requirement cryptography==50.0.1\n"
            "ERROR: No matching distribution found for cryptography==50.0.1"
        )
    )

    with pytest.raises(WheelResolutionError, match=re.escape("cryptography==50.0.1")):
        builder.download_wheels_for_resolved_deps(
            Path("/nonexistent/python"), tmp_path / "requirements.txt", tmp_path / "wheels"
        )

    assert uv.offline_calls == 0
    assert uv.network_calls == 0


def test_a_transport_failure_still_falls_back(tmp_path: Path) -> None:
    """The fallbacks keep their reason for existing."""
    wheel_dir = tmp_path / "wheels"
    wheel_dir.mkdir()
    (wheel_dir / "pyvider-0.7.1-py3-none-any.whl").write_bytes(b"")

    builder, uv = _builder(RuntimeError("Failed to download required wheels: connection reset"))

    result = builder.download_wheels_for_resolved_deps(
        Path("/nonexistent/python"), tmp_path / "requirements.txt", wheel_dir
    )

    assert [p.name for p in result] == ["pyvider-0.7.1-py3-none-any.whl"]
    assert uv.network_calls == 1
