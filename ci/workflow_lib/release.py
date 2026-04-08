from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

from .common import run_command


def write_release_checksums(release_dir: Path) -> Path:
    lines = ["# SHA256 Checksums", ""]
    wheels = sorted(release_dir.glob("*.whl"))
    psp_files = sorted(file for pattern in ("*.psp", "*.exe") for file in release_dir.glob(pattern))
    if wheels:
        lines.append("## Python Wheels")
        for wheel in wheels:
            lines.append(f"{hashlib.sha256(wheel.read_bytes()).hexdigest()}  {wheel.name}")
        lines.append("")
    if psp_files:
        lines.append("## PSP Packages")
        for package in psp_files:
            lines.append(f"{hashlib.sha256(package.read_bytes()).hexdigest()}  {package.name}")
    checksum_path = release_dir / "checksums.txt"
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def render_release_notes(version: str, repository: str) -> str:
    return f"""# Flavor Pack {version}

## Quick Install

### Install from PyPI
```bash
pip install flavorpack=={version}

curl -LO https://github.com/{repository}/releases/download/v{version}/flavor-{version}-linux_amd64.psp
chmod +x flavor-*.psp
./flavor-*.psp --help
```

## Release Assets

### Python Wheels
Platform-specific wheels with embedded Go and Rust helpers:
- `flavorpack-{version}-py3-none-manylinux2014_x86_64.whl` - Linux x86_64
- `flavorpack-{version}-py3-none-manylinux2014_aarch64.whl` - Linux ARM64
- `flavorpack-{version}-py3-none-macosx_10_9_x86_64.whl` - macOS Intel
- `flavorpack-{version}-py3-none-macosx_11_0_arm64.whl` - macOS Apple Silicon
- `flavorpack-{version}-py3-none-win_amd64.whl` - Windows x86_64
- `flavorpack-{version}-py3-none-win_arm64.whl` - Windows ARM64

### Self-Contained PSP Packages
Ready-to-run executables (no Python required):
- `flavor-{version}-linux_amd64.psp` - Linux x86_64
- `flavor-{version}-linux_arm64.psp` - Linux ARM64
- `flavor-{version}-darwin_amd64.psp` - macOS Intel
- `flavor-{version}-darwin_arm64.psp` - macOS Apple Silicon
- `flavor-{version}-windows_amd64.psp` - Windows x86_64
- `flavor-{version}-windows_arm64.psp` - Windows ARM64

### Test Packages
- `taster-{version}-*.psp` - Comprehensive test suite

## What's New

See [Changelog](https://foundry.provide.io/flavorpack/community/changelog/) for detailed changes.

## Verification

All packages are signed with Ed25519. Verify checksums:
```bash
curl -LO https://github.com/{repository}/releases/download/v{version}/checksums.txt
sha256sum -c checksums.txt
```

## Documentation

- [User Guide](https://foundry.provide.io/flavorpack/guide/)
- [API Reference](https://foundry.provide.io/flavorpack/api/)
- [Troubleshooting](https://foundry.provide.io/flavorpack/troubleshooting/)
"""


def stage_release_directory(artifacts_dir: Path, release_dir: Path) -> dict[str, int]:
    release_dir.mkdir(parents=True, exist_ok=True)
    copied_wheels = 0
    copied_psp = 0
    copied_other = 0
    patterns = {
        artifacts_dir / "release-wheels": ["*.whl"],
        artifacts_dir / "release-psp": ["*.psp", "*.exe"],
        artifacts_dir / "release-assets": ["*.txt", "*.md", "*.whl", "*.psp", "*.exe"],
    }
    for source_dir, globs in patterns.items():
        if not source_dir.is_dir():
            continue
        for glob in globs:
            for source in source_dir.glob(glob):
                if not source.is_file():
                    continue
                destination = release_dir / source.name
                shutil.copy2(source, destination)
                if source.suffix == ".whl":
                    copied_wheels += 1
                elif source.suffix in {".psp", ".exe"}:
                    copied_psp += 1
                else:
                    copied_other += 1
    return {"wheels": copied_wheels, "psp_packages": copied_psp, "other": copied_other}


def verify_release_wheels(dist_dir: Path) -> list[str]:
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError(f"No wheel files found in {dist_dir}")
    invalid = [wheel.name for wheel in wheels if not wheel.name.startswith("flavorpack-")]
    if invalid:
        raise ValueError(f"Invalid wheel names for PyPI: {', '.join(invalid)}")
    return [wheel.name for wheel in wheels]


def create_release_tag(version: str, version_tag: str, repository: str) -> None:
    run_command(["git", "config", "user.name", "github-actions[bot]"])
    run_command(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
    version_path = Path("VERSION")
    version_path.write_text(version + "\n", encoding="utf-8")
    run_command(["git", "add", "VERSION"])
    diff = run_command(["git", "diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        run_command(["git", "commit", "-m", f"Release v{version}"])
    commit_sha = run_command(["git", "rev-parse", "HEAD"]).stdout.strip()
    run_command(
        [
            "gh",
            "api",
            f"repos/{repository}/git/tags",
            "-f",
            f"tag={version_tag}",
            "-f",
            f"message=Release {version}",
            "-f",
            f"object={commit_sha}",
            "-f",
            "type=commit",
        ]
    )
    run_command(
        [
            "gh",
            "api",
            f"repos/{repository}/git/refs",
            "-f",
            f"ref=refs/tags/{version_tag}",
            "-f",
            f"sha={commit_sha}",
        ]
    )


def render_release_summary(args: object) -> str:
    version = args.version
    version_tag = args.version_tag
    repository = args.repository
    release_url = f"https://github.com/{repository}/releases/tag/{version_tag}"
    testpypi_url = f"https://test.pypi.org/project/flavorpack/{version}/"
    pypi_url = f"https://pypi.org/project/flavorpack/{version}/"
    release_status = (
        "✅ Published"
        if args.create_release_result == "success"
        else "⏭️ Skipped (Dry Run)"
        if args.create_release_result == "skipped"
        else "❌ Failed"
    )
    testpypi_status = (
        "✅ Published"
        if args.publish_testpypi_result == "success"
        else "⏭️ Skipped"
        if args.publish_testpypi_result == "skipped"
        else "❌ Failed"
    )
    pypi_status = (
        "✅ Published"
        if args.publish_pypi_result == "success"
        else "⏭️ Skipped"
        if args.publish_pypi_result == "skipped"
        else "❌ Failed"
    )
    rows = [
        f"| GitHub Release | {release_status} | {'[View Release](' + release_url + ')' if args.create_release_result == 'success' else 'N/A'} |",
        f"| TestPyPI | {testpypi_status} | {'[View on TestPyPI](' + testpypi_url + ')' if args.publish_testpypi_result == 'success' else 'N/A'} |",
        f"| PyPI | {pypi_status} | {'[View on PyPI](' + pypi_url + ')' if args.publish_pypi_result == 'success' else 'N/A'} |",
    ]
    summary = f"""# Release Summary for Flavor Pack {version}

## Release Information
- **Version**: {version}
- **Tag**: {version_tag}
- **Type**: {"Pre-release" if args.prerelease else "Stable Release"}
- **Mode**: {"Dry Run" if args.dry_run else "Production"}

## Build Sources
- **Helpers**: Run #{args.helper_run_id}
- **Flavor Pipeline**: Run #{args.flavor_run_id}

## Asset Collection
| Asset Type | Status |
|------------|--------|
| Platform Wheels | {"✅ Collected" if args.collect_wheels_result == "success" else "❌ Failed"} |
| PSP Packages | {"✅ Collected" if args.collect_packages_result == "success" else "❌ Failed"} |
| Release Assets | {"✅ Generated" if args.generate_assets_result == "success" else "❌ Failed"} |

## Publishing Status
| Target | Status | Link |
|--------|--------|------|
{chr(10).join(rows)}

## Next Steps
"""
    if args.create_release_result == "success":
        summary += (
            f"1. Verify the release at {release_url}\n"
            f"2. Test installation: `pip install flavorpack=={version}`\n"
            "3. Update documentation if needed\n"
            "4. Announce the release\n"
        )
    elif args.dry_run:
        summary += "This was a dry run. Review the collected assets, then rerun with `dry_run = false`.\n"
    else:
        summary += "The release process encountered issues. Check the logs and retry if needed.\n"
    return summary
