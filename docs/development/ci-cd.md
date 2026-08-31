# CI/CD Pipeline

## Overview

The Flavorpack CI/CD system consists of multiple independent GitHub Actions workflows that build, test, and validate the entire system across multiple platforms and language implementations.

## Workflow Architecture

```mermaid
graph LR
    A[01 helper-prep] --> B[Helper Artifacts]
    B --> C[02a pretaster-pipeline]
    B --> D[03 flavor-pipeline]
    D --> E[04 taster-pipeline]

    P[Pull request] --> Q[02b pr-pretaster]
    Q --> R[Helpers built from PR source]
    R --> F

    C --> F[Cross-Language Tests]
    D --> G[Python API Tests]
    E --> H[Integration Tests]

    F --> I{All Pass?}
    G --> I
    H --> I

    I -->|Yes| J[✅ Ready for Release]
    I -->|No| K[❌ Fix Issues]

    style A fill:#e3f2fd
    style P fill:#e3f2fd
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#fff3e0
    style Q fill:#fff3e0
    style J fill:#e8f5e9
    style K fill:#ffebee
```

Stage 02 exists twice on purpose. 02a runs after Helper Prep on main and
develop, consuming its published artifacts across the full platform matrix.
02b runs on every pull request, where those artifacts do not exist, so it
builds helpers from the PR's own source instead. 02a is the broad post-merge
sweep; 02b is the gate that stops a broken launcher reaching main.

### Design Principles

1. **Explicit Triggering**: The numbered pipeline stages are `workflow_dispatch`
   plus `workflow_run` chaining; the PR-facing workflows (02b, 05, 08) add
   `pull_request`
2. **Script Delegation**: Complex logic lives in `ci/`, not in workflow YAML —
   inline `run:` blocks are capped at three lines
3. **Artifact Sharing**: Workflows share build artifacts rather than calling each other
4. **Platform Coverage**: Multi-platform support (Linux, macOS, Windows*)

   *Windows temporarily disabled due to UTF-8 encoding issues

## Main Workflows

### 01 - Helper Prep

**File**: `.github/workflows/helper-prep.yml`

**Purpose**: Build and validate Go/Rust helpers for all platforms

**Key Features**:
- Builds helpers for multiple platforms using matrix strategy
- Creates versioned artifacts (e.g., `flavor-helpers-0.3.0-linux_amd64`)
- Validates helper functionality with basic tests
- Uploads artifacts for downstream workflows

**Platform Matrix**:
```json
[
  {"platform": "linux_amd64", "os": "ubuntu-24.04", "rust_target": "x86_64-unknown-linux-gnu"},
  {"platform": "linux_arm64", "os": "ubuntu-24.04", "rust_target": "aarch64-unknown-linux-gnu"},
  {"platform": "darwin_amd64", "os": "macos-13", "rust_target": "x86_64-apple-darwin"},
  {"platform": "darwin_arm64", "os": "macos-15", "rust_target": "aarch64-apple-darwin"}
]
```

### 02a - Pretaster Validation

**File**: `.github/workflows/pretaster-pipeline.yml`

**Purpose**: Validate cross-language compatibility after merge, on the full platform matrix

**Key Features**:
- Tests all builder/launcher combinations (4 total)
- Validates PSP execution and extraction
- Runs combination tests for cross-language support
- Provides honest validation output

**Test Matrix**:
- Go builder + Go launcher
- Go builder + Rust launcher  
- Rust builder + Go launcher
- Rust builder + Rust launcher

### 02b - Pretaster Validation (PR)

**File**: `.github/workflows/pr-pretaster.yml`

**Purpose**: Run the same suite on a pull request, before anything merges

**Why it is separate**: 02a downloads the helper artifacts published by 01, and
01 is `workflow_dispatch`-only, so a PR branch has nothing to download. This
workflow calls `ci/pr-pretaster.sh`, which runs `./build.sh` to compile helpers
from the PR's own tree, `uv sync` to install the `flavor` CLI the security
suite needs, and then the same `make -C tests/pretaster test` target.

**Key Features**:
- Matrix over ubuntu-24.04 and macos-14, `fail-fast: false` — a hardcoded
  platform path is invisible on one and fatal on the other
- `PRETASTER_STRICT=1`, which turns a skipped check into a failure: every
  prerequisite exists in CI, so a skip is a setup bug rather than "not
  applicable here"
- Uploads `tests/pretaster/logs/` on failure

**Scope**: Linux and macOS only. 02a keeps the wider matrix, FreeBSD included.

### 03 - Flavor Pipeline

**File**: `.github/workflows/flavor-pipeline.yml`

**Purpose**: Test the main Flavorpack Python package

**Key Features**:
- Runs comprehensive test suite with pytest
- Tests package building functionality
- Validates API consistency
- Generates coverage reports

### 04 - Taster Pipeline

**File**: `.github/workflows/taster-pipeline.yml`

**Purpose**: Test the Taster comprehensive test package

**Key Features**:
- Downloads helper artifacts from helper pipeline
- Builds Taster PSP package
- Runs comprehensive test suite
- Validates Python packaging functionality

### 05 - Code Quality

**File**: `.github/workflows/code-quality.yml`

**Purpose**: Enforce code quality standards

**Checks**:
- Python linting with ruff
- Type checking with mypy
- Code formatting validation
- Documentation standards

### 06 - Security Scan

**File**: `.github/workflows/security-scan.yml`

**Purpose**: Security vulnerability scanning

**Scans**:
- Dependency vulnerability checks
- SAST (Static Application Security Testing)
- Container image scanning (if applicable)
- Secret scanning

### 07 - Dependency Audit

**File**: `.github/workflows/dependency-audit.yml`

**Purpose**: Audit and validate dependencies

**Checks**:
- License compliance
- Outdated dependency detection
- Security advisory matching
- Dependency graph analysis

### 08 - License Compliance

**File**: `.github/workflows/license-compliance.yml`

**Purpose**: Ensure license compatibility

**Validates**:
- All dependencies have compatible licenses
- License headers in source files
- NOTICE file accuracy
- Third-party attribution

### 09 - Release Pipeline

**File**: `.github/workflows/release.yml`

**Purpose**: Build and publish a release

### Unnumbered workflows

- `build-go.yml`, `build-rust.yml`, `build-tastesh.yml` — reusable
  (`workflow_call`), invoked by the stages above rather than triggered directly
- `compatibility-check.yml` — daily container compatibility sweep
- `exp-freebsd.yml` — experimental FreeBSD builds, dispatch only

## Supporting Scripts

Workflow logic lives in `ci/`, which holds considerably more than the entries
below; these are the ones the numbered stages call directly.

### Build Scripts

**`ci/build-go-helpers.sh`**, **`ci/build-rust-helpers.sh`**
- Build the Go and Rust helpers for a target platform
- Handle cross-compilation settings, including the musl static build on Linux

**`ci/build-pretaster.sh`**
- Builds pretaster PSP package
- Creates test manifests dynamically
- Packages test scripts and configurations

### Test Scripts

**`ci/run-tests.sh`**
- Main test runner for Python tests
- Handles pytest configuration
- Collects test metadata and coverage

**`ci/run-pretaster-tests.sh`**
- Executes pretaster test suite
- Detects PSP execution context (FLAVOR_WORKENV)
- Provides honest validation output

**`ci/pr-pretaster.sh`**
- The entry point for 02b: builds helpers from the PR's own source, installs
  the `flavor` CLI, then runs the pretaster make target
- Exists because a PR has no Helper Prep artifacts to download

**`ci/test-metadata.py`**
- Collects and formats test metadata
- Handles Windows UTF-8 encoding
- Generates JSON reports for CI

### Utility Scripts

**`ci/quality-checks.sh`**
- The 05 gate: blocking checks (format, lint, types, clippy) exit non-zero;
  advisory ones report without failing the build

**`ci/get-version.sh`**
- Reads the version from the `VERSION` file, the single source of truth
- Used for artifact naming

## Artifact Management

### Naming Convention
```
flavor-helpers-{version}-{platform}
flavor-helpers-{version}-all
```

### Artifact Contents
- Platform-specific helper binaries
- Version-stamped for traceability
- Includes both builders and launchers

### Download Strategy
```yaml
- uses: dawidd6/action-download-artifact@v6
  with:
    workflow: helper-prep.yml
    name: flavor-helpers-0.3.0-linux_amd64
    path: ./helpers
    workflow_conclusion: success
```

## Environment Variables

### Build-Time Variables
- `FLAVOR_LAUNCHER_BIN` - Path to launcher binary
- `FLAVOR_WORKENV_BASE` - Base directory for workenv resolution
- `FLAVOR_LOG_LEVEL` - Logging verbosity (trace, debug, info, warn, error)

### Runtime Variables
- `FLAVOR_WORKENV` - Set by launcher when running as PSP
- `PYTHONUTF8=1` - Windows UTF-8 support
- `PYTHONIOENCODING=utf-8` - Windows encoding fix

## Local Testing with Act

[Act](https://github.com/nektos/act) allows running GitHub Actions locally:

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | bash

# Run a specific workflow
act -W .github/workflows/flavor-pipeline.yml

# Run with specific event
act workflow_dispatch -W .github/workflows/helper-prep.yml

# Run with secrets
act -s GITHUB_TOKEN=$GITHUB_TOKEN
```

## Windows Support

Currently disabled due to UTF-8 encoding issues with emoji characters in test scripts.

### Required Fixes for Re-enabling
1. Set UTF-8 environment variables before Python execution:
   ```bash
   export PYTHONUTF8=1
   export PYTHONIOENCODING=utf-8
   ```

2. Update test scripts to handle Windows paths correctly

3. Ensure all Python scripts use proper encoding declarations

## Testing Strategy

### Unit Tests
- Run via pytest in flavor pipeline
- Fast, isolated component tests
- Platform-independent

### Integration Tests
- Cross-language compatibility via pretaster
- PSP execution validation
- End-to-end packaging tests

### Validation Levels
1. **PSP Execution**: Proves package extracts and runs
2. **Command Validation**: Tests specific functionality
3. **Cross-Language**: Validates all combinations work

## Best Practices

### Workflow Design
1. Keep workflow YAML minimal — inline `run:` blocks are capped at three lines
2. Delegate to scripts in `ci/`
3. Use matrix strategies for multi-platform builds, with `fail-fast: false` so
   one platform's failure does not hide another's
4. Anything that must gate a merge needs a `pull_request` trigger; a
   `workflow_run` filtered to main can never fire on a PR branch

### Error Handling
1. Provide clear error messages
2. Use exit codes consistently
3. Log detailed information for debugging
4. Fail fast on critical errors

### Security
1. Use deterministic builds with `--key-seed`
2. Verify signatures in all tests
3. Never commit secrets or keys
4. Use GitHub Actions secrets for sensitive data

## Troubleshooting

### Common Issues

**Helper artifacts not found**
- Ensure helper pipeline ran successfully
- Check artifact names match expected pattern
- Verify workflow_conclusion is "success"

**Windows encoding errors**
- Set UTF-8 environment variables
- Check for emoji characters in scripts
- Use proper encoding declarations

**PSP execution fails**
- Verify helpers are built correctly
- Check manifest format (must be nested PSPF/2025)
- Ensure launcher binary is executable

### Debug Techniques

1. **Enable debug logging**:
   ```yaml
   env:
     FLAVOR_LOG_LEVEL: debug
   ```

2. **Check artifact contents**:
   ```bash
   unzip -l artifact.zip
   ```

3. **Validate manifest structure**:
   ```bash
   jq . manifest.json
   ```

4. **Test locally before CI**:
   ```bash
   ./build.sh                    # helpers for the host platform
   make -C tests/pretaster test  # the suite 02a and 02b both run
   ```

## Future Improvements

1. **Re-enable Windows Support**: Fix UTF-8 encoding issues
2. **Parallel Test Execution**: Run platform tests concurrently
3. **Caching Strategy**: Cache built helpers between runs
4. **Performance Metrics**: Add timing and size metrics
5. **Automated Releases**: Create releases from successful builds

## Related Documentation

- [Contributing Guide](contributing/)
- [Testing Guide](testing/index/)
- [Architecture](architecture/)
- [Release Process](release/)