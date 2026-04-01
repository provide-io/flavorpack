#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Python launcher parity tests for launch-time security and cache identity."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from flavor.config.policy import OperatorPolicy
from flavor.psp.format_2025.launcher import PSPFLauncher
from flavor.psp.format_2025.workenv import WorkEnvManager

pytestmark = [
    pytest.mark.cross_language,
    pytest.mark.ci,
    pytest.mark.security,
    pytest.mark.adversarial,
]


def _raw_public_key_bytes() -> bytes:
    """Generate a valid raw Ed25519 public key for trust checks."""
    public_key = Ed25519PrivateKey.generate().public_key()
    return public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def test_launcher_execute_blocks_untrusted_package_when_policy_requires_trusted_key(tmp_path: Path) -> None:
    """Execution must stop before setup when operator policy requires a trusted signing key."""
    bundle_path = tmp_path / "package.psp"
    bundle_path.write_bytes(b"bundle")

    launcher = PSPFLauncher(bundle_path)
    metadata = {
        "package": {"name": "pkg", "version": "1.0.0"},
        "execution": {"command": "echo hi"},
        "slots": [],
    }
    index = SimpleNamespace(public_key=_raw_public_key_bytes(), build_timestamp=0)

    with (
        patch.object(launcher, "read_metadata", return_value=metadata),
        patch.object(launcher, "read_index", return_value=index),
        patch("flavor.psp.format_2025.launcher.verify_package_integrity", return_value={"valid": True}),
        patch(
            "flavor.psp.format_2025.launcher.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
        patch("flavor.psp.format_2025.launcher.is_key_trusted", return_value=False),
        patch.object(launcher._workenv_manager, "setup_workenv") as mock_setup_workenv,
        patch("flavor.psp.format_2025.executor.BundleExecutor") as mock_executor,
    ):
        result = launcher.execute([])

    assert result["executed"] is False
    assert "trusted" in result["error"]
    mock_setup_workenv.assert_not_called()
    mock_executor.assert_not_called()


def test_launcher_execute_blocks_unsigned_package_when_policy_requires_trusted_key(tmp_path: Path) -> None:
    """Unsigned bundles must not satisfy require_trusted_key."""
    bundle_path = tmp_path / "unsigned.psp"
    bundle_path.write_bytes(b"bundle")

    launcher = PSPFLauncher(bundle_path)
    metadata = {
        "package": {"name": "pkg", "version": "1.0.0"},
        "execution": {"command": "echo hi"},
        "slots": [],
    }
    index = SimpleNamespace(public_key=b"\x00" * 32, attestation_key_fp=b"\x00" * 64, build_timestamp=0)

    with (
        patch.object(launcher, "read_metadata", return_value=metadata),
        patch.object(launcher, "read_index", return_value=index),
        patch("flavor.psp.format_2025.launcher.verify_package_integrity", return_value={"valid": True}),
        patch(
            "flavor.psp.format_2025.launcher.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
        patch.object(launcher._workenv_manager, "setup_workenv") as mock_setup_workenv,
        patch("flavor.psp.format_2025.executor.BundleExecutor") as mock_executor,
    ):
        mock_executor.return_value.execute.return_value = {"executed": True, "exit_code": 0}
        result = launcher.execute([])

    assert result["executed"] is False
    assert "trusted" in result["error"] or "signed" in result["error"]
    mock_setup_workenv.assert_not_called()
    mock_executor.assert_not_called()


def test_launcher_execute_blocks_when_trust_store_missing_and_policy_requires_trusted_key(
    tmp_path: Path,
) -> None:
    """Missing trust stores must fail closed when trusted-key policy is enabled."""
    bundle_path = tmp_path / "package.psp"
    bundle_path.write_bytes(b"bundle")

    launcher = PSPFLauncher(bundle_path)
    metadata = {
        "package": {"name": "pkg", "version": "1.0.0"},
        "execution": {"command": "echo hi"},
        "slots": [],
    }
    public_key = _raw_public_key_bytes()
    index = SimpleNamespace(public_key=public_key, attestation_key_fp=b"\x00" * 64, build_timestamp=0)

    with (
        patch.object(launcher, "read_metadata", return_value=metadata),
        patch.object(launcher, "read_index", return_value=index),
        patch("flavor.psp.format_2025.launcher.verify_package_integrity", return_value={"valid": True}),
        patch(
            "flavor.psp.format_2025.launcher.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=True),
        ),
        patch("flavor.psp.format_2025.launcher.is_key_trusted", return_value=None),
        patch.object(launcher._workenv_manager, "setup_workenv") as mock_setup_workenv,
        patch("flavor.psp.format_2025.executor.BundleExecutor") as mock_executor,
    ):
        mock_executor.return_value.execute.return_value = {"executed": True, "exit_code": 0}
        result = launcher.execute([])

    assert result["executed"] is False
    assert "trusted" in result["error"] or "store" in result["error"]
    mock_setup_workenv.assert_not_called()
    mock_executor.assert_not_called()


def test_launcher_execute_blocks_when_attestation_fingerprint_mismatches_public_key(tmp_path: Path) -> None:
    """Embedded attestation_key_fp must match the embedded public key fingerprint."""
    bundle_path = tmp_path / "package.psp"
    bundle_path.write_bytes(b"bundle")

    launcher = PSPFLauncher(bundle_path)
    metadata = {
        "package": {"name": "pkg", "version": "1.0.0"},
        "execution": {"command": "echo hi"},
        "slots": [],
    }
    index = SimpleNamespace(
        public_key=_raw_public_key_bytes(), attestation_key_fp=b"f" * 64, build_timestamp=0
    )

    with (
        patch.object(launcher, "read_metadata", return_value=metadata),
        patch.object(launcher, "read_index", return_value=index),
        patch("flavor.psp.format_2025.launcher.verify_package_integrity", return_value={"valid": True}),
        patch(
            "flavor.psp.format_2025.launcher.load_operator_policy",
            return_value=OperatorPolicy(require_trusted_key=False),
        ),
        patch.object(launcher._workenv_manager, "setup_workenv") as mock_setup_workenv,
        patch("flavor.psp.format_2025.executor.BundleExecutor") as mock_executor,
    ):
        mock_executor.return_value.execute.return_value = {"executed": True, "exit_code": 0}
        result = launcher.execute([])

    assert result["executed"] is False
    assert "fingerprint" in result["error"] or "metadata" in result["error"]
    mock_setup_workenv.assert_not_called()
    mock_executor.assert_not_called()


def test_launcher_execute_blocks_when_os_keychain_policy_is_enabled(tmp_path: Path) -> None:
    """use_os_keychain must fail closed until a real backend exists."""
    bundle_path = tmp_path / "package.psp"
    bundle_path.write_bytes(b"bundle")

    launcher = PSPFLauncher(bundle_path)
    metadata = {
        "package": {"name": "pkg", "version": "1.0.0"},
        "execution": {"command": "echo hi"},
        "slots": [],
    }
    index = SimpleNamespace(
        public_key=_raw_public_key_bytes(), attestation_key_fp=b"\x00" * 64, build_timestamp=0
    )

    with (
        patch.object(launcher, "read_metadata", return_value=metadata),
        patch.object(launcher, "read_index", return_value=index),
        patch("flavor.psp.format_2025.launcher.verify_package_integrity", return_value={"valid": True}),
        patch(
            "flavor.psp.format_2025.launcher.load_operator_policy",
            return_value=OperatorPolicy(use_os_keychain=True),
        ),
        patch("flavor.psp.format_2025.launcher.is_key_trusted", return_value=True),
        patch.object(launcher._workenv_manager, "setup_workenv") as mock_setup_workenv,
        patch("flavor.psp.format_2025.executor.BundleExecutor") as mock_executor,
    ):
        mock_executor.return_value.execute.return_value = {"executed": True, "exit_code": 0}
        result = launcher.execute([])

    assert result["executed"] is False
    assert "use_os_keychain" in result["error"] or "unsupported" in result["error"]
    mock_setup_workenv.assert_not_called()
    mock_executor.assert_not_called()


def test_workenv_path_is_bundle_specific_for_identical_package_metadata(tmp_path: Path) -> None:
    """Distinct bundles with the same package metadata must not share one Python workenv path."""
    bundle_one = tmp_path / "package-one.psp"
    bundle_two = tmp_path / "package-two.psp"
    bundle_one.write_bytes(b"bundle-one")
    bundle_two.write_bytes(b"bundle-two")

    reader = Mock()
    reader.read_metadata.return_value = {"package": {"name": "pkg", "version": "1.0.0"}}
    reader._index = SimpleNamespace(slot_count=0)
    manager = WorkEnvManager(reader)

    with (
        patch("flavor.cache.get_cache_dir", return_value=tmp_path / "cache"),
        patch.object(manager, "_check_cache_validity", return_value=True),
    ):
        path_one = manager.setup_workenv(bundle_one)
        path_two = manager.setup_workenv(bundle_two)

    assert path_one != path_two
