// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! Launch-time policy enforcement for the Rust launcher.

use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

/// Package-declared constraints (from package metadata).
#[derive(Default, Debug, serde::Deserialize)]
pub struct PackagePolicy {
    pub platforms: Vec<String>,
    pub refuse_root: bool,
    pub max_age_days: Option<u64>,
    pub require_env: Vec<String>,
}

/// Operator policy (from policy.toml).
#[derive(Default, Debug)]
pub struct OperatorPolicy {
    pub require_trusted_key: bool,
    pub use_os_keychain: bool,
    pub refuse_root: bool,
    pub max_age_days: Option<u64>,
    pub allow_platforms: Vec<String>,
    pub require_sbom: bool,
}

/// Merged policy: stricter wins.
#[derive(Default, Debug)]
pub struct EffectivePolicy {
    pub platforms: Vec<String>,
    pub refuse_root: bool,
    pub max_age_days: Option<u64>,
    pub require_env: Vec<String>,
    pub require_trusted_key: bool,
    pub require_sbom: bool,
}

fn get_system_policy_path() -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        if let Ok(pd) = std::env::var("PROGRAMDATA") {
            return PathBuf::from(pd).join("flavor").join("policy.toml");
        }
        return PathBuf::from("C:\\ProgramData\\flavor\\policy.toml");
    }
    #[cfg(not(target_os = "windows"))]
    PathBuf::from("/etc/flavor/policy.toml")
}

fn get_user_policy_path() -> Option<PathBuf> {
    if let Ok(dir) = std::env::var(crate::env_vars::CONFIG_DIR) {
        return Some(PathBuf::from(dir).join("policy.toml"));
    }
    if let Ok(xdg) = std::env::var("XDG_CONFIG_HOME") {
        return Some(PathBuf::from(xdg).join("flavor").join("policy.toml"));
    }
    #[cfg(not(target_os = "windows"))]
    if let Ok(home) = std::env::var("HOME") {
        return Some(
            PathBuf::from(home)
                .join(".config")
                .join("flavor")
                .join("policy.toml"),
        );
    }
    None
}

/// Parse a minimal TOML policy file. Handles only the fields FlavorPack needs.
fn parse_policy_file(content: &str, policy: &mut OperatorPolicy) {
    let mut section = String::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            section = line[1..line.len() - 1].to_lowercase();
            continue;
        }
        let parts: Vec<&str> = line.splitn(2, '=').collect();
        if parts.len() != 2 {
            continue;
        }
        let key = parts[0].trim();
        // Strip inline comments from value
        let raw_val = parts[1];
        let val = if let Some(idx) = raw_val.find('#') {
            raw_val[..idx].trim()
        } else {
            raw_val.trim()
        };
        match (section.as_str(), key) {
            ("trust", "require_trusted_key") => policy.require_trusted_key = val == "true",
            ("trust", "use_os_keychain") => policy.use_os_keychain = val == "true",
            ("execution", "refuse_root") => policy.refuse_root = val == "true",
            ("execution", "max_age_days") => {
                if let Ok(n) = val.parse::<u64>() {
                    policy.max_age_days = Some(n);
                }
            }
            ("execution", "allow_platforms") => {
                policy.allow_platforms = parse_toml_string_list(val);
            }
            ("attestation", "require_sbom") => policy.require_sbom = val == "true",
            _ => {}
        }
    }
}

fn parse_toml_string_list(val: &str) -> Vec<String> {
    let val = val.trim();
    if !val.starts_with('[') || !val.ends_with(']') {
        return Vec::new();
    }
    let inner = &val[1..val.len() - 1];
    inner
        .split(',')
        .map(|s| s.trim().trim_matches(|c| c == '"' || c == '\'').to_string())
        .filter(|s| !s.is_empty())
        .collect()
}

/// Load operator policy from system and user files.
pub fn load_operator_policy() -> OperatorPolicy {
    let mut policy = OperatorPolicy::default();
    if let Ok(content) = fs::read_to_string(get_system_policy_path()) {
        parse_policy_file(&content, &mut policy);
    }
    if let Some(path) = get_user_policy_path() {
        if let Ok(content) = fs::read_to_string(path) {
            parse_policy_file(&content, &mut policy);
        }
    }
    policy
}

/// Merge package + operator policy. Stricter always wins.
pub fn merge_policy(pkg: PackagePolicy, op: OperatorPolicy) -> EffectivePolicy {
    let platforms = if !pkg.platforms.is_empty() && !op.allow_platforms.is_empty() {
        pkg.platforms
            .iter()
            .filter(|p| op.allow_platforms.contains(p))
            .cloned()
            .collect()
    } else if !op.allow_platforms.is_empty() {
        op.allow_platforms.clone()
    } else {
        pkg.platforms.clone()
    };

    let refuse_root = pkg.refuse_root || op.refuse_root;

    let max_age_days = match (pkg.max_age_days, op.max_age_days) {
        (Some(a), Some(b)) => Some(a.min(b)),
        (Some(a), None) => Some(a),
        (None, b) => b,
    };

    EffectivePolicy {
        platforms,
        refuse_root,
        max_age_days,
        require_env: pkg.require_env,
        require_trusted_key: op.require_trusted_key,
        require_sbom: op.require_sbom,
    }
}

/// Check whether the current process is running with Windows Administrator privileges.
/// Uses `CheckTokenMembership` against the built-in Administrators SID (S-1-5-32-544).
/// Passing `None` as the token handle checks the effective token of the current process.
#[cfg(target_os = "windows")]
#[allow(unsafe_code)]
fn is_windows_admin() -> bool {
    use windows::Win32::Foundation::BOOL;
    use windows::Win32::Security::{
        AllocateAndInitializeSid, CheckTokenMembership, FreeSid, PSID, SID_IDENTIFIER_AUTHORITY,
    };
    use windows::Win32::System::SystemServices::{
        DOMAIN_ALIAS_RID_ADMINS, SECURITY_BUILTIN_DOMAIN_RID,
    };

    const NT_AUTHORITY: SID_IDENTIFIER_AUTHORITY = SID_IDENTIFIER_AUTHORITY {
        Value: [0, 0, 0, 0, 0, 5],
    };

    unsafe {
        let mut admin_sid = PSID::default();
        if AllocateAndInitializeSid(
            &NT_AUTHORITY,
            2,
            SECURITY_BUILTIN_DOMAIN_RID as u32,
            DOMAIN_ALIAS_RID_ADMINS as u32,
            0,
            0,
            0,
            0,
            0,
            0,
            &mut admin_sid,
        )
        .is_err()
        {
            return false;
        }

        let mut is_member = BOOL::default();
        let ok = CheckTokenMembership(None, admin_sid, &mut is_member);
        let _ = FreeSid(admin_sid);
        ok.is_ok() && is_member.as_bool()
    }
}

/// Enforce policy against current runtime environment.
/// Returns Err with a descriptive message on first violation.
/// `key_trusted` is false only when the trusted store exists AND the key is explicitly absent.
#[allow(unsafe_code)] // Required for libc::geteuid() FFI call
pub fn enforce_policy(
    policy: &EffectivePolicy,
    build_timestamp: u64,
    has_sbom: bool,
    key_trusted: bool,
) -> Result<(), String> {
    let current_platform = get_current_platform();

    // Platform check
    if !policy.platforms.is_empty() && !policy.platforms.contains(&current_platform) {
        return Err(format!(
            "platform not permitted: {} not in {:?}",
            current_platform, policy.platforms
        ));
    }

    // Root / Administrator check
    #[cfg(unix)]
    if policy.refuse_root && unsafe { libc::geteuid() } == 0 {
        return Err("refused to run as root".to_string());
    }
    #[cfg(target_os = "windows")]
    if policy.refuse_root && is_windows_admin() {
        return Err("refused to run as Administrator".to_string());
    }

    // Age check
    if let Some(max_days) = policy.max_age_days {
        if build_timestamp > 0 {
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            let age_days = now.saturating_sub(build_timestamp) / 86400;
            if age_days > max_days {
                return Err(format!(
                    "package is {} days old — policy requires max {} days",
                    age_days, max_days
                ));
            }
        }
    }

    // Environment variable check
    for var in &policy.require_env {
        if std::env::var(var).is_err() {
            return Err(format!("required environment variable not set: {}", var));
        }
    }

    // SBOM check
    if policy.require_sbom && !has_sbom {
        return Err(
            "package built without attestation slot — operator policy requires SBOM".to_string(),
        );
    }

    // Trusted key check
    if policy.require_trusted_key && !key_trusted {
        return Err(
            "operator policy requires a trusted signing key — package key is not in the trusted store"
                .to_string(),
        );
    }

    Ok(())
}

pub fn get_current_platform() -> String {
    let os = if cfg!(target_os = "linux") {
        "linux"
    } else if cfg!(target_os = "macos") {
        "darwin"
    } else {
        "windows"
    };
    let arch = if cfg!(target_arch = "aarch64") {
        "arm64"
    } else {
        "amd64"
    };
    format!("{}_{}", os, arch)
}

#[cfg(test)]
#[allow(unsafe_code)] // Required for env::set_var/remove_var (unsafe in Rust edition 2024)
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_get_current_platform_nonempty() {
        let p = get_current_platform();
        assert!(!p.is_empty());
        assert!(p.contains('_'));
    }

    #[test]
    fn test_merge_policy_refuse_root() {
        let pkg = PackagePolicy {
            refuse_root: false,
            ..Default::default()
        };
        let op = OperatorPolicy {
            refuse_root: true,
            ..Default::default()
        };
        let eff = merge_policy(pkg, op);
        assert!(eff.refuse_root);
    }

    #[test]
    fn test_merge_policy_max_age_days_min() {
        let pkg = PackagePolicy {
            max_age_days: Some(365),
            ..Default::default()
        };
        let op = OperatorPolicy {
            max_age_days: Some(90),
            ..Default::default()
        };
        let eff = merge_policy(pkg, op);
        assert_eq!(eff.max_age_days, Some(90));
    }

    #[test]
    fn test_merge_policy_max_age_only_pkg() {
        let pkg = PackagePolicy {
            max_age_days: Some(180),
            ..Default::default()
        };
        let op = OperatorPolicy::default();
        let eff = merge_policy(pkg, op);
        assert_eq!(eff.max_age_days, Some(180));
    }

    #[test]
    fn test_merge_policy_platforms_intersection() {
        let pkg = PackagePolicy {
            platforms: vec!["linux_amd64".to_string(), "darwin_arm64".to_string()],
            ..Default::default()
        };
        let op = OperatorPolicy {
            allow_platforms: vec!["linux_amd64".to_string(), "linux_arm64".to_string()],
            ..Default::default()
        };
        let eff = merge_policy(pkg, op);
        assert_eq!(eff.platforms, vec!["linux_amd64".to_string()]);
    }

    #[test]
    fn test_merge_policy_platforms_only_operator() {
        let pkg = PackagePolicy::default();
        let op = OperatorPolicy {
            allow_platforms: vec!["linux_amd64".to_string()],
            ..Default::default()
        };
        let eff = merge_policy(pkg, op);
        assert_eq!(eff.platforms, vec!["linux_amd64".to_string()]);
    }

    #[test]
    fn test_enforce_policy_permissive() {
        let eff = EffectivePolicy::default();
        assert!(enforce_policy(&eff, 0, false, true).is_ok());
    }

    #[test]
    fn test_enforce_policy_platform_blocked() {
        let eff = EffectivePolicy {
            platforms: vec!["__nonexistent__".to_string()],
            ..Default::default()
        };
        assert!(enforce_policy(&eff, 0, false, true).is_err());
    }

    #[test]
    fn test_enforce_policy_sbom_required() {
        let eff = EffectivePolicy {
            require_sbom: true,
            ..Default::default()
        };
        assert!(enforce_policy(&eff, 0, false, true).is_err());
        assert!(enforce_policy(&eff, 0, true, true).is_ok());
    }

    #[test]
    fn test_enforce_policy_env_var_missing() {
        let eff = EffectivePolicy {
            require_env: vec!["__FLAVOR_POLICY_TEST_NONEXISTENT__".to_string()],
            ..Default::default()
        };
        // Make sure the variable is unset
        unsafe { env::remove_var("__FLAVOR_POLICY_TEST_NONEXISTENT__") };
        assert!(enforce_policy(&eff, 0, false, true).is_err());
    }

    #[test]
    fn test_enforce_policy_env_var_present() {
        unsafe { env::set_var("__FLAVOR_POLICY_TEST__", "1") };
        let eff = EffectivePolicy {
            require_env: vec!["__FLAVOR_POLICY_TEST__".to_string()],
            ..Default::default()
        };
        assert!(enforce_policy(&eff, 0, false, true).is_ok());
        unsafe { env::remove_var("__FLAVOR_POLICY_TEST__") };
    }

    #[test]
    fn test_enforce_policy_age_exceeded() {
        let eff = EffectivePolicy {
            max_age_days: Some(0),
            ..Default::default()
        };
        // Build timestamp of 1 (ancient) should exceed 0 day limit
        assert!(enforce_policy(&eff, 1, false, true).is_err());
    }

    #[test]
    fn test_enforce_policy_require_trusted_key_untrusted() {
        let eff = EffectivePolicy {
            require_trusted_key: true,
            ..Default::default()
        };
        assert!(enforce_policy(&eff, 0, false, false).is_err());
    }

    #[test]
    fn test_enforce_policy_require_trusted_key_trusted() {
        let eff = EffectivePolicy {
            require_trusted_key: true,
            ..Default::default()
        };
        assert!(enforce_policy(&eff, 0, false, true).is_ok());
    }

    #[test]
    fn test_enforce_policy_require_trusted_key_not_required() {
        let eff = EffectivePolicy {
            require_trusted_key: false,
            ..Default::default()
        };
        // Even untrusted key should pass when policy doesn't require it
        assert!(enforce_policy(&eff, 0, false, false).is_ok());
    }

    #[test]
    fn test_load_operator_policy_missing_file() {
        unsafe {
            env::set_var(
                crate::env_vars::CONFIG_DIR,
                "/tmp/__nonexistent_flavor_policy_dir__",
            );
        }
        let policy = load_operator_policy();
        assert!(!policy.require_trusted_key);
    }

    #[test]
    fn test_parse_policy_file_all_fields() {
        let content = "[trust]\nrequire_trusted_key = true\nuse_os_keychain = true\n[execution]\nrefuse_root = true\nmax_age_days = 90\n[attestation]\nrequire_sbom = true\n";
        let mut policy = OperatorPolicy::default();
        parse_policy_file(content, &mut policy);
        assert!(policy.require_trusted_key);
        assert!(policy.use_os_keychain);
        assert!(policy.refuse_root);
        assert_eq!(policy.max_age_days, Some(90));
        assert!(policy.require_sbom);
    }

    #[test]
    fn test_parse_policy_file_ignores_comments() {
        let content = "# top comment\n[trust]\n# inline comment\nrequire_trusted_key = true\n";
        let mut policy = OperatorPolicy::default();
        parse_policy_file(content, &mut policy);
        assert!(policy.require_trusted_key);
    }

    #[test]
    fn test_parse_policy_file_inline_comment() {
        let content = "[execution]\nrefuse_root = true # disable if needed\n";
        let mut policy = OperatorPolicy::default();
        parse_policy_file(content, &mut policy);
        assert!(policy.refuse_root, "should strip inline comment");
    }

    #[test]
    fn test_parse_policy_file_allow_platforms() {
        let content = "[execution]\nallow_platforms = [\"linux_amd64\", \"linux_arm64\"]\n";
        let mut policy = OperatorPolicy::default();
        parse_policy_file(content, &mut policy);
        assert_eq!(policy.allow_platforms, vec!["linux_amd64", "linux_arm64"]);
    }

    #[test]
    fn test_parse_toml_string_list_single_quotes() {
        let result = parse_toml_string_list("['darwin_arm64', 'linux_amd64']");
        assert_eq!(result, vec!["darwin_arm64", "linux_amd64"]);
    }

    #[test]
    fn test_parse_toml_string_list_empty() {
        let result = parse_toml_string_list("[]");
        assert!(result.is_empty());
    }

    #[test]
    fn test_parse_toml_string_list_invalid() {
        let result = parse_toml_string_list("not_a_list");
        assert!(result.is_empty());
    }

    #[test]
    fn test_enforce_policy_refuse_root_current_platform() {
        // On Unix, we test the geteuid path. We cannot easily test the Windows path.
        // This test documents the expected behavior.
        let eff = EffectivePolicy {
            refuse_root: true,
            ..Default::default()
        };
        // On non-root Unix: should pass. On root Unix: would fail.
        // We cannot control UID in tests, so just verify the function runs without panic.
        let _ = enforce_policy(&eff, 0, false, true);
    }
}
