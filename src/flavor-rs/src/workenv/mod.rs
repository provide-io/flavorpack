//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

//! Workenv (work environment) management

pub mod directories;
pub mod validation;

pub use directories::{create_workenv_directories, DirectorySpec, WorkenvDirectories};
pub use validation::{check_workenv_validity, WorkenvValidator};