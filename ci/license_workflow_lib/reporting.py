from __future__ import annotations

from ci.license_workflow_lib.analysis import ProjectLicenseScan, PythonLicenseReport


def render_project_license_summary(scan: ProjectLicenseScan) -> str:
    lines = ["## 📜 Project License Analysis", ""]
    if scan.has_license:
        lines.append("### License Files Found:")
        for relative in scan.license_files:
            lines.append(f"- `{relative}`")
        lines.append("")
        lines.append(f"Primary license: **{scan.primary_license}**")
    else:
        lines.extend(
            [
                "⚠️ **No license file found in project root**",
                "",
                "Consider adding a LICENSE file to clarify usage terms.",
            ]
        )
    if scan.notice_found:
        lines.extend(["", "✅ NOTICE file found"])
    lines.extend(["", "### License Headers in Source Files"])
    labels = {"python": "Python", "go": "Go", "rust": "Rust"}
    for key, label in labels.items():
        matched, total = scan.header_counts[key]
        if total or key == "python":
            lines.append(f"- {label} files with license headers: {matched} / {total}")
    return "\n".join(lines) + "\n"


def render_python_report(summary_text: str) -> str:
    return "\n".join(
        [
            "## 🐍 Python License Compliance",
            "",
            "### License Summary",
            "```",
            summary_text.rstrip(),
            "```",
            "",
        ]
    )


def render_python_compliance(
    report: PythonLicenseReport, allowed_licenses: str, strict_mode: bool
) -> tuple[str, dict[str, str], bool]:
    lines = ["### Compliance Check", "", "#### Allowed Licenses:"]
    lines.extend(
        f"- {license_name.strip()}" for license_name in allowed_licenses.split(",") if license_name.strip()
    )
    lines.append("")
    lines.extend(["```", report.as_text().rstrip(), "```"])
    compliant = not report.violations
    if compliant:
        lines.append("✅ **All Python dependencies are license compliant**")
    elif strict_mode:
        lines.append("❌ **License compliance check failed (strict mode)**")
    else:
        lines.append("⚠️ **License compliance issues detected (informational - not blocking)**")
    return (
        "\n".join(lines) + "\n",
        {"compliant": str(compliant).lower(), "violations": str(len(report.violations))},
        strict_mode and not compliant,
    )


def render_python_distribution(rows: list[tuple[str, int, float]]) -> str:
    lines = [
        "### License Distribution",
        "",
        "| License | Count | Percentage |",
        "|---------|-------|------------|",
    ]
    for license_name, count, percentage in rows[:15]:
        lines.append(f"| {license_name[:30]} | {count} | {percentage:.1f}% |")
    return "\n".join(lines) + "\n"


def render_go_report(report_text: str) -> str:
    preview = "\n".join(report_text.splitlines()[:50]).rstrip()
    return "\n".join(["## 🐹 Go License Compliance", "", "### Go Module Licenses", "```", preview, "```", ""])


def render_go_compliance(copyleft: list[str], unknown: list[str], strict_mode: bool) -> tuple[str, str, bool]:
    lines = ["### Go License Compliance Check", ""]
    if copyleft:
        lines.append("⚠️ Copyleft licenses detected:")
        lines.extend(copyleft[:20])
    if unknown:
        lines.append("⚠️ Unknown or problematic licenses:")
        lines.extend(unknown[:20])
    compliant = not copyleft and not unknown
    if compliant:
        lines.append("✅ All Go dependencies are license compliant")
    elif strict_mode:
        lines.append("❌ Go license compliance failed (strict mode)")
    else:
        lines.append("⚠️ Go license compliance issues detected")
    return ("\n".join(lines) + "\n", str(compliant).lower(), strict_mode and not compliant)


def render_rust_report(report_text: str) -> str:
    preview = "\n".join(report_text.splitlines()[:50]).rstrip()
    return "\n".join(
        ["## 🦀 Rust License Compliance", "", "### Rust Crate Licenses", "```", preview, "```", ""]
    )


def render_rust_compliance(log_text: str, compliant: bool, strict_mode: bool) -> tuple[str, str, bool]:
    lines = ["### Rust License Compliance Check", ""]
    if compliant:
        lines.append("✅ All Rust dependencies are license compliant")
    elif strict_mode:
        lines.append("❌ Rust license compliance failed (strict mode)")
    else:
        lines.extend(
            [
                "⚠️ Rust license compliance issues detected:",
                "```",
                "\n".join(
                    line for line in log_text.splitlines() if "error[" in line or "warning[" in line
                ).strip(),
                "```",
            ]
        )
    return ("\n".join(lines) + "\n", str(compliant).lower(), strict_mode and not compliant)


def render_sbom_generation(package_count: int | None, table_preview: str, python_sbom: bool) -> str:
    lines = [
        "## 📜 Software Bill of Materials (SBOM)",
        "",
        "### Generating SBOM with Syft",
        "✅ SBOM generated in multiple formats:",
        "- SPDX JSON",
        "- CycloneDX JSON",
        "- Syft JSON",
        "- Table format",
    ]
    if python_sbom:
        lines.extend(["", "### Python SBOM (CycloneDX)", "✅ Python-specific SBOM generated"])
    lines.extend(["", "### SBOM Statistics"])
    if package_count is not None:
        lines.append(f"- Total packages detected: {package_count}")
    lines.extend(["", "### Package Summary", "```", table_preview.rstrip(), "```", ""])
    return "\n".join(lines)


def render_sbom_validation(spdx_valid: bool, cyclonedx_message: str) -> str:
    lines = ["### SBOM Validation", ""]
    lines.append("✅ SPDX SBOM is valid JSON" if spdx_valid else "❌ SPDX SBOM validation failed")
    if cyclonedx_message:
        lines.append(cyclonedx_message)
    return "\n".join(lines) + "\n"


def render_compliance_report(
    *,
    repository: str,
    run_id: str,
    strict_mode: bool,
    project_license: str,
    has_license: bool,
    python_compliant: bool,
    python_violations: int,
    go_compliant: bool,
    rust_compliant: bool,
    sbom_generated: bool,
    timestamp: str,
    iso_timestamp: str,
) -> tuple[str, dict[str, object]]:
    overall_compliant = has_license and python_compliant and go_compliant and rust_compliant
    lines = [
        "# ⚖️ License Compliance Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Repository:** {repository}",
        f"**Timestamp:** {timestamp}",
        "",
        "## 📋 Summary",
        "",
        "| Component | Status | Details |",
        "|-----------|--------|---------|",
        f"| 📜 Project License | {'✅' if has_license else '⚠️'} | {project_license if has_license else 'No license file'} |",
        f"| 🐍 Python | {'✅' if python_compliant else '⚠️'} | {'Compliant' if python_compliant else f'{python_violations} violations'} |",
        f"| 🐹 Go | {'✅' if go_compliant else '⚠️'} | {'Compliant' if go_compliant else 'Issues detected'} |",
        f"| 🦀 Rust | {'✅' if rust_compliant else '⚠️'} | {'Compliant' if rust_compliant else 'Issues detected'} |",
        f"| 📜 SBOM | {'✅' if sbom_generated else '⏭️'} | {'Generated' if sbom_generated else 'Not generated'} |",
        "",
        "## 🎯 Compliance Status",
        "",
    ]
    if not has_license:
        lines.append("⚠️ **Missing project license file**")
    if not (python_compliant and go_compliant and rust_compliant):
        lines.append("⚠️ **License compliance issues detected in dependencies**")
    lines.append(
        "✅ **Project is license compliant**"
        if overall_compliant
        else "❌ **License compliance issues require attention**"
    )
    lines.extend(
        [
            "",
            "## 📝 Recommendations",
            "",
            "1. 📜 Add a LICENSE file to the project root"
            if not has_license
            else "1. 📋 Review all dependency licenses for compatibility",
            "2. 📋 Review all dependency licenses for compatibility"
            if not has_license
            else "2. ⚖️ Ensure license compatibility with project goals",
            "3. ⚖️ Ensure license compatibility with project goals"
            if not has_license
            else "3. 📝 Consider adding license headers to source files",
            "4. 📝 Consider adding license headers to source files"
            if not has_license
            else "4. 📦 Keep SBOM updated for supply chain transparency",
            "5. 📦 Keep SBOM updated for supply chain transparency"
            if not has_license
            else "5. 🔄 Regularly audit new dependencies for license compliance",
        ]
    )
    if strict_mode and not overall_compliant:
        lines.extend(["", "❌ **Failing due to strict mode enforcement**"])
    summary = {
        "timestamp": iso_timestamp,
        "repository": repository,
        "run_id": run_id,
        "project_license": project_license,
        "has_license_file": has_license,
        "compliance": {
            "python": python_compliant,
            "go": go_compliant,
            "rust": rust_compliant,
            "overall": overall_compliant,
        },
        "violations": {"python": python_violations},
        "sbom_generated": sbom_generated,
    }
    return ("\n".join(lines) + "\n", summary)
