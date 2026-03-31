#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the security command group."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click.testing
from taster.commands.security import (  # ty: ignore[unresolved-import]
    inspect_provenance,
    inspect_sbom,
    policy_check,
    run_all,
    security_group,
    trust_list,
)


def _make_proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Create a mock CompletedProcess."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestInspectSbom:
    """Tests for the inspect-sbom subcommand."""

    def test_inspect_sbom_success(self) -> None:
        """Mock subprocess returns CycloneDX JSON; exit 0, output contains 'CycloneDX'."""
        runner = click.testing.CliRunner()
        sbom_output = '{"bomFormat": "CycloneDX", "specVersion": "1.4"}'
        mock_proc = _make_proc(returncode=0, stdout=sbom_output)

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc):
            result = runner.invoke(inspect_sbom, [])

        assert result.exit_code == 0
        assert "CycloneDX" in result.output

    def test_inspect_sbom_failure(self) -> None:
        """Mock subprocess returns exit 1; taster exits 1."""
        runner = click.testing.CliRunner()
        mock_proc = _make_proc(returncode=1, stderr="SBOM generation failed")

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc):
            result = runner.invoke(inspect_sbom, [])

        assert result.exit_code == 1

    def test_inspect_sbom_json_flag_forwarded(self) -> None:
        """--json flag is passed through to flavor inspect."""
        runner = click.testing.CliRunner()
        mock_proc = _make_proc(returncode=0, stdout='{"bomFormat": "CycloneDX"}')

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc) as mock_run:
            runner.invoke(inspect_sbom, ["--json"])

        call_args = mock_run.call_args[0][0]
        assert "--json" in call_args


class TestInspectProvenance:
    """Tests for the inspect-provenance subcommand."""

    def test_inspect_provenance_success(self) -> None:
        """Mock returns provenance JSON with 'flavor-python'; exit 0."""
        runner = click.testing.CliRunner()
        provenance_output = '{"builder": {"id": "flavor-python"}, "buildType": "pspf"}'
        mock_proc = _make_proc(returncode=0, stdout=provenance_output)

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc):
            result = runner.invoke(inspect_provenance, [])

        assert result.exit_code == 0
        assert "flavor-python" in result.output

    def test_inspect_provenance_failure(self) -> None:
        """Mock subprocess returns exit 1; taster exits 1."""
        runner = click.testing.CliRunner()
        mock_proc = _make_proc(returncode=1, stderr="provenance not found")

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc):
            result = runner.invoke(inspect_provenance, [])

        assert result.exit_code == 1


class TestPolicyCheck:
    """Tests for the policy-check subcommand."""

    def test_policy_check_passes(self) -> None:
        """Mock returns exit 0; command passes."""
        runner = click.testing.CliRunner()
        mock_proc = _make_proc(returncode=0, stdout="Policy: OK")

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc):
            result = runner.invoke(policy_check, [])

        assert result.exit_code == 0

    def test_policy_check_fails(self) -> None:
        """Mock returns exit 1 with stderr 'platform not permitted'; exits 1."""
        runner = click.testing.CliRunner()
        mock_proc = _make_proc(returncode=1, stderr="platform not permitted")

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc):
            result = runner.invoke(policy_check, [])

        assert result.exit_code == 1


class TestTrustList:
    """Tests for the trust-list subcommand."""

    def test_trust_list_runs(self) -> None:
        """Mock returns exit 0 with empty list; passes."""
        runner = click.testing.CliRunner()
        mock_proc = _make_proc(returncode=0, stdout="")

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc):
            result = runner.invoke(trust_list, [])

        assert result.exit_code == 0


class TestRunAll:
    """Tests for the 'all' subcommand."""

    def test_run_all_all_pass(self) -> None:
        """All subprocesses return 0; exit 0 and 'PASS' in output for each check."""
        runner = click.testing.CliRunner()
        mock_proc = _make_proc(returncode=0, stdout="ok")

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc):
            result = runner.invoke(run_all, [])

        assert result.exit_code == 0
        assert result.output.count("PASS") == 4
        assert "FAIL" not in result.output
        assert "inspect-sbom" in result.output
        assert "inspect-provenance" in result.output
        assert "policy-check" in result.output
        assert "trust-list" in result.output

    def test_run_all_one_fail(self) -> None:
        """One subprocess returns exit 1; run_all exits 1 and shows 'FAIL'."""
        runner = click.testing.CliRunner()
        pass_proc = _make_proc(returncode=0, stdout="ok")
        fail_proc = _make_proc(returncode=1, stderr="error")

        # policy-check (3rd call) will fail
        side_effects = [pass_proc, pass_proc, fail_proc, pass_proc]

        with patch("taster.commands.security.subprocess.run", side_effect=side_effects):
            result = runner.invoke(run_all, [])

        assert result.exit_code == 1
        assert "FAIL" in result.output
        assert "PASS" in result.output

    def test_run_all_invokes_all_checks(self) -> None:
        """run_all calls subprocess.run exactly four times."""
        runner = click.testing.CliRunner()
        mock_proc = _make_proc(returncode=0)

        with patch("taster.commands.security.subprocess.run", return_value=mock_proc) as mock_run:
            runner.invoke(run_all, [])

        assert mock_run.call_count == 4


class TestSecurityGroup:
    """Tests for the security group registration."""

    def test_group_has_expected_commands(self) -> None:
        """security group exposes all four subcommands plus 'all'."""
        expected = {"inspect-sbom", "inspect-provenance", "policy-check", "trust-list", "all"}
        assert expected <= set(security_group.commands.keys())

    def test_group_help(self) -> None:
        """security --help exits 0."""
        runner = click.testing.CliRunner()
        result = runner.invoke(security_group, ["--help"])
        assert result.exit_code == 0
        assert "Security" in result.output


# 🌶️📦🔚
