#!/usr/bin/env python3
"""Test environment variable filtering and whitelisting."""
import os
import sys

print("🌍 Environment Variable Test")
print("=" * 50)

# Get all environment variables
env_vars = dict(os.environ)
total = len(env_vars)

# Check for variables that should be removed by whitelist
unwanted_prefixes = ["DEBUG_", "TEMP_", "TEST_", "XDG_", "ITERM_", "TERM_SESSION"]
unwanted_found = []
for key in env_vars:
    for prefix in unwanted_prefixes:
        if key.startswith(prefix):
            unwanted_found.append(key)
            break

# Check for variables that MUST exist
required_vars = {
    "PATH": "PATH" in env_vars,
    "HOME": "HOME" in env_vars,
    "USER": "USER" in env_vars,
    "FLAVOR_WORKENV": "FLAVOR_WORKENV" in env_vars,
    "FLAVOR_COMMAND_NAME": "FLAVOR_COMMAND_NAME" in env_vars,
}

# Check for whitelisted variables
expected_prefixes = ["FLAVOR_", "PATH", "HOME", "USER", "LANG", "LC_", "TERM"]
unexpected = []
for key in env_vars:
    is_expected = False
    for prefix in expected_prefixes:
        if key.startswith(prefix) or key in ["PATH", "HOME", "USER", "LANG", "TERM"]:
            is_expected = True
            break
    if not is_expected:
        unexpected.append(key)

print(f"📊 Total environment variables: {total}")
print(f"\n✅ Required variables:")
for var, present in required_vars.items():
    status = "✓" if present else "✗"
    value = env_vars.get(var, "NOT SET")[:50] if present else "NOT SET"
    print(f"  {status} {var}: {value}")

if unwanted_found:
    print(f"\n⚠️ Unwanted variables found (should be filtered): {len(unwanted_found)}")
    for var in unwanted_found[:5]:
        print(f"  - {var}")
    if len(unwanted_found) > 5:
        print(f"  ... and {len(unwanted_found) - 5} more")
else:
    print(f"\n✅ No unwanted variables found (good filtering!)")

if unexpected:
    print(f"\n⚠️ Unexpected variables (not in whitelist): {len(unexpected)}")
    for var in unexpected[:5]:
        print(f"  - {var}")
    if len(unexpected) > 5:
        print(f"  ... and {len(unexpected) - 5} more")

# Exit code based on test results
all_required = all(required_vars.values())
no_unwanted = len(unwanted_found) == 0

if all_required and no_unwanted:
    print("\n✅ Environment test PASSED")
    sys.exit(0)
else:
    print("\n❌ Environment test FAILED")
    sys.exit(1)