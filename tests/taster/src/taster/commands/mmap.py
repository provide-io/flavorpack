#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import mmap
import os
from pathlib import Path
import resource
import sys
import tracemalloc

import click

# Try to import psutil for more detailed memory info
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def check_mmap_support() -> bool | None:
    """Check if mmap is supported on this system."""
    try:
        # Create a small test file
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test" * 1024)
            f.flush()

            # Try to mmap it
            with open(f.name, "r+b") as test_file, mmap.mmap(test_file.fileno(), 0) as m:
                # Read a byte to ensure it works
                _ = m[0]

            # Cleanup
            Path(f.name).unlink()
            return True
    except Exception:
        return False


def detect_bundle_mmap():
    """Detect if the current bundle is memory-mapped."""
    indicators = []

    # Check 1: Look for PSPF file descriptor
    bundle_path = sys.argv[0] if sys.argv[0].endswith(".psp") else None
    if bundle_path and Path(bundle_path).exists():
        try:
            # Check if file is currently open by process
            if HAS_PSUTIL:
                process = psutil.Process()
                for f in process.open_files():
                    if bundle_path in f.path:
                        indicators.append(f"📂 Bundle file is open: {f.path}")

                # Check memory maps
                for mmap_region in process.memory_maps():
                    if bundle_path in mmap_region.path:
                        indicators.append(f"🗺️ Bundle is memory-mapped: {mmap_region.path}")
                        indicators.append(f"  • Size: {mmap_region.rss / 1024 / 1024:.2f} MB")
                        indicators.append(f"  • Permissions: {mmap_region.perms}")
        except Exception as e:
            indicators.append(f"⚠️ Could not check process info: {e}")

    # Check 2: Memory usage patterns
    tracemalloc.start()
    current, _peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Low traced memory with large bundle suggests mmap
    if bundle_path:
        bundle_size = Path(bundle_path).stat().st_size
        if bundle_size > 1024 * 1024:  # > 1MB
            ratio = current / bundle_size
            if ratio < 0.1:  # Less than 10% in heap
                indicators.append(f"💾 Low heap usage ({ratio:.1%}) suggests mmap")

    # Check 3: Resource usage
    usage = resource.getrusage(resource.RUSAGE_SELF)
    indicators.append(f"📊 Page faults: {usage.ru_minflt} minor, {usage.ru_majflt} major")

    # Check 4: Backend detection via environment
    if os.environ.get("FLAVOR_BACKEND") == "mmap":
        pass

    return indicators


def test_mmap_operations():
    """Test various mmap operations."""
    results = []

    # Test 1: Can we use mmap?
    if check_mmap_support():
        pass
    else:
        results.append("❌ mmap is not supported")
        return results

    # Test 2: Test large file mapping
    try:
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as f:
            # Create a 10MB file
            size = 10 * 1024 * 1024
            f.write(b"\x00" * size)
            f.flush()

            # Map it
            with open(f.name, "r+b") as test_file:
                with mmap.mmap(test_file.fileno(), 0, access=mmap.ACCESS_READ) as m:
                    # Test random access
                    _ = m[0]
                    _ = m[size // 2]
                    _ = m[-1]

            Path(f.name).unlink()
    except Exception as e:
        results.append(f"❌ Large file mapping failed: {e}")

    # Test 3: Check if we're using the Python mmap backend
    try:
        from flavor.psp.format_2025.backends import MMapBackend

        # Try to create one
        MMapBackend()
    except ImportError:
        results.append("⚠️ MMapBackend not available (flavor not installed?)")
    except Exception as e:
        results.append(f"❌ MMapBackend error: {e}")

    return results


@click.command("mmap")
def mmap_command() -> None:
    """Test and verify memory-mapped I/O usage."""
    click.echo("🗺️ Memory-Mapped I/O Detection")
    click.echo("=" * 50)

    # System support
    for result in test_mmap_operations():
        click.echo(f"  {result}")

    # Bundle detection
    click.echo("\n🔍 Bundle Analysis:")
    indicators = detect_bundle_mmap()
    if indicators:
        for indicator in indicators:
            click.echo(f"  {indicator}")
    else:
        click.echo("  ⚠️ No mmap indicators detected")

    # Memory info
    if HAS_PSUTIL:
        click.echo("\n💾 Memory Usage:")
        process = psutil.Process()
        mem_info = process.memory_info()
        click.echo(f"  • RSS: {mem_info.rss / 1024 / 1024:.2f} MB")
        click.echo(f"  • VMS: {mem_info.vms / 1024 / 1024:.2f} MB")

        try:
            mem_percent = process.memory_percent()
            click.echo(f"  • Percent: {mem_percent:.2f}%")
        except (AttributeError, psutil.Error):
            pass

    # Conclusion
    click.echo("\n📊 Summary:")
    if any("memory-mapped" in str(i).lower() for i in indicators):
        pass
    elif bundle_path := (sys.argv[0] if sys.argv[0].endswith(".psp") else None):
        if Path(bundle_path).exists():
            click.echo("  ⚠️ Bundle exists but mmap usage unclear")
        else:
            click.echo("  ❓ Not running from a bundle")
    else:
        click.echo("  ❓ Cannot determine mmap status")


if __name__ == "__main__":
    mmap_command()

# 🌶️📦🔚
