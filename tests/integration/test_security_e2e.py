#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""End-to-end integration tests for PSPF security features.

Covers: policy hash binding, key fingerprint binding, SBOM digest binding,
and the CLI commands inspect, policy, and trust.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from flavor.cli import cli
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _build_simple_psp(
    builder: PSPFBuilder,
    tmp_path: Path,
    *,
    name: str = "test-pkg",
    extra_metadata: dict | None = None,  # type: ignore[type-arg]
) -> Path:
    """Build a minimal PSP into *tmp_path* and return the path."""
    slot_file = tmp_path / "payload.txt"
    slot_file.write_bytes(b"hello from " + name.encode())

    metadata = {
        "package": {
            "name": name,
            "version": "1.0.0",
        },
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    result = (
        builder.metadata(**metadata, allow_empty=True)
        .add_slot(id="payload", data=slot_file, purpose="data", lifecycle="runtime", operations="none")
        .with_options()
        .build(tmp_path / f"{name}.psp")
    )
    assert result.success, f"Build failed: {result.errors}"
    return tmp_path / f"{name}.psp"


# ---------------------------------------------------------------------------
# Class TestPolicyHashRoundtrip
# ---------------------------------------------------------------------------


class TestPolicyHashRoundtrip:
    """Policy hash is written to / read from the PSPF index."""

    def test_policy_hash_written_to_index(self, test_builder: PSPFBuilder, tmp_path: Path) -> None:
        """Build a PSP with a policy dict; the hash must be non-zero and match SHA-256."""
        policy = {"refuse_root": True, "max_age_days": 90}
        psp_path = _build_simple_psp(
            test_builder, tmp_path, name="policy-pkg", extra_metadata={"policy": policy}
        )

        with PSPFReader(psp_path) as reader:
            index = reader.read_index()

        assert index.attestation_policy_hash != b"\x00" * 64, "Policy hash must be non-zero"

        canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(canonical.encode()).hexdigest()
        stored = index.attestation_policy_hash.rstrip(b"\x00").decode("ascii")
        assert stored == expected_hash, f"Stored hash {stored!r} != expected {expected_hash!r}"

    def test_empty_policy_no_hash(self, test_builder: PSPFBuilder, tmp_path: Path) -> None:
        """Build a PSP with no policy key; attestation_policy_hash must remain all zeros."""
        psp_path = _build_simple_psp(test_builder, tmp_path, name="no-policy-pkg")

        with PSPFReader(psp_path) as reader:
            index = reader.read_index()

        assert index.attestation_policy_hash == b"\x00" * 64, (
            "attestation_policy_hash should be all zeros when no policy is set"
        )

    def test_policy_hash_canonical_key_order(self, test_builder: PSPFBuilder, tmp_path: Path) -> None:
        """Two PSPs built with the same policy dict (different insertion order) must share identical hashes."""
        policy_a = {"refuse_root": True, "max_age_days": 90}
        policy_b = {"max_age_days": 90, "refuse_root": True}

        (tmp_path / "a").mkdir(exist_ok=True)
        (tmp_path / "b").mkdir(exist_ok=True)
        psp_a = _build_simple_psp(
            test_builder, tmp_path / "a", name="policy-a", extra_metadata={"policy": policy_a}
        )
        psp_b = _build_simple_psp(
            test_builder, tmp_path / "b", name="policy-b", extra_metadata={"policy": policy_b}
        )

        with PSPFReader(psp_a) as reader_a:
            index_a = reader_a.read_index()
        with PSPFReader(psp_b) as reader_b:
            index_b = reader_b.read_index()

        assert index_a.attestation_policy_hash == index_b.attestation_policy_hash, (
            "Policy hash must be identical regardless of key insertion order"
        )


# ---------------------------------------------------------------------------
# Class TestKeyFingerprintRoundtrip
# ---------------------------------------------------------------------------


class TestKeyFingerprintRoundtrip:
    """Key fingerprint is written to / read from the PSPF index."""

    def test_key_fingerprint_written_to_index(self, tmp_path: Path) -> None:
        """Build a PSP with an explicit seed; fingerprint must match SHA-256(raw_public_key_bytes)."""
        # Use a fresh builder with a known seed so we can derive the expected fingerprint.
        seed = "test_fingerprint_seed_unique"
        builder = PSPFBuilder.create().with_keys(seed=seed)

        # Derive the same public key bytes as the builder will use.
        from flavor.psp.format_2025.keys import generate_deterministic_keys

        _priv, pub_raw = generate_deterministic_keys(seed)
        expected_fp = hashlib.sha256(pub_raw).hexdigest()

        psp_path = _build_simple_psp(builder, tmp_path, name="fp-pkg")

        with PSPFReader(psp_path) as reader:
            index = reader.read_index()

        assert index.attestation_key_fp != b"\x00" * 64, "Key fingerprint must be non-zero for signed package"
        stored_fp = index.attestation_key_fp.rstrip(b"\x00").decode("ascii")
        assert stored_fp == expected_fp, f"Stored fp {stored_fp!r} != expected {expected_fp!r}"

    def test_unsigned_package_no_fingerprint(self, tmp_path: Path) -> None:
        """A PSP built without keys must have all-zero attestation_key_fp."""
        # Build without keys: pass zeros explicitly to force the "no key" path.
        from flavor.psp.format_2025.spec import BuildSpec

        spec = BuildSpec()
        # Override key config to use zero key bytes (the builder treats b"\x00"*32 as "no key").
        zero_key = b"\x00" * 32
        builder = PSPFBuilder(spec).with_keys(private=zero_key, public=zero_key)

        slot_file = tmp_path / "payload.txt"
        slot_file.write_bytes(b"unsigned payload")
        result = (
            builder.metadata(package={"name": "unsigned", "version": "0.0.1"}, allow_empty=True)
            .add_slot(id="data", data=slot_file, purpose="data", lifecycle="runtime", operations="none")
            .with_options()
            .build(tmp_path / "unsigned.psp")
        )
        assert result.success, f"Build failed: {result.errors}"

        with PSPFReader(tmp_path / "unsigned.psp") as reader:
            index = reader.read_index()

        assert index.attestation_key_fp == b"\x00" * 64, (
            "attestation_key_fp must be all zeros for an unsigned package"
        )


# ---------------------------------------------------------------------------
# Class TestSBOMDigestRoundtrip
# ---------------------------------------------------------------------------


class TestSBOMDigestRoundtrip:
    """SBOM digest is written to / read from the PSPF index."""

    def test_sbom_digest_written_to_index(self, test_builder: PSPFBuilder, tmp_path: Path) -> None:
        """Build a PSP and verify attestation_sbom_digest is non-zero and matches attestation slot content."""
        from flavor.psp.format_2025.constants import LIFECYCLE_ATTESTATION

        psp_path = _build_simple_psp(test_builder, tmp_path, name="sbom-pkg")

        with PSPFReader(psp_path) as reader:
            index = reader.read_index()
            descriptors = reader.read_slot_descriptors()

            assert index.attestation_sbom_digest != b"\x00" * 64, "SBOM digest must be non-zero"

            # Find and read the attestation slot
            att_idx: int | None = None
            for i, d in enumerate(descriptors):
                if d.lifecycle == LIFECYCLE_ATTESTATION:
                    att_idx = i
                    break

            assert att_idx is not None, "Attestation slot must be present in built PSP"
            att_bytes = reader.read_slot(att_idx)

        expected_digest = hashlib.sha256(att_bytes).hexdigest()
        stored_digest = index.attestation_sbom_digest.rstrip(b"\x00").decode("ascii")
        assert stored_digest == expected_digest, (
            f"Stored SBOM digest {stored_digest!r} != expected {expected_digest!r}"
        )

    def test_sbom_digest_changes_with_content(self, test_builder: PSPFBuilder, tmp_path: Path) -> None:
        """Two PSPs with different package names must produce different SBOM digest values."""
        (tmp_path / "a").mkdir(exist_ok=True)
        (tmp_path / "b").mkdir(exist_ok=True)
        psp_a = _build_simple_psp(test_builder, tmp_path / "a", name="alpha-pkg")
        psp_b = _build_simple_psp(test_builder, tmp_path / "b", name="beta-pkg")

        with PSPFReader(psp_a) as reader_a:
            index_a = reader_a.read_index()
        with PSPFReader(psp_b) as reader_b:
            index_b = reader_b.read_index()

        assert index_a.attestation_sbom_digest != index_b.attestation_sbom_digest, (
            "Different package names must produce different SBOM digests"
        )


# ---------------------------------------------------------------------------
# Class TestInspectCLI
# ---------------------------------------------------------------------------


class TestInspectCLI:
    """CLI: flavor inspect --sbom / --provenance / --sbom --json"""

    @pytest.fixture
    def package_path(self, test_builder: PSPFBuilder, tmp_path: Path) -> Path:
        return _build_simple_psp(test_builder, tmp_path, name="inspect-cli-pkg")

    def test_inspect_sbom_output(self, package_path: Path) -> None:
        """inspect --sbom should exit 0 and contain CycloneDX marker."""
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", "--sbom", str(package_path)])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "CycloneDX" in result.output, f"Expected 'CycloneDX' in output: {result.output}"

    def test_inspect_provenance_output(self, package_path: Path) -> None:
        """inspect --provenance should exit 0 and contain flavor-python marker."""
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", "--provenance", str(package_path)])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "flavor-python" in result.output, f"Expected 'flavor-python' in output: {result.output}"

    def test_inspect_sbom_json(self, package_path: Path) -> None:
        """inspect --sbom should produce valid JSON SBOM with bomFormat key."""
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", "--sbom", str(package_path)])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        # The output may contain log lines before the JSON block; find the JSON object start.
        output = result.output
        json_start = output.find("{")
        assert json_start != -1, f"No JSON object found in output: {output!r}"
        json_str = output[json_start:]
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            pytest.fail(f"Output after first '{{' is not valid JSON: {json_str!r}")
        assert "bomFormat" in parsed, f"Expected 'bomFormat' key in parsed JSON: {parsed!r}"


# ---------------------------------------------------------------------------
# Class TestPolicyCLI
# ---------------------------------------------------------------------------


class TestPolicyCLI:
    """CLI: flavor policy check / show"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_policy_check_passes_no_policy(
        self, runner: CliRunner, test_builder: PSPFBuilder, tmp_path: Path
    ) -> None:
        """policy check on a PSP with no declared policy should exit 0."""
        psp = _build_simple_psp(test_builder, tmp_path, name="no-policy")
        result = runner.invoke(cli, ["policy", "check", str(psp)])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"

    def test_policy_check_passes_matching_platform(
        self, runner: CliRunner, test_builder: PSPFBuilder, tmp_path: Path
    ) -> None:
        """policy check on a PSP whose platform list includes the current host platform should exit 0."""
        import platform as _platform
        import sys

        os_name = (
            "linux"
            if sys.platform.startswith("linux")
            else ("darwin" if sys.platform == "darwin" else "windows")
        )
        machine = _platform.machine().lower()
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        current_platform = f"{os_name}_{arch}"

        psp = _build_simple_psp(
            test_builder,
            tmp_path,
            name="platform-ok",
            extra_metadata={"policy": {"platforms": [current_platform]}},
        )
        result = runner.invoke(cli, ["policy", "check", str(psp)])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"

    def test_policy_check_fails_wrong_platform(
        self, runner: CliRunner, test_builder: PSPFBuilder, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """policy check on a PSP declaring an impossible platform must exit non-zero with 'platform' in output."""
        # Use an empty config dir so any local policy.json (e.g. with enforcement.default=allow)
        # cannot override the deny-by-default enforcement mode.
        monkeypatch.setenv("FLAVOR_CONFIG_DIR", str(tmp_path / "empty-config"))
        psp = _build_simple_psp(
            test_builder,
            tmp_path,
            name="bad-platform",
            extra_metadata={"policy": {"platforms": ["mars_amd64"]}},
        )
        result = runner.invoke(cli, ["policy", "check", str(psp)])
        assert result.exit_code != 0, f"Expected non-zero exit, got 0: {result.output}"
        assert "platform" in result.output.lower(), f"Expected 'platform' in output: {result.output!r}"

    def test_policy_show_runs(self, runner: CliRunner) -> None:
        """policy show should always exit 0."""
        result = runner.invoke(cli, ["policy", "show"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"


# ---------------------------------------------------------------------------
# Class TestTrustCLI
# ---------------------------------------------------------------------------


class TestTrustCLI:
    """CLI: flavor trust add / list / remove / verify"""

    @pytest.fixture
    def trust_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Redirect trust store to a temp directory; also redirect system store to a nonexistent path."""
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir()
        # Use the env-var override so both the CLI and the trust module see the same dir.
        monkeypatch.setenv("FLAVOR_TRUSTED_KEYS_DIR", str(keys_dir))
        # Point system config dir somewhere that doesn't exist so system keys are absent.
        monkeypatch.setenv("FLAVOR_CONFIG_DIR", str(tmp_path / "config"))
        return keys_dir

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    @pytest.fixture
    def ed25519_keypair(self) -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Fresh Ed25519 key pair for trust tests."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        return private_key, private_key.public_key()

    @pytest.fixture
    def pub_key_pem_file(
        self,
        ed25519_keypair: tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey],
        tmp_path: Path,
    ) -> Path:
        """Write the public key as PEM to a temp file and return its path."""
        _, pub = ed25519_keypair
        pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        pem_file = tmp_path / "test.pub"
        pem_file.write_bytes(pem)
        return pem_file

    def _expected_fingerprint(self, pub: ed25519.Ed25519PublicKey) -> str:
        raw = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return hashlib.sha256(raw).hexdigest()

    def test_trust_list_empty(
        self,
        runner: CliRunner,
        trust_env: Path,
    ) -> None:
        """trust list on an empty store should exit 0."""
        result = runner.invoke(cli, ["trust", "list"])
        assert result.exit_code == 0, f"Expected exit 0: {result.output}"

    def test_trust_add_and_list(
        self,
        runner: CliRunner,
        trust_env: Path,
        ed25519_keypair: tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey],
        pub_key_pem_file: Path,
    ) -> None:
        """trust add followed by trust list should show the key fingerprint."""
        _, pub = ed25519_keypair
        expected_fp = self._expected_fingerprint(pub)

        add_result = runner.invoke(cli, ["trust", "add", str(pub_key_pem_file)])
        assert add_result.exit_code == 0, f"trust add failed: {add_result.output}"

        list_result = runner.invoke(cli, ["trust", "list"])
        assert list_result.exit_code == 0, f"trust list failed: {list_result.output}"
        assert expected_fp[:16] in list_result.output, (
            f"Expected fingerprint prefix {expected_fp[:16]} in: {list_result.output}"
        )

    def test_trust_remove(
        self,
        runner: CliRunner,
        trust_env: Path,
        ed25519_keypair: tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey],
        pub_key_pem_file: Path,
    ) -> None:
        """trust remove should remove the key so it no longer appears in trust list."""
        _, pub = ed25519_keypair
        expected_fp = self._expected_fingerprint(pub)

        runner.invoke(cli, ["trust", "add", str(pub_key_pem_file)])

        remove_result = runner.invoke(cli, ["trust", "remove", expected_fp])
        assert remove_result.exit_code == 0, f"trust remove failed: {remove_result.output}"

        list_result = runner.invoke(cli, ["trust", "list"])
        assert expected_fp[:16] not in list_result.output, (
            f"Fingerprint {expected_fp[:16]} should not appear after removal: {list_result.output}"
        )

    def test_trust_verify_trusted(
        self,
        runner: CliRunner,
        trust_env: Path,
        ed25519_keypair: tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey],
        pub_key_pem_file: Path,
        tmp_path: Path,
    ) -> None:
        """trust verify on a PSP whose key is in the store should exit 0."""
        from cryptography.hazmat.primitives.serialization import NoEncryption, PrivateFormat

        priv, pub = ed25519_keypair
        raw_pub = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
        raw_priv = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())

        builder = PSPFBuilder.create().with_keys(private=raw_priv, public=raw_pub)
        psp_dir = tmp_path / "trusted"
        psp_dir.mkdir(exist_ok=True)
        psp = _build_simple_psp(builder, psp_dir, name="trusted-pkg")

        runner.invoke(cli, ["trust", "add", str(pub_key_pem_file)])

        verify_result = runner.invoke(cli, ["trust", "verify", str(psp)])
        assert verify_result.exit_code == 0, (
            f"Expected exit 0 for trusted key, got {verify_result.exit_code}: {verify_result.output}"
        )

    def test_trust_verify_untrusted(
        self,
        runner: CliRunner,
        trust_env: Path,
        ed25519_keypair: tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey],
        tmp_path: Path,
    ) -> None:
        """trust verify on a PSP whose key is NOT in the store should exit 1."""
        from cryptography.hazmat.primitives.serialization import NoEncryption, PrivateFormat

        priv, pub = ed25519_keypair
        raw_pub = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
        raw_priv = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())

        builder = PSPFBuilder.create().with_keys(private=raw_priv, public=raw_pub)
        psp_dir = tmp_path / "untrusted"
        psp_dir.mkdir(exist_ok=True)
        psp = _build_simple_psp(builder, psp_dir, name="untrusted-pkg")

        # Do NOT add the key to the store — but create the store dir so is_key_trusted returns False
        # (not None).  trust_env fixture already created the keys dir.

        verify_result = runner.invoke(cli, ["trust", "verify", str(psp)])
        assert verify_result.exit_code == 1, (
            f"Expected exit 1 for untrusted key, got {verify_result.exit_code}: {verify_result.output}"
        )

    def test_trust_verify_no_fingerprint(
        self,
        runner: CliRunner,
        trust_env: Path,
        tmp_path: Path,
    ) -> None:
        """trust verify on an unsigned PSP (no fingerprint) should exit 2."""
        from flavor.psp.format_2025.spec import BuildSpec

        zero_key = b"\x00" * 32
        builder = PSPFBuilder(BuildSpec()).with_keys(private=zero_key, public=zero_key)
        slot_file = tmp_path / "payload.txt"
        slot_file.write_bytes(b"unsigned")
        result = (
            builder.metadata(package={"name": "unsigned-verify", "version": "0.0.1"}, allow_empty=True)
            .add_slot(id="data", data=slot_file, purpose="data", lifecycle="runtime", operations="none")
            .with_options()
            .build(tmp_path / "unsigned-verify.psp")
        )
        assert result.success, f"Build failed: {result.errors}"

        verify_result = runner.invoke(cli, ["trust", "verify", str(tmp_path / "unsigned-verify.psp")])
        assert verify_result.exit_code == 2, (
            f"Expected exit 2 for no fingerprint, got {verify_result.exit_code}: {verify_result.output}"
        )


# 🌶️📦🔚
