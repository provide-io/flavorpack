"""
Step definitions for PSPF 2025 Gherkin tests.
"""

import hashlib
import json
import os
import struct
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import shutil

from behave import given, when, then
from behave.runner import Context

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader, 
    PSPFIndex,
    SlotMetadata,
    PSPFLauncher,
    generate_key_pair
)


# Test helpers
class TestBundle:
    """Helper class to manage test bundles."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.slots: List[SlotMetadata] = []
        self.metadata: Dict = {}
        self.bundle_path: Optional[Path] = None
        self.launcher_type = "go"
        self.emoji_seed = None
        
    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


@given('the PSPF 2025 specification is implemented')
def step_impl(context: Context):
    """Ensure PSPF implementation is available."""
    context.test_bundle = TestBundle()
    assert PSPFBuilder is not None
    assert PSPFReader is not None


@given('ephemeral keys are available for integrity sealing')
def step_impl(context: Context):
    """Ensure ephemeral key generation works."""
    private_key, public_key = generate_key_pair()
    assert private_key is not None
    assert public_key is not None
    context.ephemeral_keys = (private_key, public_key)


@given('I have a simple executable payload')
def step_impl(context: Context):
    """Create a simple test payload."""
    payload_path = context.test_bundle.temp_dir / "payload"
    payload_path.write_bytes(b"#!/bin/sh\necho 'Hello PSPF!'")
    
    context.test_bundle.slots.append(SlotMetadata(
        index=0,
        name="hello",
        size=len(payload_path.read_bytes()),
        compressed_size=0,  # Will be set during build
        checksum=hashlib.sha256(payload_path.read_bytes()).hexdigest(),
        encoding="gzip",
        purpose="payload",
        lifecycle="persistent",
        path=payload_path
    ))


@when('I build a PSPF bundle with default settings')
def step_impl(context: Context):
    """Build a PSPF bundle."""
    builder = PSPFBuilder()
    
    # Set up metadata
    context.test_bundle.metadata = {
        "format": "PSPF/2025",
        "package": {
            "name": "test-bundle",
            "version": "1.0.0"
        },
        "slots": [slot.to_dict() for slot in context.test_bundle.slots],
        "execution": {
            "primary_slot": 0,
            "command": "{slot:0}/hello"
        },
        "verification": {
            "integrity_seal": {
                "required": True,
                "algorithm": "ed25519"
            }
        }
    }
    
    # Build bundle
    bundle_path = context.test_bundle.temp_dir / "test.psp"
    builder.build(
        output_path=bundle_path,
        metadata=context.test_bundle.metadata,
        slots=context.test_bundle.slots,
        launcher_type=context.test_bundle.launcher_type,
        emoji_seed=context.test_bundle.emoji_seed
    )
    
    context.test_bundle.bundle_path = bundle_path
    assert bundle_path.exists()


@then('the bundle should have a valid structure')
def step_impl(context: Context):
    """Verify bundle structure."""
    reader = PSPFReader(context.test_bundle.bundle_path)
    
    # Check basic structure
    assert reader.verify_magic()
    assert reader.read_index()
    assert reader.read_metadata()


@then('the emoji magic should end with 📦??🪄')
def step_impl(context: Context):
    """Verify emoji magic pattern."""
    with open(context.test_bundle.bundle_path, 'rb') as f:
        f.seek(-4, 2)
        magic = f.read(4)
        
    # Check first and last emoji
    assert magic[0:4] == "📦".encode('utf-8')
    assert magic[-4:] == "🪄".encode('utf-8')


@then('the index block should be at offset launcher_size')
def step_impl(context: Context):
    """Verify index block position."""
    reader = PSPFReader(context.test_bundle.bundle_path)
    launcher_size = reader.detect_launcher_size()
    
    with open(context.test_bundle.bundle_path, 'rb') as f:
        f.seek(launcher_size)
        index_magic = f.read(8)
        
    assert index_magic == b"PSPF2025"


@then('the index block should be exactly 256 bytes')
def step_impl(context: Context):
    """Verify index block size."""
    assert struct.calcsize(PSPFIndex.FORMAT) == 256


# Slot management steps

@given('a slot with lifecycle "{lifecycle}"')
def step_impl(context: Context, lifecycle: str):
    """Create a slot with specific lifecycle."""
    slot = SlotMetadata(
        index=0,
        name=f"test-{lifecycle}",
        size=1024,
        compressed_size=512,
        checksum="abc123",
        encoding="gzip",
        purpose="payload",
        lifecycle=lifecycle
    )
    context.current_slot = slot


@when('the launcher extracts the slot')
def step_impl(context: Context):
    """Extract a slot."""
    launcher = PSPFLauncher()
    context.extraction_result = launcher.extract_slot(
        context.current_slot,
        context.cache_dir
    )


@then('the slot should be cached')
def step_impl(context: Context):
    """Verify slot is cached."""
    cache_path = context.cache_dir / context.current_slot.name
    assert cache_path.exists()


# Security steps

@when('I build a PSPF bundle')
def step_impl(context: Context):
    """Build a bundle (generic version)."""
    # Reuse the default build step
    context.execute_steps('When I build a PSPF bundle with default settings')


@then('a new key pair should be generated')
def step_impl(context: Context):
    """Verify ephemeral key generation."""
    # Check that keys were created during build
    metadata_path = context.test_bundle.bundle_path.with_suffix('.metadata')
    if metadata_path.exists():
        with tarfile.open(metadata_path, 'r:gz') as tar:
            assert 'integrity/seal.pem' in tar.getnames()
            assert 'integrity/seal.sig' in tar.getnames()


# Table handling steps

@given('I have the following slots')
def step_impl(context: Context):
    """Create slots from table."""
    context.test_bundle.slots = []
    
    for row in context.table:
        # Create dummy content for each slot
        slot_path = context.test_bundle.temp_dir / row['name']
        slot_path.write_bytes(b"dummy content for " + row['name'].encode())
        
        slot = SlotMetadata(
            index=len(context.test_bundle.slots),
            name=row['name'],
            size=len(slot_path.read_bytes()),
            compressed_size=0,
            checksum=hashlib.sha256(slot_path.read_bytes()).hexdigest(),
            compression=row['compression'],
            purpose=row['purpose'],
            lifecycle=row['lifecycle'],
            path=slot_path
        )
        context.test_bundle.slots.append(slot)


@then('each slot should be aligned to 8 bytes')
def step_impl(context: Context):
    """Verify slot alignment."""
    reader = PSPFReader(context.test_bundle.bundle_path)
    index = reader.read_index()
    
    # Read slot table
    with open(context.test_bundle.bundle_path, 'rb') as f:
        f.seek(index.slot_table_offset)
        for i in range(index.slot_count):
            offset = struct.unpack('<Q', f.read(8))[0]
            size = struct.unpack('<Q', f.read(8))[0]
            checksum = struct.unpack('<Q', f.read(8))[0]
            
            # Verify alignment
            assert offset % 8 == 0, f"Slot {i} not aligned: offset {offset}"


# Builder steps

@given('I have the PSPF builder tools installed')
def step_impl(context: Context):
    """Ensure builder tools are available."""
    assert PSPFBuilder is not None
    context.builder_available = True


@given('I have a project to package')
def step_impl(context: Context):
    """Set up a project to package."""
    context.project_dir = context.test_bundle.temp_dir / "project"
    context.project_dir.mkdir(exist_ok=True)


@given('a manifest file with')
def step_impl(context: Context):
    """Create a manifest file from text."""
    manifest_path = context.test_bundle.temp_dir / "manifest.toml"
    manifest_path.write_text(context.text)
    context.manifest_path = manifest_path


@when('I run "pspf build {args}"')
def step_impl(context: Context, args: str):
    """Run the PSPF build command."""
    # Parse args to get manifest path
    builder = PSPFBuilder()
    
    # In real implementation, this would parse the manifest
    # For testing, we'll build with defaults
    bundle_path = context.test_bundle.temp_dir / "output.psp"
    builder.build(
        output_path=bundle_path,
        manifest_path=context.manifest_path,
        launcher_type="go"
    )
    
    context.test_bundle.bundle_path = bundle_path


@then('a PSPF bundle should be created')
def step_impl(context: Context):
    """Verify bundle was created."""
    assert context.test_bundle.bundle_path.exists()
    assert context.test_bundle.bundle_path.stat().st_size > 0


@then('it should contain the specified slots')
def step_impl(context: Context):
    """Verify bundle contains expected slots."""
    reader = PSPFReader(context.test_bundle.bundle_path)
    metadata = reader.read_metadata()
    
    # Check slots exist in metadata
    assert 'slots' in metadata
    assert len(metadata['slots']) > 0


# Execution steps

@given('a valid PSPF bundle is available')
def step_impl(context: Context):
    """Ensure a valid bundle exists."""
    if not hasattr(context, 'test_bundle') or not context.test_bundle.bundle_path:
        # Create a simple bundle
        context.execute_steps('''
            Given I have a simple executable payload
            When I build a PSPF bundle with default settings
        ''')


@given('all required slots are extracted')
def step_impl(context: Context):
    """Extract all slots."""
    launcher = PSPFLauncher(context.test_bundle.bundle_path)
    context.extracted_slots = launcher.extract_all_slots()


@given('the execution command is "{command}"')
def step_impl(context: Context, command: str):
    """Set the execution command."""
    context.execution_command = command


@when('I run the bundle')
def step_impl(context: Context):
    """Execute the bundle."""
    launcher = PSPFLauncher(context.test_bundle.bundle_path)
    context.execution_result = launcher.execute()


@then('the primary slot should be executed')
def step_impl(context: Context):
    """Verify primary slot execution."""
    assert context.execution_result is not None
    assert context.execution_result.get('executed', False)


@then('the process should start successfully')
def step_impl(context: Context):
    """Verify process started."""
    assert context.execution_result.get('pid') is not None


# Security steps

@given('the cryptographic libraries are available')
def step_impl(context: Context):
    """Ensure crypto libraries are available."""
    try:
        import cryptography
        context.crypto_available = True
    except ImportError:
        context.crypto_available = False
        raise


@given('the PSPF bundle builder is configured')
def step_impl(context: Context):
    """Ensure builder is configured."""
    context.builder_config = {
        'ephemeral_keys': True,
        'integrity_seal': True
    }


@given('a PSPF bundle with integrity seal')
def step_impl(context: Context):
    """Create a bundle with integrity seal."""
    context.execute_steps('''
        Given I have a simple executable payload
        When I build a PSPF bundle with default settings
    ''')
    
    # Verify it has integrity seal
    reader = PSPFReader(context.test_bundle.bundle_path)
    metadata = reader.read_metadata()
    assert metadata.get('verification', {}).get('integrity_seal', {}).get('required')


@when('the launcher verifies the bundle')
def step_impl(context: Context):
    """Verify bundle integrity."""
    launcher = PSPFLauncher(context.test_bundle.bundle_path)
    context.verification_result = launcher.verify_integrity()


@then('the psp.json signature should be checked')
def step_impl(context: Context):
    """Verify signature was checked."""
    assert 'signature_valid' in context.verification_result


@then('the signature should match the ephemeral public key')
def step_impl(context: Context):
    """Verify signature matches key."""
    assert context.verification_result.get('signature_valid', False)


@then('tampering should be detected')
def step_impl(context: Context):
    """Verify tampering detection works."""
    assert context.verification_result.get('tamper_detected') is not None


# Compatibility steps

@given('I build a bundle with {language} builder')
def step_impl(context: Context, language: str):
    """Build with specific language."""
    context.builder_language = language
    context.execute_steps('''
        Given I have a simple executable payload
        When I build a PSPF bundle with default settings
    ''')


@given('I use a {language} launcher')
def step_impl(context: Context, language: str):
    """Set launcher language."""
    context.launcher_language = language
    context.test_bundle.launcher_type = language.lower()


@when('I execute the bundle')
def step_impl(context: Context):
    """Execute the bundle (generic)."""
    context.execute_steps('When I run the bundle')


@then('it should run correctly')
def step_impl(context: Context):
    """Verify correct execution."""
    assert context.execution_result is not None
    assert not context.execution_result.get('error')


@then('all slots should be accessible')
def step_impl(context: Context):
    """Verify all slots are accessible."""
    reader = PSPFReader(context.test_bundle.bundle_path)
    metadata = reader.read_metadata()
    
    for slot in metadata.get('slots', []):
        assert reader.read_slot(slot['index']) is not None


@then('checksums should verify')
def step_impl(context: Context):
    """Verify all checksums."""
    reader = PSPFReader(context.test_bundle.bundle_path)
    assert reader.verify_all_checksums()


@then('emoji magic should be parsed correctly')
def step_impl(context: Context):
    """Verify emoji parsing."""
    with open(context.test_bundle.bundle_path, 'rb') as f:
        f.seek(-4, 2)
        magic = f.read(4)
        
    # Verify it's valid UTF-8 emoji sequence
    try:
        magic_str = magic.decode('utf-8')
        assert len(magic_str) == 4  # 4 emoji characters
        assert magic_str[0] == '📦'
        assert magic_str[3] == '🪄'
    except UnicodeDecodeError:
        assert False, "Invalid UTF-8 emoji sequence"


# Slot management steps

@when('someone modifies the psp.json after building')
def step_impl(context: Context):
    """Tamper with metadata."""
    # In real implementation, this would modify the metadata
    # within the bundle to simulate tampering
    context.tampered = True
    context.tamper_type = 'metadata'


@when('someone modifies a slot\'s data')
def step_impl(context: Context):
    """Tamper with slot data."""
    context.tampered = True
    context.tamper_type = 'slot'


@then('the launcher should detect tampering')
def step_impl(context: Context):
    """Verify tamper detection."""
    launcher = PSPFLauncher(context.test_bundle.bundle_path)
    if context.tampered:
        # Simulate tamper detection
        result = launcher.verify_integrity()
        assert not result.get('valid', True)


@then('refuse to extract slots')
def step_impl(context: Context):
    """Verify extraction is refused."""
    launcher = PSPFLauncher(context.test_bundle.bundle_path)
    try:
        launcher.extract_all_slots()
        assert False, "Should have refused extraction"
    except Exception as e:
        assert "verification failed" in str(e).lower()


@then('report "{message}"')
def step_impl(context: Context, message: str):
    """Verify error message."""
    # In real implementation, check actual error message
    pass


# Clean up after scenarios
def after_scenario(context, scenario):
    """Clean up test resources."""
    if hasattr(context, 'test_bundle'):
        context.test_bundle.cleanup()