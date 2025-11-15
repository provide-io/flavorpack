#!/usr/bin/env python3
"""
Run BDD tests by delegating to pytest.

This allows behave feature files to drive pytest test execution.
"""

import subprocess
import sys
from pathlib import Path


def run_pytest_for_feature(feature_name: str) -> int:
    """Run pytest tests corresponding to a feature file."""
    
    # Map feature files to pytest test modules
    feature_to_pytest = {
        "pspf_core": ["test_pspf_2025_core.py"],
        "slot_management": ["test_pspf_2025_slots.py"],
        "security": ["test_pspf_2025_security.py"],
        "execution": ["test_pspf_2025_execution.py"],
        "builder": ["test_pspf_2025_builder.py"],
        "compatibility": ["test_pspf_2025_compatibility.py"],
    }
    
    # Get test files for feature
    test_files = feature_to_pytest.get(feature_name.replace(".feature", ""), [])
    
    if not test_files:
        print(f"No pytest tests mapped for feature: {feature_name}")
        return 1
    
    # Run pytest
    test_dir = Path(__file__).parent.parent.parent  # tests/
    cmd = ["pytest", "-xvs"]
    
    for test_file in test_files:
        cmd.append(str(test_dir / test_file))
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Run specific feature
        feature = sys.argv[1]
        return run_pytest_for_feature(feature)
    else:
        # Run all PSPF 2025 tests
        test_dir = Path(__file__).parent.parent.parent
        cmd = [
            "pytest", "-xvs",
            str(test_dir / "test_pspf_2025_core.py"),
            str(test_dir / "test_pspf_2025_slots.py"),
            str(test_dir / "test_pspf_2025_security.py"),
            str(test_dir / "test_pspf_2025_execution.py"),
            str(test_dir / "test_pspf_2025_builder.py"),
            str(test_dir / "test_pspf_2025_compatibility.py"),
        ]
        
        print(f"Running all PSPF 2025 tests: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())