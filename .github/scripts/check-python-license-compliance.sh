#!/usr/bin/env bash
set -euo pipefail

# Check Python dependency license compliance
# Arguments: $1 = allowed_licenses (comma-separated)

ALLOWED_LICENSES="${1:-MIT,Apache-2.0,BSD-3-Clause,BSD-2-Clause,ISC,Python-2.0,PSF,ZPL}"

source license-env/bin/activate

echo "### Compliance Check" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Generate license reports
pip-licenses --format=json --output-file=python-licenses.json
pip-licenses --format=csv --output-file=python-licenses.csv
pip-licenses --format=markdown --output-file=python-licenses.md
pip-licenses --format=plain --output-file=python-licenses.txt
pip-licenses --summary --output-file=python-license-summary.txt

echo "#### Allowed Licenses:" >> "$GITHUB_STEP_SUMMARY"
IFS=',' read -ra ALLOWED <<< "$ALLOWED_LICENSES"
for license in "${ALLOWED[@]}"; do
  echo "- $license" >> "$GITHUB_STEP_SUMMARY"
done
echo "" >> "$GITHUB_STEP_SUMMARY"

# Analyze licenses with Python
python << 'EOF' > license-analysis.txt
import json
import sys
import os

allowed = os.environ.get('ALLOWED_LICENSES', '').split(',')
allowed = [l.strip().lower() for l in allowed]

with open('python-licenses.json') as f:
    licenses = json.load(f)

violations = []
compliant = []
unknown = []

for pkg in licenses:
    name = pkg.get('Name', 'Unknown')
    license = pkg.get('License', 'UNKNOWN')
    
    # Normalize license name
    license_lower = license.lower().replace(' ', '-')
    
    # Check if compliant
    is_compliant = False
    for allowed_license in allowed:
        if allowed_license in license_lower or license_lower in allowed_license:
            is_compliant = True
            break
    
    if license == 'UNKNOWN':
        unknown.append(f"{name}: {license}")
    elif is_compliant:
        compliant.append(f"{name}: {license}")
    else:
        violations.append(f"{name}: {license}")

print(f"Compliant: {len(compliant)}")
print(f"Violations: {len(violations)}")
print(f"Unknown: {len(unknown)}")

if violations:
    print("\nLicense Violations:")
    for v in violations[:20]:
        print(f"  ❌ {v}")

if unknown:
    print("\nUnknown Licenses:")
    for u in unknown[:10]:
        print(f"  ⚠️ {u}")

sys.exit(0 if len(violations) == 0 else 1)
EOF

PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ]; then
  echo "compliant=true" >> "$GITHUB_OUTPUT"
  echo "violations=0" >> "$GITHUB_OUTPUT"
  echo "✅ **All Python dependencies are license compliant**" >> "$GITHUB_STEP_SUMMARY"
else
  VIOLATION_COUNT=$(grep -c "❌" license-analysis.txt || echo 0)
  echo "compliant=false" >> "$GITHUB_OUTPUT"
  echo "violations=$VIOLATION_COUNT" >> "$GITHUB_OUTPUT"
  echo "⚠️ **License compliance issues detected**" >> "$GITHUB_STEP_SUMMARY"
  echo '```' >> "$GITHUB_STEP_SUMMARY"
  cat license-analysis.txt >> "$GITHUB_STEP_SUMMARY"
  echo '```' >> "$GITHUB_STEP_SUMMARY"
fi

export ALLOWED_LICENSES
