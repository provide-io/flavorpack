#!/usr/bin/env python3
"""
Windows PE Binary Analysis Script

Analyzes and compares PE binaries to identify structure differences
that might cause Windows PE loader rejection.

Usage:
    python analyze_pe_binaries.py <working_binary> <failing_binary> <output_file>
"""

import sys
import json
from pathlib import Path

def analyze_pe_binary(filepath):
    """Analyze a PE binary and extract structure information."""
    try:
        import pefile
    except ImportError:
        print("ERROR: pefile library not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pefile", "-q"])
        import pefile

    pe = pefile.PE(filepath)

    analysis = {
        "file": str(filepath),
        "size": Path(filepath).stat().st_size,
        "is_pe": pe.DOS_HEADER.e_magic == 0x5A4D,  # 'MZ'
        "pe_offset": pe.DOS_HEADER.e_lfanew,
        "machine": f"0x{pe.FILE_HEADER.Machine:04x}",
        "num_sections": pe.FILE_HEADER.NumberOfSections,
        "sections": [],
        "data_directories": [],
        "characteristics": {
            "executable": bool(pe.FILE_HEADER.Characteristics & 0x0002),
            "32bit": not bool(pe.OPTIONAL_HEADER.Magic & 0x0001),  # 0x10b = PE32, 0x20b = PE32+
        }
    }

    # Analyze sections
    for section in pe.sections:
        section_info = {
            "name": section.Name.decode('utf-8', errors='ignore').rstrip('\0'),
            "virtual_address": f"0x{section.VirtualAddress:x}",
            "virtual_size": f"0x{section.Misc_VirtualSize:x}",
            "pointer_to_raw_data": f"0x{section.PointerToRawData:x}",
            "size_of_raw_data": f"0x{section.SizeOfRawData:x}",
        }
        analysis["sections"].append(section_info)

    # Analyze all 16 data directories
    dir_names = [
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
        "Reserved"
    ]

    if hasattr(pe, 'OPTIONAL_HEADER') and hasattr(pe.OPTIONAL_HEADER, 'DATA_DIRECTORY'):
        for i, entry in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
            dir_info = {
                "index": i,
                "name": dir_names[i] if i < len(dir_names) else f"Directory {i}",
                "virtual_address": f"0x{entry.VirtualAddress:x}",
                "size": f"0x{entry.Size:x}",
                "has_data": entry.Size > 0,
            }

            # Special handling for directories with absolute offsets
            if i == 4:  # Certificate Table
                dir_info["uses_absolute_offsets"] = True
                if entry.VirtualAddress > 0:
                    dir_info["absolute_offset"] = f"0x{entry.VirtualAddress:x}"

            analysis["data_directories"].append(dir_info)

    # Check for Load Config Directory (entry 10)
    if len(analysis["data_directories"]) > 10:
        load_config = analysis["data_directories"][10]
        if load_config["has_data"]:
            # Load Config typically has file-based offsets
            load_config["note"] = "Load Config present - may have absolute offsets"

    # Check for Debug Directory (entry 6)
    if len(analysis["data_directories"]) > 6:
        debug_dir = analysis["data_directories"][6]
        if debug_dir["has_data"]:
            debug_dir["note"] = "Debug Directory present - PointerToRawData fields are absolute offsets"

    # Check for TLS Directory (entry 9)
    if len(analysis["data_directories"]) > 9:
        tls_dir = analysis["data_directories"][9]
        if tls_dir["has_data"]:
            tls_dir["note"] = "TLS Directory present - may have callback offsets"

    return analysis

def compare_analyses(working, failing):
    """Compare two PE analyses to find differences."""
    comparison = {
        "differences": [],
        "working": working,
        "failing": failing,
    }

    # Compare PE offset
    if working["pe_offset"] != failing["pe_offset"]:
        comparison["differences"].append({
            "type": "pe_offset",
            "working": f"0x{working['pe_offset']:x}",
            "failing": f"0x{failing['pe_offset']:x}",
        })

    # Compare sections
    if working["num_sections"] != failing["num_sections"]:
        comparison["differences"].append({
            "type": "section_count",
            "working": working["num_sections"],
            "failing": failing["num_sections"],
        })

    # Compare section offsets
    for i, (w_sec, f_sec) in enumerate(zip(working["sections"], failing["sections"])):
        if w_sec["pointer_to_raw_data"] != f_sec["pointer_to_raw_data"]:
            comparison["differences"].append({
                "type": "section_offset",
                "section": i,
                "section_name": w_sec["name"],
                "working": w_sec["pointer_to_raw_data"],
                "failing": f_sec["pointer_to_raw_data"],
            })

    # Compare data directories
    for i, (w_dir, f_dir) in enumerate(zip(working["data_directories"], failing["data_directories"])):
        if w_dir["virtual_address"] != f_dir["virtual_address"] or w_dir["size"] != f_dir["size"]:
            comparison["differences"].append({
                "type": "data_directory",
                "index": i,
                "name": w_dir["name"],
                "working": {"va": w_dir["virtual_address"], "size": w_dir["size"]},
                "failing": {"va": f_dir["virtual_address"], "size": f_dir["size"]},
            })

    return comparison

def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <working_binary> <failing_binary> <output_file>")
        sys.exit(1)

    working_path = sys.argv[1]
    failing_path = sys.argv[2]
    output_path = sys.argv[3]

    print(f"Analyzing working binary: {working_path}")
    working = analyze_pe_binary(working_path)

    print(f"Analyzing failing binary: {failing_path}")
    failing = analyze_pe_binary(failing_path)

    print(f"Comparing binaries...")
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
        *[f"  {i}: {s['name']:8} VA=0x{s['virtual_address'].replace('0x', ''):>8} PointerToRaw=0x{s['pointer_to_raw_data'].replace('0x', ''):>8}"
          for i, s in enumerate(working["sections"])],
        "",
        "### Data Directories (with data):",
        *[f"  [{d['index']:2}] {d['name']:25} VA=0x{d['virtual_address'].replace('0x', ''):>8} Size={d['size']}"
          for d in working["data_directories"] if d["has_data"]],
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
        *[f"  {i}: {s['name']:8} VA=0x{s['virtual_address'].replace('0x', ''):>8} PointerToRaw=0x{s['pointer_to_raw_data'].replace('0x', ''):>8}"
          for i, s in enumerate(failing["sections"])],
        "",
        "### Data Directories (with data):",
        *[f"  [{d['index']:2}] {d['name']:25} VA=0x{d['virtual_address'].replace('0x', ''):>8} Size={d['size']}"
          for d in failing["data_directories"] if d["has_data"]],
        "",
        "",
        "## Comparison",
        f"Found {len(comparison['differences'])} structural differences:",
        "",
        *[f"  - {d}" for d in comparison["differences"]],
    ]

    report_text = "\n".join(report_lines)

    # Save both JSON and text reports
    with open(output_path.replace(".json", ".txt"), "w") as f:
        f.write(report_text)

    with open(output_path, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"\nAnalysis complete!")
    print(f"Text report: {output_path.replace('.json', '.txt')}")
    print(f"JSON report: {output_path}")
    print(f"\n{report_text}")

if __name__ == "__main__":
    main()
