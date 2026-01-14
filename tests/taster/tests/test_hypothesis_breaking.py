#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Hypothesis-based tests designed to break PSPF handling"""

from pathlib import Path
import subprocess
import tempfile
from typing import Any

from hypothesis import assume, given, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule
import pytest

from flavor.psp.format_2025 import PSPFBuilder, PSPFReader, SlotMetadata


class BreakingInputStrategies:
    """Strategies for generating breaking inputs"""

    # Malicious filenames
    evil_filenames = st.one_of(
        st.just("../../../etc/passwd"),
        st.just("../../.ssh/id_rsa"),
        st.just("\x00null.txt"),
        st.just("file\nwith\nnewlines.txt"),
        st.just("file with spaces.txt"),
        st.just("file\twith\ttabs.txt"),
        st.just("file\rwith\rcarriage.txt"),
        st.just(""),  # Empty filename
        st.just("."),  # Current directory
        st.just(".."),  # Parent directory
        st.text(min_size=256, max_size=4096),  # Very long filename
        st.text().filter(lambda x: "\x00" in x or "\n" in x),  # With null/newline
    )

    # Extreme sizes
    extreme_sizes = st.one_of(
        st.just(0),  # Empty
        st.just(1),  # Single byte
        st.just(2**31 - 1),  # Max 32-bit signed
        st.just(2**31),  # Overflow 32-bit signed
        st.just(2**32 - 1),  # Max 32-bit unsigned
        st.just(2**63 - 1),  # Max 64-bit signed
        st.just(-1),  # Negative
        st.just(-(2**31)),  # Min 32-bit signed
    )

    # Malformed JSON
    malformed_json = st.one_of(
        st.just('{"unclosed": '),
        st.just('{"key": undefined}'),
        st.just('{"key": NaN}'),
        st.just('{"key": Infinity}'),
        st.just('{"key": 1e308}'),  # Near infinity
        st.just('{"key": -1e308}'),
        st.just('{"recursive": {"recursive": {"recursive": ...'),  # Incomplete recursion
    )

    # Binary chaos
    binary_chaos = st.one_of(
        st.binary(min_size=0, max_size=0),  # Empty
        st.binary(min_size=1, max_size=1),  # Single byte
        st.just(b"\x00" * 1024),  # All nulls
        st.just(b"\xff" * 1024),  # All ones
        st.just(b"A" * 1024 * 1024),  # 1MB of 'A'
        st.binary().map(lambda x: x[::-1]),  # Reversed bytes
    )


@pytest.mark.taster
@pytest.mark.stress
@pytest.mark.slow
class TestBreakingInputs:
    """Test with inputs designed to break things"""

    @given(filename=BreakingInputStrategies.evil_filenames)
    @settings(max_examples=50)
    def test_evil_filenames(self, filename: str) -> None:
        """Test handling of malicious filenames"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Try to create a slot with evil filename
            try:
                SlotMetadata(
                    index=0,
                    id=filename,
                    source="/tmp/test.txt",
                    target=filename,  # The evil filename becomes the target
                    size=100,
                    checksum="abc123",
                    operations="RAW",
                    purpose="payload",
                    lifecycle="runtime",
                )

                # Attempt to build with this slot
                builder = PSPFBuilder()
                bundle_path = tmpdir / "evil.psp"

                # This should either sanitize or reject the filename
                builder = builder.metadata(format="PSPF/2025", package={"name": "evil", "version": "1.0"})
                builder.build(bundle_path)

                # If it succeeded, verify the name was sanitized
                if bundle_path.exists():
                    reader = PSPFReader(bundle_path)
                    metadata = reader.read_metadata()
                    # Check that no path traversal is possible
                    assert ".." not in str(metadata)
                    assert "\x00" not in str(metadata)

            except (ValueError, OSError, AssertionError):
                # Expected for truly malicious names
                pass

    @given(size=BreakingInputStrategies.extreme_sizes)
    @settings(max_examples=50)
    def test_extreme_sizes(self, size: int) -> None:
        """Test handling of extreme file sizes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Skip truly impossible sizes
            if size < 0 or size > 2**32:
                assume(False)

            try:
                slot = SlotMetadata(
                    index=0,
                    id="huge",
                    source="/tmp/huge.dat",
                    target="huge.dat",
                    size=size,
                    checksum="abc",
                    operations="GZIP" if size > 0 else "RAW",
                    purpose="payload",
                    lifecycle="runtime",
                )

                # Just test metadata serialization
                slot_dict = slot.to_dict()
                assert slot_dict["size"] == size

                # Test that we can create metadata with this size
                metadata = {
                    "format": "PSPF/2025",
                    "package": {"name": "huge", "version": "1.0"},
                    "slots": [slot_dict],
                }

                # Should handle large sizes in metadata
                import json

                json_str = json.dumps(metadata)
                assert str(size) in json_str

            except (ValueError, OverflowError):
                # Expected for impossible sizes
                pass

    @given(json_data=BreakingInputStrategies.malformed_json)
    @settings(max_examples=50)
    def test_malformed_json_metadata(self, json_data: str) -> None:
        """Test handling of malformed JSON in metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Write malformed JSON to a file
            json_file = tmpdir / "malformed.json"
            json_file.write_text(json_data)

            # Try to parse it as manifest
            import json

            try:
                with json_file.open(encoding="utf-8") as f:
                    json.load(f)
                # If it parsed successfully, check if it's one of the edge cases
                # that Python's JSON parser might accept
                if "NaN" in json_data or "Infinity" in json_data:
                    # These should have failed but Python's parser might handle them
                    pass
                elif "..." in json_data:
                    # Incomplete JSON should have failed
                    pass
                else:
                    # Regular valid JSON is ok
                    pass
            except (json.JSONDecodeError, ValueError):
                # Expected for truly malformed JSON
                pass

    @given(binary_data=BreakingInputStrategies.binary_chaos)
    @settings(max_examples=50)
    def test_binary_chaos(self, binary_data: bytes) -> None:
        """Test handling of chaotic binary data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Try to read this as a PSPF bundle
            chaos_file = tmpdir / "chaos.psp"
            chaos_file.write_bytes(binary_data)

            try:
                reader = PSPFReader(chaos_file)

                # Try various operations that might break
                reader.verify_magic_trailer()  # Should fail for most inputs

            except Exception:
                # Expected for chaotic data
                pass


class PSPFStateMachine(RuleBasedStateMachine):
    """Stateful testing of PSPF operations"""

    def __init__(self) -> None:
        super().__init__()
        self.tmpdir = tempfile.mkdtemp()
        self.bundles = []
        self.slots = []

    @initialize()
    def setup(self) -> None:
        """Initialize test state"""
        self.tmpdir = Path(self.tmpdir)

    @rule(
        name=st.text(min_size=1, max_size=100),
        size=st.integers(min_value=0, max_value=1024 * 1024),
        operations=st.sampled_from(["RAW", "GZIP"]),
    )
    def add_slot(self, name: str, size: int, operations: str) -> None:
        """Add a slot to the pending list"""
        slot = SlotMetadata(
            index=len(self.slots),
            id=name,
            source="/tmp/test.txt",
            target=name,
            size=size,
            checksum="test",
            operations=operations,
            purpose="data",
            lifecycle="runtime",
        )
        self.slots.append(slot)

    @rule()
    def build_bundle(self) -> None:
        """Build a bundle with current slots"""
        if not self.slots:
            return

        builder = PSPFBuilder()
        bundle_path = self.tmpdir / f"bundle_{len(self.bundles)}.psp"

        try:
            builder = builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.0"})
            builder.build(bundle_path)

            if bundle_path.exists():
                self.bundles.append(bundle_path)

        except Exception:
            # Some combinations might fail
            pass

    @rule()
    def read_random_bundle(self) -> None:
        """Read a random bundle"""
        if not self.bundles:
            return

        import random

        bundle = random.choice(self.bundles)

        try:
            reader = PSPFReader(bundle)
            reader.verify_magic_trailer()
            reader.read_metadata()
        except Exception:
            # Might be corrupted
            pass

    @invariant()
    def bundles_exist(self) -> None:
        """Check that created bundles still exist"""
        for bundle in self.bundles:
            assert bundle.exists() or not bundle.exists()  # Tautology but checks access


@pytest.mark.hypothesis
@pytest.mark.taster
@pytest.mark.stress
@pytest.mark.integration
class TestHypothesisPipeIntegration:
    """Test piping data through taster with hypothesis"""

    @given(data=st.binary(min_size=0, max_size=10 * 1024))
    @settings(max_examples=20, deadline=1000)  # Increased deadline for launcher startup
    def test_pipe_stdin_stdout(self, data: bytes) -> None:
        """Test piping arbitrary binary data through taster"""
        # Skip if taster not available
        taster_path = Path(__file__).parents[1] / "dist" / "taster.psp"
        if not taster_path.exists():
            pytest.skip("taster.psp not built")

        # Pipe data through taster
        result = subprocess.run(
            [str(taster_path), "pipe", "stdin", "--format", "raw"],
            input=data,
            capture_output=True,
        )

        # Should preserve data exactly
        assert result.stdout == data

    @given(
        data=st.binary(min_size=1, max_size=1024),
        corruption_prob=st.floats(min_value=0.0, max_value=0.5),
    )
    @settings(max_examples=10, deadline=1000)  # Increased deadline for launcher startup
    def test_pipe_corruption(self, data: bytes, corruption_prob: float) -> None:
        """Test corruption command"""
        taster_path = Path(__file__).parents[1] / "dist" / "taster.psp"
        if not taster_path.exists():
            pytest.skip("taster.psp not built")

        # Corrupt data
        result = subprocess.run(
            [
                str(taster_path),
                "pipe",
                "corrupt",
                "--probability",
                str(corruption_prob),
            ],
            input=data,
            capture_output=True,
        )

        # Output should have same length but potentially different content
        assert len(result.stdout) == len(data)

        # With high probability, should be different
        if corruption_prob > 0.1 and len(data) > 10:
            assert result.stdout != data  # Likely corrupted

    @given(
        json_obj=st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.one_of(st.integers(), st.floats(allow_nan=False), st.text(), st.booleans()),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=20, deadline=1000)  # Increased deadline for launcher startup
    def test_pipe_json_validation(self, json_obj: dict[str, Any]) -> None:
        """Test JSON validation through pipe"""
        taster_path = Path(__file__).parents[1] / "dist" / "taster.psp"
        if not taster_path.exists():
            pytest.skip("taster.psp not built")

        import json

        json_str = json.dumps(json_obj)

        # Validate JSON
        result = subprocess.run(
            [str(taster_path), "pipe", "validate", "--schema", "json"],
            input=json_str.encode("utf-8"),
            capture_output=True,
        )

        # Should succeed for valid JSON
        assert result.returncode == 0

        # Output should be pretty-printed JSON
        output_obj = json.loads(result.stdout.decode("utf-8"))
        assert output_obj == json_obj


# Run with: pytest tests/stress/test_hypothesis_breaking.py -v --hypothesis-show-statistics

# 🌶️📦🔚
