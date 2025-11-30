//! Utility functions for flavor

pub mod xor;

use std::env;

// Re-export XOR functions for convenience
pub use xor::{XOR_KEY, xor_decode_default, xor_encode_default};

/// Check if an environment variable is set to a truthy value
/// Accepts: "1", "true", "on", "yes", "t" (case insensitive)
pub fn is_env_true(key: &str) -> bool {
    match env::var(key) {
        Ok(val) => {
            let val_lower = val.to_lowercase();
            matches!(val_lower.as_str(), "1" | "true" | "on" | "yes" | "t")
        }
        Err(_) => false,
    }
}

/// Get normalized platform string in format 'os_arch'
///
/// Returns strings like:
/// - "darwin_arm64" for macOS ARM64
/// - "linux_amd64" for Linux x86_64
/// - "windows_amd64" for Windows x86_64
pub fn get_platform_string() -> String {
    let os = match env::consts::OS {
        "macos" => "darwin",
        other => other,
    };

    let arch = match env::consts::ARCH {
        "x86_64" => "amd64",
        "aarch64" => "arm64",
        other => other,
    };

    format!("{os}_{arch}")
}

/// Get the appropriate cache directory for the current platform
/// Uses XDG Base Directory Specification for consistency across all platforms
pub fn get_cache_dir() -> std::path::PathBuf {
    use std::path::PathBuf;

    if let Ok(cache_dir) = env::var("FLAVOR_CACHE") {
        return PathBuf::from(cache_dir);
    }

    // Use XDG_CACHE_HOME if set, otherwise ~/.cache
    // This provides consistency across all Unix-like platforms (Linux, macOS, BSDs)
    if let Ok(xdg_cache) = env::var("XDG_CACHE_HOME") {
        return PathBuf::from(xdg_cache).join("flavor");
    }

    if let Some(home) = env::var_os("HOME") {
        return PathBuf::from(home).join(".cache/flavor");
    }

    #[cfg(target_os = "windows")]
    {
        if let Ok(local_app_data) = env::var("LOCALAPPDATA") {
            return PathBuf::from(local_app_data).join("flavor/cache");
        }
    }

    // Fallback to temp directory
    env::temp_dir().join("flavor")
}
