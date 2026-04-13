// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! Version information for Flavor binaries

/// Current version of Flavor Rust implementation
pub const VERSION: &str = "0.3.25";

/// Build timestamp (set at compile time)
pub const BUILD_TIME: Option<&str> = option_env!("BUILD_TIME");

/// Git commit hash (set at compile time)
pub const GIT_COMMIT: Option<&str> = option_env!("GIT_COMMIT");

/// Get full version string with optional build information
pub fn full_version() -> String {
    full_version_with(GIT_COMMIT, BUILD_TIME)
}

fn full_version_with(commit: Option<&str>, build_time: Option<&str>) -> String {
    let mut version = VERSION.to_string();

    if let Some(commit) = commit {
        version.push_str(&format!(" ({})", &commit[..8.min(commit.len())]));
    }

    if let Some(time) = build_time {
        version.push_str(&format!(" built {}", time));
    }

    version
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn full_version_includes_the_base_version() {
        let version = full_version();
        assert!(version.starts_with(VERSION));
    }

    #[test]
    fn full_version_includes_optional_metadata_when_available() {
        let version = full_version();

        if let Some(commit) = GIT_COMMIT {
            assert!(version.contains(&commit[..8.min(commit.len())]));
        }

        if let Some(time) = BUILD_TIME {
            assert!(version.contains(time));
        }
    }

    #[test]
    fn full_version_with_test_inputs_truncates_commit_and_appends_build_time() {
        let version = full_version_with(Some("0123456789abcdef"), Some("2026-03-31T00:00:00Z"));

        assert_eq!(version, "0.3.25 (01234567) built 2026-03-31T00:00:00Z");
    }

    #[test]
    fn full_version_with_only_commit_omits_build_time() {
        let version = full_version_with(Some("abcdef1234567890"), None);
        assert_eq!(version, format!("{} (abcdef12)", VERSION));
    }

    #[test]
    fn full_version_with_only_build_time_omits_commit() {
        let version = full_version_with(None, Some("2026-01-01"));
        assert_eq!(version, format!("{} built 2026-01-01", VERSION));
    }

    #[test]
    fn full_version_with_neither_returns_just_version() {
        let version = full_version_with(None, None);
        assert_eq!(version, VERSION);
    }

    #[test]
    fn full_version_with_short_commit_does_not_panic() {
        let version = full_version_with(Some("abc"), None);
        assert_eq!(version, format!("{} (abc)", VERSION));
    }
}
