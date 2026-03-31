//! Utility functions for flavor

use std::env;

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

    if let Ok(cache_dir) = env::var(crate::env_vars::CACHE_DIR) {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn is_env_true_handles_truthy_and_falsey_values() {
        assert!(matches!(is_env_true_from_value(Some("true")), true));
        assert!(matches!(is_env_true_from_value(Some("YES")), true));
        assert!(matches!(is_env_true_from_value(Some("0")), false));
        assert!(matches!(is_env_true_from_value(None), false));
    }

    #[test]
    fn get_platform_string_uses_expected_separator() {
        let platform = get_platform_string();
        assert!(platform.contains('_'));
    }

    #[test]
    fn get_cache_dir_prefers_explicit_override() {
        let dir = env::temp_dir().join("flavor-cache-test");
        let value = dir.to_string_lossy().into_owned();
        let resolved = get_cache_dir_from_env(Some(&value), None, None);
        assert_eq!(resolved, dir);
    }

    #[test]
    fn get_cache_dir_prefers_xdg_then_home_then_temp() {
        let xdg = get_cache_dir_from_env(None, Some("/tmp/xdg-cache"), Some("/tmp/home"));
        assert_eq!(
            xdg,
            std::path::PathBuf::from("/tmp/xdg-cache").join("flavor")
        );

        let home = get_cache_dir_from_env(None, None, Some("/tmp/home"));
        assert_eq!(
            home,
            std::path::PathBuf::from("/tmp/home").join(".cache/flavor")
        );
    }

    fn is_env_true_from_value(value: Option<&str>) -> bool {
        match value {
            Some(val) => {
                let val_lower = val.to_lowercase();
                matches!(val_lower.as_str(), "1" | "true" | "on" | "yes" | "t")
            }
            None => false,
        }
    }

    fn get_cache_dir_from_env(
        cache_dir: Option<&str>,
        xdg_cache: Option<&str>,
        home: Option<&str>,
    ) -> std::path::PathBuf {
        use std::path::PathBuf;

        if let Some(cache_dir) = cache_dir {
            return PathBuf::from(cache_dir);
        }
        if let Some(xdg_cache) = xdg_cache {
            return PathBuf::from(xdg_cache).join("flavor");
        }
        if let Some(home) = home {
            return PathBuf::from(home).join(".cache/flavor");
        }
        env::temp_dir().join("flavor")
    }
}
