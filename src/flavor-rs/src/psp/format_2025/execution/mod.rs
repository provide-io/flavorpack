//! Process execution for PSPF/2025

mod validation;
mod commands;
mod placeholders;

// Re-export public API
pub use validation::{save_package_checksum, IndexMetadata, save_index_metadata, check_workenv_validity_full};
pub use commands::{execute_setup_commands, execute_command, run_command, execute_main_command};
pub use placeholders::substitute_placeholders;
