#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Inspect memory-mapped I/O capabilities for the running bundle."""

from __future__ import annotations

import contextlib
import mmap
import os
from pathlib import Path
import sys

if sys.platform != "win32":
    import resource  # Unix-only
import tempfile
import tracemalloc

import click
from provide.foundation.console import pout

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:  # pragma: no cover - optional dependency
    psutil = None  # ty: ignore[invalid-assignment]
    HAS_PSUTIL = False


@click.command("mmap")
def mmap_command() -> None:
    """Test and verify memory-mapped I/O usage."""
    pout("🗺️ Memory-Mapped I/O Detection")
    pout("=" * 50)

    for result in test_mmap_operations():
        pout(f"  {result}")

    bundle_path = _bundle_path_from_argv()
    pout("\n🔍 Bundle Analysis:")
    indicators = detect_bundle_mmap(bundle_path)
    if indicators:
        for indicator in indicators:
            pout(f"  {indicator}")
    else:
        pout("  ⚠️ No mmap indicators detected")

    if HAS_PSUTIL:
        pout("\n💾 Memory Usage:")
        process = psutil.Process()
        mem_info = process.memory_info()
        pout(f"  • RSS: {mem_info.rss / 1024 / 1024:.2f} MB")
        pout(f"  • VMS: {mem_info.vms / 1024 / 1024:.2f} MB")
        with contextlib.suppress(psutil.Error, AttributeError):
            pout(f"  • Percent: {process.memory_percent():.2f}%")

    pout("\n📊 Summary:")
    if any("memory-mapped" in indicator.lower() for indicator in indicators):
        pout("  ✅ Bundle appears to be memory-mapped")
    elif bundle_path and bundle_path.exists():
        pout("  ⚠️ Bundle exists but mmap usage is unclear")
    else:
        pout("  ❓ Not running from a bundle or insufficient evidence")


def test_mmap_operations() -> list[str]:
    """Run a suite of mmap capability checks."""
    results = []
    if not _check_basic_mmap():
        results.append("❌ mmap is not supported on this platform")
        return results

    error = _test_large_file_mapping()
    if error:
        results.append(error)
    else:
        results.append("✅ Large file mapping succeeded")

    backend_error = _test_backend_availability()
    if backend_error:
        results.append(backend_error)
    else:
        results.append("✅ PSPF MMapBackend available")

    return results


def detect_bundle_mmap(bundle_path: Path | None) -> list[str]:
    """Collect indicators that the current process is memory-mapping the bundle."""
    indicators: list[str] = []
    if bundle_path:
        indicators.extend(_psutil_bundle_indicators(bundle_path))
        indicators.extend(_memory_ratio_indicators(bundle_path))

    indicators.append(_resource_usage_indicator())
    env_backend = os.environ.get("FLAVOR_BACKEND")
    if env_backend == "mmap":
        indicators.append("🧩 FLAVOR_BACKEND reports mmap usage")
    return [indicator for indicator in indicators if indicator]


def _check_basic_mmap() -> bool:
    """Verify that mmap works for a small file."""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"test" * 1024)
            handle.flush()
            path = Path(handle.name)

        with path.open("r+b") as test_file, mmap.mmap(test_file.fileno(), 0) as mm:
            _ = mm[0]
        path.unlink(missing_ok=True)
    except Exception:
        return False
    return True


def _test_large_file_mapping() -> str | None:
    """Create and map a larger file to test kernel limits."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as handle:
            path = Path(handle.name)
            size = 10 * 1024 * 1024
            handle.write(b"\x00" * size)
            handle.flush()

        with path.open("r+b") as test_file, mmap.mmap(test_file.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            _ = mm[0]
            _ = mm[size // 2]
            _ = mm[-1]
    except Exception as exc:
        return f"❌ Large file mapping failed: {exc}"
    finally:
        path.unlink(missing_ok=True)
    return None


def _test_backend_availability() -> str | None:
    """Attempt to construct the PSPF mmap backend."""
    try:
        from flavor.psp.format_2025.backends import MMapBackend

        MMapBackend()
    except ImportError:
        return "⚠️ MMapBackend not available (flavor not installed?)"
    except Exception as exc:
        return f"❌ MMapBackend error: {exc}"
    return None


def _bundle_path_from_argv() -> Path | None:
    """Return the bundle path if running from a .psp file."""
    argv0 = Path(sys.argv[0])
    if argv0.suffix == ".psp" and argv0.exists():
        return argv0
    return None


def _psutil_bundle_indicators(bundle_path: Path) -> list[str]:
    """Use psutil (if available) to determine mmap usage."""
    if not HAS_PSUTIL:
        return []

    indicators: list[str] = []
    process = psutil.Process()
    with contextlib.suppress(psutil.Error):
        for handle in process.open_files():
            if bundle_path.samefile(handle.path):
                indicators.append(f"📂 Bundle file is open: {handle.path}")

    with contextlib.suppress(psutil.Error):
        for mmap_region in process.memory_maps():  # ty: ignore[unresolved-attribute]
            if bundle_path.name in mmap_region.path:
                indicators.append(f"🗺️ Bundle is memory-mapped: {mmap_region.path}")
                indicators.append(f"  • Size: {mmap_region.rss / 1024 / 1024:.2f} MB")
                perms = getattr(mmap_region, "perms", "N/A")
                indicators.append(f"  • Permissions: {perms}")

    return indicators


def _memory_ratio_indicators(bundle_path: Path) -> list[str]:
    """Compare traced heap vs bundle size to infer mmap usage."""
    tracemalloc.start()
    current, _peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    bundle_size = bundle_path.stat().st_size
    if bundle_size <= 0:
        return []

    ratio = current / bundle_size
    if ratio < 0.1:
        return [f"💾 Low heap usage ({ratio:.1%}) suggests mmap"]
    return []


def _resource_usage_indicator() -> str:
    """Report page-fault counts as a lightweight signal."""
    if sys.platform == "win32":
        return "📊 Page faults: N/A (not available on Windows)"
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return f"📊 Page faults: {usage.ru_minflt} minor, {usage.ru_majflt} major"


if __name__ == "__main__":
    mmap_command()


# 🌶️📦🔚
