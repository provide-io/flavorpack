//! Flavor Rust builder binary

use clap::Parser;
use flavor::{build_package, BuildOptions};
use std::{env, path::PathBuf, process};

const VERSION: &str = "0.3.0";

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
    // Handle --version before clap
    if env::args().nth(1).as_deref() == Some("--version") {
        println!("flavor-rs-builder {}", VERSION);
        process::exit(0);
    }

    let args = Args::parse();

    // Set workenv base if provided
    if let Some(ref base) = args.workenv_base {
        // SAFETY: This is called once at program startup before any threads are spawned
        unsafe {
            env::set_var("FLAVOR_WORKENV_BASE", base.display().to_string());
        }
    }

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
    };

    if let Err(e) = build_package(&args.manifest, &args.output, options) {
        eprintln!("Error: {}", e);
        process::exit(1);
    }
}
