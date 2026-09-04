//! Console records carry the `🦀 ` prefix.
//!
//! The prefix is the reason this crate could not adopt provide-telemetry until
//! 0.10: the pretaster runs all four builder×launcher combinations into one
//! stream, and the prefix is the only thing saying which runtime produced a
//! line. Adopting the crate while losing it would have traded one gap for
//! another.
//!
//! Its own test binary because telemetry setup and the `log` backend are both
//! once-per-process: a second test in this file would run against a runtime the
//! first one configured.

#![allow(unsafe_code)] // env::set_var is unsafe in edition 2024

use std::env;
use std::fs;

use flavor::logger::FlavorLogger;

#[test]
fn console_records_reach_the_log_file_with_the_runtime_prefix() {
    let dir = tempfile::tempdir().expect("tempdir");
    let log_path = dir.path().join("flavor.log");

    unsafe {
        env::set_var(flavor::env_vars::LOG_PATH, &log_path);
    }

    let (level, source) = FlavorLogger::init_with_level("debug", "integration-test");
    assert_eq!(level, "debug");
    assert_eq!(source, "integration-test");

    log::info!("a message from the rust runtime");
    log::warn!("and a second one");
    log::debug!("and a third");

    let written = fs::read_to_string(&log_path).expect("log file");

    let lines: Vec<&str> = written.lines().filter(|line| !line.is_empty()).collect();
    assert!(!lines.is_empty(), "nothing was logged:\n{written}");
    for line in &lines {
        assert!(
            line.starts_with("🦀 "),
            "line is not attributable to a runtime: {line:?}"
        );
    }

    assert!(
        written.contains("a message from the rust runtime"),
        "the message did not survive the bridge:\n{written}"
    );
    assert!(
        written.contains("and a second one"),
        "a later record was dropped:\n{written}"
    );

    // Every record takes exactly one prefix, so the count matches the lines.
    assert_eq!(
        written.matches("🦀 ").count(),
        lines.len(),
        "a line was prefixed more than once, or not at all:\n{written}"
    );
}
