//! Flavor Rust launcher binary

use flavor::{launch_package, LaunchOptions, exit_codes::*};
use std::{env, panic, process};

fn main() {
    // Set up panic handler to return specific exit code
    panic::set_hook(Box::new(|panic_info| {
        eprintln!("PANIC: {}", panic_info);
        process::exit(EXIT_PANIC);
    }));
    
    // Wrap main logic in catch_unwind for extra safety
    let result = panic::catch_unwind(|| run());
    
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
    
    log::trace!("Launcher starting");
    
    // --- Argument and Environment Parsing ---
    let args: Vec<String> = env::args().collect();
    log::trace!("Arguments: {:?}", args);
    
    // Check for --version flag early (before PSPF validation)
    if args.len() > 1 && args[1] == "--version" {
        println!("flavor-rs-launcher {}", flavor::version::full_version());
        return 0;
    }
    
    let exe_path = match env::current_exe() {
        Ok(path) => path,
        Err(e) => {
            eprintln!("Failed to get executable path: {}", e);
            return EXIT_IO_ERROR;
        }
    };

    // Determine if running in CLI mode ONLY from the environment variable.
    let cli_mode = env::var("FLAVOR_LAUNCHER_CLI").map_or(false, |v| v == "1" || v.to_lowercase() == "true");

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
                    match flavor::psp::format_2025::cli::extract_slot(&exe_path, &command_args[1], &command_args[2]) {
                        code if code == 0 => 0,
                        _ => EXIT_EXTRACTION_ERROR,
                    }
                }
            }
            "run" => {
                // 'run' command executes the package with remaining arguments.
                let remaining_args = if command_args.len() > 1 { command_args[1..].to_vec() } else { vec![] };
                let options = LaunchOptions {
                    insecure: env::var("FLAVOR_INSECURE").unwrap_or_default() == "1",
                    workdir: None,
                };
                match launch_package(&exe_path, &remaining_args, options) {
                    Ok(code) => code,
                    Err(e) => {
                        eprintln!("Launch error: {}", e);
                        EXIT_EXECUTION_ERROR
                    }
                }
            }
            _ => {
                eprintln!("Error: Unknown command '{}'", command);
                eprintln!("Available commands: info, verify, metadata, extract, run");
                EXIT_INVALID_ARGS
            }
        };
        return exit_code;
    }

    // --- Standard Package Execution ---
    // Not in CLI mode, so treat all args after the executable name as app arguments.
    
    // But first check if this is just a standalone launcher being called with --version
    // (without being a bundle and without CLI mode)
    if args.len() > 1 && args[1] == "--version" {
        log::debug!("Checking if executable is a PSPF bundle: {:?}", exe_path);
        // Try to detect if this is a PSPF bundle first
        match flavor::psp::detect_format(&exe_path) {
            Ok(_format) => {
                log::debug!("Executable is a PSPF bundle, continuing to launch");
                // It's a bundle, continue to launch
            }
            Err(e) => {
                // Not a bundle, just show version
                log::debug!("Not a PSPF bundle ({}), showing launcher version", e);
                println!("flavor-rs-launcher {}", flavor::version::full_version());
                return 0;
            }
        }
    }
    
    // Check if this is a bundle being run with special commands
    // These commands should work even without CLI mode for compatibility
    if args.len() > 1 {
        match args[1].as_str() {
            "info" => {
                log::debug!("Running info command on bundle");
                return flavor::psp::format_2025::cli::show_info(&exe_path);
            }
            "verify" => {
                log::debug!("Running verify command on bundle");
                return flavor::psp::format_2025::cli::verify_bundle(&exe_path);
            }
            "metadata" => {
                log::debug!("Running metadata command on bundle");
                return flavor::psp::format_2025::cli::show_metadata(&exe_path);
            }
            _ => {
                // Not a special command, continue to launch
                log::trace!("Not a special command, proceeding with launch");
            }
        }
    }

    // Launch the package with the provided arguments.
    let remaining_args = args[1..].to_vec();
    let options = LaunchOptions {
        insecure: env::var("FLAVOR_INSECURE").unwrap_or_default() == "1",
        workdir: None,
    };

    match launch_package(&exe_path, &remaining_args, options) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("Launch error: {}", e);
            match e.to_string() {
                s if s.contains("PSPF") || s.contains("format") => EXIT_PSPF_ERROR,
                s if s.contains("extract") => EXIT_EXTRACTION_ERROR,
                s if s.contains("execute") || s.contains("spawn") => EXIT_EXECUTION_ERROR,
                s if s.contains("I/O") || s.contains("file") => EXIT_IO_ERROR,
                _ => EXIT_EXECUTION_ERROR,
            }
        }
    }
}