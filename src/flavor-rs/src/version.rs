//! Version information for Flavor binaries

/// Current version of Flavor Rust implementation
pub const VERSION: &str = "0.3.0";

/// Build timestamp (set at compile time)
pub const BUILD_TIME: Option<&str> = option_env!("BUILD_TIME");

/// Git commit hash (set at compile time)
pub const GIT_COMMIT: Option<&str> = option_env!("GIT_COMMIT");

/// Get full version string with optional build information
pub fn full_version() -> String {
    let mut version = VERSION.to_string();

    if let Some(commit) = GIT_COMMIT {
        version.push_str(&format!(" ({})", &commit[..8.min(commit.len())]));
    }

    if let Some(time) = BUILD_TIME {
        version.push_str(&format!(" built {}", time));
    }

    version
}
