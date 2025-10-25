//! Flavor Rust builder binary

use clap::Parser;
use flavor::{BuildOptions, build_package, exit_codes::*};
use std::{env, panic, path::PathBuf, process};

const VERSION: &str = flavor::version::VERSION;

#[derive(Parser, Debug)]
#[command(version = VERSION, about = "Build PSPF packages")]
struct Args {
    /// Path to manifest.json
    #[arg(short, long)]
    manifest: PathBuf,

    /// Output path for PSPF bundle
    #[arg(short, long)]
    output: PathBuf,

    /// Path to launcher binary
    #[arg(long)]
    launcher_bin: Option<PathBuf>,

    /// Path to private key (PEM format)
    #[arg(long)]
    private_key: Option<PathBuf>,

    /// Path to public key (PEM format, optional if private key provided)
    #[arg(long)]
    public_key: Option<PathBuf>,

    /// Seed for deterministic key generation
    #[arg(long)]
    key_seed: Option<String>,

    /// Log level (trace, debug, info, warn, error)
    #[arg(long)]
    log_level: Option<String>,

    /// Base directory for {workenv} resolution (defaults to CWD)
    #[arg(long)]
    workenv_base: Option<PathBuf>,
}

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
            eprintln!("Fatal: Unhandled panic in builder");
            process::exit(EXIT_PANIC);
        }
    }
}

fn run() -> i32 {
    // Handle --version before clap
    if env::args().nth(1).as_deref() == Some("--version") {
        println!("flavor-rs-builder {}", flavor::version::full_version());
        return EXIT_SUCCESS;
    }

    let args = Args::parse();

    // Initialize logging with level if provided
    if let Some(ref level) = args.log_level {
        flavor::logger::JsonLogger::init_with_level(level, "CLI --log-level");
    } else {
        flavor::logger::JsonLogger::init();
    }

    let options = BuildOptions {
        launcher_bin: args.launcher_bin,
        skip_verification: false,
        private_key_path: args.private_key,
        public_key_path: args.public_key,
        key_seed: args.key_seed,
        workenv_base: args.workenv_base,
    };

    match build_package(&args.manifest, &args.output, options) {
        Ok(_) => EXIT_SUCCESS,
        Err(e) => {
            eprintln!("Build error: {}", e);
            match e.to_string() {
                s if s.contains("manifest") || s.contains("config") => EXIT_CONFIG_ERROR,
                s if s.contains("PSPF") || s.contains("format") => EXIT_PSPF_ERROR,
                s if s.contains("I/O")
                    || s.contains("file")
                    || s.contains("read")
                    || s.contains("write") =>
                {
                    EXIT_IO_ERROR
                }
                s if s.contains("signature") || s.contains("key") => EXIT_SIGNATURE_ERROR,
                s if s.contains("dependency") || s.contains("missing") => EXIT_DEPENDENCY_ERROR,
                _ => EXIT_BUILD_ERROR,
            }
        }
    }
}
