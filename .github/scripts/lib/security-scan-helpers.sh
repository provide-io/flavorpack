#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Shared helper functions for security scanning tools
# Usage: source .github/scripts/lib/security-scan-helpers.sh

set -euo pipefail

# Initialize step summary if not already done
init_summary() {
    if [[ ! -f "${GITHUB_STEP_SUMMARY:-/dev/null}" ]]; then
        export GITHUB_STEP_SUMMARY="/tmp/step-summary-$$.md"
    fi
}

# Add a section header to step summary
summary_header() {
    local title="$1"
    local emoji="${2:-🔒}"
    init_summary
    echo "" >> "$GITHUB_STEP_SUMMARY"
    echo "## ${emoji} ${title}" >> "$GITHUB_STEP_SUMMARY"
    echo "" >> "$GITHUB_STEP_SUMMARY"
}

# Add a table row to step summary
summary_table_row() {
    local col1="$1"
    local col2="$2"
    init_summary
    echo "| ${col1} | ${col2} |" >> "$GITHUB_STEP_SUMMARY"
}

# Add a table header to step summary
summary_table_header() {
    local col1="$1"
    local col2="$2"
    init_summary
    echo "| ${col1} | ${col2} |" >> "$GITHUB_STEP_SUMMARY"
    echo "|----------|----------|" >> "$GITHUB_STEP_SUMMARY"
}

# Add a bullet point to step summary
summary_bullet() {
    local text="$1"
    init_summary
    echo "- ${text}" >> "$GITHUB_STEP_SUMMARY"
}

# Add text to step summary
summary_text() {
    local text="$1"
    init_summary
    echo "${text}" >> "$GITHUB_STEP_SUMMARY"
}

# Parse JSON and count findings by severity
count_findings() {
    local json_file="$1"
    local severity_field="${2:-severity}"

    if [[ ! -f "$json_file" ]]; then
        echo "0"
        return
    fi

    python3 -c "
import json
import sys
try:
    with open('$json_file') as f:
        data = json.load(f)
    # Handle different JSON structures
    if isinstance(data, list):
        items = data
    elif 'results' in data:
        items = data['results']
    elif 'issues' in data:
        items = data['issues']
    elif 'vulnerabilities' in data:
        items = data['vulnerabilities']
    else:
        items = []

    count = 0
    for item in items:
        if isinstance(item, dict):
            severity = item.get('$severity_field', item.get('Severity', item.get('severity_level', ''))).lower()
            if severity in ['critical', 'high', 'medium', 'low']:
                count += 1
    print(count)
except Exception as e:
    print('0', file=sys.stderr)
    print(f'Error: {e}', file=sys.stderr)
" 2>/dev/null || echo "0"
}

# Count findings by specific severity level
count_by_severity() {
    local json_file="$1"
    local target_severity="$2"
    local severity_field="${3:-severity}"

    if [[ ! -f "$json_file" ]]; then
        echo "0"
        return
    fi

    python3 -c "
import json
try:
    with open('$json_file') as f:
        data = json.load(f)
    # Handle different JSON structures
    if isinstance(data, list):
        items = data
    elif 'results' in data:
        items = data['results']
    elif 'issues' in data:
        items = data['issues']
    elif 'vulnerabilities' in data:
        items = data['vulnerabilities']
    else:
        items = []

    count = sum(1 for item in items if isinstance(item, dict) and
                item.get('$severity_field', item.get('Severity', item.get('severity_level', ''))).lower() == '$target_severity')
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0"
}

# Format scan results as markdown table
format_results_table() {
    local json_file="$1"
    local tool_name="$2"

    if [[ ! -f "$json_file" ]]; then
        summary_text "No results file found"
        return
    fi

    local critical=$(count_by_severity "$json_file" "critical")
    local high=$(count_by_severity "$json_file" "high")
    local medium=$(count_by_severity "$json_file" "medium")
    local low=$(count_by_severity "$json_file" "low")
    local total=$((critical + high + medium + low))

    summary_table_header "Severity" "Count"
    summary_table_row "🔴 Critical" "$critical"
    summary_table_row "🟠 High" "$high"
    summary_table_row "🟡 Medium" "$medium"
    summary_table_row "🟢 Low" "$low"
    summary_table_row "**Total**" "**$total**"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install tool using pip if not present
install_pip_tool() {
    local tool="$1"
    if ! command_exists "$tool"; then
        echo "📦 Installing $tool..."
        pip install -q "$tool"
    fi
}

# Install tool using cargo if not present
install_cargo_tool() {
    local tool="$1"
    if ! command_exists "$tool"; then
        echo "📦 Installing $tool..."
        cargo install "$tool" --quiet
    fi
}

# Install tool using go if not present
install_go_tool() {
    local tool_path="$1"
    local binary_name="${2:-$(basename "$tool_path")}"
    if ! command_exists "$binary_name"; then
        echo "📦 Installing $binary_name..."
        go install "$tool_path@latest"
    fi
}

# Run scan and handle errors
run_scan() {
    local tool="$1"
    shift
    local args=("$@")

    echo "🔍 Running $tool scan..."
    if "${args[@]}"; then
        echo "✅ $tool scan completed successfully"
        return 0
    else
        local exit_code=$?
        echo "⚠️ $tool scan completed with warnings (exit code: $exit_code)"
        return 0  # Don't fail the build on scan warnings
    fi
}

# Save scan results to artifacts directory
save_results() {
    local source_file="$1"
    local dest_name="$2"
    local artifacts_dir="${3:-artifacts/security}"

    mkdir -p "$artifacts_dir"
    if [[ -f "$source_file" ]]; then
        cp "$source_file" "$artifacts_dir/$dest_name"
        echo "💾 Saved results to $artifacts_dir/$dest_name"
    fi
}

# 🌶️📦🔚
