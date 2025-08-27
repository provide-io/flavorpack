//! Flavor Rust launcher binary

use flavor::{launch_package, LaunchOptions};
use std::{env, process};

const VERSION: &str = "0.3.0";

fn main() {
    let args: Vec<String> = env::args().collect();

    // Get executable path
    let exe_path = env::current_exe().unwrap_or_else(|e| {
        eprintln!("Failed to get executable path: {}", e);
        process::exit(1);
    });

    // Check if we're running as a standalone binary (not a PSP package)
    // by attempting to detect the package format
    let is_standalone = match flavor::psp::detect_format(&exe_path) {
        Ok(format) => {
            // Found PSPF format - we're embedded in a package
            if env::var("FLAVOR_DEBUG_LAUNCHER").is_ok() {
                eprintln!("DEBUG: Detected format {:?} in {:?}", format, exe_path);
            }
            false
        }
        Err(e) => {
            // No PSPF format found - we're standalone
            if env::var("FLAVOR_DEBUG_LAUNCHER").is_ok() {
                eprintln!("DEBUG: No PSPF format in {:?}: {}", exe_path, e);
            }
            true
        }
    };

    // Handle CLI mode: either FLAVOR_LAUNCHER_CLI=1 or standalone binary
    let cli_mode = env::var("FLAVOR_LAUNCHER_CLI").unwrap_or_default() == "1" || is_standalone;

    // Handle --version in CLI mode
    if cli_mode && args.len() > 1 && args[1] == "--version" {
        println!("flavor-rs-launcher {}", VERSION);
        process::exit(0);
    }

    // If standalone, we're NOT embedded in a package
    if is_standalone {
        // Show help if no arguments
        if args.len() == 1 {
            eprintln!("flavor-rs-launcher {}", VERSION);
            eprintln!("Usage: {} <package.psp> [args...]", args[0]);
            eprintln!("\nThis is the Flavor Rust launcher for PSPF packages.");
            process::exit(1);
        }
        
        // For standalone launcher, first arg should be the package to launch
        eprintln!("Standalone launcher mode not yet implemented");
        eprintln!("Use this launcher embedded in a PSPF package");
        process::exit(1);
    }

    // Only initialize logging when we're actually launching a package
    // Skip logging initialization for standalone --version
    if !(cli_mode && args.len() > 1 && args[1] == "--version") {
        // Initialize logging based on FLAVOR_LOG_LEVEL env var
        if let Ok(level) = env::var("FLAVOR_LOG_LEVEL") {
            flavor::logger::JsonLogger::init_with_level(&level, "FLAVOR_LOG_LEVEL");
        } else {
            flavor::logger::JsonLogger::init();
        }
    }

    // Pass ALL args except program name - don't consume any flags
    let remaining_args = args[1..].to_vec();

    // Create launch options
    let options = LaunchOptions {
        insecure: env::var("FLAVOR_INSECURE").unwrap_or_default() == "1",
        workdir: None,
    };

    let exit_code = launch_package(&exe_path, &remaining_args, options).unwrap_or_else(|e| {
        eprintln!("Error: {}", e);
        1
    });

    process::exit(exit_code);
}
