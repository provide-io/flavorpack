//! JSON records carry no prefix, because a prefixed line is not JSON.
//!
//! The console prefix and this are the same decision seen from two sides: a
//! human reading a shared stream needs to know which runtime spoke, and a
//! parser reading the same records needs a line it can parse. Prefixing JSON
//! would break every consumer of it, so the destination is installed bare.
//!
//! Its own test binary because telemetry setup and the `log` backend are both
//! once-per-process.

#![allow(unsafe_code)] // env::set_var is unsafe in edition 2024

use std::env;
use std::fs;

use flavor::logger::FlavorLogger;

#[test]
fn json_records_are_parseable_and_unprefixed() {
    let dir = tempfile::tempdir().expect("tempdir");
    let log_path = dir.path().join("flavor.jsonl");

    unsafe {
        env::set_var(flavor::env_vars::LOG_PATH, &log_path);
    }

    let (level, _) = FlavorLogger::init_with_level("json:debug", "integration-test");
    assert_eq!(level, "debug");

    log::info!("a structured message");

    let written = fs::read_to_string(&log_path).expect("log file");
    let lines: Vec<&str> = written.lines().filter(|line| !line.is_empty()).collect();

    assert!(!lines.is_empty(), "nothing was logged:\n{written}");
    assert!(
        !written.contains("🦀"),
        "the prefix reached JSON output, which no parser will accept:\n{written}"
    );

    for line in &lines {
        let parsed: serde_json::Value = serde_json::from_str(line)
            .unwrap_or_else(|error| panic!("line is not JSON: {line:?} ({error})"));
        assert!(parsed.is_object(), "line is not a JSON object: {line:?}");
    }

    assert!(
        written.contains("a structured message"),
        "the message did not survive the bridge:\n{written}"
    );
}
