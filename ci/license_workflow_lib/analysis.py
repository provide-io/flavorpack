from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

ALWAYS_ALLOWED = {
    "mit",
    "apache",
    "apache-2.0",
    "apache software license",
    "bsd",
    "bsd-2-clause",
    "bsd-3-clause",
    "bsd license",
    "3-clause bsd",
    "new bsd license",
    "isc",
    "isc license (iscl)",
    "python",
    "psf",
    "python software foundation",
    "python-2.0",
    "psf-2.0",
    "zlib",
    "zpl",
    "zope public license",
    "lgpl",
    "lgpl-2.1",
    "lgpl-3.0",
    "gnu lesser general public license",
    "mpl",
    "mpl-2.0",
    "mozilla public license",
    "cc0",
    "public domain",
    "unlicense",
    "efl",
    "eupl",
    "artistic",
    "cddl",
    "historical permission notice and disclaimer",
    "hpnd",
    "osl",
    "openssl",
    "wtfpl",
    "boost",
    "boost software license",
}
COPYLEFT_DENY = {"gpl-2.0", "gpl-3.0", "agpl", "agpl-3.0"}
SCAN_TOOLS = {
    "pip-licenses",
    "licensecheck",
    "license-expression",
    "pip-audit",
    "pipdeptree",
    "prettytable",
    "wcwidth",
    "requests-cache",
    "url-normalize",
    "requirements-parser",
    "fhconfparser",
    "cattrs",
    "loguru",
    "appdirs",
    "cyclonedx-python-lib",
}
GO_IGNORE_MODULES = ("github.com/livingstaccato", "github.com/provide-io/flavorpack")
RUST_DENY_TOML = """[licenses]
version = 2
unlicensed = "deny"
allow = [
    "MIT",
    "Apache-2.0",
    "Apache-2.0 WITH LLVM-exception",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Unicode-3.0",
    "Unicode-DFS-2016",
    "CC0-1.0",
    "OpenSSL",
    "Zlib",
]
deny = [
    "GPL-2.0",
    "GPL-3.0",
    "AGPL-3.0",
]

[[licenses.exceptions]]
allow = ["Unicode-DFS-2016", "Unicode-3.0"]
name = "unicode-ident"

[bans]
multiple-versions = "warn"
wildcards = "allow"

[sources]
unknown-registry = "warn"
unknown-git = "warn"
"""


@dataclass(frozen=True)
class ProjectLicenseScan:
    primary_license: str
    has_license: bool
    license_files: list[str]
    notice_found: bool
    header_counts: dict[str, tuple[int, int]]


@dataclass(frozen=True)
class PythonLicenseReport:
    compliant: list[str]
    violations: list[str]
    unknown: list[str]

    def as_text(self) -> str:
        lines = [
            f"Compliant: {len(self.compliant)}",
            f"Violations: {len(self.violations)}",
            f"Unknown: {len(self.unknown)}",
        ]
        if self.violations:
            lines.append("")
            lines.append("License Violations:")
            lines.extend(f"  X {entry}" for entry in self.violations[:20])
        if self.unknown:
            lines.append("")
            lines.append("Unknown Licenses:")
            lines.extend(f"  ! {entry}" for entry in self.unknown[:10])
        return "\n".join(lines) + "\n"


def detect_license_type(text: str) -> str:
    lowered = text.lower()
    if "mit license" in lowered:
        return "MIT"
    if "apache license" in lowered:
        return "Apache-2.0"
    if "mozilla public license" in lowered:
        return "MPL-2.0"
    if "gnu general public license" in lowered:
        if "version 3" in lowered:
            return "GPL-3.0"
        if "version 2" in lowered:
            return "GPL-2.0"
        return "GPL"
    if "bsd" in lowered:
        return "BSD"
    return "Unknown"


def scan_project_license(repo_root: Path) -> ProjectLicenseScan:
    license_files = sorted(
        str(path.relative_to(repo_root))
        for path in repo_root.glob("*")
        if path.is_file() and path.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))
    )
    primary_license = "NONE"
    if license_files:
        detected = []
        for relative in license_files:
            content = (repo_root / relative).read_text(encoding="utf-8", errors="ignore")
            detected.append(detect_license_type(content))
        primary_license = next((item for item in detected if item != "Unknown"), detected[0])
    return ProjectLicenseScan(
        primary_license=primary_license,
        has_license=bool(license_files),
        license_files=license_files,
        notice_found=any((repo_root / name).is_file() for name in ("NOTICE", "NOTICE.txt", "NOTICE.md")),
        header_counts={
            "python": _count_headers(repo_root / "src", ".py") + _count_headers(repo_root / "helpers", ".py"),
            "go": _count_headers(repo_root / "src" / "flavor-go", ".go"),
            "rust": _count_headers(repo_root / "src" / "flavor-rs", ".rs"),
        },
    )


def _count_headers(root: Path, suffix: str) -> tuple[int, int]:
    if not root.is_dir():
        return (0, 0)
    matches = 0
    total = 0
    for path in root.rglob(f"*{suffix}"):
        if not path.is_file():
            continue
        total += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "Copyright" in text or "License" in text:
            matches += 1
    return (matches, total)


def load_python_licenses(path: Path) -> list[dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_python_licenses(licenses: list[dict[str, str]]) -> PythonLicenseReport:
    compliant: list[str] = []
    violations: list[str] = []
    unknown: list[str] = []
    for package in licenses:
        name = package.get("Name", "Unknown")
        if name.lower() in SCAN_TOOLS:
            continue
        license_name = package.get("License", "UNKNOWN")
        lowered = license_name.lower()
        entry = f"{name}: {license_name}"
        if license_name == "UNKNOWN":
            unknown.append(entry)
            continue
        if any(token in lowered for token in COPYLEFT_DENY):
            violations.append(entry)
        elif any(token in lowered for token in ALWAYS_ALLOWED):
            compliant.append(entry)
        else:
            violations.append(entry)
    return PythonLicenseReport(compliant=compliant, violations=violations, unknown=unknown)


def license_distribution(licenses: list[dict[str, str]]) -> list[tuple[str, int, float]]:
    counts: dict[str, int] = {}
    for package in licenses:
        name = package.get("Name", "")
        if name.lower() in SCAN_TOOLS:
            continue
        license_name = package.get("License", "UNKNOWN")
        counts[license_name] = counts.get(license_name, 0) + 1
    total = sum(counts.values()) or 1
    return [
        (license_name, count, (count / total) * 100.0)
        for license_name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def evaluate_go_compliance(report_text: str) -> tuple[list[str], list[str]]:
    copyleft = [
        line for line in report_text.splitlines() if any(token in line for token in ("GPL", "AGPL", "LGPL"))
    ]
    unknown = [line for line in report_text.splitlines() if "UNKNOWN" in line or "ERROR" in line]
    return (copyleft, unknown)
