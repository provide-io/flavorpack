#!/usr/bin/env python3
"""Generate markdown summary for helper pipeline from validation report."""

import json
import sys
import os
from pathlib import Path


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
        print(f"❌ Validation report not found: {validation_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in validation report: {e}")
        sys.exit(1)
    
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
    summary.append("| Platform | Component | Language | Version | Build Time | Status |")
    summary.append("|----------|-----------|----------|---------|------------|--------|")
    
    platforms_order = ["linux_amd64", "linux_arm64", "darwin_amd64", "darwin_arm64", "windows_amd64"]
    platform_emojis = {
        "linux_amd64": "🐧",
        "linux_arm64": "🐧", 
        "darwin_amd64": "🍎",
        "darwin_arm64": "🍎",
        "windows_amd64": "🪟"
    }
    
    # Map component to language
    component_languages = {
        "go-launcher": "Go",
        "go-builder": "Go",
        "rust-launcher": "Rust",
        "rust-builder": "Rust"
    }
    
    # Try to load test results if available
    test_results = {}
    if "test_results" in data:
        # Test results are embedded in the validation data
        test_results = data.get("test_results", {})
    
    # Helper function to get test result for a binary
    def get_test_result(platform, component):
        if platform in test_results:
            # test_results[platform] is the full platform test data
            platform_data = test_results[platform]
            if isinstance(platform_data, dict) and "binaries" in platform_data:
                for binary in platform_data["binaries"]:
                    if binary.get("component") == component:
                        return binary
        return None
    
    for platform_key in platforms_order:
        if platform_key not in data.get("platforms", {}):
            continue
            
        platform = data["platforms"][platform_key]
        platform_emoji = platform_emojis.get(platform_key, "❓")
        platform_display = f"{platform_emoji} {platform_key}"
        
        # If no binaries, show single row for platform
        if not platform.get("binaries"):
            status = platform.get("status", "unknown")
            if status == "failed":
                summary.append(f"| {platform_display} | - | - | - | - | ❌ Failed |")
            else:
                summary.append(f"| {platform_display} | - | - | - | - | ⚠️ No data |")
            continue
        
        # Show each binary component
        for binary in platform.get("binaries", []):
            component = binary.get("component", "unknown")
            language = component_languages.get(component, "Unknown")
            version = binary.get("version", "unknown")
            build_time = binary.get("build_time", "unknown")
            tested = binary.get("tested", False)
            error = binary.get("error")
            
            # Check if we have test results for this binary
            test_result = get_test_result(platform_key, component)
            if test_result:
                # Use data from test results if available
                if test_result.get("version") and test_result.get("version") != "unknown":
                    version = test_result.get("version")
                # Get build time from test results
                if test_result.get("build_time") and test_result.get("build_time") not in ["unknown", "not_executed"]:
                    build_time = test_result.get("build_time")
                elif test_result.get("test_timestamp"):
                    # Use test timestamp if build time not available
                    build_time = test_result.get("test_timestamp")
                # Update tested status based on test results
                test_type = test_result.get("test_mode", test_result.get("test_type", ""))
                if "native" in test_type or "emulated" in test_type or "execution" in test_type or "help" in test_type:
                    tested = True
            
            # Format build time
            if build_time == "cross-compiled":
                build_time_display = "📦 Cross-compiled"
            elif build_time == "unknown" or build_time == "not_executed":
                build_time_display = "-"
            elif " " in build_time:
                # Already formatted as yyyy-mm-dd hh:mm:ss
                build_time_display = build_time
            else:
                # Try to format timestamp if it looks like ISO format
                if "T" in build_time and len(build_time) > 10:
                    # Convert ISO format to yyyy-mm-dd hh:mm:ss
                    # Examples: 2025-08-18T23:09:52+00:00 or 2025-08-18T23:09:52Z
                    try:
                        # Remove timezone info and microseconds
                        clean_time = build_time.replace("Z", "").split("+")[0].split(".")[0]
                        # Replace T with space
                        build_time_display = clean_time.replace("T", " ")
                    except:
                        build_time_display = build_time
                else:
                    build_time_display = build_time
            
            # Format status with build/cache info and test evidence
            cache_status = platform.get("cache_status", "unknown")
            
            # Determine test status from test results
            test_status = ""
            if test_result:
                test_type = test_result.get("test_type", test_result.get("test_mode", ""))
                if test_result.get("passed", False):
                    if "native_execution" in test_type or "native" in test_type:
                        test_status = "✅ Native"
                    elif "emulated_execution" in test_type or "emulated" in test_type:
                        test_status = "✅ Emulated"
                    elif "format_check" in test_type or "format-only" in test_type:
                        test_status = "📦 Format OK"
                    elif "execution" in test_type:
                        test_status = "✅ Executed"
                    elif "help" in test_type:
                        test_status = "✅ Help OK"
                    else:
                        test_status = "✅ Tested"
                else:
                    # Test failed - show specific error
                    test_error = test_result.get("error", "")
                    if "failed to run" in test_error or "Failed to execute" in test_error:
                        test_status = "❌ Failed to run"
                    else:
                        test_status = "❌ Test failed"
            
            # Check binary-level error
            if error:
                if "failed to run" in error:
                    status_display = "❌ Failed to run"
                else:
                    status_display = f"❌ {error}"
            elif test_status:
                # Use test result status
                if cache_status == "cached":
                    status_display = f"{test_status} (💾)"
                elif cache_status == "built":
                    status_display = f"{test_status} (🔨)"
                else:
                    status_display = test_status
            elif tested:
                # Fallback to old logic if no test results
                if cache_status == "cached":
                    status_display = "✅ Tested (💾)"
                elif cache_status == "built":
                    status_display = "✅ Tested (🔨)"
                else:
                    status_display = "✅ Tested"
            else:
                if cache_status == "cached":
                    status_display = "📦 Not tested (💾)"
                elif cache_status == "built":
                    status_display = "📦 Not tested (🔨)"
                else:
                    status_display = "📦 Not tested"
            
            # Format component name
            component_display = f"`{component}`"
            
            # Format version
            version_display = f"**{version}**" if version != "unknown" else "-"
            
            summary.append(f"| {platform_display} | {component_display} | {language} | {version_display} | {build_time_display} | {status_display} |")
    
    summary.append("\n")
    
    # Add artifact links section
    summary.append("### Artifacts\n")
    summary.append("| Artifact | Size | Status |")
    summary.append("|----------|------|--------|")
    
    for platform_key in platforms_order:
        if platform_key not in data.get("platforms", {}):
            continue
            
        platform = data["platforms"][platform_key]
        status = platform.get("status", "unknown")
        cache_status = platform.get("cache_status", "unknown")
        
        # Create artifact name with link
        artifact_name = f"flavor-helpers-{data.get('version', '0.3.0')}-{platform_key}.zip"
        if run_id and github_repository:
            if status == "passed":
                artifact_url = f"{github_server_url}/{github_repository}/actions/runs/{run_id}#artifacts"
                artifact_link = f"[{artifact_name}]({artifact_url})"
            else:
                artifact_link = f"~~{artifact_name}~~"
        else:
            artifact_link = artifact_name
        
        # Status indicator
        if status == "passed":
            if cache_status == "cached":
                status_indicator = "💾 Cached"
            elif cache_status == "built":
                status_indicator = "🔨 Built"
            else:
                status_indicator = "✅ Ready"
        else:
            status_indicator = "❌ Failed"
        
        # Size would need to be extracted from artifacts
        size = "-"  # Placeholder, could be enhanced
        
        summary.append(f"| {artifact_link} | {size} | {status_indicator} |")
    
    summary.append("\n")
    
    # Summary statistics
    s = data.get("summary", {})
    total = s.get("total_platforms", 0)
    passed = s.get("passed", 0)
    failed = s.get("failed", 0)
    
    summary.append("### Summary\n")
    summary.append(f"- **Total Platforms:** {total}")
    summary.append(f"- **Passed:** {passed} ✅")
    summary.append(f"- **Failed:** {failed} ❌")
    
    if failed == 0:
        summary.append("\n🎉 **All platforms validated successfully!**")
    else:
        summary.append(f"\n⚠️ **{failed} platform(s) failed validation**")
    
    summary.append("\n")
    
    # Binary version details
    summary.append("<details>")
    summary.append("<summary>📋 Binary Version Details</summary>")
    summary.append("\n```json")
    
    version_details = {}
    for platform_key in platforms_order:
        if platform_key not in data.get("platforms", {}):
            continue
        platform = data["platforms"][platform_key]
        version_details[platform_key] = {}
        for binary in platform.get("binaries", []):
            version_details[platform_key][binary["component"]] = {
                "version": binary.get("version", "unknown"),
                "build_time": binary.get("build_time", "unknown"),
                "tested": binary.get("tested", False)
            }
    
    summary.append(json.dumps(version_details, indent=2))
    summary.append("```")
    summary.append("</details>")
    
    summary.append("\n")
    
    # Artifact links if available
    if run_id and github_repository:
        summary.append("### Artifacts\n")
        base_url = f"{github_server_url}/{github_repository}/actions/runs/{run_id}"
        summary.append(f"- [View all artifacts]({base_url})")
        summary.append(f"- [Download logs]({base_url}/logs)")
    
    summary.append("\n")
    
    # Legend
    summary.append("### Status Legend\n")
    summary.append("| Icon | Meaning |")
    summary.append("|------|---------|")
    summary.append("| ✅ | Test passed - binary executed successfully |")
    summary.append("| 📦 | Cross-compiled - format verified only |")
    summary.append("| ❌ | Test failed - binary did not execute |")
    summary.append("| 🔨 | Freshly built in this run |")
    summary.append("| 💾 | Retrieved from cache |")
    summary.append("\nStatus format: `<test-result> (<build-source>)` e.g., \"✅ Tested (🔨 Built)\"")
    
    # Output summary
    summary_text = "\n".join(summary)
    
    # Write to GitHub Step Summary if available
    github_step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_step_summary:
        with open(github_step_summary, "a") as f:
            f.write(summary_text)
        print(f"✅ Summary written to GitHub Actions step summary")
    
    # Always output to console
    print(summary_text)
    
    # Save to file
    output_file = Path("pipeline-summary.md")
    output_file.write_text(summary_text)
    print(f"\n📄 Summary saved to {output_file}")


if __name__ == "__main__":
    main()