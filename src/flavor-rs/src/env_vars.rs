// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! Centralized FLAVOR_* environment variable name constants.
//! All env var names must be referenced via these constants, never as inline strings.

/// Log level for both launcher and builder
pub const LOG_LEVEL: &str = "FLAVOR_LOG_LEVEL";
/// Log level override for launcher only
pub const LAUNCHER_LOG_LEVEL: &str = "FLAVOR_LAUNCHER_LOG_LEVEL";
/// Path to write log file
pub const LOG_PATH: &str = "FLAVOR_LOG_PATH";

/// Cache directory (matches FLAVOR_CACHE_DIR in Go)
pub const CACHE_DIR: &str = "FLAVOR_CACHE_DIR";
/// Configuration directory
pub const CONFIG_DIR: &str = "FLAVOR_CONFIG_DIR";
/// Directory containing trusted public keys
pub const TRUSTED_KEYS_DIR: &str = "FLAVOR_TRUSTED_KEYS_DIR";

/// Override workenv extraction directory
pub const WORKENV: &str = "FLAVOR_WORKENV";
/// Disable workenv caching when set to "0" or "false"
pub const WORKENV_CACHE: &str = "FLAVOR_WORKENV_CACHE";
/// Base directory for {workenv} resolution
pub const WORKENV_BASE: &str = "FLAVOR_WORKENV_BASE";

/// Execution mode: "exec" (default) or "spawn"
pub const EXEC_MODE: &str = "FLAVOR_EXEC_MODE";
/// Path to launcher binary
pub const LAUNCHER_BIN: &str = "FLAVOR_LAUNCHER_BIN";
/// Enable CLI mode in launcher
pub const LAUNCHER_CLI: &str = "FLAVOR_LAUNCHER_CLI";
/// Validation strictness: "strict", "relaxed", "none"
pub const VALIDATION: &str = "FLAVOR_VALIDATION";

/// Enable metadata debug output in reader
pub const DEBUG_METADATA: &str = "FLAVOR_DEBUG_METADATA";

// Logging (builder-specific)
/// Log level override for builder only
pub const BUILDER_LOG_LEVEL: &str = "FLAVOR_BUILDER_LOG_LEVEL";
/// Enable JSON-formatted log output
pub const JSON_LOG: &str = "FLAVOR_JSON_LOG";

// Execution keys
/// Deterministic key seed for signing
pub const KEY_SEED: &str = "FLAVOR_KEY_SEED";

// Launcher IPC / CLI mode
/// Additional launcher arguments
pub const LAUNCHER_ARGS: &str = "FLAVOR_LAUNCHER_ARGS";
/// Bundle path for launcher
pub const LAUNCHER_BUNDLE: &str = "FLAVOR_LAUNCHER_BUNDLE";
/// Launcher mode (e.g., "extract", "exec")
pub const LAUNCHER_MODE: &str = "FLAVOR_LAUNCHER_MODE";
/// Helper binary path for launcher
pub const LAUNCHER_HELPER: &str = "FLAVOR_LAUNCHER_HELPER";
/// Subprocess binary path for launcher
pub const LAUNCHER_SUBPROCESS: &str = "FLAVOR_LAUNCHER_SUBPROCESS";
/// Spawn-exit helper binary path
pub const LAUNCHER_SPAWN_EXIT_HELPER: &str = "FLAVOR_LAUNCHER_SPAWN_EXIT_HELPER";

// Runtime env vars injected into the child process
// Note: FLAVOR_CACHE is Go-only (injected into child process at launch);
// Rust uses FLAVOR_CACHE_DIR (the cache directory path) instead.

/// Binary name passed to launched process
pub const COMMAND_NAME: &str = "FLAVOR_COMMAND_NAME";
/// Original command path passed to launched process
pub const ORIGINAL_COMMAND: &str = "FLAVOR_ORIGINAL_COMMAND";
