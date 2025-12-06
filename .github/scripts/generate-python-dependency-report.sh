#!/bin/bash

set -e

source audit-env/bin/activate

# This script assumes that the other analysis scripts have been run first
COPYLEFT=$(pip-licenses --format=json | jq '[.[] | select(.License | test("GPL|AGPL|LGPL"))] | length')
UNKNOWN=$(pip-licenses --format=json | jq '[.[] | select(.License == "UNKNOWN")] | length')

# Create comprehensive report
cat > python-deps-report.json << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "total_dependencies": $(pip list --format=json | jq length),
  "direct_dependencies": $(grep -c "^[^#]" requirements-audit.txt 2>/dev/null || echo 0),
  "vulnerabilities": {
    "pip_audit": $([ -f pip-audit-deps.json ] && jq '.vulnerabilities | length' pip-audit-deps.json || echo 0),
    "safety": $([ -f safety-deps.json ] && jq '.vulnerabilities | length' safety-deps.json 2>/dev/null || echo 0)
  },
  "updates_available": $([ -f outdated-python.json ] && jq length outdated-python.json || echo 0),
  "licenses": {
    "copyleft": $COPYLEFT,
    "unknown": $UNKNOWN
  }
}
EOF
