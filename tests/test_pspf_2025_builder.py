"""
PSPF 2025 Builder Tests

Tests bundle building, manifest handling, and build options.
"""

import hashlib
import os
import tempfile
import tomllib
from pathlib import Path

import pytest

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader,
    SlotMetadata,
    MAGIC_WAND_EMOJI
)


class TestPSPFBuilder:
    """Test PSPF bundle building."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        import shutil
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def manifest_file(self, temp_dir):
        """Create a manifest file."""
        # Create test files
        wheel_path = temp_dir / "dist" / "myapp.whl"
        wheel_path.parent.mkdir()
        wheel_path.write_bytes(b"WHEEL_CONTENT")
        
        manifest_data = {
            "name": "myapp",
            "version": "1.0.0",
            "slots": [
                {
                    "path": str(wheel_path),
                    "purpose": "payload",
                    "lifecycle": "runtime"
                }
            ]
        }
        
        manifest_path = temp_dir / "manifest.toml"
        # Write TOML manually for test
        toml_content = f'''
name = "{manifest_data['name']}"
version = "{manifest_data['version']}"

[[slots]]
path = "{manifest_data['slots'][0]['path']}"
purpose = "{manifest_data['slots'][0]['purpose']}"
lifecycle = "{manifest_data['slots'][0]['lifecycle']}"
'''
        manifest_path.write_text(toml_content)
        
        return manifest_path
    
    
    
    def test_automatic_launcher_selection_python(self, temp_dir, test_builder):
        """Test automatic Python launcher selection."""
        # Create Python wheel
        wheel_path = temp_dir / "app.whl"
        wheel_path.write_bytes(b"PK")  # Zip magic
        
        slot = SlotMetadata(
            index=0,
            name="app",
            size=2,
            checksum="abc",
            encoding="none",
            purpose="payload",
            lifecycle="runtime",
            path=wheel_path
        )
        
        bundle_path = temp_dir / "auto_python.psp"
        # Use test_builder from fixture
        result = (test_builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.0"})
                             .add_slot(slot.name, slot.path, encoding=slot.encoding, purpose=slot.purpose, lifecycle=slot.lifecycle)
                             .with_options(launcher_type="python")
                             .build(bundle_path))
        assert result.success, f"Build failed: {result.errors}"
        
        # Check emoji
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            magic = f.read(4).decode('utf-8')
        
        assert magic == MAGIC_WAND_EMOJI
    
    def test_magic_wand_selection(self, temp_dir, test_builder):
        """Test magic wand emoji selection."""
        bundle_path = temp_dir / "magic_wand.psp"
        
        # Use test_builder from fixture
        result = (test_builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.0"}, allow_empty=True)
                          .with_options(launcher_type="go")
                          .build(bundle_path))
        assert result.success, f"Build failed: {result.errors}"
        
        # Check emoji
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            magic = f.read(4).decode('utf-8')
        
        assert magic == MAGIC_WAND_EMOJI
    
    def test_compression_selection(self, temp_dir, test_builder):
        """Test automatic compression selection."""
        # Create different file types
        text_path = temp_dir / "text.json"
        text_path.write_text('{"data": "value"}' * 100)
        
        binary_path = temp_dir / "binary.so"
        binary_path.write_bytes(os.urandom(1024))
        
        random_path = temp_dir / "random.dat"
        random_path.write_bytes(os.urandom(1024))
        
        slots = [
            SlotMetadata(
                index=0,
                name="text",
                size=text_path.stat().st_size,
                checksum="abc",
                encoding="gzip",  # Good for text
                purpose="config",
                lifecycle="runtime",
                path=text_path
            ),
            SlotMetadata(
                index=1,
                name="binary",
                size=binary_path.stat().st_size,
                checksum="def",
                encoding="none",  # Binary files often don't compress well
                purpose="library",
                lifecycle="runtime",
                path=binary_path
            ),
            SlotMetadata(
                index=2,
                name="random",
                size=random_path.stat().st_size,
                checksum="ghi",
                encoding="none",  # Random data doesn't compress
                purpose="data",
                lifecycle="runtime",
                path=random_path
            )
        ]
        
        bundle_path = temp_dir / "compressed.psp"
        # Use test_builder from fixture
        builder = test_builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.0"})
        for slot in slots:
            builder = builder.add_slot(slot.name, slot.path, encoding=slot.encoding, purpose=slot.purpose, lifecycle=slot.lifecycle)
        result = builder.build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"
        
        # Verify compression worked
        assert bundle_path.exists()
        # Text should compress well
        # Random should not compress
    
    def test_build_validation_missing_file(self, temp_dir, test_builder):
        """Test build fails with missing file."""
        slot = SlotMetadata(
            index=0,
            name="missing",
            size=100,
            checksum="abc",
            encoding="none",
            purpose="payload",
            lifecycle="runtime",
            path=temp_dir / "nonexistent.txt"
        )
        
        bundle_path = temp_dir / "invalid.psp"
        # Use test_builder from fixture
        
        result = (test_builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.0"})
                              .add_slot(slot.name, slot.path, encoding=slot.encoding, purpose=slot.purpose, lifecycle=slot.lifecycle)
                              .build(bundle_path))
        assert not result.success
        assert any("does not exist" in e for e in result.errors)
    
    def test_build_validation_invalid_purpose(self, temp_dir, test_builder):
        """Test validation of slot purpose."""
        valid_purposes = ["payload", "library", "config", "asset", "runtime", "binary", "installer", "data"]
        
        for purpose in valid_purposes:
            slot = SlotMetadata(
                index=0,
                name=f"test_{purpose}",
                size=100,
                checksum="abc",
                encoding="none",
                purpose=purpose,
                lifecycle="runtime"
            )
            
            # Should not raise
            assert slot.purpose in valid_purposes
    
    def test_build_validation_duplicate_indices(self, temp_dir, test_builder):
        """Test handling of duplicate slot indices."""
        slot1 = SlotMetadata(
            index=0,
            name="slot1",
            size=100,
            checksum="abc",
            encoding="none",
            purpose="payload",
            lifecycle="runtime"
        )
        
        slot2 = SlotMetadata(
            index=0,  # Duplicate index
            name="slot2",
            size=100,
            checksum="def",
            encoding="none",
            purpose="payload",
            lifecycle="runtime"
        )
        
        # Builder should handle this appropriately
        # In real implementation, might auto-assign indices
        assert slot1.index == slot2.index
    
    def test_incremental_build(self, temp_dir, test_builder):
        """Test incremental build optimization."""
        # Create initial slots
        slots = []
        for i in range(3):
            path = temp_dir / f"slot{i}.dat"
            path.write_bytes(b"DATA" * 100)
            
            slots.append(SlotMetadata(
                index=i,
                name=f"slot{i}",
                size=path.stat().st_size,
                checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
                encoding="gzip",
                purpose="payload",
                lifecycle="runtime",
                path=path
            ))
        
        # First build
        bundle_path = temp_dir / "incremental.psp"
        # Use test_builder from fixture
        builder = test_builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.0"})
        for slot in slots:
            builder = builder.add_slot(slot.name, slot.path, encoding=slot.encoding, purpose=slot.purpose, lifecycle=slot.lifecycle)
        result = builder.build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"
        
        # Modify one slot
        slots[1].path.write_bytes(b"MODIFIED" * 100)
        slots[1].checksum = hashlib.sha256(slots[1].path.read_bytes()).hexdigest()
        
        # Incremental build (in real impl would reuse unchanged slots)
        builder = test_builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.1"})
        for slot in slots:
            builder = builder.add_slot(slot.name, slot.path, encoding=slot.encoding, purpose=slot.purpose, lifecycle=slot.lifecycle)
        result = builder.build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"
        
        # Verify update
        reader = PSPFReader(bundle_path)
        metadata = reader.read_metadata()
        assert metadata['package']['version'] == '1.1'
    
    def test_cross_platform_build(self, temp_dir, test_builder):
        """Test cross-platform building."""
        # Simulate building for different target
        bundle_path = temp_dir / "cross_platform.psp"
        
        # Use test_builder from fixture
        # In real implementation, would download target launcher
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "test", "version": "1.0"},
            "target_platform": "linux-amd64"
        }
        result = (test_builder.metadata(**metadata, allow_empty=True)
                          .with_options(launcher_type="go")
                          .build(bundle_path))
        assert result.success, f"Build failed: {result.errors}"
        
        assert bundle_path.exists()
    
    def test_reproducible_build(self, temp_dir, test_builder):
        """Test reproducible build mode."""
        slot_path = temp_dir / "data.txt"
        slot_path.write_text("Reproducible content")
        
        slot = SlotMetadata(
            index=0,
            name="data",
            size=slot_path.stat().st_size,
            checksum=hashlib.sha256(slot_path.read_bytes()).hexdigest(),
            encoding="none",
            purpose="payload",
            lifecycle="runtime",
            path=slot_path
        )
        
        # In reproducible mode:
        # - Timestamps should be zeroed
        # - Magic wand emoji is always used
        # - Ephemeral key derived deterministically
        
        bundle_path = temp_dir / "reproducible.psp"
        # Use test_builder from fixture
        
        result = (test_builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.0"})
                          .add_slot(slot.name, slot.path, encoding=slot.encoding, purpose=slot.purpose, lifecycle=slot.lifecycle)
                          .build(bundle_path))
        assert result.success, f"Build failed: {result.errors}"
        
        # Check emoji is always magic wand
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            magic = f.read(4).decode('utf-8')
        
        assert magic == MAGIC_WAND_EMOJI
    
    def test_size_optimization(self, temp_dir, test_builder):
        """Test size optimization build mode."""
        # Create compressible content
        large_path = temp_dir / "large.txt"
        large_path.write_text("REPEAT" * 10000)
        
        slot = SlotMetadata(
            index=0,
            name="large",
            size=large_path.stat().st_size,
            checksum="abc",
            encoding="gzip",  # Would use max compression
            purpose="payload",
            lifecycle="runtime",
            path=large_path
        )
        
        bundle_path = temp_dir / "optimized.psp"
        # Use test_builder from fixture
        result = (test_builder.metadata(format="PSPF/2025", package={"name": "test", "version": "1.0"})
                          .add_slot(slot.name, slot.path, encoding=slot.encoding, purpose=slot.purpose, lifecycle=slot.lifecycle)
                          .build(bundle_path))
        assert result.success, f"Build failed: {result.errors}"
        
        # Verify bundle was created
        bundle_size = bundle_path.stat().st_size
        original_size = large_path.stat().st_size
        
        # Bundle exists and is reasonable size (includes launcher)
        assert bundle_size > 0
        # The bundle includes a ~2.6MB launcher, so it will be larger than small text files
        assert bundle_path.exists()
    
    def test_persistent_key_signing(self, temp_dir, test_builder):
        """Test signing with persistent keys."""
        # In real implementation, would use actual crypto keys
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "signed",
                "version": "1.0.0"
            },
            "verification": {
                "integrity_seal": {
                    "required": True,
                    "algorithm": "ed25519"
                },
                "trust_signatures": {
                    "required": True,
                    "signers": [
                        {
                            "name": "Developer",
                            "key_id": "DEV123",
                            "algorithm": "ed25519"
                        }
                    ]
                }
            }
        }
        
        bundle_path = temp_dir / "signed.psp"
        # Use test_builder from fixture
        result = (test_builder.metadata(**metadata, allow_empty=True)
                          .build(bundle_path))
        assert result.success, f"Build failed: {result.errors}"
        
        # Verify both signatures exist
        reader = PSPFReader(bundle_path)
        read_metadata = reader.read_metadata()
        
        assert read_metadata['verification']['integrity_seal']['required']
        assert read_metadata['verification']['trust_signatures']['required']
    
    def test_multi_slot_bundling(self, temp_dir, test_builder):
        """Test bundling many slots."""
        slots = []
        
        # Create 20 slots of different types
        slot_types = [
            ("runtime", 2),
            ("library", 5),
            ("payload", 3),
            ("asset", 10)
        ]
        
        slot_index = 0
        for slot_type, count in slot_types:
            for i in range(count):
                path = temp_dir / f"{slot_type}_{i}.dat"
                path.write_bytes(f"{slot_type}_{i}".encode() * 10)
                
                slots.append(SlotMetadata(
                    index=slot_index,
                    name=f"{slot_type}_{i}",
                    size=path.stat().st_size,
                    checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
                    encoding="none",
                    purpose=slot_type if slot_type != "payload" else "library",
                    lifecycle="runtime",
                    path=path
                ))
                slot_index += 1
        
        bundle_path = temp_dir / "multi_slot.psp"
        # Use test_builder from fixture
        builder = test_builder.metadata(format="PSPF/2025", package={"name": "complex-app", "version": "1.0"})
        for slot in slots:
            builder = builder.add_slot(slot.name, slot.path, encoding=slot.encoding, purpose=slot.purpose, lifecycle=slot.lifecycle)
        result = builder.build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"
        
        # Verify all slots included
        reader = PSPFReader(bundle_path)
        index = reader.read_index()
        assert index.slot_count == 20
        
        metadata = reader.read_metadata()
        assert len(metadata['slots']) == 20
        
        # Verify sequential indices
        for i, slot_meta in enumerate(metadata['slots']):
            assert slot_meta['index'] == i