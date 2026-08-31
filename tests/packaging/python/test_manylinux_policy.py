#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""The manylinux tag policy, and the download commands built from it.

The regression these guard: pip's `--platform` replaces the set of tags pip will
consider and expands each one downward only, so a single hardcoded tag hides
every package that has moved to a newer manylinux baseline. jq is the canary --
it published manylinux2014 wheels through 1.10.0 and manylinux_2_26/2_28 from
1.11.0, and a lock holding jq 1.12.0 failed the Linux build outright.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flavor.packaging.python.manylinux import (
    DEFAULT_MANYLINUX_TAGS,
    platform_constraint_hint,
    platform_tags_for_arch,
    resolve_manylinux_tags,
)
from flavor.packaging.python.pypapip_manager import PyPaPipManager


class TestDefaultPolicy:
    def test_default_prefers_manylinux2014_so_existing_artifacts_do_not_move(self) -> None:
        """pip prefers the tag listed first, and that has to stay 2014.

        Listing a newer tag first would silently raise the glibc floor of every
        artifact that has a 2_17 wheel available, which is a compatibility
        decision, not a bug fix.
        """
        assert DEFAULT_MANYLINUX_TAGS[0] == "manylinux2014"

    def test_default_also_admits_manylinux_2_28(self) -> None:
        assert "manylinux_2_28" in DEFAULT_MANYLINUX_TAGS

    def test_no_config_yields_the_default(self) -> None:
        assert resolve_manylinux_tags(None) == DEFAULT_MANYLINUX_TAGS
        assert resolve_manylinux_tags({}) == DEFAULT_MANYLINUX_TAGS
        assert resolve_manylinux_tags({"other": "value"}) == DEFAULT_MANYLINUX_TAGS


class TestConfiguredPolicy:
    def test_a_single_tag_is_accepted_as_a_string(self) -> None:
        assert resolve_manylinux_tags({"manylinux": "manylinux_2_34"}) == ("manylinux_2_34",)

    def test_a_list_keeps_the_declared_order(self) -> None:
        config = {"manylinux": ["manylinux_2_28", "manylinux2014"]}
        assert resolve_manylinux_tags(config) == ("manylinux_2_28", "manylinux2014")

    def test_an_unusable_value_falls_back_rather_than_failing_the_build(self) -> None:
        assert resolve_manylinux_tags({"manylinux": 42}) == DEFAULT_MANYLINUX_TAGS
        assert resolve_manylinux_tags({"manylinux": []}) == DEFAULT_MANYLINUX_TAGS
        assert resolve_manylinux_tags({"manylinux": ["", "  "]}) == DEFAULT_MANYLINUX_TAGS

    def test_non_string_entries_are_dropped_and_the_rest_kept(self) -> None:
        assert resolve_manylinux_tags({"manylinux": ["manylinux2014", None]}) == ("manylinux2014",)


class TestArchExpansion:
    def test_amd64_uses_the_x86_64_spelling(self) -> None:
        assert platform_tags_for_arch(("manylinux2014",), "amd64") == ["manylinux2014_x86_64"]

    def test_arm64_uses_the_aarch64_spelling(self) -> None:
        assert platform_tags_for_arch(("manylinux2014",), "arm64") == ["manylinux2014_aarch64"]

    def test_order_survives_expansion(self) -> None:
        assert platform_tags_for_arch(DEFAULT_MANYLINUX_TAGS, "amd64") == [
            "manylinux2014_x86_64",
            "manylinux_2_28_x86_64",
        ]

    def test_an_unmapped_arch_leaves_the_platform_unconstrained(self) -> None:
        """Better to let pip resolve for the running machine than to invent a tag."""
        assert platform_tags_for_arch(DEFAULT_MANYLINUX_TAGS, "riscv64") == []


class TestDownloadCommand:
    def _cmd(self, manager: PyPaPipManager, **kwargs: object) -> list[str]:
        return manager._get_pypapip_download_cmd(
            python_exe=Path("/usr/bin/python3"),
            dest_dir=Path("/tmp/wheels"),
            packages=["jq"],
            binary_only=True,
            **kwargs,  # type: ignore[arg-type]
        )

    def test_linux_download_requests_every_configured_tag(self) -> None:
        manager = PyPaPipManager()
        with (
            patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.pypapip_manager.get_arch_name", return_value="amd64"),
        ):
            cmd = self._cmd(manager)

        assert cmd.count("--platform") == 2
        assert "manylinux2014_x86_64" in cmd
        assert "manylinux_2_28_x86_64" in cmd

    def test_the_preferred_tag_is_passed_first(self) -> None:
        """pip picks the first matching tag, so order in the command is the policy."""
        manager = PyPaPipManager()
        with (
            patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.pypapip_manager.get_arch_name", return_value="arm64"),
        ):
            cmd = self._cmd(manager)

        platforms = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--platform"]
        assert platforms == ["manylinux2014_aarch64", "manylinux_2_28_aarch64"]

    def test_a_packages_own_policy_replaces_the_default(self) -> None:
        manager = PyPaPipManager(manylinux_tags=("manylinux_2_34",))
        with (
            patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="linux"),
            patch("flavor.packaging.python.pypapip_manager.get_arch_name", return_value="amd64"),
        ):
            cmd = self._cmd(manager)

        platforms = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--platform"]
        assert platforms == ["manylinux_2_34_x86_64"]

    def test_an_explicit_platform_tag_still_wins(self) -> None:
        """Callers that already know the exact tag they need keep that ability."""
        manager = PyPaPipManager()
        with patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="linux"):
            cmd = self._cmd(manager, platform_tag="manylinux2014_x86_64")

        platforms = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--platform"]
        assert platforms == ["manylinux2014_x86_64"]

    def test_several_explicit_tags_are_all_passed(self) -> None:
        manager = PyPaPipManager()
        with patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="linux"):
            cmd = self._cmd(manager, platform_tag=["manylinux2014_x86_64", "manylinux_2_28_x86_64"])

        platforms = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--platform"]
        assert platforms == ["manylinux2014_x86_64", "manylinux_2_28_x86_64"]

    def test_non_linux_hosts_are_left_unconstrained(self) -> None:
        manager = PyPaPipManager()
        with patch("flavor.packaging.python.pypapip_manager.get_os_name", return_value="darwin"):
            cmd = self._cmd(manager)

        assert "--platform" not in cmd


class TestFailureHint:
    def test_the_hint_names_the_tags_that_were_requested(self) -> None:
        hint = platform_constraint_hint(["manylinux2014_x86_64", "manylinux_2_28_x86_64"])
        assert "manylinux2014_x86_64" in hint
        assert "manylinux_2_28_x86_64" in hint

    def test_the_hint_explains_that_newer_tags_are_invisible(self) -> None:
        """The whole point: the constraint hides published wheels."""
        hint = platform_constraint_hint(["manylinux2014_x86_64"])
        assert "never newer" in hint

    def test_no_constraint_means_no_hint(self) -> None:
        assert platform_constraint_hint([]) == ""
