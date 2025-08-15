# Flavor Default Components Changed to Rust

As of this update, the default launcher and builder have been changed from Go to Rust.

## Changes Made:

1. **Default Launcher**: Changed from `go` to `rust` in:
   - `src/flavor/api.py` 
   - `src/flavor/cli.py`
   - `src/flavor/psp/format_2025/builder.py`
   - `src/flavor/packaging/orchestrator.py`

2. **Default Builder**: Changed to use Rust pspf-builder-rs by default in:
   - `src/flavor/packaging/orchestrator.py`

3. **Rust Package Names**: Updated to use "flavor" prefix:
   - `pspf-launcher-rs` → `flavor-launcher`
   - `pspf-builder-rs` → `flavor-builder`  
   - `pspf-common` → `flavor-common`

## Rationale:

The Rust implementation provides better argv[0] handling for launched processes. While the Go launcher has a limitation where it cannot properly set argv[0] (due to Go's exec.Command restrictions on Unix systems), the Rust launcher can use Unix-specific APIs to correctly set argv[0], allowing Python processes to see the original command name instead of the Python module path.

## Go Launcher Limitation:

The Go launcher includes this documented limitation in `src/flavor/go/cmd/pspf-launcher/main.go`:
- Cannot actually change what the subprocess sees as argv[0]
- The subprocess will always see the actual executable path (e.g., "/path/to/python")
- As a workaround, it sets FLAVOR_COMMAND_NAME and FLAVOR_ORIGINAL_COMMAND environment variables

## To Use Go Components:

You can still explicitly use Go components by setting:
- `--launcher go` when running `flavor package`
- Or set environment variable: `FLAVOR_LAUNCHER=go`