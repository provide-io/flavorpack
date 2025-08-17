# Code Review: Duplicate and Stale Logic Issues

## Critical Issues

### 1. **DUPLICATE CRYPTO IMPLEMENTATIONS** 🔴
**Files affected:**
- `src/flavor/crypto.py` - Uses ECDSA P-256 (OUTDATED, but STILL IN USE!)
- `src/flavor/packaging/keys.py` - Uses ECDSA P-256 (OUTDATED)
- `src/flavor/psp/format_2025/crypto.py` - Uses Ed25519 (CORRECT)
- `src/flavor/packaging/python_packager.py` line 165 - USES the old crypto.py!

**Problem:** We have THREE different crypto implementations! The old modules use ECDSA P-256, but the spec requires Ed25519. Even worse, `python_packager.py` is actively using the wrong crypto!

**Impact:** 
- The keygen command generates ECDSA keys that are incompatible with the actual PSPF format
- The python_packager.compute_signature() method signs with ECDSA instead of Ed25519
- However, this signature appears to be written to a file but may not actually be used by builders

**Fix Required:**
- Update `src/flavor/packaging/python_packager.py` to remove compute_signature() method entirely (builders handle signing)
- Delete `src/flavor/crypto.py` after removing its usage
- Update `src/flavor/packaging/keys.py` to use Ed25519
- Update `src/flavor/commands/keygen.py` documentation

### 2. **STALE "EPHEMERAL" TERMINOLOGY** 🟡
**Files affected:**
- `src/flavor/inspect.py` lines 186-196

**Problem:** Still references "ephemeral_keys" and "EphemeralPublicKey" which is outdated terminology. The spec now just calls them "PublicKey" since keys aren't necessarily ephemeral.

**Fix Required:**
- Update to use "public_key" instead of "ephemeral_key"
- Remove references to "ephemeral_keys" in metadata

### 3. **INCORRECT MAGIC SIZE COMMENT** 🟡
**Files affected:**
- `src/flavor/psp/format_2025/reader.py` line 117

**Problem:** Comment says "first 8 bytes of 16-byte magic" but magic is only 8 bytes total.

**Fix Required:**
- Update comment to "Look for PSPF magic (8 bytes)"

## Duplicate Logic Issues

### 4. **SUBPROCESS EXECUTION** 🟡
**Multiple implementations:**
- `src/flavor/packaging/util.py::run_subprocess()` - Main implementation
- `src/flavor/psp/format_2025/launcher.py::_run_setup_commands()` - Inline subprocess.run
- `src/flavor/psp/format_2025/executor.py` - Another subprocess.run implementation
- `src/flavor/optimization.py` - Direct subprocess.run calls
- `src/flavor/helpers.py` - Direct subprocess.run calls

**Problem:** Inconsistent error handling and logging across implementations.

**Fix Required:**
- Standardize on `packaging.util.run_subprocess()` for all subprocess calls
- Add a simpler variant for cases that don't need full error handling

### 5. **VERIFICATION LOGIC** 🟡
**Multiple implementations:**
- `src/flavor/verification.py::FlavorVerifier` - High-level verifier
- `src/flavor/psp/format_2025/reader.py::verify_integrity()` - Low-level verification
- `src/flavor/api.py::verify_package()` - API wrapper

**Problem:** Three layers of verification wrappers, potentially confusing.

**Assessment:** This is actually OK - proper separation of concerns.

## Minor Issues

### 6. **UNUSED IMPORTS AND DEAD CODE** 🟢
**Files with issues:**
- `src/flavor/crypto.py` - Entire file appears unused
- Various files may have unused imports after refactoring

**Fix Required:**
- Delete `src/flavor/crypto.py`
- Run import cleanup tool

### 7. **INCONSISTENT CHECKSUM NAMING** 🟢
**Observation:** Code correctly uses Adler-32 everywhere, but constants file has both CHECKSUM_ADLER32 and CHECKSUM_CRC32 defined.

**Assessment:** This is OK - they're defined for future extensibility.

## Summary of Required Actions

### High Priority (Breaking Issues):
1. **Fix crypto implementations** - Update keygen to use Ed25519
2. **Delete stale crypto.py** - Remove entirely

### Medium Priority (Confusing but not breaking):
3. **Update ephemeral terminology** - Change to "public_key"
4. **Fix magic size comment** - Correct the misleading comment
5. **Standardize subprocess calls** - Use util.run_subprocess consistently

### Low Priority (Cleanup):
6. **Remove unused imports** - Run cleanup tool
7. **Add deprecation warnings** - For any old functions still in use

## Specific File Changes Needed

### 1. `src/flavor/packaging/keys.py`
```python
# Replace ECDSA implementation with:
from cryptography.hazmat.primitives.asymmetric import ed25519

def generate_key_pair(keys_dir: Path) -> tuple[Path, Path]:
    """Generates a new Ed25519 key pair and saves them to the specified directory."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    # ... save as PEM with proper Ed25519 format
```

### 2. `src/flavor/commands/keygen.py`
```python
# Update docstring:
"""Generates an Ed25519 key pair for package integrity signing."""
```

### 3. `src/flavor/inspect.py`
```python
# Update lines 186-196:
security["public_key"] = None  # not "ephemeral_key"
# Check for public key in metadata
if "public_key" in metadata:  # not "ephemeral_keys"
```

### 4. `src/flavor/psp/format_2025/reader.py`
```python
# Line 117:
# Look for PSPF magic (8 bytes)
```

### 5. Delete entirely:
- `src/flavor/crypto.py`

## Testing Impact

After these changes:
- Run all crypto-related tests
- Test keygen command
- Test package signing and verification
- Ensure cross-language compatibility with Go/Rust implementations

## Code Quality Metrics

### Duplication Found:
- **3 crypto implementations** (should be 1)
- **5+ subprocess.run patterns** (should use util function)
- **2 key generation systems** (ECDSA vs Ed25519)

### Stale Code Found:
- Ephemeral key terminology (spec changed)
- ECDSA crypto (spec requires Ed25519)
- 16-byte magic comments (magic is 8 bytes)
- Unused signature.bin file generation

### Security Issues:
- **CRITICAL**: Wrong signature algorithm (ECDSA instead of Ed25519)
- Keys generated by keygen command won't work with actual packages

### Positive Findings:
- Checksum implementation is consistent (Adler-32)
- Index size is consistent (8192 bytes)
- Verification logic is properly layered
- Format constants are well-defined
- Cross-language compatibility is maintained in the actual builders

## Recommended Priority

1. **IMMEDIATE**: Fix crypto to use Ed25519 everywhere
2. **HIGH**: Remove stale ECDSA code
3. **MEDIUM**: Update terminology and comments
4. **LOW**: Consolidate subprocess handling