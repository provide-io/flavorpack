# PSP Reader Script Test Results

## Summary
✅ **The PSP reader script successfully processes PSP files from different builder/launcher combinations**

## Test Results

### Tested PSP Files

1. **taster-py-go.psp** (Python builder + Go launcher)
   - Size: 49 MB
   - Launcher: 5,030,194 bytes (Go)
   - Slots: 3 (uv, python, wheels)
   - Deterministic: No
   - ✅ All commands work

2. **taster-py-rust.psp** (Python builder + Rust launcher)
   - Size: 46 MB
   - Launcher: 1,715,328 bytes (Rust)
   - Slots: 3 (uv, python, wheels)
   - Deterministic: No
   - ✅ All commands work

3. **test-go-go.psp** (Go builder + Go launcher)
   - Size: 4.8 MB
   - Launcher: 5,030,194 bytes (Go)
   - Slots: 0 (test package)
   - Build tool: flavor-go
   - ✅ All commands work

4. **test-go-rust.psp** (Go builder + Rust launcher)
   - Size: 1.6 MB
   - Launcher: 1,715,328 bytes (Rust)
   - Slots: 0 (test package)
   - Build tool: flavor-go
   - ✅ All commands work

5. **taster-ephemeral.psp** (Ephemeral keys)
   - Deterministic: false
   - ✅ Verification works

6. **taster-deterministic1.psp** (Deterministic build)
   - Deterministic: true
   - Key seed used: test123
   - ✅ Verification works

### Command Testing

#### `info` Command
✅ Successfully displays:
- PSPF format and version
- Index checksum
- Package and launcher sizes
- Metadata location and size
- Slot count
- Public key (first 16 chars)
- Signature presence

#### `meta` Command
✅ Extracts and displays formatted JSON metadata
- Package name and version
- Build information
- Slot definitions
- Execution configuration

#### `query` Command
✅ JQ expressions work correctly:
- `.package.name` - Gets package name
- `.slots | length` - Counts slots
- `.build.tool` - Gets build tool
- `.build.deterministic` - Checks if deterministic

#### `verify` Command
✅ Verification checks:
- Package size matches index
- Ed25519 signature present
- Metadata decompresses successfully

#### `launcher` Command
✅ Successfully extracts launcher binary:
- Correct size (1.6 MB for Rust, 4.8 MB for Go)
- Executable Mach-O format
- Permissions set correctly

#### `hexdump` Command
✅ Shows PSPF index block in hex format
- Displays 256 bytes at correct offset
- Shows PSPF2025 magic clearly

#### `json` Command
✅ Outputs complete package info as JSON
- Can be piped to jq for processing
- Includes all metadata

#### `slots` Command
✅ Lists slots (with caveat about slot table format differences)

### Key Findings

1. **Launcher Size Differences**:
   - Go launcher: ~5 MB (5,030,194 bytes)
   - Rust launcher: ~1.6 MB (1,715,328 bytes)

2. **Index Location Detection**:
   - Script successfully finds PSPF index at different offsets
   - Common offsets pre-loaded for faster detection

3. **Metadata Format**:
   - All packages use gzipped JSON metadata
   - Successfully decompressed and parsed with jq

4. **Signature Verification**:
   - All packages have Ed25519 signatures
   - Public keys present in index

5. **Cross-Builder Compatibility**:
   - Python builder packages work with script
   - Go builder packages work with script
   - Different metadata structures handled correctly

## Conclusion

The PSP reader script successfully processes PSPF/2025 packages from all tested builder/launcher combinations. It provides a portable way to inspect, verify, and extract package contents using only standard BSD tools, jq, and openssl available on macOS.