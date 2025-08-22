# Pretaster Integration into Flavor Pipeline - Revised Proposal

## Overview

Based on the existing Flavor pipeline architecture, this proposal outlines how to integrate pretaster as a PSPF validation suite that follows the established patterns:
- Uses helper artifacts from helper-pipeline.yml
- Follows the script-based approach in `.github/scripts/`
- Integrates with existing test matrix patterns
- Maintains compatibility with manual triggering via workflow_dispatch

## 1. New Workflow: `pretaster-pipeline.yml`

Create a new workflow that follows the same pattern as `taster-pipeline.yml`:

```yaml
# .github/workflows/pretaster-pipeline.yml
name: 🧪 Pretaster PSPF Validation

on:
  workflow_dispatch:
    inputs:
      helper_run_id:
        description: 'Helper Pipeline run ID (leave empty for latest)'
        type: string
        required: false
      test_suite:
        description: 'Test suite to run (all, combo, core, direct)'
        type: string
        required: false
        default: 'all'
  
  workflow_run:
    workflows: ["🔨 Helper Pipeline"]
    types: [completed]
    branches: [main]

jobs:
  setup:
    name: 🔧 Setup & Get Helpers
    runs-on: ubuntu-latest
    outputs:
      helper_version: ${{ steps.helpers.outputs.version }}
      test_matrix: ${{ steps.matrix.outputs.matrix }}
    steps:
      - uses: actions/checkout@v4
      
      - name: 🔍 Determine helper version
        id: helpers
        run: |
          source .github/scripts/get-helper-run.sh "${{ inputs.helper_run_id }}"
          echo "run_id=$RUN_ID" >> $GITHUB_OUTPUT
          echo "version=$VERSION" >> $GITHUB_OUTPUT
        env:
          GH_TOKEN: ${{ github.token }}
      
      - name: 📥 Download helper artifacts
        uses: dawidd6/action-download-artifact@v6
        with:
          workflow: helper-pipeline.yml
          run_id: ${{ steps.helpers.outputs.run_id }}
          name: flavor-helpers-${{ steps.helpers.outputs.version }}-all
          path: ./helpers-dist
      
      - name: 📤 Upload helpers for test jobs
        uses: actions/upload-artifact@v4
        with:
          name: pretaster-helpers-${{ github.run_id }}
          path: helpers-dist/*.zip
      
      - name: 🧪 Define test matrix
        id: matrix
        run: |
          .github/scripts/create-pretaster-matrix.sh > matrix.json
          MATRIX=$(cat matrix.json | jq -c .)
          echo "matrix=$MATRIX" >> $GITHUB_OUTPUT

  test-pretaster:
    name: 🧪 Pretaster ${{ matrix.name }}
    needs: setup
    runs-on: ${{ matrix.runner }}
    timeout-minutes: 30
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.setup.outputs.test_matrix) }}
    steps:
      - uses: actions/checkout@v4
      
      - name: 📥 Download helpers
        uses: actions/download-artifact@v4
        with:
          name: pretaster-helpers-${{ github.run_id }}
          path: ./helpers-dist
      
      - name: 🔧 Extract and run pretaster
        run: |
          .github/scripts/run-pretaster-tests.sh \
            "${{ matrix.platform }}" \
            "${{ needs.setup.outputs.helper_version }}" \
            "${{ inputs.test_suite }}"
      
      - name: 📤 Upload test logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pretaster-logs-${{ matrix.platform }}-${{ github.run_id }}
          path: helpers/pretaster/logs/

  validate:
    name: ✅ Validate PSPF Compatibility
    needs: [setup, test-pretaster]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: 📥 Download all logs
        uses: actions/download-artifact@v4
        with:
          pattern: pretaster-logs-*
          path: all-logs
      
      - name: 📊 Generate compatibility report
        run: |
          .github/scripts/generate-pspf-compatibility-report.sh all-logs > report.md
          cat report.md >> $GITHUB_STEP_SUMMARY
```

## 2. Supporting Scripts

### 2.1 `create-pretaster-matrix.sh`

```bash
#!/bin/bash
# .github/scripts/create-pretaster-matrix.sh
# Generate test matrix for pretaster

cat << 'EOF'
{
  "include": [
    {"name": "linux-amd64", "runner": "ubuntu-latest", "platform": "linux_amd64"},
    {"name": "linux-arm64", "runner": "ubuntu-24.04-arm", "platform": "linux_arm64"},
    {"name": "darwin-amd64", "runner": "macos-13", "platform": "darwin_amd64"},
    {"name": "darwin-arm64", "runner": "macos-15", "platform": "darwin_arm64"}
  ]
}
EOF
```

### 2.2 `run-pretaster-tests.sh`

```bash
#!/bin/bash
# .github/scripts/run-pretaster-tests.sh
# Run pretaster test suite

set -euo pipefail

PLATFORM="${1}"
VERSION="${2}"
TEST_SUITE="${3:-all}"

echo "🧪 Running pretaster tests for $PLATFORM"

# Extract helpers
mkdir -p helpers/bin
unzip -o "helpers-dist/flavor-helpers-$VERSION-$PLATFORM.zip" -d helpers/bin/
chmod +x helpers/bin/*

# Build pretaster
cd helpers/pretaster

# Run specified test suite
case "$TEST_SUITE" in
  all)
    make all
    ;;
  combo)
    make combo-test
    ;;
  core)
    make test-core
    ;;
  direct)
    make test-direct
    ;;
  *)
    echo "Unknown test suite: $TEST_SUITE"
    exit 1
    ;;
esac

echo "✅ Pretaster tests completed for $PLATFORM"
```

### 2.3 `generate-pspf-compatibility-report.sh`

```bash
#!/bin/bash
# .github/scripts/generate-pspf-compatibility-report.sh
# Generate PSPF compatibility report from pretaster logs

set -euo pipefail

LOGS_DIR="${1:-all-logs}"

echo "## 🧪 PSPF Compatibility Report"
echo ""
echo "### Test Matrix"
echo ""
echo "| Platform | Builder | Launcher | Status |"
echo "|----------|---------|----------|--------|"

# Parse logs and generate matrix
for log_dir in "$LOGS_DIR"/pretaster-logs-*; do
  if [ -d "$log_dir" ]; then
    PLATFORM=$(basename "$log_dir" | sed 's/pretaster-logs-//' | sed 's/-[0-9]*$//')
    
    # Check each combination
    for combo in "rs-rs" "rs-go" "go-rs" "go-go"; do
      BUILDER=$(echo "$combo" | cut -d'-' -f1)
      LAUNCHER=$(echo "$combo" | cut -d'-' -f2)
      
      LOG_FILE="$log_dir/logs/pretaster-b_${BUILDER}-l_${LAUNCHER}.*.log"
      if ls $LOG_FILE 1> /dev/null 2>&1; then
        if grep -q "✅ All tests passed" $LOG_FILE; then
          STATUS="✅ PASS"
        else
          STATUS="❌ FAIL"
        fi
      else
        STATUS="⚠️ SKIP"
      fi
      
      echo "| $PLATFORM | $BUILDER | $LAUNCHER | $STATUS |"
    done
  fi
done

echo ""
echo "### Summary"
echo ""

# Count passes and failures
TOTAL_TESTS=$(find "$LOGS_DIR" -name "*.log" | wc -l)
PASSED_TESTS=$(find "$LOGS_DIR" -name "*.log" -exec grep -l "✅ All tests passed" {} \; | wc -l)
FAILED_TESTS=$((TOTAL_TESTS - PASSED_TESTS))

echo "- **Total Tests:** $TOTAL_TESTS"
echo "- **Passed:** $PASSED_TESTS"
echo "- **Failed:** $FAILED_TESTS"
echo "- **Success Rate:** $((PASSED_TESTS * 100 / TOTAL_TESTS))%"
```

## 3. Integration with Existing Pipelines

### 3.1 Add to `flavor-pipeline.yml`

Add a new test category in the test matrix:

```yaml
# In flavor-pipeline.yml, add to the test matrix
{"name": "pspf-validation", "runner": "ubuntu-latest", "script": "run-pretaster-validation.sh", "timeout": 30}
```

Create the validation script:

```bash
#!/bin/bash
# .github/scripts/run-pretaster-validation.sh
# Quick PSPF validation for PR testing

set -euo pipefail

# Only run core tests for PR validation (faster)
cd helpers/pretaster
make build-helpers
make test-core

echo "✅ PSPF validation passed"
```

### 3.2 Add to `release.yml`

Add pretaster validation as a pre-release check:

```yaml
# In release.yml, add before the release job
pspf-validation:
  name: 🧪 PSPF Validation
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: 🔍 Get latest helpers
      run: |
        source .github/scripts/get-helper-run.sh
        echo "HELPER_VERSION=$VERSION" >> $GITHUB_ENV
    
    - name: 📥 Download helpers
      uses: dawidd6/action-download-artifact@v6
      with:
        workflow: helper-pipeline.yml
        name: flavor-helpers-${{ env.HELPER_VERSION }}-all
        path: ./helpers-dist
    
    - name: 🧪 Run full PSPF validation
      run: |
        .github/scripts/download-helpers.sh helpers-dist "${{ env.HELPER_VERSION }}" "all"
        cd helpers/pretaster
        make all
    
    - name: 📊 Generate report
      run: |
        .github/scripts/generate-pspf-compatibility-report.sh \
          helpers/pretaster/logs > pspf-report.md
        cat pspf-report.md >> $GITHUB_STEP_SUMMARY
```

### 3.3 Add to `taster-pipeline.yml`

Use pretaster to validate taster packages:

```yaml
# In taster-pipeline.yml, add after building taster
validate-with-pretaster:
  name: 🧪 Validate Taster with Pretaster
  needs: [build-taster]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: 📥 Download taster package
      uses: actions/download-artifact@v4
      with:
        name: taster-${{ needs.setup.outputs.helper_version }}-${{ matrix.platform }}
        path: ./artifacts
    
    - name: 🧪 Validate with pretaster
      run: |
        .github/scripts/validate-package-with-pretaster.sh \
          "artifacts/taster-*.psp"
```

## 4. Local Development Integration

### 4.1 Update Root Makefile

Add to `/REDACTED_ABS_PATH`:

```makefile
# PSPF Validation targets
.PHONY: validate-pspf
validate-pspf: ## Run PSPF compatibility tests
	@cd helpers/pretaster && make test

.PHONY: validate-pspf-full
validate-pspf-full: ## Run full PSPF validation suite
	@cd helpers/pretaster && make all

.PHONY: validate-package
validate-package: ## Validate a PSPF package
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Usage: make validate-package PACKAGE=path/to/package.psp"; \
		exit 1; \
	fi
	@.github/scripts/validate-package-with-pretaster.sh "$(PACKAGE)"
```

### 4.2 Create Validation Script

```bash
#!/bin/bash
# .github/scripts/validate-package-with-pretaster.sh
# Validate any PSPF package using pretaster

set -euo pipefail

PACKAGE="${1:-}"

if [ -z "$PACKAGE" ]; then
    echo "Usage: $0 <package.psp>"
    exit 1
fi

echo "🔍 Validating PSPF package: $PACKAGE"

# Build pretaster if needed
if [ ! -f "helpers/pretaster/dist/pretaster.psp" ]; then
    echo "📦 Building pretaster..."
    cd helpers/pretaster
    make quick
    cd ../..
fi

# Run validation tests
echo "🧪 Testing package execution..."
if FLAVOR_LOG_LEVEL=error "$PACKAGE" --version; then
    echo "✅ Package executes successfully"
else
    echo "❌ Package execution failed"
    exit 1
fi

# Test with pretaster
echo "🧪 Running pretaster validation..."
./helpers/pretaster/dist/pretaster.psp info
echo "✅ Pretaster validation complete"
```

## 5. Pre-commit Hook

```bash
#!/bin/bash
# .githooks/pre-commit
# Run quick PSPF validation before commit

# Check if PSPF-related files changed
if git diff --cached --name-only | grep -E 'helpers/(flavor-rs|flavor-go|pretaster)/'; then
    echo "🧪 Running PSPF validation..."
    
    # Quick validation only
    if ! make -C helpers/pretaster test-core; then
        echo "❌ PSPF validation failed"
        echo "Run 'make validate-pspf-full' for details"
        exit 1
    fi
fi
```

## 6. Implementation Plan

### Phase 1: Core Scripts (Day 1-2)
- [ ] Create `create-pretaster-matrix.sh`
- [ ] Create `run-pretaster-tests.sh`
- [ ] Create `generate-pspf-compatibility-report.sh`
- [ ] Create `validate-package-with-pretaster.sh`

### Phase 2: Workflow Integration (Day 3-4)
- [ ] Create `pretaster-pipeline.yml`
- [ ] Add validation to `flavor-pipeline.yml`
- [ ] Add validation to `release.yml`
- [ ] Add validation to `taster-pipeline.yml`

### Phase 3: Developer Tools (Day 5)
- [ ] Update root Makefile
- [ ] Add pre-commit hook
- [ ] Document in CLAUDE.md

### Phase 4: Testing & Refinement (Day 6-7)
- [ ] Test all workflows
- [ ] Optimize for speed
- [ ] Add caching where appropriate
- [ ] Create dashboard for results

## 7. Success Metrics

- **Coverage**: All PSPF packages validated in CI
- **Speed**: Core validation < 5 minutes
- **Reliability**: No false positives
- **Compatibility**: All 4 builder/launcher combinations tested

## 8. Benefits

1. **Early Detection**: Catch PSPF compatibility issues in PRs
2. **Release Confidence**: Validate before every release
3. **Cross-Platform**: Test on all supported platforms
4. **Developer Friendly**: Local validation tools
5. **Automated**: Runs on every helper pipeline completion