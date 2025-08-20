#!/bin/bash
set -e

# Generate markdown summary for helper pipeline from validation report
# Usage: .github/scripts/generate-pipeline-summary.sh <validation_json> [run_id]

VALIDATION_JSON="${1:-validation-report.json}"
RUN_ID="${2:-}"
GITHUB_SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-}"

echo "📝 Generating pipeline summary"
echo "   Validation report: $VALIDATION_JSON"

if [ ! -f "$VALIDATION_JSON" ]; then
    echo "❌ Validation report not found: $VALIDATION_JSON"
    exit 1
fi

# Generate markdown summary
SUMMARY=$(python3 -c '
import json
import sys
import os

validation_file = "'"$VALIDATION_JSON"'"
run_id = "'"$RUN_ID"'"
github_server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
github_repository = os.environ.get("GITHUB_REPOSITORY", "")

with open(validation_file) as f:
    data = json.load(f)

summary = []
summary.append("## 🔨 Helper Pipeline Summary\n")

# Build information
if "timestamp" in data:
    summary.append(f"**Validation Time:** {data[\"timestamp\"]}  ")

if run_id and github_repository:
    run_url = f"{github_server_url}/{github_repository}/actions/runs/{run_id}"
    summary.append(f"**Run:** [#{run_id}]({run_url})  ")

summary.append("\n")

# Platform status table
summary.append("### Platform Status\n")
summary.append("| Platform | Status | Source | Go Launcher | Go Builder | Rust Launcher | Rust Builder |")
summary.append("|----------|--------|--------|-------------|------------|---------------|--------------|")

platforms_order = ["linux_amd64", "linux_arm64", "darwin_amd64", "darwin_arm64", "windows_amd64"]

for platform_key in platforms_order:
    if platform_key not in data.get("platforms", {}):
        continue
        
    platform = data["platforms"][platform_key]
    
    # Platform name with icon
    platform_name = f"{platform.get('icon', '')} {platform.get('name', platform_key)}"
    
    # Status
    status = "✅" if platform.get("status") == "passed" else "❌"
    
    # Cache status
    source = platform.get("cache_status", "unknown")
    if source == "built":
        source = "🔨 Built"
    elif source == "cached":
        source = "💾 Cached"
    else:
        source = "❓ Unknown"
    
    # Binary versions
    binaries = {b["component"]: b for b in platform.get("binaries", [])}
    
    def format_version(component):
        if component in binaries:
            b = binaries[component]
            version = b.get("version", "?")
            if b.get("tested", False):
                return f"✅ {version}"
            elif b.get("error"):
                return f"❌ {version}"
            else:
                return f"📦 {version}"
        return "—"
    
    go_launcher = format_version("go-launcher")
    go_builder = format_version("go-builder")
    rust_launcher = format_version("rust-launcher")
    rust_builder = format_version("rust-builder")
    
    summary.append(f"| {platform_name} | {status} | {source} | {go_launcher} | {go_builder} | {rust_launcher} | {rust_builder} |")

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

# Legend
summary.append("### Legend\n")
summary.append("- ✅ = Test passed (binary executed successfully)")
summary.append("- 📦 = Cross-compiled (format verified only)")
summary.append("- ❌ = Test failed")
summary.append("- 🔨 Built = Freshly built in this run")
summary.append("- 💾 Cached = Retrieved from cache")

print("\n".join(summary))
')

# Output to GitHub Step Summary if available
if [ -n "$GITHUB_STEP_SUMMARY" ]; then
    echo "$SUMMARY" >> "$GITHUB_STEP_SUMMARY"
    echo "✅ Summary written to GitHub Actions"
else
    # Just output to console
    echo "$SUMMARY"
fi

# Also save to file for reference
echo "$SUMMARY" > pipeline-summary.md
echo "📄 Summary saved to pipeline-summary.md"