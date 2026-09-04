//! Logging for the Rust launcher and builder, on provide-telemetry.
//!
//! `flavor-go` logs through provide-telemetry and this side did not, so the two
//! launchers produced structurally different telemetry for the same operation
//! even though either can run any package. What kept them apart was the writer:
//! the Rust crate emitted through `eprintln!` with nothing able to intercept
//! it, so adopting it would have dropped the `🦀 ` prefix the pretaster's
//! combined output depends on. `provide-telemetry` 0.10 added `set_log_output`,
//! which is what closes the gap.
//!
//! The crate publishes its own `Logger` rather than backing the `log` facade,
//! so [`bridge::TelemetryBridge`] is installed as the `log` backend and every
//! existing `log::info!` in this crate reaches it unchanged.

pub mod bridge;
pub mod prefix;

use std::env;
use std::fs::OpenOptions;
use std::io::{self, Write};

use log::LevelFilter;
use provide_telemetry::{LoggingConfig, TelemetryConfig, set_log_output, setup_telemetry};

use bridge::TelemetryBridge;
use prefix::PrefixWriter;

/// Marks this runtime's lines in a stream several runtimes share.
const RUNTIME_PREFIX: &str = "🦀 ";

/// The service name this runtime's records carry.
const SERVICE_NAME: &str = "flavor-rs";

/// The `log` backend, as a static: the bridge holds no state, so it needs no
/// allocation and none of `log`'s `alloc` feature.
static BRIDGE: TelemetryBridge = TelemetryBridge;

/// Sets up logging for the process.
#[derive(Debug)]
pub struct FlavorLogger;

impl FlavorLogger {
    /// Parse the logging mode and level.
    ///
    /// A level may carry a `json:` prefix — `json:debug` — or be `json` alone,
    /// which means JSON at info.
    ///
    /// An unrecognised level filters at info. That is not the widest choice,
    /// and it is deliberate: a level nobody typed on purpose should not turn
    /// the launcher's trace output on in front of a user.
    pub fn parse_level_mode(level_str: &str) -> (bool, String, LevelFilter) {
        let (use_json, actual_level) = if let Some(stripped) = level_str.strip_prefix("json:") {
            (true, stripped)
        } else if level_str == "json" {
            (true, "info")
        } else {
            (false, level_str)
        };

        let level_filter = match actual_level {
            "trace" => LevelFilter::Trace,
            "debug" => LevelFilter::Debug,
            "info" => LevelFilter::Info,
            "warn" => LevelFilter::Warn,
            "error" => LevelFilter::Error,
            "off" => LevelFilter::Off,
            _ => LevelFilter::Info,
        };

        (use_json, actual_level.to_string(), level_filter)
    }

    /// Initialize logging at a given level, naming where the level came from.
    ///
    /// Returns the level and the source it settled on, which the callers report.
    pub fn init_with_level(level_str: &str, source: &str) -> (String, String) {
        let (use_json, actual_level, level_filter) = Self::parse_level_mode(level_str);

        let config = TelemetryConfig {
            service_name: SERVICE_NAME.to_string(),
            logging: LoggingConfig {
                level: level_filter.to_string().to_uppercase(),
                fmt: if use_json { "json" } else { "console" }.to_string(),
                ..LoggingConfig::default()
            },
            ..TelemetryConfig::default()
        };

        if let Err(error) = setup_telemetry(Some(config)) {
            eprintln!("Failed to set up telemetry: {error}");
            return (actual_level, source.to_string());
        }

        install_log_output(use_json);

        // Installing the backend can only succeed once per process. A second
        // call is the ordinary case for a binary that has already logged, and
        // is not a failure: the level below still moves, and the records still
        // reach the same place.
        let _ = log::set_logger(&BRIDGE);
        log::set_max_level(level_filter);

        (actual_level, source.to_string())
    }

    /// Initialize logging from the environment.
    pub fn init() {
        let log_level =
            env::var(crate::env_vars::LOG_LEVEL).unwrap_or_else(|_| "trace".to_string());
        Self::init_with_level(&log_level, crate::env_vars::LOG_LEVEL);
    }
}

/// Point rendered records at their destination.
///
/// `FLAVOR_LOG_PATH` names a file to write to; without it records go to stderr.
/// A file that cannot be opened falls back to stderr rather than dropping the
/// records: a launcher that cannot write its log file is still a launcher, and
/// has just become the thing worth reading a log about.
fn install_log_output(use_json: bool) {
    let file = env::var(crate::env_vars::LOG_PATH)
        .ok()
        .and_then(|path| OpenOptions::new().create(true).append(true).open(path).ok());

    match file {
        Some(file) => install_destination(file, use_json),
        None => install_destination(io::stderr(), use_json),
    }
}

/// Install a destination, prefixed unless the records are JSON.
///
/// JSON is parsed by whatever consumes it, so a prefix would make every line
/// invalid. Console output is read by a person, and in the pretaster's combined
/// stream the prefix is the only thing saying which runtime a line came from.
fn install_destination<W: Write + Send + 'static>(destination: W, use_json: bool) {
    if use_json {
        set_log_output(destination);
    } else {
        set_log_output(PrefixWriter::new(RUNTIME_PREFIX, destination));
    }
}

/// Whether the environment asks for JSON logging.
pub fn is_json_logging() -> bool {
    is_json_logging_value(env::var(crate::env_vars::LOG_LEVEL).ok().as_deref())
}

fn is_json_logging_value(value: Option<&str>) -> bool {
    value.map(|v| v.starts_with("json")).unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_level_mode_handles_plain_levels() {
        let (use_json, level, filter) = FlavorLogger::parse_level_mode("debug");

        assert!(!use_json);
        assert_eq!(level, "debug");
        assert_eq!(filter, LevelFilter::Debug);
    }

    #[test]
    fn parse_level_mode_handles_a_json_prefixed_level() {
        let (use_json, level, filter) = FlavorLogger::parse_level_mode("json:warn");

        assert!(use_json);
        assert_eq!(level, "warn");
        assert_eq!(filter, LevelFilter::Warn);
    }

    #[test]
    fn json_alone_means_json_at_info() {
        let (use_json, level, filter) = FlavorLogger::parse_level_mode("json");

        assert!(use_json);
        assert_eq!(level, "info");
        assert_eq!(filter, LevelFilter::Info);
    }

    #[test]
    fn every_named_level_maps_to_its_filter() {
        for (name, expected) in [
            ("trace", LevelFilter::Trace),
            ("debug", LevelFilter::Debug),
            ("info", LevelFilter::Info),
            ("warn", LevelFilter::Warn),
            ("error", LevelFilter::Error),
            ("off", LevelFilter::Off),
        ] {
            let (_, _, filter) = FlavorLogger::parse_level_mode(name);
            assert_eq!(filter, expected, "level {name}");
        }
    }

    #[test]
    fn an_unrecognised_level_filters_at_info() {
        let (_, level, filter) = FlavorLogger::parse_level_mode("json:bogus");

        assert_eq!(level, "bogus");
        assert_eq!(filter, LevelFilter::Info);
    }

    #[test]
    fn is_json_logging_reads_the_prefix() {
        assert!(is_json_logging_value(Some("json")));
        assert!(is_json_logging_value(Some("json:trace")));
        assert!(!is_json_logging_value(Some("debug")));
        assert!(!is_json_logging_value(None));
    }
}
