#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the post-build check that a package is readable by its own launcher.

A PSPF package carries the launcher that runs it, so a build mixes two versions:
the builder writing the metadata and the launcher binary prepended to it. Nothing
made them agree. A builder that drops a field the embedded launcher requires
produces a package that builds clean and fails at run time, in whoever's hands it
reached — which is the expensive shape for a defect to have.

``verify_built_package`` closes that by asking the embedded launcher to read the
package back before the build is allowed to succeed.
"""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from flavor.exceptions import BuildError
from flavor.packaging.orchestrator_helpers import verify_built_package

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="the stub launchers are shell scripts",
)


def _stub_package(path: Path, body: str) -> Path:
    """Write an executable stub standing in for a built package."""
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
    return path


class TestVerifyBuiltPackage:
    """The embedded launcher has to accept the package before the build passes."""

    def test_package_its_launcher_reads_is_accepted(self, tmp_path: Path) -> None:
        """A launcher that verifies its package lets the build finish."""
        package = _stub_package(tmp_path / "good.psp", "exit 0")

        verify_built_package(
            package, launcher_name="flavor-rs-launcher-linux_amd64", host_platform="linux_amd64"
        )

    def test_package_its_launcher_cannot_read_fails_the_build(self, tmp_path: Path) -> None:
        """A launcher that rejects its own package fails the build, not the user."""
        package = _stub_package(tmp_path / "bad.psp", "exit 1")

        with pytest.raises(BuildError, match=r"cannot read the package"):
            verify_built_package(
                package, launcher_name="flavor-rs-launcher-linux_amd64", host_platform="linux_amd64"
            )

    def test_failure_carries_what_the_launcher_said(self, tmp_path: Path) -> None:
        """The launcher's own diagnosis reaches the developer.

        Without it the error says a package is unreadable and not why, which
        leaves the actual missing field to be rediscovered by hand.
        """
        package = _stub_package(
            tmp_path / "bad.psp",
            'echo "missing field \\`primary_slot\\`" >&2\nexit 1',
        )

        with pytest.raises(BuildError, match=r"primary_slot"):
            verify_built_package(
                package, launcher_name="flavor-rs-launcher-linux_amd64", host_platform="linux_amd64"
            )

    def test_diagnosis_survives_leading_log_noise(self, tmp_path: Path) -> None:
        """The reason is the last thing printed, not the first.

        Launchers emit startup logging before they get as far as rejecting a
        package, so reporting the head of the output names a log line as the
        cause and buries the real one.
        """
        package = _stub_package(
            tmp_path / "noisy.psp",
            'echo "DEBUG launcher process started" >&2\n'
            'echo "DEBUG reading trailer" >&2\n'
            'echo "Error: missing field \\`primary_slot\\`" >&2\n'
            "exit 1",
        )

        with pytest.raises(BuildError) as caught:
            verify_built_package(
                package, launcher_name="flavor-rs-launcher-linux_amd64", host_platform="linux_amd64"
            )

        reported = [line for line in str(caught.value).splitlines() if "Launcher said" in line]
        assert reported, "the failure did not quote the launcher at all"
        assert "primary_slot" in str(caught.value)

    def test_check_runs_the_launcher_in_cli_mode(self, tmp_path: Path) -> None:
        """Without FLAVOR_LAUNCHER_CLI the launcher runs the payload instead of verifying.

        A check that silently executed the package would be worse than no check.
        """
        package = _stub_package(
            tmp_path / "probe.psp",
            '[ "$FLAVOR_LAUNCHER_CLI" = "1" ] || exit 1\n[ "$1" = "verify" ] || exit 1\nexit 0',
        )

        verify_built_package(
            package, launcher_name="flavor-rs-launcher-linux_amd64", host_platform="linux_amd64"
        )

    def test_foreign_launcher_skips_the_check(self, tmp_path: Path) -> None:
        """A launcher built for another platform cannot run here, so the check stands down.

        The stub fails if executed, so reaching the end proves it was not run.
        """
        package = _stub_package(tmp_path / "foreign.psp", "exit 1")

        verify_built_package(
            package, launcher_name="flavor-rs-launcher-linux_arm64", host_platform="darwin_arm64"
        )

    def test_platform_agnostic_launcher_is_still_checked(self, tmp_path: Path) -> None:
        """An "any" launcher runs anywhere, so it gets checked anywhere.

        Skipping it would silently drop the check for every package built with one.
        """
        package = _stub_package(tmp_path / "any.psp", "exit 1")

        with pytest.raises(BuildError, match=r"cannot read the package"):
            verify_built_package(package, launcher_name="flavor-rs-launcher-any", host_platform="darwin_arm64")

    def test_skip_is_reported(self, tmp_path: Path) -> None:
        """A skipped check says so, naming both platforms.

        A check that quietly does nothing reads as a check that passed, which is
        the failure this whole function exists to remove.
        """
        package = _stub_package(tmp_path / "foreign.psp", "exit 1")

        with patch("flavor.packaging.orchestrator_helpers.logger") as log:
            verify_built_package(
                package, launcher_name="flavor-rs-launcher-linux_arm64", host_platform="darwin_arm64"
            )

        said = " ".join(str(call) for call in log.warning.call_args_list)
        assert "linux_arm64" in said, f"skip did not name the launcher: {said}"
        assert "darwin_arm64" in said, f"skip did not name the host platform: {said}"

    def test_unrunnable_environment_is_reported_as_itself(self, tmp_path: Path) -> None:
        """A package that will not start is a different failure from one that is rejected.

        A noexec mount or a lost execute bit stops the check from running at all.
        Reporting that as "the launcher cannot read the package" sends the
        developer after a format bug that is not there.
        """
        package = tmp_path / "noexec.psp"
        package.write_text("#!/bin/sh\nexit 0\n")
        package.chmod(0o644)

        with pytest.raises(BuildError, match=r"Could not run"):
            verify_built_package(
                package, launcher_name="flavor-rs-launcher-linux_amd64", host_platform="linux_amd64"
            )

    def test_unrunnable_environment_does_not_pass_silently(self, tmp_path: Path) -> None:
        """Not being able to check is not the same as checking and passing."""
        package = tmp_path / "noexec.psp"
        package.write_text("#!/bin/sh\nexit 0\n")
        package.chmod(0o644)

        with pytest.raises(BuildError) as caught:
            verify_built_package(
                package, launcher_name="flavor-rs-launcher-linux_amd64", host_platform="linux_amd64"
            )

        assert "never made" in str(caught.value)

    def test_missing_package_is_an_error(self, tmp_path: Path) -> None:
        """A build that produced no file at all fails here rather than later."""
        with pytest.raises(BuildError, match=r"produced no file"):
            verify_built_package(
                tmp_path / "absent.psp",
                launcher_name="flavor-rs-launcher-linux_amd64",
                host_platform="linux_amd64",
            )


class TestIntegrityIsNotRunnability:
    """A package can pass every integrity check and still not run."""

    def test_python_verifier_accepts_what_the_launcher_rejects(self, tmp_path: Path) -> None:
        """``flavor pack --verify`` proves Python can read a package, not that it runs.

        The existing post-build check calls FlavorVerifier: checksums, signature,
        magic. All of those hold for a package whose embedded launcher refuses to
        parse the metadata, so the build reports "Package integrity verified" for
        something nobody can execute. The two checks answer different questions
        and neither substitutes for the other.
        """
        from flavor.psp.format_2025.pspf_builder import PSPFBuilder
        from flavor.verification import FlavorVerifier

        payload = tmp_path / "payload.txt"
        payload.write_text("payload\n")

        # Stands in for a launcher that cannot read what this builder wrote.
        launcher = tmp_path / "launcher-stub.sh"
        launcher.write_text("#!/bin/sh\necho 'Error: missing field' >&2\nexit 1\n")
        launcher.chmod(0o755)

        package = tmp_path / "unrunnable.psp"
        result = (
            PSPFBuilder.create()
            .metadata(name="probe", version="1.0.0", execution={"command": "true", "env": {}})
            .add_slot(
                id="payload",
                data=payload,
                target="data/payload.txt",
                operations="",
                purpose="data",
                lifecycle="runtime",
                permissions="0644",
            )
            .with_keys(seed="integrity-is-not-runnability")
            .with_options(launcher_bin=launcher)
            .build(package)
        )
        assert result.success, result.errors
        package.chmod(0o755)

        integrity = FlavorVerifier.verify_package(package)
        assert integrity["valid"], "fixture is wrong: the package should be internally sound"
        assert integrity["checksums_valid"]
        assert integrity["signature_valid"]

        with pytest.raises(BuildError, match=r"cannot read the package"):
            verify_built_package(package, launcher_name="flavor-rs-launcher-any", host_platform="linux_amd64")


# 🌶️📦🔚
