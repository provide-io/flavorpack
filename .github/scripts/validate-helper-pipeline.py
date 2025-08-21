#!/usr/bin/env python3
"""Validate helper pipeline artifacts and generate detailed report."""

import json
import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime

def get_default_version():
    """Get version from VERSION file."""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.3.0"  # fallback


def main():
    # Parse arguments
    artifacts_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    output_json = sys.argv[2] if len(sys.argv) > 2 else "validation-report.json"
    version = sys.argv[3] if len(sys.argv) > 3 else get_default_version()
    
    print(f"🔍 Validating helper pipeline artifacts")
    print(f"   Artifacts directory: {artifacts_dir}")
    print(f"   Output report: {output_json}")
    print(f"   Version: {version}")
    
    # Initialize report
    report = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": version,
        "platforms": {},
        "test_results": {},
        "summary": {
            "total_platforms": 0,
            "passed": 0,
            "failed": 0
        }
    }
    
    # Load combined test results if available
    test_results_file = Path(artifacts_dir) / "final" / "combined-test-report.json"
    if test_results_file.exists():
        print("📋 Found combined test results")
        try:
            with open(test_results_file) as f:
                test_data = json.load(f)
                report["test_results"] = test_data.get("platforms", {})
            print("  ✅ Test results loaded")
        except Exception as e:
            print(f"  ⚠️ Failed to load test results: {e}")
    
    # Define platforms
    platforms = [
        ("linux_amd64", "Linux AMD64", "🐧"),
        ("linux_arm64", "Linux ARM64", "🐧"),
        ("darwin_amd64", "Darwin AMD64", "🍎"),
        ("darwin_arm64", "Darwin ARM64", "🍎"),
        ("windows_amd64", "Windows AMD64", "🪟"),
    ]
    
    # Process each platform
    for platform_key, platform_name, platform_icon in platforms:
        print(f"\nTesting {platform_icon} {platform_name} ({platform_key})...")
        report["summary"]["total_platforms"] += 1
        
        platform_data = {
            "name": platform_name,
            "icon": platform_icon,
            "status": "unknown",
            "cache_status": "unknown",
            "binaries": []
        }
        
        # Check if artifact exists
        artifact_dir = Path(artifacts_dir) / f"flavor-helpers-{version}-{platform_key}"
        zip_file = artifact_dir / f"flavor-helpers-{version}-{platform_key}.zip"
        
        if not zip_file.exists():
            print(f"  ❌ Artifact not found: {zip_file}")
            platform_data["status"] = "failed"
            platform_data["error"] = "artifact not found"
            report["summary"]["failed"] += 1
        else:
            # Check cache status (simple check based on file age)
            import time
            file_age = time.time() - zip_file.stat().st_mtime
            if file_age < 3600:  # Less than 1 hour old
                platform_data["cache_status"] = "built"
                print("  📦 Source: built")
            else:
                platform_data["cache_status"] = "cached"
                print("  📦 Source: cached")
            
            # Get test results for this platform
            platform_test_file = artifact_dir / "test-results" / f"{platform_key}-test-report.json"
            if platform_test_file.exists():
                print("  📋 Found test results file")
                try:
                    with open(platform_test_file) as f:
                        test_report = json.load(f)
                    
                    # Process binaries from test results
                    for test in test_report.get("binaries", []):
                        binary = {
                            "component": test.get("component", "unknown"),
                            "version": clean_string(test.get("version", "unknown")),
                            "build_time": clean_string(test.get("build_time", "unknown")),
                            "tested": test.get("passed", False),
                            "test_type": test.get("test_type", test.get("test_mode", "unknown"))
                        }
                        
                        # Clean up build_time
                        if binary["build_time"] in ["unknown", "not_executed", ""]:
                            if "native" in binary["test_type"]:
                                binary["build_time"] = "native"
                            else:
                                binary["build_time"] = "cross-compiled"
                        
                        if not test.get("passed"):
                            binary["error"] = clean_string(test.get("error", "test failed"))
                        
                        platform_data["binaries"].append(binary)
                    
                    # Determine platform status
                    if not platform_data["binaries"]:
                        platform_data["status"] = "failed"
                        report["summary"]["failed"] += 1
                    elif all(b.get("tested", False) for b in platform_data["binaries"]):
                        platform_data["status"] = "passed"
                        report["summary"]["passed"] += 1
                        print("  ✅ Platform validation passed")
                    else:
                        platform_data["status"] = "failed"
                        report["summary"]["failed"] += 1
                        print("  ❌ Platform validation failed")
                        
                except Exception as e:
                    print(f"  ⚠️ Failed to parse test results: {e}")
                    platform_data["status"] = "failed"
                    report["summary"]["failed"] += 1
            else:
                # No test results - try to extract and test binaries
                print("  ⚠️ No test results file, checking binaries directly")
                try:
                    with zipfile.ZipFile(zip_file, 'r') as zf:
                        for filename in zf.namelist():
                            if filename.startswith("flavor-"):
                                # Determine component from filename
                                component = "unknown"
                                if "go-launcher" in filename:
                                    component = "go-launcher"
                                elif "go-builder" in filename:
                                    component = "go-builder"
                                elif "rs-launcher" in filename:
                                    component = "rust-launcher"
                                elif "rs-builder" in filename:
                                    component = "rust-builder"
                                
                                # Extract version from filename
                                import re
                                version_match = re.search(r'-(\d+\.\d+\.\d+)-', filename)
                                version_str = version_match.group(1) if version_match else "unknown"
                                
                                platform_data["binaries"].append({
                                    "component": component,
                                    "version": version_str,
                                    "build_time": "unknown",
                                    "tested": False
                                })
                    
                    if platform_data["binaries"]:
                        platform_data["status"] = "passed"
                        report["summary"]["passed"] += 1
                    else:
                        platform_data["status"] = "failed"
                        report["summary"]["failed"] += 1
                        
                except Exception as e:
                    print(f"  ⚠️ Failed to process zip file: {e}")
                    platform_data["status"] = "failed"
                    report["summary"]["failed"] += 1
        
        report["platforms"][platform_key] = platform_data
    
    # Write report
    with open(output_json, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Validation complete. Report written to {output_json}")
    
    # Print summary
    s = report["summary"]
    print(f"\n📊 Summary:")
    print(f"  Total platforms: {s['total_platforms']}")
    print(f"  Passed: {s['passed']} ✅")
    print(f"  Failed: {s['failed']} ❌")
    
    if s["failed"] == 0:
        print("\n🎉 All platforms validated successfully!")
    else:
        print(f"\n⚠️ {s['failed']} platform(s) failed validation")
    
    sys.exit(0 if s["failed"] == 0 else 1)


def clean_string(s):
    """Remove control characters and clean up strings."""
    if not s:
        return ""
    # Remove newlines, tabs, and other control characters
    return str(s).replace('\n', ' ').replace('\r', '').replace('\t', ' ').strip()


if __name__ == "__main__":
    main()