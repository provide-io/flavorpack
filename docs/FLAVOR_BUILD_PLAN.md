# Flavor Build Pipeline Implementation Plan

## Overview
Add Flavor and Taster build jobs to the helper pipeline to create a complete end-to-end validation cycle where helpers build Flavor, Flavor builds Taster, and Taster tests everything.

## Architecture Flow
```
Helper Build Jobs → Helper Tests → Combine Helpers
                                          ↓
                                   Build Flavor PSPs
                                          ↓
                                   Test with Taster
                                          ↓
                                   Combine & Validate
```

## Implementation Plan

### Phase 1: Build Scripts

#### 1.1 build-flavor.sh
Creates Flavor PSP packages using platform-specific helpers.
- Sets up Python workenv
- Installs Flavor in editable mode
- Extracts platform helpers from artifacts
- Builds `flavor-{version}-{platform}.psp[.exe]`
- Uses platform's own launcher

#### 1.2 test-flavor-with-taster.sh
Tests Flavor by building and running Taster.
- Installs Flavor from built PSP
- Builds Taster using the new Flavor
- Runs comprehensive Taster tests:
  - `time ./taster.psp --version` (startup performance)
  - `./taster.psp verify ../flavor-{version}-{platform}.psp`
  - `./taster.psp info`
  - `./taster.psp exit 0`
  - `./taster.psp file test`
  - `./taster.psp env`
  - `./taster.psp cache list`

### Phase 2: Workflow Jobs

#### 2.1 Build Flavor Jobs (5 platforms)
- build-flavor-linux-amd64
- build-flavor-linux-arm64
- build-flavor-darwin-amd64
- build-flavor-darwin-arm64
- build-flavor-windows-amd64

Each job:
- Downloads platform helper artifacts
- Sets up Python 3.11+
- Runs build-flavor.sh
- Runs test-flavor-with-taster.sh
- Uploads artifacts

#### 2.2 Combine Flavor Job
- Downloads all Flavor PSP artifacts
- Downloads all Taster PSP artifacts
- Creates checksums
- Uploads combined artifacts

#### 2.3 Update Validate Job
- Add dependency on combine-flavor
- Include Flavor/Taster validation
- Generate comprehensive report

## Detailed Implementation Checklist

### ✅ Completed Tasks
- [x] Create build-flavor.sh script
  - [x] Python environment setup
  - [x] Helper extraction logic
  - [x] Launcher selection
  - [x] Package building
  - [x] Basic testing

### ⏳ In Progress Tasks
- [ ] Create test-flavor-with-taster.sh script
  - [ ] Flavor installation from PSP
  - [ ] Taster build commands
  - [ ] Performance timing
  - [ ] Verification tests
  - [ ] Self-testing suite

### 📋 Pending Tasks

#### Scripts
- [ ] test-flavor-with-taster.sh implementation
  - [ ] Install Flavor from PSP
  - [ ] Install Taster dependencies
  - [ ] Build Taster package
  - [ ] Run timed tests
  - [ ] Verify Flavor artifact
  - [ ] Run self-tests

#### Workflow Jobs - Linux
- [ ] build-flavor-linux-amd64
  - [ ] Job configuration
  - [ ] Runner: ubuntu-latest
  - [ ] Download helpers
  - [ ] Run build script
  - [ ] Run test script
  - [ ] Upload artifacts

- [ ] build-flavor-linux-arm64
  - [ ] Job configuration
  - [ ] Runner: ubuntu-24.04-arm
  - [ ] Download helpers
  - [ ] Run build script
  - [ ] Run test script
  - [ ] Upload artifacts

#### Workflow Jobs - Darwin
- [ ] build-flavor-darwin-amd64
  - [ ] Job configuration
  - [ ] Runner: macos-13
  - [ ] Download helpers
  - [ ] Run build script
  - [ ] Run test script
  - [ ] Upload artifacts

- [ ] build-flavor-darwin-arm64
  - [ ] Job configuration
  - [ ] Runner: macos-15
  - [ ] Download helpers
  - [ ] Run build script
  - [ ] Run test script
  - [ ] Upload artifacts

#### Workflow Jobs - Windows
- [ ] build-flavor-windows-amd64
  - [ ] Job configuration
  - [ ] Runner: windows-2025
  - [ ] Download helpers
  - [ ] Run build script
  - [ ] Run test script
  - [ ] Upload artifacts

#### Combination & Validation
- [ ] combine-flavor job
  - [ ] Download all Flavor artifacts
  - [ ] Download all Taster artifacts
  - [ ] Generate checksums
  - [ ] Create combined archives
  - [ ] Upload final artifacts

- [ ] Update validate job
  - [ ] Add combine-flavor dependency
  - [ ] Download Flavor/Taster artifacts
  - [ ] Run validation scripts
  - [ ] Generate summary report

#### Testing & Verification
- [ ] Test workflow locally with act
- [ ] Trigger test run on CI
- [ ] Verify all artifacts created
- [ ] Check artifact structure
- [ ] Validate checksums
- [ ] Review pipeline summary

## Artifact Naming Convention

### Flavor Packages
- Linux AMD64: `flavor-{version}-linux_amd64.psp`
- Linux ARM64: `flavor-{version}-linux_arm64.psp`
- Darwin AMD64: `flavor-{version}-darwin_amd64.psp`
- Darwin ARM64: `flavor-{version}-darwin_arm64.psp`
- Windows AMD64: `flavor-{version}-windows_amd64.exe`

### Taster Packages
- Linux AMD64: `taster-{version}-linux_amd64.psp`
- Linux ARM64: `taster-{version}-linux_arm64.psp`
- Darwin AMD64: `taster-{version}-darwin_amd64.psp`
- Darwin ARM64: `taster-{version}-darwin_arm64.psp`
- Windows AMD64: `taster-{version}-windows_amd64.exe`

### Combined Artifacts
- `flavor-{version}-all` - All Flavor packages
- `taster-{version}-all` - All Taster packages
- `flavor-checksums-{version}.txt` - SHA256 checksums
- `taster-checksums-{version}.txt` - SHA256 checksums

## Success Criteria

1. **Helper Build**: All platform helpers build successfully
2. **Flavor Build**: Flavor PSPs created for all platforms
3. **Taster Build**: Taster built using new Flavor on all platforms
4. **Verification**: Taster verifies Flavor package integrity
5. **Self-Test**: Taster passes all self-tests
6. **Performance**: Startup time < 2 seconds
7. **Artifacts**: All artifacts uploaded and downloadable
8. **Validation**: Final validation report shows all green

## Notes

- Use deterministic key seeds for reproducible builds
- Windows outputs have .exe extension automatically
- Each platform uses its own helpers (no cross-compilation)
- Taster is the ultimate test - if it works, everything works
- All scripts must handle both Unix and Windows paths
- Use pip3 for wheel operations, uv for package installation