#!/usr/bin/env bash
set -euo pipefail

# Generate Software Bill of Materials (SBOM) in multiple formats

echo "## 📜 Software Bill of Materials (SBOM)" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Install SBOM tools
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
pip install cyclonedx-bom
npm install -g @cyclonedx/cli 2>/dev/null || true

echo "### Generating SBOM with Syft" >> "$GITHUB_STEP_SUMMARY"

# Generate SBOM with Syft in multiple formats
syft . -o json > sbom-syft.json
syft . -o spdx-json > sbom-spdx.json
syft . -o cyclonedx-json > sbom-cyclonedx.json
syft . -o table > sbom-table.txt

echo "✅ SBOM generated in multiple formats:" >> "$GITHUB_STEP_SUMMARY"
echo "- SPDX JSON" >> "$GITHUB_STEP_SUMMARY"
echo "- CycloneDX JSON" >> "$GITHUB_STEP_SUMMARY"
echo "- Syft JSON" >> "$GITHUB_STEP_SUMMARY"
echo "- Table format" >> "$GITHUB_STEP_SUMMARY"

# Generate Python-specific SBOM
if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
  echo "" >> "$GITHUB_STEP_SUMMARY"
  echo "### Python SBOM (CycloneDX)" >> "$GITHUB_STEP_SUMMARY"
  
  if [ -f "requirements.txt" ]; then
    cyclonedx-py -r requirements.txt -o sbom-python.json --format json || true
  elif [ -f "pyproject.toml" ]; then
    cyclonedx-py -p pyproject.toml -o sbom-python.json --format json || true
  fi
  
  if [ -f "sbom-python.json" ]; then
    echo "✅ Python-specific SBOM generated" >> "$GITHUB_STEP_SUMMARY"
  fi
fi

# Summary statistics
echo "" >> "$GITHUB_STEP_SUMMARY"
echo "### SBOM Statistics" >> "$GITHUB_STEP_SUMMARY"

if [ -f "sbom-syft.json" ]; then
  PACKAGE_COUNT=$(jq '.artifacts | length' sbom-syft.json)
  echo "- Total packages detected: $PACKAGE_COUNT" >> "$GITHUB_STEP_SUMMARY"
fi

echo "" >> "$GITHUB_STEP_SUMMARY"
echo "### Package Summary" >> "$GITHUB_STEP_SUMMARY"
echo '```' >> "$GITHUB_STEP_SUMMARY"
head -50 sbom-table.txt >> "$GITHUB_STEP_SUMMARY"
echo '```' >> "$GITHUB_STEP_SUMMARY"
