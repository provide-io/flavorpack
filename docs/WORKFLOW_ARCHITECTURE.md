# GitHub Workflow Architecture

## Overview
The workflow system uses a **separated architecture** where helper builds are completely independent from the main CI pipeline.

## Workflow Separation

```
┌─────────────────────────────────────────────────────────────────┐
│                     🔨 HELPER PIPELINE                          │
│                  (build-helpers.yml)                            │
├─────────────────────────────────────────────────────────────────┤
│ Purpose: Build and test helper binaries                         │
│ Triggers:                                                       │
│   - Changes to helpers/** code                                  │
│   - Manual workflow_dispatch                                    │
│   - Can be called by other workflows                           │
│ Outputs:                                                        │
│   - helpers-{sha} artifact containing all binaries             │
└─────────────────────────────────────────────────────────────────┘
                              ⬇️
                     Creates Artifacts
                              ⬇️
┌─────────────────────────────────────────────────────────────────┐
│                        🎯 MAIN CI                               │
│                      (main-ci.yml)                              │
├─────────────────────────────────────────────────────────────────┤
│ Purpose: Run tests using existing helper artifacts              │
│ Triggers:                                                       │
│   - Push to main/feature branches                              │
│   - Pull requests                                              │
│   - Manual workflow_dispatch                                    │
│ Behavior:                                                       │
│   - Checks if helper artifacts exist for current SHA           │
│   - If yes: Downloads and uses them                            │
│   - If no: Skips tests requiring helpers OR notifies          │
│   - NEVER builds helpers itself                                │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. Complete Separation
- **Helper Pipeline** is 100% independent
- **Main CI** never triggers helper builds
- Each workflow has its own triggers and lifecycle

### 2. Artifact-Based Communication
- Helper Pipeline produces `helpers-{sha}` artifacts
- Main CI checks for and uses these artifacts if available
- No direct workflow dependencies

### 3. Graceful Degradation
- If helpers aren't available, Main CI can:
  - Skip tests that require helpers
  - Run Python unit tests without helpers
  - Notify developers that helpers need building

## Workflow Details

### 🔨 Helper Pipeline (`build-helpers.yml`)

**When it runs:**
- On push to `helpers/**` directories
- On manual trigger via workflow_dispatch
- When called by other workflows (workflow_call)

**What it does:**
1. Checks if artifacts already exist for the commit
2. If not, builds all helpers (Go + Rust) for all platforms
3. Runs tests on the built helpers
4. Uploads `helpers-{sha}` artifact
5. Artifacts are retained for reuse

**Key features:**
- Smart caching to avoid rebuilds
- Cross-platform builds (Linux, macOS, Windows)
- Can force rebuild with `force_rebuild` input

### 🎯 Main CI (`main-ci.yml`)

**When it runs:**
- On every push to main/feature branches
- On pull requests
- On manual trigger

**What it does:**
1. Detects what changed (Python code, tests, etc.)
2. Checks if helper artifacts exist for current SHA
3. Runs Python tests (with or without helpers)
4. Runs Taster tests (only if helpers available)
5. Generates summary report

**Key features:**
- Never builds helpers
- Works with or without helper artifacts
- Clear notifications when helpers need building

## Usage Scenarios

### Scenario 1: Developer Changes Python Code Only
1. Push triggers Main CI
2. Main CI checks for helper artifacts (likely exist from previous builds)
3. Downloads helpers and runs all tests
4. ✅ Everything works seamlessly

### Scenario 2: Developer Changes Helper Code
1. Push triggers BOTH workflows:
   - Helper Pipeline starts building new helpers
   - Main CI checks for artifacts (won't exist yet)
2. Main CI notifies that helpers are being built
3. Helper Pipeline completes and creates artifacts
4. Developer can re-run Main CI or it will work on next push

### Scenario 3: Fresh Clone or New Branch
1. No helper artifacts exist initially
2. Developer manually triggers Helper Pipeline
3. Once complete, all subsequent CI runs use those artifacts

## Commands

### Building Helpers
```bash
# Manually trigger helper build
gh workflow run build-helpers.yml

# Force rebuild even if artifacts exist
gh workflow run build-helpers.yml -f force_rebuild=true
```

### Running Main CI
```bash
# Manually trigger main CI
gh workflow run main-ci.yml

# Run with specific options
gh workflow run main-ci.yml \
  -f run_python_tests=true \
  -f run_taster_tests=true \
  -f platforms=linux,macos
```

### Checking Artifact Status
```bash
# List artifacts for current commit
gh api repos/:owner/:repo/actions/artifacts \
  --jq '.artifacts[] | select(.name | startswith("helpers-"))'

# Download helpers locally
gh run download --name helpers-$(git rev-parse HEAD)
```

## Benefits of This Architecture

1. **Clear Separation of Concerns**
   - Helper builds are isolated from test runs
   - Each workflow has a single responsibility

2. **Efficiency**
   - Helpers only rebuild when needed
   - Tests can run without waiting for helper builds
   - Artifacts are reused across multiple CI runs

3. **Flexibility**
   - Can manually trigger helper builds
   - Can run tests with specific helper versions
   - Easy to add new test workflows that use helpers

4. **Reliability**
   - No complex workflow dependencies
   - Clear failure modes
   - Easy to debug and understand

## Migration Notes

If you're coming from the old integrated system:
- The `main-coordinator.yml` is replaced by `main-ci.yml`
- The `helper-pipeline.yml` that was called by coordinator is now standalone as `build-helpers.yml`
- Helper artifacts are now named `helpers-{sha}` instead of `all-helpers-{sha}`
- Tests gracefully handle missing helpers instead of failing