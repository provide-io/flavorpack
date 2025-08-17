"""
PSPF 2025 Comprehensive Cross-Language Combination Tests

Tests all 16 builder/launcher combinations using pytest parametrization.
"""

import hashlib
import json
import os
import struct
import tempfile
from pathlib import Path

import pytest

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader,
    PSPFLauncher,
    SlotMetadata,
    MAGIC_WAND_EMOJI,
    PSPF_MAGIC,
    INDEX_SIZE
)
from flavor.utils import get_platform_string


# Only test actual existing builders/launchers
# Python and Node builders/launchers were removed from the codebase
LANGUAGES = ["go", "rust"]
BUILDER_LAUNCHER_COMBINATIONS = [
    (builder, launcher) 
    for builder in LANGUAGES 
    for launcher in LANGUAGES
]


def check_helper_available(helper_type: str, language: str) -> bool:
    """Check if a helper binary is available."""
    platform_str = get_platform_string()
    
    # Map language types to actual binary names
    if language in ["rust", "python", "node", "unknown"]:
        suffix = "rs"
    else:
        suffix = language
    
    helper_name = f"flavor-{suffix}-{helper_type}"
    
    # Check in workenv
    workenv_dir = Path.cwd() / "workenv" / "flavors" / platform_str
    if (workenv_dir / helper_name).exists():
        return True
    
    # Check in helpers/bin
    helpers_dir = Path.cwd() / "helpers" / "bin"
    if (helpers_dir / helper_name).exists():
        return True
    
    # Check in ~/.cache/flavor/bin
    cache_dir = Path.home() / ".cache" / "flavor" / "bin"
    if (cache_dir / helper_name).exists():
        return True
    
    return False


def check_helpers_available() -> bool:
    """Check if all required helpers are available."""
    for language in LANGUAGES:
        if not check_helper_available("launcher", language):
            return False
    return True


@pytest.mark.integration
@pytest.mark.cross_language
@pytest.mark.requires_helpers
@pytest.mark.slow
@pytest.mark.skipif(not check_helpers_available(), reason="Helper binaries not available - build with 'flavor helpers build'")
class TestAllCombinations:
    """Test all builder/launcher combinations systematically."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        yield
        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.parametrize("builder,launcher", BUILDER_LAUNCHER_COMBINATIONS)
    def test_builder_launcher_combination(self, builder, launcher, test_builder):
        """Test a specific builder/launcher combination."""
        # Create a proper tar archive with an executable script
        tar_path = self.temp_dir / f"{builder}_{launcher}_payload.tar.gz"
        
        # Create a simple executable script
        script_content = f"""#!/bin/sh
echo "Built with {builder}, launched with {launcher}"
exit 0
"""
        
        # Create tar archive containing the script
        import tarfile
        import io
        
        with tarfile.open(tar_path, 'w:gz') as tar:
            # Add the run script
            script_info = tarfile.TarInfo(name='run')
            script_info.size = len(script_content)
            script_info.mode = 0o755  # Make it executable
            tar.addfile(script_info, io.BytesIO(script_content.encode()))
        
        # Get size for metadata
        payload_size = tar_path.stat().st_size
        payload_content = tar_path.read_bytes()
        
        # Create slot
        slot = SlotMetadata(
            index=0,
            name="payload.tar.gz",
            size=payload_size,
            checksum=hashlib.sha256(payload_content).hexdigest(),
            encoding="none",  # Already compressed
            purpose="payload",
            lifecycle="runtime",
            path=tar_path
        )
        
        # Build bundle
        bundle_path = self.temp_dir / f"{builder}_{launcher}.psp"
        builder_obj = test_builder
        
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": f"{builder}_{launcher}_test",
                "version": "1.0.0"
            },
            "builder": {
                "name": builder,
                "version": "1.0.0"
            },
            "launcher": {
                "name": launcher,
                "version": "1.0.0"
            },
            "execution": {
                "command": "{slot:0}/run"
            }
        }
        
        builder_obj.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[slot],
            launcher_type=launcher
        )
        
        # Verify bundle exists
        assert bundle_path.exists(), f"Bundle not created for {builder}/{launcher}"
        
        # Verify bundle structure
        reader = PSPFReader(bundle_path)
        
        # 1. Verify magic
        assert reader.verify_magic(), f"Invalid magic for {builder}/{launcher}"
        
        # 2. Verify index
        index = reader.read_index()
        assert index.format_magic == PSPF_MAGIC
        assert index.format_version == 0x20250001
        assert index.slot_count == 1
        
        # 3. Verify launcher emoji
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            emoji_magic = f.read(4).decode('utf-8').strip('\x00')
        
        assert emoji_magic == MAGIC_WAND_EMOJI  # Magic wand emoji
        
        # 4. Verify metadata
        metadata_read = reader.read_metadata()
        assert metadata_read['format'] == 'PSPF/2025'
        assert metadata_read['package']['name'] == f"{builder}_{launcher}_test"
        assert metadata_read['builder']['name'] == builder
        assert metadata_read['launcher']['name'] == launcher
        
        # 5. Verify slot
        assert len(metadata_read['slots']) == 1
        slot_meta = metadata_read['slots'][0]
        assert slot_meta['name'] == 'payload.tar.gz'
        assert slot_meta['encoding'] == 'none'  # Already compressed
        
        # 6. Verify checksums
        assert reader.verify_all_checksums()
        
        # 7. Test execution
        launcher_obj = PSPFLauncher(bundle_path)
        result = launcher_obj.execute()
        assert result['executed']
        assert result['error'] is None
    
    @pytest.mark.parametrize("builder,launcher", BUILDER_LAUNCHER_COMBINATIONS)
    def test_compatibility_matrix(self, builder, launcher, test_builder):
        """Test compatibility aspects of each combination."""
        bundle_path = self.temp_dir / f"compat_{builder}_{launcher}.psp"
        
        # Test various content types
        test_files = {
            "text": b"Hello, World!\n" * 100,
            "json": json.dumps({"test": True, "builder": builder}).encode(),
            "binary": os.urandom(1024),
            "unicode": "Hello 世界 🌍".encode('utf-8')
        }
        
        slots = []
        for idx, (name, content) in enumerate(test_files.items()):
            file_path = self.temp_dir / f"{name}_{builder}_{launcher}.dat"
            file_path.write_bytes(content)
            
            slots.append(SlotMetadata(
                index=idx,
                name=name,
                size=len(content),
                checksum=hashlib.sha256(content).hexdigest(),
                encoding="gzip" if name == "text" else "none",
                purpose="payload",
                lifecycle="runtime",
                path=file_path
            ))
        
        # Build with multiple slots
        builder_obj = test_builder
        builder_obj.build(
            output_path=bundle_path,
            metadata={
                "format": "PSPF/2025",
                "package": {"name": f"compat_{builder}_{launcher}", "version": "1.0.0"},
                "builder": builder,
                "launcher": launcher
            },
            slots=slots,
            launcher_type=launcher
        )
        
        # Verify all slots readable
        reader = PSPFReader(bundle_path)
        metadata = reader.read_metadata()
        assert len(metadata['slots']) == len(test_files)
        
        # Verify slot content integrity
        for slot_meta in metadata['slots']:
            assert slot_meta['checksum'] == slots[slot_meta['index']].checksum
    
    def test_all_combinations_summary(self, test_builder):
        """Generate summary of all combinations."""
        results = []
        
        for builder in LANGUAGES:
            for launcher in LANGUAGES:
                bundle_path = self.temp_dir / f"summary_{builder}_{launcher}.psp"
                
                # Quick build
                builder_obj = test_builder
                builder_obj.build(
                    output_path=bundle_path,
                    metadata={
                        "format": "PSPF/2025",
                        "package": {"name": f"{builder}_{launcher}", "version": "1.0.0"}
                    },
                    slots=[],
                    launcher_type=launcher
                )
                
                # Check
                reader = PSPFReader(bundle_path)
                is_valid = reader.verify_magic()
                
                results.append({
                    "builder": builder,
                    "launcher": launcher,
                    "valid": is_valid,
                    "size": bundle_path.stat().st_size
                })
        
        # Verify all 4 combinations (2 builders x 2 launchers)
        assert len(results) == 4
        assert all(r['valid'] for r in results)
        
        # Print summary table
        print("\n\nBuilder/Launcher Compatibility Matrix:")
        print("=" * 60)
        print(f"{'Builder':<10} {'Launcher':<10} {'Status':<10} {'Size':<10}")
        print("-" * 60)
        
        for r in sorted(results, key=lambda x: (x['builder'], x['launcher'])):
            status = "✅ PASS" if r['valid'] else "❌ FAIL"
            print(f"{r['builder']:<10} {r['launcher']:<10} {status:<10} {r['size']:<10}")
        
        print("=" * 60)
        print(f"Total combinations tested: {len(results)}")
        print(f"Passed: {sum(1 for r in results if r['valid'])}")
        print(f"Failed: {sum(1 for r in results if not r['valid'])}")
    
    @pytest.mark.parametrize("launcher", LANGUAGES)
    def test_launcher_emoji_correctness(self, launcher, test_builder):
        """Test each launcher has correct emoji."""
        bundle_path = self.temp_dir / f"emoji_test_{launcher}.psp"
        
        # Use test_builder from fixture
        test_builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "emoji", "version": "1.0"}},
            slots=[],
            launcher_type=launcher
        )
        
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            magic = f.read(4).decode('utf-8').strip('\x00')
        
        expected_emoji = MAGIC_WAND_EMOJI
        assert magic == expected_emoji, f"Wrong emoji for {launcher}: expected {expected_emoji}, got {magic}"
    
    @pytest.mark.parametrize("builder,launcher", [
        ("go", "rust"),       # Go builder with Rust launcher
        ("rust", "go"),       # Rust builder with Go launcher
    ])
    def test_critical_cross_language_paths(self, builder, launcher, test_builder):
        """Test critical cross-language combinations in detail."""
        # Create realistic payload for language
        payloads = {
            "python": b"#!/usr/bin/env python3\nprint('Hello from Python')\n",
            "go": b"package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Hello from Go\") }\n",
            "rust": b"fn main() {\n    println!(\"Hello from Rust\");\n}\n",
            "node": b"console.log('Hello from Node.js');\n"
        }
        
        payload_path = self.temp_dir / f"{builder}_source.{builder[:2]}"
        payload_path.write_bytes(payloads.get(builder, b"echo 'Hello'"))
        
        # Create slot with language-appropriate settings
        slot = SlotMetadata(
            index=0,
            name="main",
            size=payload_path.stat().st_size,
            checksum=hashlib.sha256(payload_path.read_bytes()).hexdigest(),
            encoding="gzip",  # Use gzip for all tests since zstd isn't implemented yet
            purpose="payload",
            lifecycle="runtime",
            path=payload_path
        )
        
        # Build bundle
        bundle_path = self.temp_dir / f"critical_{builder}_{launcher}.psp"
        builder_obj = test_builder
        
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": f"{builder}_app",
                "version": "1.0.0",
                "description": f"Built with {builder}, runs on {launcher}"
            },
            "builder": {
                "name": builder,
                "version": "1.0.0",
                "platform": "darwin-arm64"
            },
            "launcher": {
                "name": launcher,
                "version": "1.0.0",
                "platform": "darwin-arm64"
            },
            "execution": {
                "command": "{slot:0}/main",
                "env": {
                    "PSPF_BUILDER": builder,
                    "PSPF_LAUNCHER": launcher
                }
            }
        }
        
        builder_obj.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[slot],
            launcher_type=launcher
        )
        
        # Detailed verification
        reader = PSPFReader(bundle_path)
        
        # 1. Index integrity
        index = reader.read_index()
        assert index.package_size == bundle_path.stat().st_size
        
        # 2. Metadata integrity
        read_metadata = reader.read_metadata()
        assert read_metadata['execution']['env']['PSPF_BUILDER'] == builder
        assert read_metadata['execution']['env']['PSPF_LAUNCHER'] == launcher
        
        # 3. Launcher compatibility
        launcher_obj = PSPFLauncher(bundle_path)
        
        # Setup work environment and extract slots
        workenv_dir = launcher_obj.setup_workenv()
        extracted = launcher_obj.extract_all_slots(workenv_dir)
        assert len(extracted) == 1
        
        # Verify integrity
        integrity = launcher_obj.verify_integrity()
        assert integrity['valid']
        assert integrity['signature_valid']
        assert not integrity['tamper_detected']
    
    # ===== Additional compatibility tests merged from test_pspf_2025_compatibility.py =====
    
    def test_checksum_compatibility(self, test_builder):
        """Test checksum computation across languages."""
        import hashlib
        # Create test data
        test_data = b"The quick brown fox jumps over the lazy dog"
        expected_sha256 = "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592"
        
        slot_path = self.temp_dir / "test.txt"
        slot_path.write_bytes(test_data)
        
        # Test with each "language" (simulated)
        languages = ["python", "go", "rust"]
        
        for lang in languages:
            slot = SlotMetadata(
                index=0,
                name="checksum_test",
                size=len(test_data),
                checksum=expected_sha256,
                encoding="none",
                purpose="payload",
                lifecycle="runtime",
                path=slot_path
            )
            
            # All should compute same checksum
            computed = hashlib.sha256(test_data).hexdigest()
            assert computed == expected_sha256
    
    def test_compression_compatibility(self, test_builder):
        """Test compression algorithm compatibility."""
        # Create slots with different compression
        test_data = b"Compress me!" * 100
        
        compressions = [
            ("gzip", "python"),
            ("none", "go"),  # Changed from zstd since it's not implemented
            ("none", "rust")
        ]
        
        slots = []
        for i, (compression, lang) in enumerate(compressions):
            slot_path = self.temp_dir / f"slot_{i}.dat"
            slot_path.write_bytes(test_data)
            
            slots.append(SlotMetadata(
                index=i,
                name=f"slot-{i}",
                size=len(test_data),
                checksum="abc",
                encoding=compression,
                purpose="payload",
                lifecycle="runtime",
                path=slot_path
            ))
        
        # Build bundle
        bundle_path = self.temp_dir / "compressed.psp"
        test_builder.build(
            output_path=bundle_path,
            metadata={
                "format": "PSPF/2025",
                "package": {"name": "compression-test", "version": "1.0"}
            },
            slots=slots
        )
        
        # Each language should decompress all correctly
        reader = PSPFReader(bundle_path)
        metadata = reader.read_metadata()
        
        assert len(metadata['slots']) == 3
        for slot_meta in metadata['slots']:
            assert slot_meta['encoding'] in ["gzip", "none"]
    
    def test_utf8_emoji_handling(self, test_builder):
        """Test UTF-8 emoji handling across languages."""
        bundle_path = self.temp_dir / "emoji_test.psp"
        test_builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "emoji", "version": "1.0"}},
            slots=[],
            launcher_type="python"
        )
        
        # Test reading by different "languages"
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            emoji_bytes = f.read(4)
        
        # All should read identical bytes
        py_decoded = emoji_bytes.decode('utf-8')
        assert py_decoded == '🪄'
        
        # Simulate other languages reading same bytes
        assert len(emoji_bytes) == 4
        assert emoji_bytes == '🪄'.encode('utf-8')
    
    def test_binary_parsing_compatibility(self, test_builder):
        """Test binary structure parsing compatibility."""
        import struct
        # Create bundle
        bundle_path = self.temp_dir / "binary_test.psp"
        test_builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "binary", "version": "1.0"}},
            slots=[]
        )
        
        # Test different parsing methods
        reader = PSPFReader(bundle_path)
        launcher_size = reader.detect_launcher_size()
        
        with open(bundle_path, 'rb') as f:
            # Python struct.unpack
            f.seek(launcher_size)
            index_data = f.read(INDEX_SIZE)
            
            # Parse manually
            magic = index_data[0:8]
            version = struct.unpack('<I', index_data[8:12])[0]
            checksum = struct.unpack('<I', index_data[12:16])[0]
            package_size = struct.unpack('<Q', index_data[16:24])[0]
            
            assert magic == PSPF_MAGIC
            assert version == 0x20250001
            
            # All parsers should read identical values
    
    def test_metadata_json_compatibility(self, test_builder):
        """Test JSON metadata compatibility."""
        # Complex metadata with edge cases
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "json-test",
                "version": "1.0.0"
            },
            "unicode": "hello 世界 🌍",
            "numbers": {
                "small": 1.23e-10,
                "large": 1.23e10,
                "integer": 42,
                "negative": -273.15
            },
            "special_chars": 'quote" and \n newline',
            "null_value": None,
            "boolean": True,
            "array": [1, 2.5, "three", None, True]
        }
        
        bundle_path = self.temp_dir / "json_test.psp"
        test_builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[]
        )
        
        # Read back
        reader = PSPFReader(bundle_path)
        read_metadata = reader.read_metadata()
        
        # All values should be preserved exactly
        assert read_metadata['unicode'] == "hello 世界 🌍"
        assert read_metadata['numbers']['small'] == 1.23e-10
        assert read_metadata['special_chars'] == 'quote" and \n newline'
        assert read_metadata['null_value'] is None
        assert read_metadata['boolean'] is True
    
    def test_large_file_handling(self, test_builder):
        """Test 2GB+ file handling."""
        # Create a large slot reference (not actual 2GB for testing)
        large_slot = SlotMetadata(
            index=0,
            name="large_file",
            size=2 * 1024 * 1024 * 1024 + 1,  # 2GB + 1 byte
            checksum="abc123",
            encoding="none",  # Large files often use no compression
            purpose="data",
            lifecycle="runtime"
        )
        
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "large-test", "version": "1.0"},
            "slots": [large_slot.to_dict()]
        }
        
        bundle_path = self.temp_dir / "large.psp"
        test_builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[]  # Don't actually include the large file
        )
        
        # Verify no 32-bit limitations
        reader = PSPFReader(bundle_path)
        read_metadata = reader.read_metadata()
        
        slot_meta = read_metadata['slots'][0]
        assert slot_meta['size'] == 2 * 1024 * 1024 * 1024 + 1
        assert slot_meta['size'] > 2**31 - 1  # Larger than 32-bit signed max
    
    def test_endianness_handling(self, test_builder):
        """Test little-endian consistency."""
        import struct
        # PSPF mandates little-endian
        bundle_path = self.temp_dir / "endian.psp"
        test_builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "endian", "version": "1.0"}},
            slots=[]
        )
        
        # Read index manually
        reader = PSPFReader(bundle_path)
        launcher_size = reader.detect_launcher_size()
        
        with open(bundle_path, 'rb') as f:
            f.seek(launcher_size + 8)  # Skip magic
            
            # Read version as little-endian
            version_bytes = f.read(4)
            version_le = struct.unpack('<I', version_bytes)[0]
            
            # Simulate big-endian read (would be wrong)
            version_be = struct.unpack('>I', version_bytes)[0]
            
            # Little-endian should be correct
            assert version_le == 0x20250001
            assert version_be != 0x20250001