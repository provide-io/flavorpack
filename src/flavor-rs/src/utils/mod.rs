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
    resolve_cache_dir(
        env::var_os(crate::env_vars::CACHE_DIR),
        env::var_os("XDG_CACHE_HOME"),
        env::var_os("HOME"),
        env::var_os("LOCALAPPDATA"),
        env::temp_dir(),
    )
}

/// Treat a variable that is set to nothing as one that is not set.
///
/// `var_os` reports an empty value as `Some("")`, and joining that onto a
/// relative suffix yields a relative cache directory -- one that lands wherever
/// the process happens to be running rather than under a home. A caller that
/// builds a child environment from `os.environ.get("HOME", "")` produces
/// exactly that value on a platform with no HOME.
fn non_empty(value: Option<std::ffi::OsString>) -> Option<std::ffi::OsString> {
    value.filter(|v| !v.is_empty())
}

/// Resolve the cache directory from already-read environment values.
///
/// Split from `get_cache_dir` so the ordering is reachable from a test. The
/// LOCALAPPDATA fallback is not compiled out on other platforms: nothing sets
/// it there, so it costs a `None` check and stays exercised by the suite.
fn resolve_cache_dir(
    cache_dir: Option<std::ffi::OsString>,
    xdg_cache: Option<std::ffi::OsString>,
    home: Option<std::ffi::OsString>,
    local_app_data: Option<std::ffi::OsString>,
    temp_dir: std::path::PathBuf,
) -> std::path::PathBuf {
    use std::path::PathBuf;

    if let Some(cache_dir) = non_empty(cache_dir) {
        return PathBuf::from(cache_dir);
    }

    // XDG_CACHE_HOME if set, otherwise ~/.cache. This provides consistency
    // across all Unix-like platforms (Linux, macOS, BSDs).
    if let Some(xdg_cache) = non_empty(xdg_cache) {
        return PathBuf::from(xdg_cache).join("flavor");
    }

    if let Some(home) = non_empty(home) {
        return PathBuf::from(home).join(".cache/flavor");
    }

    if let Some(local_app_data) = non_empty(local_app_data) {
        return PathBuf::from(local_app_data).join("flavor/cache");
    }

    temp_dir.join("flavor")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn is_env_true_handles_truthy_and_falsey_values() {
        assert!(is_env_true_from_value(Some("true")));
        assert!(is_env_true_from_value(Some("YES")));
        assert!(!is_env_true_from_value(Some("0")));
        assert!(!is_env_true_from_value(None));
    }

    #[test]
    fn get_platform_string_uses_expected_separator() {
        let platform = get_platform_string();
        assert!(platform.contains('_'));
    }

    fn os(value: &str) -> Option<std::ffi::OsString> {
        Some(std::ffi::OsString::from(value))
    }

    fn temp() -> std::path::PathBuf {
        std::path::PathBuf::from("/var/tmp")
    }

    #[test]
    fn cache_dir_prefers_explicit_override() {
        let resolved = resolve_cache_dir(os("/cache"), os("/xdg"), os("/home"), None, temp());
        assert_eq!(resolved, std::path::PathBuf::from("/cache"));
    }

    #[test]
    fn cache_dir_prefers_xdg_then_home_then_temp() {
        let xdg = resolve_cache_dir(None, os("/xdg-cache"), os("/home"), None, temp());
        assert_eq!(xdg, std::path::PathBuf::from("/xdg-cache").join("flavor"));

        let home = resolve_cache_dir(None, None, os("/home"), None, temp());
        assert_eq!(
            home,
            std::path::PathBuf::from("/home").join(".cache/flavor")
        );

        let fallback = resolve_cache_dir(None, None, None, None, temp());
        assert_eq!(fallback, temp().join("flavor"));
    }

    #[test]
    fn cache_dir_is_absolute_when_home_is_set_to_nothing() {
        // A caller building a child environment from `os.environ.get("HOME", "")`
        // passes an empty value on a platform with no HOME. Joining onto it
        // yields `.cache/flavor`, which resolves against the child's working
        // directory instead of a home.
        let resolved = resolve_cache_dir(None, None, os(""), None, temp());
        assert!(
            resolved.is_absolute(),
            "empty HOME produced a relative cache directory: {resolved:?}"
        );
        assert_eq!(resolved, temp().join("flavor"));
    }

    #[test]
    fn cache_dir_falls_back_to_local_app_data_when_home_is_empty() {
        let resolved =
            resolve_cache_dir(None, None, os(""), os("C:/Users/r/AppData/Local"), temp());
        assert_eq!(
            resolved,
            std::path::PathBuf::from("C:/Users/r/AppData/Local").join("flavor/cache")
        );
    }

    #[test]
    fn cache_dir_ignores_an_empty_override() {
        let resolved = resolve_cache_dir(os(""), os(""), os("/home"), None, temp());
        assert_eq!(
            resolved,
            std::path::PathBuf::from("/home").join(".cache/flavor")
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
}
