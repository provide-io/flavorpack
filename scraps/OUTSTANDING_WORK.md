# Outstanding Work for Flavor Project

## 🔴 Critical Priority Items

### 1. Test Suite Integrity
- **Issue**: 17+ tests have "In real implementation" placeholder comments
- **Impact**: Tests aren't validating actual behavior, giving false confidence
- **Affected Files**:
  - `test_pspf_2025_execution.py` (6 occurrences)
  - `test_pspf_2025_security.py` (4 occurrences)
  - `test_pspf_2025_builder.py` (3 occurrences)
- **Action Required**: Replace all placeholder implementations with real test logic

### 2. Reproducible Builds
- **Issue**: Each build produces different bundles due to random ephemeral keys, emoji selection, and timestamps
- **Impact**: Cannot verify builds or create deterministic packages
- **Solution**:
  - Add `--reproducible` flag that uses deterministic values
  - Use SOURCE_DATE_EPOCH for timestamps
  - Derive ephemeral keys from content hash

### 3. Feature Parity (Go vs Rust)
**Current Status**: 55.2% parity (16/29 features matching)

#### Missing in Go Implementation:
- **Runtime Environment**:
  - ✅ Glob patterns in unset/pass (just implemented)
  - ✅ Whitelist mode (unset=*) (just implemented)
- **Process Management**:
  - ❌ argv[0] setting (Go limitation - cannot be fixed)
  - ❌ Signal forwarding (SIGTERM/SIGINT)
  - ❌ Graceful shutdown
  - ❌ Process cleanup
- **Concurrency & Reliability**:
  - ❌ Lock files (.extraction.lock)
  - ❌ Stale lock detection
  - ❌ Incomplete extraction handling
  - ❌ PID-based lock validation
- **Observability**:
  - ❌ JSON logging
  - ❌ Structured log output
  - ❌ Log file output

## 🟡 Important - Architecture & Design

### 1. Multi-Layer Signing Strategy
- **Issue**: Tests suggest both integrity seals AND trust signatures
- **Questions**:
  - When are trust signatures used vs integrity seals?
  - Should persistent keys be supported alongside ephemeral?
  - How to handle key rotation and revocation?

### 2. Cross-Language Test Vectors
- **Problem**: Each language has separate tests
- **Solution**: Create shared JSON test vectors for binary compatibility

## 🟢 Nice to Have - Code Quality

### 1. Implement enumerate_and_execute Setup Command
- **Current**: Placeholder warning in launcher
- **Use Case**: Running setup on multiple matching files

### 2. Improve Tarball Extraction Validation
- **Current**: Extracts tarballs without validation
- **Risks**: Path traversal, symlink attacks
- **Add**: Sandbox extraction, path validation

### 3. Add Slot Purpose Extensibility
- **Current**: Maps unknown purposes to "payload"
- **Better**: Formal extension mechanism

## 📊 Test Coverage Gaps

### Current Test Failures (12 remaining)
- Slot lifecycle tests (6 failures - incorrect extract_slot calls)
- Cross-language builder/launcher tests (6 failures - Go/Rust combinations)

## 🏗️ Technical Debt

- Missing error handling in setup commands
- No timeout handling in process execution
- No resource limits for extraction/execution
- Potential unwrap() issues in Rust code (21 instances that could panic)

## 📚 Documentation Needs

1. **Compression/Encoding Field**: Document value 2+ as reserved
2. **Signing Architecture**: When to use ephemeral vs persistent keys
3. **Reproducible Build Guide**: How to achieve reproducibility
4. **Cross-Language Compatibility**: Binary format guarantees

## 🛡️ Security Hardening (for 1.0 Release)

### Critical Security Tasks
- [ ] Remove FLAVOR_INSECURE from production builds
- [ ] Implement secure key storage (not in environment variables)
- [ ] Add key rotation mechanism
- [ ] Implement reproducible builds
- [ ] Add dependency vulnerability scanning

### Runtime Security
- [ ] Implement seccomp filters for Linux
- [ ] Add AppArmor/SELinux profiles
- [ ] Implement process isolation
- [ ] Add memory protection (ASLR, DEP, PIE)

## 🚀 Production Readiness

### Must-Have for 1.0
- [ ] Self-update capability
- [ ] Rollback mechanism
- [ ] Prometheus metrics integration
- [ ] Proxy support (HTTP/HTTPS/SOCKS)
- [ ] Custom CA certificates
- [ ] Air-gapped installation support

### Platform Support
- [ ] Windows native testing (currently untested)
- [ ] Linux distributions (Ubuntu, RHEL, Alpine)
- [ ] ARM64 Linux testing
- [ ] FreeBSD compatibility

## 📈 Performance Optimization

- Large binary sizes (Go launcher: 4.7MB, Rust launcher: 2.5MB)
- No optimization for repeated extractions
- Python runtime included in every package (~20MB)
- Need to test with large packages (>1GB)
- Need to test with many small files (10,000+)

## 🎯 Priority Order

1. **Fix placeholder tests** - Test integrity is critical
2. **Reproducible builds** - Security & verifiability 
3. **Complete Go feature parity** - Where possible (excluding argv[0])
4. **Fix remaining test failures** - 12 tests failing
5. **Security hardening** - For production readiness