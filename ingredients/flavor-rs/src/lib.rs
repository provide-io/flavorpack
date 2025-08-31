//! Flavor - Progressive Secure Package Format (PSPF) implementation
//!
//! This crate provides functionality for building, launching, and verifying
//! PSPF packages with support for multiple format versions.

pub mod api;
pub mod exceptions;
pub mod exit_codes;
pub mod logger;
pub mod psp;
pub mod utils;
pub mod version;

use std::sync::atomic::AtomicU32;

// Re-export main API functions
pub use api::{build_package, launch_package, verify_package, BuildOptions, LaunchOptions};
pub use exceptions::FlavorError;
pub use utils::get_platform_string;

// Re-export format-specific types for advanced usage
pub use psp::format_2025;
pub use psp::PackageFormat;

// Global state for signal handling (used by binary)
pub static CHILD_PID: AtomicU32 = AtomicU32::new(0);
