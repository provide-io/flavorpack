#!/usr/bin/env python3
"""
Windows PE Binary Analysis Script

Analyzes and compares PE binaries to identify structure differences
that might cause Windows PE loader rejection.

Usage:
    python analyze_pe_binaries.py <working_binary> <failing_binary> <output_file>
"""

import json
from pathlib import Path
import sys
from typing import Any

DATA_DIRECTORY_NAMES = [
    "Export Table",
    "Import Table",
    "Resource Table",
    "Exception Table",
    "Certificate Table",
    "Base Relocation Table",
    "Debug",
    "Architecture",
    "Global Ptr",
    "TLS Table",
    "Load Config Table",
    "Bound Import",
    "IAT",
    "Delay Import Descriptor",
    "COM+ Runtime Header",
    "Reserved",
]

AnalysisDict = dict[str, Any]
SectionInfo = dict[str, str]
DirectoryInfo = dict[str, Any]


def _ensure_pefile_module() -> Any:
    """Ensure pefile is available and return the module."""
    try:
        import pefile  # type: ignore
    except ImportError:  # pragma: no cover - best-effort installer for script usage
        print("ERROR: pefile library not installed. Installing...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "pefile", "-q"])
        import pefile  # type: ignore

    return pefile


def _analyze_sections(pe: Any) -> list[SectionInfo]:
    """Return normalized section information."""
    sections: list[SectionInfo] = []
    for section in pe.sections:
        section_info: SectionInfo = {
            "name": section.Name.decode("utf-8", errors="ignore").rstrip("\0"),
            "virtual_address": f"0x{section.VirtualAddress:x}",
            "virtual_size": f"0x{section.Misc_VirtualSize:x}",
            "pointer_to_raw_data": f"0x{section.PointerToRawData:x}",
            "size_of_raw_data": f"0x{section.SizeOfRawData:x}",
        }
        sections.append(section_info)
    return sections


def _analyze_data_directories(pe: Any) -> list[DirectoryInfo]:
    """Return the PE data directory information."""
    directories: list[DirectoryInfo] = []
    if not hasattr(pe, "OPTIONAL_HEADER") or not hasattr(pe.OPTIONAL_HEADER, "DATA_DIRECTORY"):
        return directories

    for i, entry in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
        dir_info: DirectoryInfo = {
            "index": i,
            "name": DATA_DIRECTORY_NAMES[i] if i < len(DATA_DIRECTORY_NAMES) else f"Directory {i}",
            "virtual_address": f"0x{entry.VirtualAddress:x}",
            "size": f"0x{entry.Size:x}",
            "has_data": entry.Size > 0,
        }

        # Special handling for directories with absolute offsets
        if i == 4:  # Certificate Table
            dir_info["uses_absolute_offsets"] = True
            if entry.VirtualAddress > 0:
                dir_info["absolute_offset"] = f"0x{entry.VirtualAddress:x}"

        directories.append(dir_info)
    return directories


def _annotate_special_directories(directories: list[DirectoryInfo]) -> None:
    """Add explanatory notes for directories that typically use absolute offsets."""
    annotations = {
        10: "Load Config present - may have absolute offsets",
        6: "Debug Directory present - PointerToRawData fields are absolute offsets",
        9: "TLS Directory present - may have callback offsets",
    }
    for index, note in annotations.items():
        if index < len(directories):
            directory = directories[index]
            if directory.get("has_data"):
                directory["note"] = note


def analyze_pe_binary(filepath: str | Path) -> AnalysisDict:
    """Analyze a PE binary and extract structure information."""
    pefile = _ensure_pefile_module()
    path = Path(filepath)
    pe = pefile.PE(str(path))

    sections = _analyze_sections(pe)
    data_directories = _analyze_data_directories(pe)
    _annotate_special_directories(data_directories)

    analysis: AnalysisDict = {
        "file": str(path),
        "size": path.stat().st_size,
        "is_pe": pe.DOS_HEADER.e_magic == 0x5A4D,  # 'MZ'
        "pe_offset": pe.DOS_HEADER.e_lfanew,
        "machine": f"0x{pe.FILE_HEADER.Machine:04x}",
        "num_sections": pe.FILE_HEADER.NumberOfSections,
        "sections": sections,
        "data_directories": data_directories,
        "characteristics": {
            "executable": bool(pe.FILE_HEADER.Characteristics & 0x0002),
            "32bit": not bool(pe.OPTIONAL_HEADER.Magic & 0x0001),  # 0x10b = PE32, 0x20b = PE32+
        },
    }
    return analysis


def compare_analyses(working: AnalysisDict, failing: AnalysisDict) -> AnalysisDict:
    """Compare two PE analyses to find differences."""
    comparison = {
        "differences": [],
        "working": working,
        "failing": failing,
    }

    # Compare PE offset
    if working["pe_offset"] != failing["pe_offset"]:
        comparison["differences"].append(
            {
                "type": "pe_offset",
                "working": f"0x{working['pe_offset']:x}",
                "failing": f"0x{failing['pe_offset']:x}",
            }
        )

    # Compare sections
    if working["num_sections"] != failing["num_sections"]:
        comparison["differences"].append(
            {
                "type": "section_count",
                "working": working["num_sections"],
                "failing": failing["num_sections"],
            }
        )

    # Compare section offsets
    for i, (w_sec, f_sec) in enumerate(zip(working["sections"], failing["sections"], strict=False)):
        if w_sec["pointer_to_raw_data"] != f_sec["pointer_to_raw_data"]:
            comparison["differences"].append(
                {
                    "type": "section_offset",
                    "section": i,
                    "section_name": w_sec["name"],
                    "working": w_sec["pointer_to_raw_data"],
                    "failing": f_sec["pointer_to_raw_data"],
                }
            )

    # Compare data directories
    for i, (w_dir, f_dir) in enumerate(
        zip(working["data_directories"], failing["data_directories"], strict=False)
    ):
        if w_dir["virtual_address"] != f_dir["virtual_address"] or w_dir["size"] != f_dir["size"]:
            comparison["differences"].append(
                {
                    "type": "data_directory",
                    "index": i,
                    "name": w_dir["name"],
                    "working": {"va": w_dir["virtual_address"], "size": w_dir["size"]},
                    "failing": {"va": f_dir["virtual_address"], "size": f_dir["size"]},
                }
            )

    return comparison


def main() -> None:
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <working_binary> <failing_binary> <output_file>")
        sys.exit(1)

    working_path = sys.argv[1]
    failing_path = sys.argv[2]
    output_path = Path(sys.argv[3])

    print(f"Analyzing working binary: {working_path}")
    working = analyze_pe_binary(working_path)

    print(f"Analyzing failing binary: {failing_path}")
    failing = analyze_pe_binary(failing_path)

    print("Comparing binaries...")
    comparison = compare_analyses(working, failing)

    # Generate text report
    report_lines = [
        "# Windows PE Binary Analysis Report",
        "",
        "## Working Binary (Rust+Rust)",
        f"File: {working['file']}",
        f"Size: {working['size']} bytes",
        f"PE Offset: {working['pe_offset']} (0x{working['pe_offset']:x})",
        f"Sections: {working['num_sections']}",
        f"Machine Type: {working['machine']}",
        "",
        "### Sections:",
        *[
            f"  {i}: {s['name']:8} VA=0x{s['virtual_address'].replace('0x', ''):>8} PointerToRaw=0x{s['pointer_to_raw_data'].replace('0x', ''):>8}"
            for i, s in enumerate(working["sections"])
        ],
        "",
        "### Data Directories (with data):",
        *[
            f"  [{d['index']:2}] {d['name']:25} VA=0x{d['virtual_address'].replace('0x', ''):>8} Size={d['size']}"
            for d in working["data_directories"]
            if d["has_data"]
        ],
        "",
        "",
        "## Failing Binary (Rust+Go)",
        f"File: {failing['file']}",
        f"Size: {failing['size']} bytes",
        f"PE Offset: {failing['pe_offset']} (0x{failing['pe_offset']:x})",
        f"Sections: {failing['num_sections']}",
        f"Machine Type: {failing['machine']}",
        "",
        "### Sections:",
        *[
            f"  {i}: {s['name']:8} VA=0x{s['virtual_address'].replace('0x', ''):>8} PointerToRaw=0x{s['pointer_to_raw_data'].replace('0x', ''):>8}"
            for i, s in enumerate(failing["sections"])
        ],
        "",
        "### Data Directories (with data):",
        *[
            f"  [{d['index']:2}] {d['name']:25} VA=0x{d['virtual_address'].replace('0x', ''):>8} Size={d['size']}"
            for d in failing["data_directories"]
            if d["has_data"]
        ],
        "",
        "",
        "## Comparison",
        f"Found {len(comparison['differences'])} structural differences:",
        "",
        *[f"  - {d}" for d in comparison["differences"]],
    ]

    report_text = "\n".join(report_lines)

    # Save both JSON and text reports
    output_text_path = output_path.with_suffix(".txt")
    output_text_path.write_text(report_text, encoding="utf-8")

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print("\nAnalysis complete!")
    print(f"Text report: {output_text_path}")
    print(f"JSON report: {output_path}")
    print(f"\n{report_text}")


if __name__ == "__main__":
    main()
