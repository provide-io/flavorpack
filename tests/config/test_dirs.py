#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for XDG-compliant config directory resolution."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from flavor.config.dirs import get_config_dir, get_policy_file, get_system_config_dir, get_trusted_keys_dir


def test_config_dir_env_override(tmp_path: Path) -> None:
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        assert get_config_dir() == tmp_path


def test_config_dir_xdg(tmp_path: Path) -> None:
    env = {"XDG_CONFIG_HOME": str(tmp_path), "FLAVOR_CONFIG_DIR": ""}
    with mock.patch.dict(os.environ, env, clear=False):
        assert get_config_dir() == tmp_path / "flavor"


def test_config_dir_default(tmp_path: Path) -> None:
    with (
        mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": "", "XDG_CONFIG_HOME": ""}),
        mock.patch("pathlib.Path.home", return_value=tmp_path),
    ):
        result = get_config_dir()
    assert result == tmp_path / ".config" / "flavor"


def test_system_config_dir_non_windows() -> None:
    with mock.patch("sys.platform", "linux"):
        assert get_system_config_dir() == Path("/etc/flavor")


def test_system_config_dir_windows(tmp_path: Path) -> None:
    with (
        mock.patch("sys.platform", "win32"),
        mock.patch.dict(os.environ, {"PROGRAMDATA": str(tmp_path)}),
    ):
        assert get_system_config_dir() == tmp_path / "flavor"


def test_trusted_keys_dir_env_override(tmp_path: Path) -> None:
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(tmp_path)}):
        assert get_trusted_keys_dir() == tmp_path


def test_trusted_keys_dir_default(tmp_path: Path) -> None:
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": "", "FLAVOR_CONFIG_DIR": str(tmp_path)}):
        assert get_trusted_keys_dir() == tmp_path / "trusted-keys"


def test_trusted_keys_dir_system(tmp_path: Path) -> None:
    with mock.patch("flavor.config.dirs.get_system_config_dir", return_value=tmp_path):
        assert get_trusted_keys_dir(system=True) == tmp_path / "trusted-keys"


def test_policy_file_user(tmp_path: Path) -> None:
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path), "FLAVOR_TRUSTED_KEYS_DIR": ""}):
        assert get_policy_file() == tmp_path / "policy.toml"


def test_policy_file_system(tmp_path: Path) -> None:
    with mock.patch("flavor.config.dirs.get_system_config_dir", return_value=tmp_path):
        assert get_policy_file(system=True) == tmp_path / "policy.toml"
