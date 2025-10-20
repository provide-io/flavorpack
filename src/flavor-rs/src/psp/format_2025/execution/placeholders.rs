//! Placeholder substitution utilities

use super::super::metadata::PackageInfo;
use log::warn;
use std::path::Path;

/// Substitute placeholders in text
pub fn substitute_placeholders(text: &str, workenv_dir: &Path, package: &PackageInfo) -> String {
    let workenv_string;
    let workenv_str = if let Some(s) = workenv_dir.to_str() {
        s
    } else {
        warn!("Work environment path contains non-UTF8 characters, using lossy conversion");
        workenv_string = workenv_dir.to_string_lossy().into_owned();
        &workenv_string
    };
    text.replace("{workenv}", workenv_str)
        .replace("{package_name}", &package.name)
        .replace("{version}", &package.version)
}
