#!/bin/bash

set -e

cat >> $GITHUB_STEP_SUMMARY << EOF
# 🚀 Release Summary for Flavor Pack ${NEEDS_PREPARE_OUTPUTS_VERSION}

## 📌 Release Information
- **Version**: ${NEEDS_PREPARE_OUTPUTS_VERSION}
- **Tag**: ${NEEDS_PREPARE_OUTPUTS_VERSION_TAG}
- **Type**: ${INPUTS_PRERELEASE}
- **Mode**: ${INPUTS_DRY_RUN}

## 🔨 Build Sources
- **Helpers**: Run #${NEEDS_PREPARE_OUTPUTS_HELPER_RUN_ID}
- **Flavor Pipeline**: Run #${NEEDS_PREPARE_OUTPUTS_FLAVOR_RUN_ID}

## 📦 Asset Collection
| Asset Type | Status |
|------------|--------|
| Platform Wheels | ${NEEDS_COLLECT_WHEELS_RESULT} |
| PSP Packages | ${NEEDS_COLLECT_PACKAGES_RESULT} |
| Release Assets | ${NEEDS_GENERATE_ASSETS_RESULT} |

## 🚀 Publishing Status
| Target | Status | Link |
|--------|--------|------|
| GitHub Release | ${NEEDS_CREATE_RELEASE_RESULT} | ${CREATE_RELEASE_LINK} |
| TestPyPI | ${NEEDS_PUBLISH_TESTPYPI_RESULT} | ${TESTPYPI_LINK} |
| PyPI | ${NEEDS_PUBLISH_PYPI_RESULT} | ${PYPI_LINK} |

## 📋 Next Steps
EOF

if [ "${NEEDS_CREATE_RELEASE_RESULT}" = "success" ]; then
  cat >> $GITHUB_STEP_SUMMARY << EOF
1. Verify the release at https://github.com/${GITHUB_REPOSITORY}/releases/tag/${NEEDS_PREPARE_OUTPUTS_VERSION_TAG}
2. Test installation: 
   skip
3. Update documentation if needed
4. Announce the release
EOF
elif [ "${INPUTS_DRY_RUN}" = "true" ]; then
  cat >> $GITHUB_STEP_SUMMARY << EOF
This was a dry run. To create the actual release:
1. Review the collected assets
2. Run the workflow again with dry_run = false
EOF
else
  cat >> $GITHUB_STEP_SUMMARY << EOF
⚠️ The release process encountered issues. Please check the logs and retry if necessary.
EOF
fi
