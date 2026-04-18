// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! Process execution for PSPF/2025

mod commands;
mod placeholders;
mod validation;

// Re-export public API
pub use commands::{
    execute_command, execute_main_command, execute_setup_commands, run_command, shell_split,
};
pub use placeholders::substitute_placeholders;
pub use validation::{
    IndexMetadata, check_workenv_validity_full, save_index_metadata, save_package_checksum,
};
