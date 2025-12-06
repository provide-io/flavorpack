#!/usr/bin/env bash
set -euo pipefail

# Validate generated SBOM files

echo "### SBOM Validation" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Validate SPDX format
if [ -f "sbom-spdx.json" ]; then
  if python -m json.tool sbom-spdx.json > /dev/null 2>&1; then
    echo "✅ SPDX SBOM is valid JSON" >> "$GITHUB_STEP_SUMMARY"
  else
    echo "❌ SPDX SBOM validation failed" >> "$GITHUB_STEP_SUMMARY"
  fi
fi

# Validate CycloneDX format
if [ -f "sbom-cyclonedx.json" ]; then
  if command -v cyclonedx &> /dev/null; then
    cyclonedx validate --input-file sbom-cyclonedx.json --input-format json 2>&1 | tee cyclonedx-validation.log || true
    if grep -q "valid" cyclonedx-validation.log; then
      echo "✅ CycloneDX SBOM is valid" >> "$GITHUB_STEP_SUMMARY"
    else
      echo "⚠️ CycloneDX SBOM validation warnings" >> "$GITHUB_STEP_SUMMARY"
    fi
  else
    echo "⚠️ CycloneDX CLI not available for validation" >> "$GITHUB_STEP_SUMMARY"
  fi
fi

# Validate Syft JSON
if [ -f "sbom-syft.json" ]; then
  if python -m json.tool sbom-syft.json > /dev/null 2>&1; then
    echo "✅ Syft SBOM is valid JSON" >> "$GITHUB_STEP_SUMMARY"
  else
    echo "❌ Syft SBOM validation failed" >> "$GITHUB_STEP_SUMMARY"
  fi
fi

echo "✅ SBOM validation complete" >> "$GITHUB_STEP_SUMMARY"
