use std::env;
use std::fs;
use std::path::Path;

fn main() {
    // Read version from VERSION file at root of repo (two levels up from flavor-rs)
    let version = if let Ok(v) = env::var("FLAVOR_VERSION") {
        // Use environment variable if set
        v
    } else {
        // Try to read from VERSION file
        let version_file = Path::new("../../VERSION");
        if version_file.exists() {
            fs::read_to_string(version_file)
                .unwrap_or_else(|_| "0.0.1".to_string())
                .trim()
                .to_string()
        } else {
            // Fallback version
            "0.0.1".to_string()
        }
    };

    // Pass version to the build
    println!("cargo:rustc-env=FLAVOR_VERSION={}", version);
    println!("cargo:rerun-if-changed=../../VERSION");
    println!("cargo:rerun-if-env-changed=FLAVOR_VERSION");
}
