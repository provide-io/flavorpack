#!/usr/bin/env bash
set -euo pipefail

# Detect project license from LICENSE files
# Outputs: project_license, has_license to GITHUB_OUTPUT

echo "## 📜 Project License Analysis" >> "$GITHUB_STEP_SUMMARY"
echo "" >> "$GITHUB_STEP_SUMMARY"

# Check for license files
LICENSE_FILES=$(find . -maxdepth 2 -iname "LICENSE*" -o -iname "LICENCE*" -o -iname "COPYING*" | head -10)

if [ -n "$LICENSE_FILES" ]; then
  echo "has_license=true" >> "$GITHUB_OUTPUT"
  echo "### License Files Found:" >> "$GITHUB_STEP_SUMMARY"
  
  for file in $LICENSE_FILES; do
    echo "- \`$file\`" >> "$GITHUB_STEP_SUMMARY"
    
    # Try to detect license type
    if grep -qi "MIT License" "$file"; then
      LICENSE_TYPE="MIT"
    elif grep -qi "Apache License" "$file"; then
      LICENSE_TYPE="Apache-2.0"
    elif grep -qi "BSD" "$file"; then
      LICENSE_TYPE="BSD"
    elif grep -qi "GNU GENERAL PUBLIC LICENSE" "$file"; then
      if grep -qi "Version 3" "$file"; then
        LICENSE_TYPE="GPL-3.0"
      elif grep -qi "Version 2" "$file"; then
        LICENSE_TYPE="GPL-2.0"
      else
        LICENSE_TYPE="GPL"
      fi
    elif grep -qi "Mozilla Public License" "$file"; then
      LICENSE_TYPE="MPL-2.0"
    else
      LICENSE_TYPE="Unknown"
    fi
    
    echo "  Type: **$LICENSE_TYPE**" >> "$GITHUB_STEP_SUMMARY"
    echo "project_license=$LICENSE_TYPE" >> "$GITHUB_OUTPUT"
  done
else
  echo "has_license=false" >> "$GITHUB_OUTPUT"
  echo "project_license=NONE" >> "$GITHUB_OUTPUT"
  echo "⚠️ **No license file found in project root**" >> "$GITHUB_STEP_SUMMARY"
  echo "" >> "$GITHUB_STEP_SUMMARY"
  echo "Consider adding a LICENSE file to clarify usage terms." >> "$GITHUB_STEP_SUMMARY"
fi

# Check for NOTICE file
if [ -f "NOTICE" ] || [ -f "NOTICE.txt" ] || [ -f "NOTICE.md" ]; then
  echo "" >> "$GITHUB_STEP_SUMMARY"
  echo "✅ NOTICE file found" >> "$GITHUB_STEP_SUMMARY"
fi
