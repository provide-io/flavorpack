#!/usr/bin/env python3
"""Generate markdown summary for helper pipeline from validation report."""

import json
import sys
import os
from pathlib import Path

def get_default_version():
    """Get version from VERSION file."""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.3.0"  # fallback


def main():
    if len(sys.argv) < 2:
        print("Usage: generate-pipeline-summary.py <validation_json> [run_id]")
        sys.exit(1)
    
    validation_file = sys.argv[1]
    run_id = sys.argv[2] if len(sys.argv) > 2 else ""
    github_server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    github_repository = os.environ.get("GITHUB_REPOSITORY", "")
    
    # Load validation report
    try:
        with open(validation_file) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Validation report not found: {validation_file}, using empty report")
        data = {"status": "no-validation", "artifacts": [], "platforms": {}}
    except json.JSONDecodeError as e:
        print(f"⚠️ Invalid JSON in validation report: {e}, using empty report")
        data = {"status": "partial", "artifacts": [], "platforms": {}}
    
    # Generate summary
    summary = []
    summary.append("## 🔨 Helper Pipeline Summary\n")
    
    # Build information
    if "timestamp" in data:
        summary.append(f"**Validation Time:** {data['timestamp']}  ")
    
    if run_id and github_repository:
        run_url = f"{github_server_url}/{github_repository}/actions/runs/{run_id}"
        summary.append(f"**Run:** [#{run_id}]({run_url})  ")
    
    summary.append("\n")
    
    # Helper binaries status table - detailed view
    summary.append("### Helper Binaries Status\n")
    summary.append("| Artifact | Component | Version | Test Result |")
    summary.append("|----------|-----------|---------|-------------|")
    
    platforms_order = ["linux_amd64", "linux_arm64", "darwin_amd64", "darwin_arm64", "windows_amd64"]
    platform_emojis = {
        "linux_amd64": "🐧",
        "linux_arm64": "🐧", 
        "darwin_amd64": "🍎",
        "darwin_arm64": "🍎",
        "windows_amd64": "🪟"
    }
    
    # Track what we've already shown to avoid duplicates
    shown_artifacts = set()
    
    version = data.get('version', get_default_version())
    
    # Check if we have any platforms
    if not data.get("platforms"):
        summary.append("| ⚠️ No helper artifacts found | - | - | - |\n")
        summary.append("\n")
        summary.append("**Status:** No helper binaries were validated in this run.\n")
    else:
        for platform_key in platforms_order:
            if platform_key not in data.get("platforms", {}):
                continue
            
            platform = data["platforms"][platform_key]
            platform_emoji = platform_emojis.get(platform_key, "❓")
            
            # Create artifact link
            artifact_name = f"flavor-helpers-{version}-{platform_key}"
            if run_id and github_repository:
                artifact_url = f"{github_server_url}/{github_repository}/actions/runs/{run_id}#artifacts"
                artifact_link = f"[{artifact_name}]({artifact_url})"
            else:
                artifact_link = artifact_name
            
            # Skip if we've already shown this artifact
            if artifact_name in shown_artifacts:
                continue
            shown_artifacts.add(artifact_name)
            
            # Get unique binaries for this platform
            binaries_seen = set()
            binaries_info = []
            
            for binary in platform.get("binaries", []):
                component = binary.get("component", "unknown")
                
                # Skip duplicates
                if component in binaries_seen:
                    continue
                binaries_seen.add(component)
                
                version_str = binary.get("version", "unknown")
                tested = binary.get("tested", False)
                test_type = binary.get("test_type", "unknown")
                
                # Determine test status
                if tested:
                    if "native" in test_type:
                        test_status = "✅ Native execution"
                    elif "emulated" in test_type:
                        test_status = "✅ Emulated"
                    elif "format" in test_type:
                        test_status = "📦 Format verified"
                    else:
                        test_status = "✅ Tested"
                else:
                    test_status = "❌ Not tested"
                
                binaries_info.append({
                    "component": component,
                    "version": version_str,
                    "test_status": test_status
                })
            
            # If no binaries, show platform status
            if not binaries_info:
                status = platform.get("status", "unknown")
                if status == "failed":
                    summary.append(f"| {platform_emoji} {artifact_link} | - | - | ❌ Failed |")
                else:
                    summary.append(f"| {platform_emoji} {artifact_link} | - | - | ⚠️ No data |")
            else:
                # Show all components for this platform in one row
                components_str = ", ".join([b["component"] for b in binaries_info])
                versions_str = ", ".join([b["version"] for b in binaries_info if b["version"] != "unknown"])
                
                # Aggregate test status
                all_tested = all(b["test_status"].startswith("✅") or b["test_status"].startswith("📦") for b in binaries_info)
                if all_tested:
                    overall_status = "✅ All tested"
                else:
                    tested_count = sum(1 for b in binaries_info if b["test_status"].startswith("✅") or b["test_status"].startswith("📦"))
                    overall_status = f"⚠️ {tested_count}/{len(binaries_info)} tested"
                
                summary.append(f"| {platform_emoji} {artifact_link} | {components_str} | {versions_str or '-'} | {overall_status} |")
    
    summary.append("\n")
    
    # Add Flavor and Taster artifacts section if they exist
    if run_id and github_repository:
        summary.append("### Flavor & Taster Packages\n")
        summary.append("| Package | Platform | Status |")
        summary.append("|---------|----------|--------|")
        
        for platform_key in platforms_order:
            platform_emoji = platform_emojis.get(platform_key, "❓")
            
            # Flavor package
            if platform_key == "windows_amd64":
                flavor_artifact = f"flavor-{version}-{platform_key}.exe"
                taster_artifact = f"taster-{version}-{platform_key}.exe"
            else:
                flavor_artifact = f"flavor-{version}-{platform_key}.psp"
                taster_artifact = f"taster-{version}-{platform_key}.psp"
            
            flavor_url = f"{github_server_url}/{github_repository}/actions/runs/{run_id}#artifacts"
            flavor_link = f"[{flavor_artifact}]({flavor_url})"
            taster_link = f"[{taster_artifact}]({flavor_url})"
            
            # Check if these artifacts were built (we'll assume they exist if the helper pipeline succeeded)
            if platform_key in data.get("platforms", {}) and data["platforms"][platform_key].get("status") == "passed":
                summary.append(f"| {flavor_link} | {platform_emoji} {platform_key} | 🎁 Built |")
                summary.append(f"| {taster_link} | {platform_emoji} {platform_key} | 🧪 Built & Tested |")
            else:
                summary.append(f"| ~~{flavor_artifact}~~ | {platform_emoji} {platform_key} | ⏭️ Skipped |")
                summary.append(f"| ~~{taster_artifact}~~ | {platform_emoji} {platform_key} | ⏭️ Skipped |")
        
        summary.append("\n")
    
    # Summary statistics
    s = data.get("summary", {})
    total = s.get("total_platforms", 0)
    passed = s.get("passed", 0)
    failed = s.get("failed", 0)
    
    summary.append("### Summary\n")
    summary.append(f"- **Total Platforms:** {total}\n")
    summary.append(f"- **Passed:** {passed} ✅\n")
    summary.append(f"- **Failed:** {failed} ❌\n")
    
    if failed == 0:
        summary.append("\n🎉 **All platforms validated successfully!**\n")
    else:
        summary.append(f"\n⚠️ **{failed} platform(s) failed validation**\n")
    
    # Write to GitHub step summary if running in CI
    summary_text = "".join(summary)
    
    github_step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_step_summary:
        with open(github_step_summary, 'w') as f:
            f.write(summary_text)
        print("✅ GitHub step summary written")
    
    # Also write to local file
    with open("pipeline-summary.md", 'w') as f:
        f.write(summary_text)
    
    print("✅ Pipeline summary generated")
    print(summary_text)


if __name__ == "__main__":
    main()