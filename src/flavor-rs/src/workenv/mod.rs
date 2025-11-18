//! Workenv (work environment) management

pub mod directories;
pub mod validation;

pub use directories::{create_workenv_directories, DirectorySpec, WorkenvDirectories};
pub use validation::{check_workenv_validity, WorkenvValidator};