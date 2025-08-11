//
// flavor/rust/flavor-packager-rs/src/main.rs
//
use clap::{Parser, Subcommand};
use std::path::PathBuf;

mod commands;
mod flavor;
mod crypto;
mod utils;

use commands::*;

#[derive(Parser)]
#[command(name = "flavor-rust")]
#[command(about = "Flavor binary builder written in Rust")]
#[command(version = "0.1.0")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Generate ECDSA P256 key pair for Flavor package signing
    Keygen {
        /// Directory to store generated keys
        #[arg(long)]
        out_dir: PathBuf,
    },
    /// Build a Flavor package from component parts
    Build {
        /// Output path for the Flavor file
        #[arg(long)]
        out: PathBuf,
        /// Directory containing the provider payload
        #[arg(long)]
        payload_dir: PathBuf,
        /// Path to the private key for signing
        #[arg(long)]
        package_key: PathBuf,
        /// Path to the public key for verification
        #[arg(long)]
        public_key: PathBuf,
        /// Path to the flavor-launcher binary
        #[arg(long)]
        launcher_bin: PathBuf,
    },
    /// Verify the integrity and signature of a Flavor file
    Verify {
        /// Path to the Flavor file to verify
        flavor_file: PathBuf,
    },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    env_logger::init();
    
    let cli = Cli::parse();
    
    match cli.command {
        Commands::Keygen { out_dir } => {
            keygen_command(out_dir).await
        }
        Commands::Build { 
            out, 
            payload_dir, 
            package_key, 
            public_key, 
            launcher_bin 
        } => {
            build_command(out, payload_dir, package_key, public_key, launcher_bin).await
        }
        Commands::Verify { flavor_file } => {
            verify_command(flavor_file).await
        }
    }
}


// 📦🍜📄🪄
