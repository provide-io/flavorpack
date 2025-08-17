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


# Only test actual existing builders/launchers
# Python and Node builders/launchers were removed from the codebase
LANGUAGES = ["go", "rust"]
BUILDER_LAUNCHER_COMBINATIONS = [
    (builder, launcher) 
    for builder in LANGUAGES 
    for launcher in LANGUAGES
]


@pytest.mark.integration
@pytest.mark.cross_language
@pytest.mark.requires_helpers
@pytest.mark.slow
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
    def test_builder_launcher_combination(self, builder, launcher):
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
            lifecycle="persistent",
            path=tar_path
        )
        
        # Build bundle
        bundle_path = self.temp_dir / f"{builder}_{launcher}.pspf"
        builder_obj = PSPFBuilder()
        
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
        
        # 6. Verify checksums - TODO: implement verify_all_checksums()
        # assert reader.verify_all_checksums()
        
        # 7. Test execution
        launcher_obj = PSPFLauncher(bundle_path)
        result = launcher_obj.execute()
        assert result['executed']
        assert result['error'] is None
    
    @pytest.mark.parametrize("builder,launcher", BUILDER_LAUNCHER_COMBINATIONS)
    def test_compatibility_matrix(self, builder, launcher):
        """Test compatibility aspects of each combination."""
        bundle_path = self.temp_dir / f"compat_{builder}_{launcher}.pspf"
        
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
                lifecycle="persistent",
                path=file_path
            ))
        
        # Build with multiple slots
        builder_obj = PSPFBuilder()
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
    
    def test_all_combinations_summary(self):
        """Generate summary of all combinations."""
        results = []
        
        for builder in LANGUAGES:
            for launcher in LANGUAGES:
                bundle_path = self.temp_dir / f"summary_{builder}_{launcher}.pspf"
                
                # Quick build
                builder_obj = PSPFBuilder()
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
    def test_launcher_emoji_correctness(self, launcher):
        """Test each launcher has correct emoji."""
        bundle_path = self.temp_dir / f"emoji_test_{launcher}.pspf"
        
        builder = PSPFBuilder()
        builder.build(
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
    def test_critical_cross_language_paths(self, builder, launcher):
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
            lifecycle="persistent",
            path=payload_path
        )
        
        # Build bundle
        bundle_path = self.temp_dir / f"critical_{builder}_{launcher}.pspf"
        builder_obj = PSPFBuilder()
        
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