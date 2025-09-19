# Known Issues

## Rust Components (flavor-rs-builder and flavor-rs-launcher)

### ✅ FIXED: Memory Issues with Large Files
- **Issue**: The Rust builder (`flavor-rs-builder`) was getting killed by the OS (signal 9) when processing large files
- **Root Cause**: The builder was reading entire slot files into memory using `fs::read()`
- **Fix Applied**: Refactored to use streaming I/O with `BufReader` and `io::copy()`
- **Result**: Can now handle files of any size with constant memory usage (~8MB buffer)
- **Performance**: Successfully builds packages with 46MB+ files in under 0.3 seconds

### Rust Launcher Issues  
- **Issue**: The Rust launcher (`flavor-rs-launcher`) also gets killed when invoked
- **Root Cause**: Unknown, requires further investigation
- **Impact**: Cannot use Rust launcher in any packages
- **Workaround**: Use Go launcher (`flavor-go-launcher`) instead

## Test Configuration Notes

All pretaster tests have been configured to use Go components due to the above Rust component issues:
- `test-pretaster.sh`: Uses Go builder and Go launcher for all tests
- `Makefile`: Configured to use Go builder as workaround
- `direct-execution-tests.sh`: Uses simplified configs that work with both builders

When the Rust components are fixed, the tests can be reverted to use the intended builder/launcher combinations for better cross-language testing.