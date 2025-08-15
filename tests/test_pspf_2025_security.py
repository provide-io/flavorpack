"""
PSPF 2025 Security Tests

Tests ephemeral keys, integrity sealing, and tamper detection.
"""

import hashlib
import json
import os
import struct
import tarfile
import tempfile
from pathlib import Path
import zlib

import pytest

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader,
    PSPFLauncher,
    PSPFIndex,
    SlotMetadata,
    ephemeral_key_pair,
    PSPF_MAGIC,
    INDEX_SIZE
)


class TestPSPFSecurity:
    """Test PSPF security features."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        import shutil
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def secure_bundle(self, temp_dir):
        """Create a secure bundle for testing."""
        # Create payload
        payload_path = temp_dir / "secure.py"
        payload_path.write_text("print('Secure payload')")
        
        slot = SlotMetadata(
            index=0,
            name="secure_payload",
            size=payload_path.stat().st_size,
            checksum=hashlib.sha256(payload_path.read_bytes()).hexdigest(),
            encoding="gzip",
            purpose="payload",
            lifecycle="persistent",
            path=payload_path
        )
        
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "secure-bundle",
                "version": "1.0.0"
            },
            "slots": [slot.to_dict()],
            "verification": {
                "integrity_seal": {
                    "required": True,
                    "algorithm": "ed25519"
                }
            }
        }
        
        bundle_path = temp_dir / "secure.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[slot]
        )
        
        return bundle_path
    
    def test_ephemeral_key_generation(self):
        """Test ephemeral key pair generation."""
        # Generate multiple key pairs
        keys = []
        for _ in range(5):
            private_key, public_key = ephemeral_key_pair()
            keys.append((private_key, public_key))
        
        # Verify all keys are unique
        private_keys = [k[0] for k in keys]
        public_keys = [k[1] for k in keys]
        
        assert len(set(private_keys)) == 5
        assert len(set(public_keys)) == 5
        
        # Verify key properties
        for private, public in keys:
            assert len(private) == 32
            assert len(public) == 32
            assert private != public
    
    def test_ephemeral_key_in_bundle(self, temp_dir):
        """Test ephemeral key is included in bundle."""
        bundle_path = temp_dir / "ephemeral.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "test", "version": "1.0"}},
            slots=[]
        )
        
        # Read index
        reader = PSPFReader(bundle_path)
        index = reader.read_index()
        
        # Verify public key is present
        assert index.ephemeral_public_key != b'\x00' * 32
        assert len(index.ephemeral_public_key) == 32
    
    def test_integrity_seal_creation(self, secure_bundle):
        """Test integrity seal is created during build."""
        reader = PSPFReader(secure_bundle)
        index = reader.read_index()
        
        # Extract metadata archive
        with open(secure_bundle, 'rb') as f:
            f.seek(index.metadata_offset)
            archive_data = f.read(index.metadata_size)
        
        # Check seal files exist
        import io
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode='r:gz') as tar:
            names = tar.getnames()
            assert 'integrity/seal.sig' in names
            assert 'integrity/seal.pem' in names
            
            # Verify public key matches index
            key_member = tar.getmember('integrity/seal.pem')
            key_data = tar.extractfile(key_member).read()
            assert key_data == index.ephemeral_public_key
    
    def test_integrity_seal_verification(self, secure_bundle):
        """Test integrity seal verification."""
        launcher = PSPFLauncher(secure_bundle)
        result = launcher.verify_integrity()
        
        assert result['valid']
        assert result['signature_valid']
        assert not result['tamper_detected']
    
    def test_metadata_tampering_detection(self, secure_bundle):
        """Test detection of tampered metadata."""
        # Read original bundle
        reader = PSPFReader(secure_bundle)
        index = reader.read_index()
        
        # Create tampered bundle
        tampered_path = secure_bundle.with_suffix('.tampered')
        import shutil
        shutil.copy2(secure_bundle, tampered_path)
        
        # Modify psp.json in metadata archive
        with open(tampered_path, 'r+b') as f:
            f.seek(index.metadata_offset)
            archive_data = f.read(index.metadata_size)
            
            # Decompress the archive
            import io
            import gzip
            with gzip.GzipFile(fileobj=io.BytesIO(archive_data)) as gz:
                with tarfile.open(fileobj=gz, mode='r') as tar:
                    # Extract all members
                    members_data = {}
                    for member in tar.getmembers():
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            members_data[member.name] = (member, file_obj.read())
            
            # Modify psp.json
            for name, (member, data) in members_data.items():
                if name == 'psp.json':
                    # Tamper with the JSON
                    modified_json = data.replace(b'"version": "1.0.0"', b'"version": "2.0.0"')
                    members_data[name] = (member, modified_json)
                    member.size = len(modified_json)
                    break
            
            # Recompress the archive
            output = io.BytesIO()
            with gzip.GzipFile(fileobj=output, mode='w') as gz:
                with tarfile.open(fileobj=gz, mode='w') as tar:
                    for name, (member, data) in members_data.items():
                        tar.addfile(member, io.BytesIO(data))
            
            # Write back the modified archive
            modified_data = output.getvalue()
            f.seek(index.metadata_offset)
            
            # Ensure we don't exceed the original size
            if len(modified_data) <= index.metadata_size:
                f.write(modified_data)
                # Pad with zeros if needed
                if len(modified_data) < index.metadata_size:
                    f.write(b'\x00' * (index.metadata_size - len(modified_data)))
        
        # Verify tampering is detected
        launcher = PSPFLauncher(tampered_path)
        result = launcher.verify_integrity()
        
        # The integrity check should fail due to tampering
        assert not result['valid'], "Tampering should be detected"
        assert result['tamper_detected'] or not result['signature_valid'], "Should detect tampered metadata"
    
    def test_slot_tampering_detection(self, temp_dir):
        """Test detection of tampered slot data."""
        # Create bundle with slot
        slot_path = temp_dir / "data.txt"
        original_data = b"Original slot data"
        slot_path.write_bytes(original_data)
        
        slot = SlotMetadata(
            index=0,
            name="data",
            size=len(original_data),
            checksum=hashlib.sha256(original_data).hexdigest(),
            encoding="none",
            purpose="payload",
            lifecycle="persistent",
            path=slot_path
        )
        
        bundle_path = temp_dir / "slot_tamper.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "test", "version": "1.0"}},
            slots=[slot]
        )
        
        # Tamper with slot data
        reader = PSPFReader(bundle_path)
        index = reader.read_index()
        
        with open(bundle_path, 'r+b') as f:
            # Read slot table to find slot location
            f.seek(index.slot_table_offset)
            slot_offset = struct.unpack('<Q', f.read(8))[0]
            
            # Modify slot data
            f.seek(slot_offset)
            f.write(b"Tampered slot data")
        
        # Checksum verification should fail when extracting the slot
        launcher = PSPFLauncher(bundle_path)
        
        # Try to extract the tampered slot (pass slot index, not SlotMetadata)
        with pytest.raises(ValueError, match="Checksum mismatch"):
            launcher.extract_slot(0, temp_dir / "extracted", verify_checksum=True)
    
    def test_index_checksum_validation(self, temp_dir):
        """Test index block checksum validation."""
        bundle_path = temp_dir / "index_check.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "test", "version": "1.0"}},
            slots=[]
        )
        
        # Tamper with index
        launcher_size = PSPFReader(bundle_path).detect_launcher_size()
        
        with open(bundle_path, 'r+b') as f:
            f.seek(launcher_size + 20)  # Modify some field
            f.write(struct.pack('<Q', 0xDEADBEEF))
        
        # Should fail checksum validation
        reader = PSPFReader(bundle_path)
        with pytest.raises(ValueError, match="Index checksum mismatch"):
            reader.read_index()
    
    def test_emoji_magic_corruption(self, temp_dir):
        """Test detection of corrupted emoji magic."""
        bundle_path = temp_dir / "magic_corrupt.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "test", "version": "1.0"}},
            slots=[]
        )
        
        # Corrupt emoji magic
        with open(bundle_path, 'r+b') as f:
            f.seek(-4, 2)
            f.write(b"BAD!")
        
        reader = PSPFReader(bundle_path)
        assert not reader.verify_magic()
        
        # Launcher should detect invalid magic during integrity check
        launcher = PSPFLauncher(bundle_path)
        result = launcher.verify_integrity()
        assert not result['valid'], "Should fail integrity check with bad magic"
    
    def test_missing_integrity_seal(self, temp_dir):
        """Test handling of missing integrity seal."""
        # Create metadata without seal requirement
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "no-seal",
                "version": "1.0.0"
            },
            "verification": {
                "integrity_seal": {
                    "required": False
                }
            }
        }
        
        bundle_path = temp_dir / "no_seal.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[]
        )
        
        # Should work without seal if not required
        launcher = PSPFLauncher(bundle_path)
        result = launcher.verify_integrity()
        assert result['valid']
    
    def test_trust_signatures(self, temp_dir):
        """Test trust signature handling."""
        # Create bundle with trust signatures
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "trusted",
                "version": "1.0.0"
            },
            "verification": {
                "integrity_seal": {
                    "required": True,
                    "algorithm": "ed25519"
                },
                "trust_signatures": {
                    "required": False,
                    "signers": [
                        {
                            "name": "Developer",
                            "key_id": "ABC123",
                            "algorithm": "ed25519"
                        }
                    ]
                }
            }
        }
        
        bundle_path = temp_dir / "trusted.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[]
        )
        
        # Read and verify structure
        reader = PSPFReader(bundle_path)
        read_metadata = reader.read_metadata()
        
        assert 'trust_signatures' in read_metadata['verification']
        assert len(read_metadata['verification']['trust_signatures']['signers']) == 1
    
    def test_build_reproducibility(self, temp_dir):
        """Test build reproducibility aspects."""
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "reproducible",
                "version": "1.0.0"
            }
        }
        
        # Build twice
        bundle1_path = temp_dir / "bundle1.pspf"
        bundle2_path = temp_dir / "bundle2.pspf"
        
        builder = PSPFBuilder()
        builder.build(output_path=bundle1_path, metadata=metadata, slots=[])
        builder.build(output_path=bundle2_path, metadata=metadata, slots=[])
        
        # Compare bundles
        data1 = bundle1_path.read_bytes()
        data2 = bundle2_path.read_bytes()
        
        # Bundles should differ due to:
        # - Different ephemeral keys
        # - Different random emojis
        # - Possibly different timestamps
        assert data1 != data2
        
        # But structure should be identical
        reader1 = PSPFReader(bundle1_path)
        reader2 = PSPFReader(bundle2_path)
        
        index1 = reader1.read_index()
        index2 = reader2.read_index()
        
        assert index1.format_magic == index2.format_magic
        assert index1.format_version == index2.format_version
        assert index1.launcher_size == index2.launcher_size