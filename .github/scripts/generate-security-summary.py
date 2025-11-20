#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Generate consolidated security report from multiple security scan results
# Usage: generate-security-summary.py <artifacts_dir> <output_file> [options]

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def count_findings(data: dict[str, Any] | list[Any], severity_field: str = "severity") -> dict[str, int]:  # noqa: C901
    """
    Count findings by severity level from security scan JSON data.

    Supports multiple JSON structures from different security tools:
    - Bandit: results array with issue_severity field
    - Safety: issues array with severity field
    - pip-audit: vulnerabilities array with severity field
    - Semgrep: results array with severity field
    - Trivy: results array with severity field
    - Checkov: check_type and results
    - Gosec: issues array with severity field
    - Cargo audit: vulnerabilities array
    - TruffleHog: newline-delimited JSON

    Args:
        data: Parsed JSON data from security scan
        severity_field: Field name containing severity level

    Returns:
        Dictionary with counts: {"critical": int, "high": int, "medium": int, "low": int}
    """
    counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    # Normalize data structure
    items: list[dict[str, Any]] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "results" in data:
            items = data["results"]
        elif "issues" in data:
            items = data["issues"]
        elif "vulnerabilities" in data:
            items = data["vulnerabilities"]
        elif "vulnerabilities_found" in data:
            items = data["vulnerabilities_found"]
        else:
            items = []

    # Count by severity
    for item in items:
        if not isinstance(item, dict):
            continue

        # Extract severity with multiple field name fallbacks
        severity = (
            item.get(severity_field)
            or item.get("issue_severity")
            or item.get("Severity")
            or item.get("severity_level")
            or item.get("severity")
            or ""
        )

        if isinstance(severity, str):
            severity = severity.lower()
            if severity == "critical":
                counts["critical"] += 1
            elif severity == "high":
                counts["high"] += 1
            elif severity == "medium":
                counts["medium"] += 1
            elif severity == "low":
                counts["low"] += 1

    return counts


def process_security_report(
    file_path: Path,
) -> tuple[dict[str, int], dict[str, Any]]:
    """
    Process a single security scan report.

    Args:
        file_path: Path to JSON report file

    Returns:
        Tuple of (counts dict, metadata dict)
    """
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        counts = count_findings(data)
        metadata = {
            "file": file_path.name,
            "path": str(file_path),
        }

        return counts, metadata

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from {file_path.name}: {e}")
        return {"critical": 0, "high": 0, "medium": 0, "low": 0}, {"file": file_path.name, "error": str(e)}
    except Exception as e:
        logger.warning(f"Error processing {file_path.name}: {e}")
        return {"critical": 0, "high": 0, "medium": 0, "low": 0}, {"file": file_path.name, "error": str(e)}


def aggregate_reports(
    artifacts_dir: Path,
) -> dict[str, Any]:
    """
    Aggregate security reports from all JSON files in artifacts directory.

    Args:
        artifacts_dir: Path to directory containing security scan results

    Returns:
        Aggregated security summary dictionary
    """
    if not artifacts_dir.exists():
        logger.error(f"Artifacts directory does not exist: {artifacts_dir}")
        return {}

    # Define expected security tools and their result files
    tool_patterns = {
        # Secret scanning
        "trufflehog": ["trufflehog", "trufflehog-results"],
        "detect-secrets": ["detect-secrets"],
        # Python security
        "bandit": ["bandit"],
        "safety": ["safety"],
        "pip-audit": ["pip-audit"],
        "semgrep": ["semgrep"],
        "dodgy": ["dodgy"],
        # Go security
        "gosec": ["gosec"],
        "govulncheck": ["govulncheck"],
        # Rust security
        "cargo-audit": ["cargo-audit", "cargo_audit"],
        # Container/IaC
        "trivy": ["trivy", "trivy-results"],
        "checkov": ["checkov"],
        "tfsec": ["tfsec"],
        "grype": ["grype"],
    }

    summary: dict[str, Any] = {
        "timestamp": None,
        "tools": {},
        "totals": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": 0,
        },
    }

    # Find and process all JSON files
    json_files = list(artifacts_dir.rglob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files in {artifacts_dir}")

    for json_file in json_files:
        # Determine which tool this report belongs to
        tool_name = "unknown"
        for tool, patterns in tool_patterns.items():
            if any(pattern in json_file.name.lower() for pattern in patterns):
                tool_name = tool
                break

        # Process the report
        counts, metadata = process_security_report(json_file)

        # Store tool results
        if tool_name not in summary["tools"]:
            summary["tools"][tool_name] = {
                "files": [],
                "counts": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "total": 0,
                },
            }

        # Accumulate counts for this tool
        summary["tools"][tool_name]["files"].append(metadata)
        for severity in ["critical", "high", "medium", "low"]:
            summary["tools"][tool_name]["counts"][severity] += counts[severity]

        summary["tools"][tool_name]["counts"]["total"] = sum(
            summary["tools"][tool_name]["counts"][sev] for sev in ["critical", "high", "medium", "low"]
        )

        # Accumulate totals
        for severity in ["critical", "high", "medium", "low"]:
            summary["totals"][severity] += counts[severity]

    # Calculate grand total
    summary["totals"]["total"] = sum(summary["totals"][sev] for sev in ["critical", "high", "medium", "low"])

    return summary


def generate_markdown_summary(summary: dict[str, Any]) -> str:
    """
    Generate markdown report from aggregated security summary.

    Args:
        summary: Aggregated security summary dictionary

    Returns:
        Markdown formatted string
    """
    lines = [
        "# 🔒 Security Scan Summary",
        "",
        "## Overall Results",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| 🔴 Critical | **{summary['totals']['critical']}** |",
        f"| 🟠 High | **{summary['totals']['high']}** |",
        f"| 🟡 Medium | **{summary['totals']['medium']}** |",
        f"| 🟢 Low | **{summary['totals']['low']}** |",
        f"| **Total** | **{summary['totals']['total']}** |",
        "",
    ]

    # Add per-tool results if available
    if summary.get("tools"):
        lines.extend(
            [
                "## Results by Tool",
                "",
            ]
        )

        for tool_name in sorted(summary["tools"].keys()):
            tool_data = summary["tools"][tool_name]
            counts = tool_data["counts"]

            if counts["total"] > 0:
                lines.extend(
                    [
                        f"### {tool_name}",
                        "",
                        "| Severity | Count |",
                        "|----------|-------|",
                        f"| 🔴 Critical | {counts['critical']} |",
                        f"| 🟠 High | {counts['high']} |",
                        f"| 🟡 Medium | {counts['medium']} |",
                        f"| 🟢 Low | {counts['low']} |",
                        f"| **Total** | **{counts['total']}** |",
                        "",
                    ]
                )

    # Add status summary
    lines.append("## Status")
    lines.append("")

    if summary["totals"]["critical"] > 0:
        lines.append(
            f"❌ **Critical:** {summary['totals']['critical']} finding(s) require immediate attention"
        )
        lines.append("")
    if summary["totals"]["high"] > 0:
        lines.append(f"⚠️ **High:** {summary['totals']['high']} finding(s) should be addressed soon")
        lines.append("")
    if summary["totals"]["medium"] > 0:
        lines.append(f"**Medium:** {summary['totals']['medium']} finding(s) should be reviewed")
        lines.append("")
    if summary["totals"]["low"] > 0:
        lines.append(f"💡 **Low:** {summary['totals']['low']} finding(s) noted for future improvement")
        lines.append("")

    if summary["totals"]["total"] == 0:
        lines.append("✅ **All clear:** No security findings detected")

    return "\n".join(lines)


def main() -> int:
    """
    Main entry point for security summary generation.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Generate consolidated security report from multiple security scan results",
    )
    parser.add_argument(
        "artifacts_dir",
        type=Path,
        help="Directory containing security scan artifacts",
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="Output JSON file for security summary",
    )
    parser.add_argument(
        "--github-repo",
        default=None,
        help="GitHub repository (owner/repo)",
    )
    parser.add_argument(
        "--github-ref",
        default=None,
        help="GitHub ref (branch/tag name)",
    )
    parser.add_argument(
        "--github-sha",
        default=None,
        help="GitHub commit SHA",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="GitHub Actions run ID",
    )

    args = parser.parse_args()

    logger.info(f"Processing security reports from: {args.artifacts_dir}")

    # Aggregate all reports
    summary = aggregate_reports(args.artifacts_dir)

    # Add metadata if provided
    if args.github_repo:
        summary["github_repo"] = args.github_repo
    if args.github_ref:
        summary["github_ref"] = args.github_ref
    if args.github_sha:
        summary["github_sha"] = args.github_sha
    if args.run_id:
        summary["run_id"] = args.run_id

    # Write JSON report
    try:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        with args.output_file.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Security summary written to: {args.output_file}")
    except Exception as e:
        logger.error(f"Failed to write output file: {e}")
        return 1

    # Write markdown summary to GitHub step summary if available
    github_summary_path = Path(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"))
    if github_summary_path.exists() or github_summary_path.parent.exists():
        try:
            markdown_summary = generate_markdown_summary(summary)
            with github_summary_path.open("a", encoding="utf-8") as f:
                f.write("\n")
                f.write(markdown_summary)
            logger.info(f"Markdown summary appended to: {github_summary_path}")
        except Exception as e:
            logger.warning(f"Failed to write GitHub step summary: {e}")

    # Log summary statistics
    logger.info("")
    logger.info("=== Security Summary ===")
    logger.info(f"Critical: {summary['totals']['critical']}")
    logger.info(f"High:     {summary['totals']['high']}")
    logger.info(f"Medium:   {summary['totals']['medium']}")
    logger.info(f"Low:      {summary['totals']['low']}")
    logger.info(f"Total:    {summary['totals']['total']}")
    logger.info("========================")

    return 0


if __name__ == "__main__":
    import os

    sys.exit(main())

# 🌶️📦🔚
