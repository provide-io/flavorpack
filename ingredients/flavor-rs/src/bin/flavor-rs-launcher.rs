//! Flavor Rust launcher binary

use flavor::{launch_package, LaunchOptions};
use std::{env, process};

const VERSION: &str = "0.3.0";

fn main() {
    // --- Argument and Environment Parsing ---
    let args: Vec<String> = env::args().collect();
    let exe_path = env::current_exe().unwrap_or_else(|e| {
        eprintln!("Failed to get executable path: {}", e);
        process::exit(1);
    });

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
                    1
                } else {
                    flavor::psp::format_2025::cli::extract_slot(&exe_path, &command_args[1], &command_args[2])
                }
            }
            "run" => {
                // 'run' command executes the package with remaining arguments.
                let remaining_args = if command_args.len() > 1 { command_args[1..].to_vec() } else { vec![] };
                let options = LaunchOptions {
                    insecure: env::var("FLAVOR_INSECURE").unwrap_or_default() == "1",
                    workdir: None,
                };
                launch_package(&exe_path, &remaining_args, options).unwrap_or_else(|e| {
                    eprintln!("Error: {}", e);
                    1
                })
            }
            "--version" => {
                println!("flavor-rs-launcher {}", VERSION);
                0
            }
            _ => {
                eprintln!("Error: Unknown command '{}'", command);
                eprintln!("Available commands: info, verify, metadata, extract, run");
                1
            }
        };
        process::exit(exit_code);
    }

    // --- Standard Package Execution ---
    // Not in CLI mode, so treat all args after the executable name as app arguments.
    
    // Initialize logging for standard execution.
    if let Ok(level) = env::var("FLAVOR_LAUNCHER_LOG_LEVEL") {
        flavor::logger::JsonLogger::init_with_level(&level, "FLAVOR_LAUNCHER_LOG_LEVEL");
    } else if let Ok(level) = env::var("FLAVOR_LOG_LEVEL") {
        flavor::logger::JsonLogger::init_with_level(&level, "FLAVOR_LOG_LEVEL");
    } else {
        flavor::logger::JsonLogger::init();
    }

    // Launch the package with the provided arguments.
    let remaining_args = args[1..].to_vec();
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
