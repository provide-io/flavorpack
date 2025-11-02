//! Flavor Rust launcher binary

use flavor::{LaunchOptions, exit_codes::*, launch_package};
use std::{env, panic, process};

fn main() {
    // Set up panic handler to return specific exit code
    panic::set_hook(Box::new(|panic_info| {
        eprintln!("PANIC: {}", panic_info);
        process::exit(EXIT_PANIC);
    }));

    // Wrap main logic in catch_unwind for extra safety
    let result = panic::catch_unwind(run);

    match result {
        Ok(exit_code) => process::exit(exit_code),
        Err(_) => {
            eprintln!("Fatal: Unhandled panic in launcher");
            process::exit(EXIT_PANIC);
        }
    }
}

fn run() -> i32 {
    // Initialize logging as early as possible for debugging
    if let Ok(level) = env::var("FLAVOR_LAUNCHER_LOG_LEVEL") {
        flavor::logger::JsonLogger::init_with_level(&level, "FLAVOR_LAUNCHER_LOG_LEVEL");
    } else if let Ok(level) = env::var("FLAVOR_LOG_LEVEL") {
        flavor::logger::JsonLogger::init_with_level(&level, "FLAVOR_LOG_LEVEL");
    } else {
        flavor::logger::JsonLogger::init();
    }

    log::debug!("🚀 Launcher process started");
    log::trace!("📝 Launcher initializing");

    // --- Argument and Environment Parsing ---
    let args: Vec<String> = env::args().collect();
    log::trace!("📋 Arguments: {:?}", args);

    // ⚠️ CRITICAL: NEVER intercept command line arguments unless in CLI mode!
    // The launcher must pass ALL arguments to the package entrypoint unchanged.
    // Only FLAVOR_LAUNCHER_CLI=1 enables CLI mode where the launcher processes commands.

    let exe_path = match env::current_exe() {
        Ok(path) => {
            log::debug!("📍 Executable path: {:?}", path);
            path
        }
        Err(e) => {
            log::error!("❌ Failed to get executable path: {}", e);
            return EXIT_IO_ERROR;
        }
    };

    // Special case: Handle --version and --help when run as standalone binary (for CI/testing)
    // This must be checked before attempting to read as a package
    if args.len() == 2 && (args[1] == "--version" || args[1] == "--help") {
        // Check if we're running as a standalone launcher (not a package)
        // Simply check for the package emoji magic at the start of the file
        use std::fs::File;
        use std::io::Read;

        if let Ok(mut file) = File::open(&exe_path) {
            let mut magic = [0u8; 4];
            if file.read_exact(&mut magic).is_ok() {
                // Check for package emoji (📦 in UTF-8)
                if magic == [0xF0, 0x9F, 0x93, 0xA6] {
                    // This is a PSPF package, continue normal processing
                } else {
                    // Not a package - we're running as a standalone launcher
                    if args[1] == "--version" {
                        // Show version info and exit
                        println!("flavor-rs-launcher {}", env!("CARGO_PKG_VERSION"));
                        if let Ok(timestamp) = env::var("BUILD_TIMESTAMP") {
                            println!("Built: {}", timestamp);
                        }
                        return 0;
                    } else if args[1] == "--help" {
                        // Show help and exit
                        println!("flavor-rs-launcher - PSPF package launcher");
                        println!();
                        println!("Usage:");
                        println!("  flavor-rs-launcher [options]");
                        println!("  flavor-rs-launcher --version");
                        println!("  flavor-rs-launcher --help");
                        println!();
                        println!("Options:");
                        println!("  --version          Show version information");
                        println!("  --help             Show this help message");
                        println!();
                        println!("CLI Mode:");
                        println!(
                            "  Set FLAVOR_LAUNCHER_CLI=1 to enable CLI mode for package inspection"
                        );
                        println!("  Commands: info, verify, metadata, extract, run, help");
                        println!();
                        println!("  Example: FLAVOR_LAUNCHER_CLI=1 ./mypackage.psp info");
                        return 0;
                    }
                }
            }
        }
    }

    // Determine if running in CLI mode ONLY from the environment variable.
    let cli_mode =
        env::var("FLAVOR_LAUNCHER_CLI").is_ok_and(|v| v == "1" || v.to_lowercase() == "true");

    // --- CLI Mode Execution ---
    if cli_mode {
        // In CLI mode, the first argument is the command.
        let command_args = &args[1..];

        // Default to 'info' command if no arguments are provided in CLI mode.
        let command = if command_args.is_empty() {
            "info"
        } else {
            command_args[0].as_str()
        };

        // Route to the appropriate CLI command.
        let exit_code = match command {
            "info" => flavor::psp::format_2025::cli::show_info(&exe_path),
            "verify" => flavor::psp::format_2025::cli::verify_bundle(&exe_path),
            "metadata" => flavor::psp::format_2025::cli::show_metadata(&exe_path),
            "extract" => {
                if command_args.len() < 3 {
                    eprintln!("Usage: {} extract <slot_index> <output_dir>", args[0]);
                    EXIT_INVALID_ARGS
                } else {
                    match flavor::psp::format_2025::cli::extract_slot(
                        &exe_path,
                        &command_args[1],
                        &command_args[2],
                    ) {
                        0 => 0,
                        _ => EXIT_EXTRACTION_ERROR,
                    }
                }
            }
            "run" => {
                // 'run' command executes the package with remaining arguments.
                let remaining_args = if command_args.len() > 1 {
                    command_args[1..].to_vec()
                } else {
                    vec![]
                };
                let options = LaunchOptions { workdir: None };
                match launch_package(&exe_path, &remaining_args, options) {
                    Ok(code) => code,
                    Err(e) => {
                        eprintln!("Launch error: {}", e);
                        EXIT_EXECUTION_ERROR
                    }
                }
            }
            "help" | "--help" => {
                println!("PSPF Package Launcher - CLI Mode");
                println!();
                println!("Available commands:");
                println!("  info              Show package information (default)");
                println!("  verify            Verify package integrity");
                println!("  metadata          Show raw package metadata");
                println!("  extract INDEX DIR Extract slot to directory");
                println!("  run [args...]     Execute package with arguments");
                println!("  help              Show this help message");
                println!();
                println!("Usage:");
                println!("  FLAVOR_LAUNCHER_CLI=1 ./package.psp <command>");
                println!();
                println!("Examples:");
                println!("  FLAVOR_LAUNCHER_CLI=1 ./package.psp info");
                println!("  FLAVOR_LAUNCHER_CLI=1 ./package.psp verify");
                println!("  FLAVOR_LAUNCHER_CLI=1 ./package.psp extract 0 /tmp/output");
                0
            }
            _ => {
                eprintln!("Error: Unknown command '{}'", command);
                eprintln!("Available commands: info, verify, metadata, extract, run, help");
                EXIT_INVALID_ARGS
            }
        };
        return exit_code;
    }

    // --- Standard Package Execution ---
    // ⚠️ CRITICAL: Not in CLI mode - pass ALL arguments directly to the package!
    // The launcher MUST NOT intercept any arguments (including --version).
    // All command-line arguments belong to the packaged application, not the launcher.

    log::trace!("🔄 Not in CLI mode, passing all arguments to entrypoint");

    // Launch the package with the provided arguments.
    let remaining_args = args[1..].to_vec();
    let options = LaunchOptions { workdir: None };

    log::debug!("🚀 Attempting to launch package: {:?}", exe_path);
    match launch_package(&exe_path, &remaining_args, options) {
        Ok(code) => {
            log::debug!("✅ Package launched successfully, exit code: {}", code);
            code
        }
        Err(e) => {
            log::error!("❌ Launch error: {}", e);

            // Provide helpful error messages based on the error type
            let error_msg = e.to_string();
            if error_msg.contains("signature verification failed")
                || error_msg.contains("Signature verification failed")
            {
                eprintln!("❌ Package signature verification failed");
                eprintln!();
                eprintln!("This package's cryptographic signature could not be verified.");
                eprintln!(
                    "This may indicate the package has been tampered with or was not properly signed."
                );
                eprintln!();
                eprintln!(
                    "To use different validation levels, set FLAVOR_VALIDATION environment variable:"
                );
                eprintln!("  export FLAVOR_VALIDATION=relaxed  # Skip signatures");
                eprintln!("For more details, run with FLAVOR_LOG_LEVEL=debug");
            } else if error_msg.contains("checksum") {
                eprintln!("❌ Package integrity check failed: {}", error_msg);
                eprintln!();
                eprintln!("The package appears to be corrupted or modified.");
                eprintln!();
                eprintln!(
                    "To use different validation levels, set FLAVOR_VALIDATION environment variable:"
                );
                eprintln!("  export FLAVOR_VALIDATION=none  # Skip all checks (testing only)");
            } else {
                eprintln!("❌ Failed to launch package: {}", error_msg);
                eprintln!();
                eprintln!("For more details, run with FLAVOR_LOG_LEVEL=debug");
            }

            match error_msg {
                s if s.contains("PSPF") || s.contains("format") => EXIT_PSPF_ERROR,
                s if s.contains("signature") || s.contains("checksum") => EXIT_SIGNATURE_ERROR,
                s if s.contains("extract") => EXIT_EXTRACTION_ERROR,
                s if s.contains("execute") || s.contains("spawn") => EXIT_EXECUTION_ERROR,
                s if s.contains("I/O") || s.contains("file") => EXIT_IO_ERROR,
                _ => EXIT_EXECUTION_ERROR,
            }
        }
    }
}
