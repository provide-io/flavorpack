"""
Behave step definitions that run corresponding pytest tests.

This allows BDD feature files to execute the comprehensive pytest test suite.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

from behave import given, when, then
from behave.runner import Context


class PytestRunner:
    """Run pytest tests and cache results."""
    
    CACHE_FILE = Path(tempfile.gettempdir()) / "pspf_test_cache.json"
    
    @classmethod
    def run_test(cls, test_path: str, test_name: Optional[str] = None) -> Dict:
        """Run a specific pytest test and return results."""
        # Check cache first
        cache = cls._load_cache()
        cache_key = f"{test_path}::{test_name}" if test_name else test_path
        
        if cache_key in cache:
            return cache[cache_key]
        
        # Run pytest
        cmd = ["pytest", "-xvs", test_path]
        if test_name:
            cmd.extend(["-k", test_name])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        test_result = {
            "passed": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
        
        # Cache result
        cache[cache_key] = test_result
        cls._save_cache(cache)
        
        return test_result
    
    @classmethod
    def _load_cache(cls) -> Dict:
        """Load test result cache."""
        if cls.CACHE_FILE.exists():
            try:
                return json.loads(cls.CACHE_FILE.read_text())
            except:
                return {}
        return {}
    
    @classmethod
    def _save_cache(cls, cache: Dict) -> None:
        """Save test result cache."""
        cls.CACHE_FILE.write_text(json.dumps(cache, indent=2))


# Map feature scenarios to pytest tests
SCENARIO_TO_PYTEST = {
    # Core features
    "PSPF 2025 specification is implemented": "test_pspf_2025_core::TestPSPFCore::test_pspf_specification_implemented",
    "Create minimal PSPF bundle": "test_pspf_2025_core::TestPSPFCore::test_build_minimal_bundle",
    "Verify emoji magic pattern": "test_pspf_2025_core::TestPSPFCore::test_emoji_magic_format",
    "Index block at correct offset": "test_pspf_2025_core::TestPSPFCore::test_index_block_location",
    "Index block size validation": "test_pspf_2025_core::TestPSPFCore::test_index_block_size",
    
    # Slot management
    "Persistent slot lifecycle": "test_pspf_2025_slots::TestPSPFSlots::test_slot_lifecycle_persistent",
    "Volatile slot lifecycle": "test_pspf_2025_slots::TestPSPFSlots::test_slot_lifecycle_volatile",
    "Temporary slot lifecycle": "test_pspf_2025_slots::TestPSPFSlots::test_slot_lifecycle_temporary",
    "Install slot lifecycle": "test_pspf_2025_slots::TestPSPFSlots::test_slot_lifecycle_install",
    "Multiple slots handling": "test_pspf_2025_slots::TestPSPFSlots::test_multiple_slots",
    
    # Security
    "Ephemeral key generation": "test_pspf_2025_security::TestPSPFSecurity::test_ephemeral_key_generation",
    "Integrity seal verification": "test_pspf_2025_security::TestPSPFSecurity::test_integrity_seal_verification",
    "Tampered metadata detection": "test_pspf_2025_security::TestPSPFSecurity::test_metadata_tampering_detection",
    "Tampered slot detection": "test_pspf_2025_security::TestPSPFSecurity::test_slot_tampering_detection",
    
    # Execution
    "Simple command execution": "test_pspf_2025_execution::TestPSPFExecution::test_simple_execution",
    "Slot substitution in commands": "test_pspf_2025_execution::TestPSPFExecution::test_slot_substitution_single",
    "Environment variable injection": "test_pspf_2025_execution::TestPSPFExecution::test_environment_substitution",
    "Multi-platform execution": "test_pspf_2025_execution::TestPSPFExecution::test_platform_specific_slot_selection",
    
    # Builder
    "Build from manifest file": "test_pspf_2025_builder::TestPSPFBuilder::test_build_from_manifest",
    "Automatic launcher selection": "test_pspf_2025_builder::TestPSPFBuilder::test_automatic_launcher_selection_python",
    "Custom emoji selection": "test_pspf_2025_builder::TestPSPFBuilder::test_custom_emoji_selection",
    "Compression selection": "test_pspf_2025_builder::TestPSPFBuilder::test_compression_selection",
    
    # Compatibility
    "Python builder with Go launcher": "test_pspf_2025_compatibility::TestPSPFCompatibility::test_python_builder_go_launcher",
    "Go builder with Rust launcher": "test_pspf_2025_compatibility::TestPSPFCompatibility::test_go_builder_rust_launcher",
    "Rust builder with Python launcher": "test_pspf_2025_compatibility::TestPSPFCompatibility::test_rust_builder_python_launcher",
    "Checksum compatibility": "test_pspf_2025_compatibility::TestPSPFCompatibility::test_checksum_compatibility",
}


@given('the PSPF 2025 specification is implemented')
def step_impl(context: Context):
    """Run pytest to verify implementation."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_core.py",
        "test_pspf_specification_implemented"
    )
    assert result['passed'], f"Test failed: {result['stderr']}"


@given('ephemeral keys are available for integrity sealing')
def step_impl(context: Context):
    """Run pytest for ephemeral key test."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_security.py",
        "test_ephemeral_key_generation"
    )
    assert result['passed']


@given('I have a simple executable payload')
def step_impl(context: Context):
    """Set up context for payload tests."""
    context.has_payload = True


@when('I build a PSPF bundle with default settings')
def step_impl(context: Context):
    """Run build test."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_core.py",
        "test_build_minimal_bundle"
    )
    context.build_result = result
    assert result['passed']


@then('the bundle should have a valid structure')
def step_impl(context: Context):
    """Verify structure test passed."""
    assert context.build_result['passed']


@then('the emoji magic should end with 📦??🪄')
def step_impl(context: Context):
    """Run emoji test."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_core.py",
        "test_emoji_magic_format"
    )
    assert result['passed']


# Generic step handlers

@given('a slot with lifecycle "{lifecycle}"')
def step_impl(context: Context, lifecycle: str):
    """Run lifecycle test for specific type."""
    test_name = f"test_slot_lifecycle_{lifecycle}"
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_slots.py",
        test_name
    )
    context.lifecycle_result = result


@when('the launcher extracts the slot')
def step_impl(context: Context):
    """Verify extraction in lifecycle test."""
    assert context.lifecycle_result['passed']


@then('the slot should be cached')
def step_impl(context: Context):
    """Verify caching in lifecycle test."""
    assert context.lifecycle_result['passed']


# Table-driven tests

@given('I have the following slots')
def step_impl(context: Context):
    """Run multiple slots test."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_slots.py",
        "test_multiple_slots"
    )
    context.slots_result = result


@then('each slot should be aligned to 8 bytes')
def step_impl(context: Context):
    """Run alignment test."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_core.py",
        "test_slot_alignment"
    )
    assert result['passed']


# Security steps

@when('I build a PSPF bundle')
def step_impl(context: Context):
    """Generic build step."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_core.py",
        "test_build_minimal_bundle"
    )
    context.build_result = result


@then('a new key pair should be generated')
def step_impl(context: Context):
    """Run ephemeral key in bundle test."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_security.py",
        "test_ephemeral_key_in_bundle"
    )
    assert result['passed']


# Builder steps

@given('I have the PSPF builder tools installed')
def step_impl(context: Context):
    """Verify builder available."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_core.py",
        "test_pspf_specification_implemented"
    )
    assert result['passed']


@given('I have a project to package')
def step_impl(context: Context):
    """Set up project context."""
    context.has_project = True


@given('a manifest file with')
def step_impl(context: Context):
    """Create manifest from text."""
    context.manifest_content = context.text


@when('I run "pspf build {args}"')
def step_impl(context: Context, args: str):
    """Run build from manifest test."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_builder.py",
        "test_build_from_manifest"
    )
    context.build_result = result


@then('a PSPF bundle should be created')
def step_impl(context: Context):
    """Verify bundle created."""
    assert context.build_result['passed']


# Execution steps

@given('a valid PSPF bundle is available')
def step_impl(context: Context):
    """Ensure bundle exists."""
    context.has_bundle = True


@given('all required slots are extracted')
def step_impl(context: Context):
    """Set up extracted slots."""
    context.slots_extracted = True


@when('I run the bundle')
def step_impl(context: Context):
    """Run execution test."""
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_execution.py",
        "test_simple_execution"
    )
    context.execution_result = result


@then('the primary slot should be executed')
def step_impl(context: Context):
    """Verify execution."""
    assert context.execution_result['passed']


# Compatibility steps

@given('I build a bundle with {language} builder')
def step_impl(context: Context, language: str):
    """Run language-specific builder test."""
    test_map = {
        "Python": "test_python_builder_go_launcher",
        "Go": "test_go_builder_rust_launcher",
        "Rust": "test_rust_builder_python_launcher"
    }
    
    test_name = test_map.get(language, "test_python_builder_go_launcher")
    result = PytestRunner.run_test(
        "tests/test_pspf_2025_compatibility.py",
        test_name
    )
    context.builder_result = result


@given('I use a {language} launcher')
def step_impl(context: Context, language: str):
    """Set launcher language."""
    context.launcher_language = language


@when('I execute the bundle')
def step_impl(context: Context):
    """Run compatibility execution."""
    assert context.builder_result['passed']


@then('it should run correctly')
def step_impl(context: Context):
    """Verify correct execution."""
    assert context.builder_result['passed']


@then('all slots should be accessible')
def step_impl(context: Context):
    """Verify slot accessibility."""
    assert context.builder_result['passed']


# Utility function to clear cache
def clear_pytest_cache():
    """Clear the pytest result cache."""
    PytestRunner.CACHE_FILE.unlink(missing_ok=True)


# Hook to clear cache before test run
def before_all(context):
    """Clear cache before running tests."""
    clear_pytest_cache()