//! Standard exit codes for Flavor binaries
//!
//! These exit codes are used by both builder and launcher to provide
//! consistent error reporting across the Flavor ecosystem.

/// Successful execution
pub const EXIT_SUCCESS: i32 = 0;

/// Generic error (avoid using - be more specific)
pub const EXIT_ERROR: i32 = 1;

/// Panic or unrecoverable error
pub const EXIT_PANIC: i32 = 101;

/// PSPF format error (invalid package structure, corrupt data)
pub const EXIT_PSPF_ERROR: i32 = 102;

/// Extraction error (failed to extract slots, disk space, permissions)
pub const EXIT_EXTRACTION_ERROR: i32 = 103;

/// Execution error (failed to spawn process, missing interpreter)
pub const EXIT_EXECUTION_ERROR: i32 = 104;

/// Invalid command-line arguments
pub const EXIT_INVALID_ARGS: i32 = 105;

/// I/O error (file not found, permission denied, disk error)
pub const EXIT_IO_ERROR: i32 = 106;

/// Signature verification failed
pub const EXIT_SIGNATURE_ERROR: i32 = 107;

/// Build/packaging error (builder-specific)
pub const EXIT_BUILD_ERROR: i32 = 108;

/// Configuration error (invalid manifest, missing required fields)
pub const EXIT_CONFIG_ERROR: i32 = 109;

/// Dependency error (missing required tools or libraries)
pub const EXIT_DEPENDENCY_ERROR: i32 = 110;
