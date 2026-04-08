from __future__ import annotations


def render_dependency_report(
    *,
    repository: str,
    run_id: str,
    timestamp: str,
    iso_timestamp: str,
    python_report: dict[str, object] | None,
    go_has_report: bool,
    go_vulnerable: bool,
    go_has_updates: bool,
    rust_has_report: bool,
    rust_vulnerable: bool,
    rust_has_updates: bool,
) -> tuple[str, dict[str, object]]:
    python_total = int((python_report or {}).get("total_dependencies", 0))
    python_vulns = _python_vulnerability_count(python_report)
    python_updates = int((python_report or {}).get("updates_available", 0))
    python_copyleft = int(((python_report or {}).get("licenses", {}) or {}).get("copyleft", 0))
    total_vulnerabilities = python_vulns + int(go_vulnerable) + int(rust_vulnerable)
    total_updates = python_updates + int(go_has_updates) + int(rust_has_updates)
    copyleft_found = python_copyleft > 0

    rows = [
        f"| 🐍 Python | {python_total or '-'} | {python_vulns} | {python_updates} | {_status(python_vulns, python_updates)} |",
        f"| 🐹 Go | - | {'1' if go_vulnerable else '0'} | {'1' if go_has_updates else '0'} | {'🚨' if go_vulnerable else ('⚠️' if go_has_updates else '✅')} |",
        f"| 🦀 Rust | - | {'1' if rust_vulnerable else '0'} | {'1' if rust_has_updates else '0'} | {'🚨' if rust_vulnerable else ('⚠️' if rust_has_updates else '✅')} |",
    ]

    lines = [
        "# 📦 Dependency Audit Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Repository:** {repository}",
        f"**Timestamp:** {timestamp}",
        "",
        "## 📋 Summary",
        "",
        "| Language | Dependencies | Vulnerabilities | Updates | Status |",
        "|----------|--------------|-----------------|---------|--------|",
        *rows,
        "",
        "## 🔒 Security Findings",
        "",
        (
            f"🚨 **Total vulnerabilities: {total_vulnerabilities}**"
            if total_vulnerabilities
            else "✅ **No vulnerabilities found in dependencies**"
        ),
        "",
        "## 📋 License Compliance",
        "",
        (
            f"⚠️ Python: {python_copyleft} copyleft licenses detected"
            if copyleft_found
            else "✅ No copyleft licenses detected"
        ),
        "",
        "## 🔄 Update Opportunities",
        "",
    ]
    if python_updates:
        lines.append(f"- 🐍 Python: {python_updates} packages can be updated")
    if go_has_updates:
        lines.append("- 🐹 Go: Module updates available")
    if rust_has_updates:
        lines.append("- 🦀 Rust: Crate updates available")
    if not total_updates:
        lines.append("✅ All dependencies are up to date")
    lines.extend(
        [
            "",
            "## 📝 Recommendations",
            "",
            (
                f"1. 🚨 **Critical:** Fix {total_vulnerabilities} security vulnerabilities immediately"
                if total_vulnerabilities
                else "1. 📋 Review dependency audit output for production use"
            ),
            "2. 📦 Review pending dependency updates"
            if total_updates
            else "2. 🔍 Audit and remove unused dependencies",
            "3. 📋 Review license compliance for production use",
            "4. 🔍 Audit and remove unused dependencies",
            "5. 📅 Schedule regular dependency updates",
        ]
    )

    summary = {
        "timestamp": iso_timestamp,
        "repository": repository,
        "run_id": run_id,
        "summary": {
            "total_vulnerabilities": total_vulnerabilities,
            "updates_available": total_updates,
            "copyleft_licenses": copyleft_found,
        },
        "languages": {
            "python": {"has_report": python_report is not None},
            "go": {"has_report": go_has_report},
            "rust": {"has_report": rust_has_report},
        },
    }
    return ("\n".join(lines) + "\n", summary)


def _python_vulnerability_count(python_report: dict[str, object] | None) -> int:
    vulnerabilities = (python_report or {}).get("vulnerabilities", {}) or {}
    return int(vulnerabilities.get("pip_audit", 0)) + int(vulnerabilities.get("safety", 0))


def _status(vulnerabilities: int, updates: int) -> str:
    if vulnerabilities:
        return "🚨"
    if updates > 5:
        return "⚠️"
    return "✅"
