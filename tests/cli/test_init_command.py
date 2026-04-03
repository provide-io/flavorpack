#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for `flavor init [--global]`."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from flavor.cli import cli


def test_init_creates_trusted_keys_dir(tmp_path: Path) -> None:
    """flavor init creates trusted-keys directory."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "trusted-keys").is_dir()


def test_init_creates_policy_json(tmp_path: Path) -> None:
    """flavor init creates a scaffolded policy.json."""
    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        runner.invoke(cli, ["init"])
    assert (tmp_path / "policy.json").exists()


def test_init_policy_json_valid(tmp_path: Path) -> None:
    """Scaffolded policy.json is valid JSON with a version field."""
    import json

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_CONFIG_DIR": str(tmp_path)}):
        runner.invoke(cli, ["init"])
    content = (tmp_path / "policy.json").read_text(encoding="utf-8")
    data = json.loads(content)
    assert data["version"] == 1


def test_init_is_idempotent(tmp_path: Path) -> None:
    """Running flavor init twice does not overwrite existing policy.json."""
    runner = CliRunner()
    env = {"FLAVOR_CONFIG_DIR": str(tmp_path)}
    with mock.patch.dict(os.environ, env):
        runner.invoke(cli, ["init"])
    policy_file = tmp_path / "policy.json"
    policy_file.write_text('{"custom": true}\n', encoding="utf-8")
    with mock.patch.dict(os.environ, env):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "custom" in policy_file.read_text(encoding="utf-8")


def test_init_global_uses_system_dir(tmp_path: Path) -> None:
    """flavor init --global targets the system config dir."""
    runner = CliRunner()
    with mock.patch("flavor.commands.init.get_system_config_dir", return_value=tmp_path):
        result = runner.invoke(cli, ["init", "--global"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "trusted-keys").is_dir()
    assert (tmp_path / "policy.json").exists()
