#!/usr/bin/env python3
"""
Memray analysis utilities.

Provides post-run analysis for memray stress test binaries:
- Parse .bin files and extract allocation statistics
- Identify top allocators and hotspots
- Generate comparison reports across runs
- Detect memory regressions vs baseline
"""

from pathlib import Path
import subprocess
from typing import Any


def parse_memray_stats(binfile: Path) -> dict[str, Any]:
    """
    Parse memray stats output from a binary file.

    Args:
        binfile: Path to memray .bin file

    Returns:
        Dictionary with parsed allocation statistics
    """
    try:
        result = subprocess.run(
            ["memray", "stats", str(binfile)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"error": f"memray stats failed: {result.stderr}"}

        lines = result.stdout.split("\n")
        stats: dict[str, Any] = {
            "total_lines": len(lines),
            "output": result.stdout,
        }

        for line in lines:
            if "Peak" in line or "peak" in line:
                stats["peak_memory_line"] = line.strip()

        return stats
    except subprocess.TimeoutExpired:
        return {"error": "memray stats timed out"}
    except Exception as e:
        return {"error": str(e)}


def generate_flamegraph(binfile: Path, output_html: Path | None = None) -> bool:
    """
    Generate flamegraph from memray binary file.

    Args:
        binfile: Path to memray .bin file
        output_html: Optional output path for HTML file

    Returns:
        True if successful, False otherwise
    """
    try:
        if output_html is None:
            output_html = binfile.parent / f"{binfile.stem}_flamegraph.html"

        result = subprocess.run(
            ["memray", "flamegraph", str(binfile), "-o", str(output_html)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print(f"  Generated: {output_html.name}")
            return True
        else:
            print(f"  Failed: {result.stderr[:100]}")
            return False
    except subprocess.TimeoutExpired:
        print("  Flamegraph generation timed out")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def compare_allocations(baseline: Path, current: Path) -> dict[str, Any]:
    """
    Compare allocation patterns between baseline and current runs.

    Args:
        baseline: Path to baseline memray .bin file
        current: Path to current memray .bin file

    Returns:
        Dictionary with comparison results
    """
    baseline_stats = parse_memray_stats(baseline)
    current_stats = parse_memray_stats(current)

    comparison: dict[str, Any] = {
        "baseline_file": str(baseline),
        "current_file": str(current),
        "baseline_stats": baseline_stats,
        "current_stats": current_stats,
        "regression_detected": False,
        "details": "",
    }

    baseline_size = baseline.stat().st_size
    current_size = current.stat().st_size

    size_increase = (
        ((current_size - baseline_size) / baseline_size * 100) if baseline_size > 0 else 0
    )

    if size_increase > 10:  # More than 10% increase
        comparison["regression_detected"] = True
        comparison["details"] = f"Memory usage increased by {size_increase:.1f}%"

    return comparison


def generate_analysis_report(output_dir: Path) -> str:
    """
    Generate comprehensive analysis report from all stress test binaries.

    Args:
        output_dir: Directory containing memray .bin files

    Returns:
        Formatted analysis report as string
    """
    binfiles = sorted(output_dir.glob("memray_*.bin"))

    if not binfiles:
        return "No memray binary files found in output directory"

    report_lines = [
        "# MEMRAY ANALYSIS REPORT",
        "",
        f"Output directory: `{output_dir}`",
        "",
        "## Summary",
        "",
    ]

    for binfile in binfiles:
        script_name = binfile.stem
        stats = parse_memray_stats(binfile)

        report_lines.append(f"### {script_name}")
        report_lines.append("")

        if "error" in stats:
            report_lines.append(f"- **Error**: {stats['error']}")
        else:
            report_lines.append(f"- **File size**: {binfile.stat().st_size:,} bytes")
            if "peak_memory_line" in stats:
                report_lines.append(f"- {stats['peak_memory_line']}")

        report_lines.append("")

    report_lines.extend([
        "## Key Patterns to Watch",
        "",
        "1. **Operation chain packing** (`memray_operations_stress`):",
        "   - `pack_operations()` bit-shifting allocation",
        "   - `unpack_operations()` list creation per call",
        "   - Watch for list allocation overhead in tight loops",
        "",
        "2. **XOR encode/decode** (`memray_xor_stress`):",
        "   - Per-byte allocation pattern across payload sizes",
        "   - Bytes object creation per encode/decode call",
        "   - Memory scaling: 1KB vs 1MB payload cost ratio",
        "",
        "3. **Slot descriptor serialization** (`memray_slot_descriptor_stress`):",
        "   - `struct.pack()` / `struct.unpack()` allocation",
        "   - attrs class instantiation overhead in `unpack()`",
        "   - Binary buffer allocation per pack cycle",
        "",
        "4. **Builder pipeline** (`memray_builder_stress`):",
        "   - Immutable builder chain (each method creates new PSPFBuilder)",
        "   - Temp file creation for slot data",
        "   - Metadata assembly + gzip compression allocation",
        "   - Key generation per build cycle",
        "",
        "5. **Reader pipeline** (`memray_reader_stress`):",
        "   - Backend creation/teardown per read cycle",
        "   - Index parsing and checksum verification",
        "   - Slot descriptor deserialization",
        "   - Gzip decompression allocation for slot data",
        "",
        "## Next Steps",
        "",
        "```bash",
        "# Generate flamegraphs for visual inspection",
        "uv run python scripts/memray/memray_analysis.py",
        "",
        "# Compare against baseline after optimization",
        "# (save current as baseline first, then re-run after changes)",
        "```",
        "",
    ])

    return "\n".join(report_lines)


def main() -> None:
    """Run analysis on all memray binaries in output directory."""
    output_dir = Path("memray-output")

    if not output_dir.exists():
        print("memray-output directory not found. Run: uv run python scripts/memray/run_memray_stress.py")
        return

    print("Analyzing memray results...")
    print()

    # Generate flamegraphs
    for binfile in sorted(output_dir.glob("memray_*.bin")):
        print(f"Processing {binfile.name}...")
        generate_flamegraph(binfile)

    # Generate report
    report = generate_analysis_report(output_dir)
    report_file = output_dir / "ANALYSIS.md"
    report_file.write_text(report)

    print()
    print(f"Analysis report: {report_file}")
    print()
    print(report)


if __name__ == "__main__":
    main()
