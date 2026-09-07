"""The Windows passthrough carries what Foundation's allowlist does not.

`_windows_system_env` was written when `provide.foundation` scrubbed subprocess
environments down to an allowlist that dropped `SYSTEMROOT` and `WINDIR`, which
left Windows unable to find its Winsock service-provider DLLs. Foundation added
those variables in v0.3.28, and this package floors it well above that, so the
overlap is now a no-op that reads as if it were load-bearing.

These pin the division: the passthrough supplies the variables Foundation's
allowlist omits, and stops restating the ones it guarantees.

SPDX-FileCopyrightText: Copyright (c) 2025-2026 provide.io llc. All rights reserved.
SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from provide.foundation.process.env import SAFE_ENV_ALLOWLIST
import pytest

from flavor.packaging.python.uv_manager import _WINDOWS_VARS, _windows_system_env


def test_passthrough_does_not_restate_the_allowlist() -> None:
    """A variable Foundation already guarantees does not belong here."""
    overlap = sorted(set(_WINDOWS_VARS) & SAFE_ENV_ALLOWLIST)
    assert overlap == [], f"Foundation's allowlist already carries {overlap}"


def test_passthrough_supplies_what_the_allowlist_omits() -> None:
    """The variables that are this package's own reason for the passthrough."""
    assert "PROGRAMFILES" in _WINDOWS_VARS
    assert "NUMBER_OF_PROCESSORS" in _WINDOWS_VARS


def test_dll_loading_variables_are_still_reaching_the_child() -> None:
    """Dropping them here is only safe because Foundation carries them."""
    for name in ("SYSTEMROOT", "WINDIR", "COMSPEC", "USERPROFILE", "LOCALAPPDATA"):
        assert name in SAFE_ENV_ALLOWLIST


def test_passthrough_is_empty_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("flavor.packaging.python.uv_manager.sys.platform", "linux")
    assert _windows_system_env() == {}


def test_passthrough_reads_the_live_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("flavor.packaging.python.uv_manager.sys.platform", "win32")
    monkeypatch.setenv("NUMBER_OF_PROCESSORS", "4")
    assert _windows_system_env()["NUMBER_OF_PROCESSORS"] == "4"
