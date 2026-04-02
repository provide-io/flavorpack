#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Adversarial tests for workenv target path validation."""

from __future__ import annotations

import re

from hypothesis import assume, given, settings, strategies as st
import pytest

from flavor.psp.format_2025.targets import normalize_workenv_target


def _safe_param_id(prefix: str, value: str) -> str:
    """Return a pytest CLI-safe id for path-like adversarial inputs."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return f"{prefix}-{slug or 'empty'}"


@pytest.mark.security
class TestNormalizeWorkenvTargetRejectsTraversal:
    """Verify normalize_workenv_target rejects all path escape attempts."""

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "../etc/passwd",
            "../../etc/shadow",
            "../../../root/.ssh/id_rsa",
            "slot/../../../etc/passwd",
            "valid/../../escape",
            "{workenv}/../escape",
            "{workenv}/../../root",
            "{workenv}/bin/../../../etc/shadow",
        ],
        ids=lambda t: _safe_param_id("traversal", t),
    )
    def test_rejects_parent_traversal(self, malicious_target: str) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            normalize_workenv_target(malicious_target)

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "/etc/passwd",
            "/tmp/x",
            "/absolute/path",
            "//double/slash",
        ],
        ids=lambda t: _safe_param_id("absolute", t),
    )
    def test_rejects_posix_absolute_paths(self, malicious_target: str) -> None:
        with pytest.raises(ValueError, match="absolute paths"):
            normalize_workenv_target(malicious_target)

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "C:\\Windows\\System32",
            "D:/autoexec.bat",
            "c:\\users\\admin",
            "Z:\\share\\file",
        ],
        ids=lambda t: _safe_param_id("windows", t),
    )
    def test_rejects_windows_drive_paths(self, malicious_target: str) -> None:
        with pytest.raises(ValueError, match="absolute paths"):
            normalize_workenv_target(malicious_target)

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "",
            "   ",
            "\t",
        ],
    )
    def test_rejects_empty_or_whitespace(self, malicious_target: str) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            normalize_workenv_target(malicious_target)

    def test_rejects_unsupported_workenv_placeholder(self) -> None:
        with pytest.raises(ValueError, match="unsupported placeholder"):
            normalize_workenv_target("foo/{workenv}/bar")


@pytest.mark.security
class TestNormalizeWorkenvTargetAcceptsValid:
    """Verify normalize_workenv_target accepts all valid targets."""

    @pytest.mark.parametrize(
        ("input_target", "expected"),
        [
            ("bin/uv", "bin/uv"),
            ("Scripts/uv.exe", "Scripts/uv.exe"),
            ("{workenv}", "{workenv}"),
            ("{workenv}/bin/python3", "bin/python3"),
            ("{workenv}/Scripts/python.exe", "Scripts/python.exe"),
            ("{workenv}/", "."),
            (".", "."),
            ("simple_file.txt", "simple_file.txt"),
            ("nested/deep/path/file.dat", "nested/deep/path/file.dat"),
        ],
    )
    def test_accepts_and_normalizes(self, input_target: str, expected: str) -> None:
        assert normalize_workenv_target(input_target) == expected


@pytest.mark.security
class TestNormalizeWorkenvTargetHypothesis:
    """Property-based tests: normalize_workenv_target never allows escape."""

    @given(target=st.text(min_size=1, max_size=200))
    @settings(max_examples=500)
    def test_never_returns_path_with_parent_traversal(self, target: str) -> None:
        """Any accepted target must not contain .. components."""
        try:
            result = normalize_workenv_target(target)
        except ValueError:
            return
        assert ".." not in result.split("/")

    @given(target=st.text(min_size=1, max_size=200))
    @settings(max_examples=500)
    def test_never_returns_absolute_path(self, target: str) -> None:
        """Any accepted target must not be absolute."""
        try:
            result = normalize_workenv_target(target)
        except ValueError:
            return
        if result in ("{workenv}", "."):
            return
        assert not result.startswith("/"), f"Accepted absolute path: {result!r}"

    @given(
        path=st.from_regex(r"[a-z0-9_/.-]{1,50}", fullmatch=True),
    )
    @settings(max_examples=200)
    def test_safe_relative_paths_accepted(self, path: str) -> None:
        """Simple alphanumeric relative paths should be accepted."""
        assume(".." not in path.split("/"))
        assume(not path.startswith("/"))
        assume(path.strip())
        result = normalize_workenv_target(path)
        assert result


class TestSafeParamId:
    """Regression coverage for pytest selector-safe adversarial ids."""

    @pytest.mark.parametrize(
        ("prefix", "value", "expected"),
        [
            ("traversal", "{workenv}/../escape", "traversal-workenv-escape"),
            ("absolute", "/etc/passwd", "absolute-etc-passwd"),
            ("windows", "C:\\Windows\\System32", "windows-c-windows-system32"),
            ("windows", "D:/autoexec.bat", "windows-d-autoexec-bat"),
            ("windows", "\t", "windows-empty"),
        ],
    )
    def test_safe_param_id_emits_cli_safe_slugs(self, prefix: str, value: str, expected: str) -> None:
        assert _safe_param_id(prefix, value) == expected
