//! Flavor - Progressive Secure Package Format (PSPF) implementation
//!
//! This crate provides functionality for building, launching, and verifying
//! PSPF packages with support for multiple format versions.

// Enforce strict code quality and reliability
#![deny(
    // Safety
    unsafe_code,

    // Correctness
    missing_debug_implementations,
    unreachable_pub,

    // Future compatibility
    future_incompatible,

    // Rust 2018 idioms
    rust_2018_idioms,

    // All warnings must be fixed
    warnings,
)]
#![warn(
    // Documentation
    missing_docs,

    // Error handling best practices
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::unimplemented,
    clippy::todo,

    // Performance
    clippy::inefficient_to_string,
    clippy::large_enum_variant,

    // Code clarity and maintainability
    clippy::cognitive_complexity,
    clippy::too_many_arguments,
    clippy::type_complexity,

    // Best practices
    clippy::clone_on_ref_ptr,
    clippy::wildcard_imports,
    clippy::enum_glob_use,
    clippy::if_not_else,
    clippy::single_match_else,
    clippy::needless_continue,
    clippy::explicit_iter_loop,
    clippy::explicit_into_iter_loop,
)]
#![allow(
    // Temporarily allowed but should be fixed
    clippy::too_many_arguments,  // Some functions need refactoring
    missing_docs,  // TODO: Complete documentation
)]

pub mod api;
pub mod exceptions;
pub mod exit_codes;
pub mod logger;
pub mod psp;
pub mod utils;
pub mod version;

use std::sync::atomic::AtomicU32;

// Re-export main API functions
pub use api::{BuildOptions, LaunchOptions, build_package, launch_package, verify_package};
pub use exceptions::FlavorError;
pub use utils::get_platform_string;

// Re-export format-specific types for advanced usage
pub use psp::PackageFormat;
pub use psp::format_2025;

// Global state for signal handling (used by binary)
pub static CHILD_PID: AtomicU32 = AtomicU32::new(0);
