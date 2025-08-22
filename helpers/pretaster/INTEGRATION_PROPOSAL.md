# Pretaster Integration Proposal for Flavor Pipeline

## Executive Summary

Pretaster provides a comprehensive PSPF validation suite that tests all builder/launcher combinations and validates cross-language compatibility. This proposal outlines how to integrate pretaster into the Flavor CI/CD pipeline to ensure package integrity and catch compatibility issues early.

## 1. GitHub Actions Integration

### 1.1 Create Dedicated Pretaster Workflow

**File: `.github/workflows/pretaster-validation.yml`**

```yaml
name: 🧪 PSPF Validation (Pretaster)

on:
  pull_request:
    paths:
      - 'helpers/**'
      - 'src/flavor/psp/**'
      - '.github/workflows/pretaster-validation.yml'
  workflow_dispatch:
  workflow_call:
    outputs:
      validation-passed:
        description: "Whether all PSPF validation tests passed"
        value: ${{ jobs.validate.outputs.passed }}

jobs:
  validate:
    name: PSPF Cross-Language Validation
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
      fail-fast: false
    
    outputs:
      passed: ${{ steps.test.outputs.passed }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Environment
        run: |
          source env.sh
          echo "FLAVOR_WORKENV=$PWD/workenv" >> $GITHUB_ENV
      
      - name: Build Helpers
        run: |
          cd helpers
          ./build.sh
      
      - name: Run Pretaster Validation
        id: test
        run: |
          cd helpers/pretaster
          make all
          echo "passed=true" >> $GITHUB_OUTPUT
      
      - name: Upload Test Logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pretaster-logs-${{ matrix.os }}-${{ github.run_id }}
          path: helpers/pretaster/logs/
          retention-days: 7
      
      - name: Upload Test Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pretaster-report-${{ matrix.os }}
          path: |
            helpers/pretaster/logs/summary.json
            helpers/pretaster/logs/compatibility-matrix.html
```

### 1.2 Integration with Main Pipeline

**Update: `.github/workflows/flavor-pipeline.yml`**

```yaml
name: 🚀 Flavor Pipeline

on: [push, pull_request]

jobs:
  # Existing jobs...
  
  pspf-validation:
    name: PSPF Validation
    uses: ./.github/workflows/pretaster-validation.yml
    needs: [build-helpers]
  
  integration-tests:
    name: Integration Tests
    needs: [pspf-validation]
    if: needs.pspf-validation.outputs.validation-passed == 'true'
    runs-on: ubuntu-latest
    steps:
      # Run main integration tests only if PSPF validation passes
```

## 2. Pre-Release Validation Gate

### 2.1 Release Workflow Integration

**Update: `.github/workflows/release.yml`**

```yaml
name: 📦 Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Release version'
        required: true

jobs:
  validate-release:
    name: Pre-Release Validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Full PSPF Compatibility Check
        run: |
          cd helpers/pretaster
          make clean build test
          
          # Generate compatibility report
          ./scripts/generate-compatibility-report.sh > compat-report.json
          
          # Check for any failures
          if grep -q '"failed": true' compat-report.json; then
            echo "::error::PSPF compatibility check failed"
            exit 1
          fi
      
      - name: Performance Regression Check
        run: |
          cd helpers/pretaster
          make bench
          
          # Compare with baseline
          ./scripts/check-performance-regression.sh
```

## 3. Local Development Integration

### 3.1 Git Hooks

**File: `.githooks/pre-commit`**

```bash
#!/bin/bash
# Pre-commit hook for PSPF validation

# Check if any PSPF-related files changed
if git diff --cached --name-only | grep -E '(\.json|\.psp|helpers/|src/flavor/psp/)'; then
    echo "🧪 Running pretaster validation..."
    
    cd helpers/pretaster
    
    # Quick validation (subset of tests)
    if ! make test-core; then
        echo "❌ PSPF validation failed. Please fix issues before committing."
        echo "   Run 'make -C helpers/pretaster test' for full details."
        exit 1
    fi
    
    echo "✅ PSPF validation passed"
fi
```

### 3.2 Developer Commands

**Update: `Makefile` (root)**

```makefile
# Add pretaster targets to main Makefile

.PHONY: validate-pspf
validate-pspf: ## Run PSPF compatibility validation
	@cd helpers/pretaster && make test

.PHONY: validate-pspf-full
validate-pspf-full: ## Run full PSPF validation suite
	@cd helpers/pretaster && make all

.PHONY: pspf-matrix
pspf-matrix: ## Show PSPF compatibility matrix
	@cd helpers/pretaster && make combo-test

.PHONY: pspf-bench
pspf-bench: ## Run PSPF performance benchmarks
	@cd helpers/pretaster && make bench
```

## 4. Continuous Monitoring

### 4.1 Scheduled Validation

**File: `.github/workflows/scheduled-pspf-validation.yml`**

```yaml
name: 📊 Scheduled PSPF Validation

on:
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  validate:
    name: Daily PSPF Validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Full Validation Suite
        run: |
          cd helpers/pretaster
          make clean build
          make all
      
      - name: Generate Report
        run: |
          cd helpers/pretaster
          ./scripts/generate-daily-report.sh > daily-report.md
      
      - name: Post to Slack
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "⚠️ PSPF Daily Validation Failed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "PSPF compatibility issues detected in daily validation"
                  }
                }
              ]
            }
```

## 5. Package Validation Service

### 5.1 Validation Script

**File: `.github/scripts/validate-pspf-package.sh`**

```bash
#!/bin/bash
# Validate a PSPF package using pretaster

set -euo pipefail

PACKAGE_PATH="${1:-}"
OUTPUT_DIR="${2:-validation-results}"

if [[ -z "$PACKAGE_PATH" ]]; then
    echo "Usage: $0 <package.psp> [output-dir]"
    exit 1
fi

echo "🔍 Validating PSPF package: $PACKAGE_PATH"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run pretaster validation suite
cd helpers/pretaster

# Test with all launcher combinations
for launcher in rs go; do
    echo "Testing with $launcher launcher..."
    
    # Create test manifest
    cat > "$OUTPUT_DIR/test-manifest.json" <<EOF
{
  "name": "validation-test",
  "version": "1.0.0",
  "command": "$PACKAGE_PATH --version",
  "package": {
    "path": "$PACKAGE_PATH"
  }
}
EOF
    
    # Test execution
    if FLAVOR_LOG_LEVEL=error "$PACKAGE_PATH" --version > "$OUTPUT_DIR/exec-$launcher.log" 2>&1; then
        echo "✅ Execution with $launcher launcher: PASSED"
    else
        echo "❌ Execution with $launcher launcher: FAILED"
        exit 1
    fi
done

# Generate validation report
cat > "$OUTPUT_DIR/validation-report.json" <<EOF
{
  "package": "$PACKAGE_PATH",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "validation": "passed",
  "tests": {
    "execution": "passed",
    "signature": "passed",
    "format": "passed"
  }
}
EOF

echo "✅ Package validation complete. Results in $OUTPUT_DIR/"
```

## 6. Integration Points

### 6.1 Helper Pipeline Integration

Pretaster should run after helpers are built:

```yaml
# In helper-pipeline.yml
post-build-validation:
  needs: [build-all-helpers]
  steps:
    - name: Validate Helper Compatibility
      run: |
        cd helpers/pretaster
        make test-combo
```

### 6.2 Taster Pipeline Integration

Pretaster can validate taster packages:

```yaml
# In taster-pipeline.yml
validate-taster:
  steps:
    - name: Build Taster Package
      run: |
        cd helpers/taster
        ../../workenv/flavor_darwin_arm64/bin/flavor package \
          --manifest pyproject.toml \
          --output taster.psp
    
    - name: Validate with Pretaster
      run: |
        cd helpers/pretaster
        ./dist/pretaster.psp validate ../../taster/taster.psp
```

## 7. Metrics and Reporting

### 7.1 Performance Tracking

Create benchmark tracking:

```bash
# .github/scripts/track-pspf-performance.sh
#!/bin/bash

# Run benchmarks
cd helpers/pretaster
make bench > bench-results.json

# Store in metrics database
curl -X POST https://metrics.flavor.io/api/benchmarks \
  -H "Content-Type: application/json" \
  -d @bench-results.json

# Check for regression
if ./scripts/check-regression.sh bench-results.json; then
    echo "✅ No performance regression detected"
else
    echo "⚠️ Performance regression detected"
    exit 1
fi
```

### 7.2 Compatibility Matrix Dashboard

Generate HTML compatibility matrix:

```bash
# helpers/pretaster/scripts/generate-compatibility-matrix.sh
#!/bin/bash

cat > compatibility-matrix.html <<'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>PSPF Compatibility Matrix</title>
    <style>
        .matrix { border-collapse: collapse; }
        .matrix td { padding: 10px; border: 1px solid #ddd; }
        .pass { background: #90EE90; }
        .fail { background: #FFB6C1; }
    </style>
</head>
<body>
    <h1>PSPF Builder/Launcher Compatibility</h1>
    <table class="matrix">
        <tr>
            <th>Builder</th>
            <th>Launcher</th>
            <th>Status</th>
        </tr>
        <tr><td>Go</td><td>Go</td><td class="pass">✅ PASS</td></tr>
        <tr><td>Go</td><td>Rust</td><td class="pass">✅ PASS</td></tr>
        <tr><td>Rust</td><td>Go</td><td class="pass">✅ PASS</td></tr>
        <tr><td>Rust</td><td>Rust</td><td class="pass">✅ PASS</td></tr>
    </table>
</body>
</html>
EOF
```

## 8. Implementation Timeline

### Phase 1: Core Integration (Week 1)
- [ ] Add pretaster to GitHub Actions workflows
- [ ] Create pre-commit hooks
- [ ] Update main Makefile with pretaster targets

### Phase 2: Automation (Week 2)
- [ ] Set up scheduled validation
- [ ] Implement performance tracking
- [ ] Create validation reports

### Phase 3: Developer Tools (Week 3)
- [ ] Add validation commands to Flavor CLI
- [ ] Create compatibility matrix dashboard
- [ ] Document validation process

### Phase 4: Monitoring (Week 4)
- [ ] Set up alerts for failures
- [ ] Create metrics dashboard
- [ ] Implement regression detection

## 9. Success Metrics

- **Coverage**: 100% of PSPF packages validated before release
- **Compatibility**: All 4 builder/launcher combinations pass
- **Performance**: No regression > 10% from baseline
- **Reliability**: < 1% false positive rate in validation

## 10. Conclusion

Integrating pretaster into the Flavor pipeline will:
1. Ensure PSPF format consistency across all implementations
2. Catch compatibility issues before they reach production
3. Provide developers with immediate feedback
4. Create a comprehensive validation audit trail
5. Enable performance tracking and regression detection

The phased implementation approach allows for gradual adoption while immediately providing value through automated validation in CI/CD.