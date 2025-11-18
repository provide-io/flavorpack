//! Process execution for PSPF/2025

mod commands;
mod placeholders;
mod validation;

// Re-export public API
pub use commands::{execute_command, execute_main_command, execute_setup_commands, run_command};
pub use placeholders::substitute_placeholders;
pub use validation::{
    IndexMetadata, check_workenv_validity_full, save_index_metadata, save_package_checksum,
};
