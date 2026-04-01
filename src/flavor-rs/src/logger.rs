//! JSON structured logging implementation for Flavor

use chrono::{Local, Utc};
use log::{Level, Log, Metadata, Record};
use serde_json::json;
use std::env;
use std::fs::OpenOptions;
use std::io::{self, Write};
use std::sync::Mutex;

/// JSON logger implementation
#[derive(Debug)]
pub struct JsonLogger {
    level: Level,
    target_file: Mutex<Option<std::fs::File>>,
}

impl JsonLogger {
    /// Create a new JSON logger
    pub fn new(level: Level, log_path: Option<String>) -> Self {
        let target_file = if let Some(path) = log_path {
            OpenOptions::new().create(true).append(true).open(path).ok()
        } else {
            None
        };

        JsonLogger {
            level,
            target_file: Mutex::new(target_file),
        }
    }

    /// Parse the logging mode and level.
    fn parse_level_mode(level_str: &str) -> (bool, String, log::LevelFilter, Level) {
        // Parse JSON format from log level (e.g., "json:debug" or just "debug")
        let (use_json, actual_level) = if let Some(stripped) = level_str.strip_prefix("json:") {
            (true, stripped)
        } else if level_str == "json" {
            (true, "info")
        } else {
            (false, level_str)
        };

        let level_filter = match actual_level {
            "trace" => log::LevelFilter::Trace,
            "debug" => log::LevelFilter::Debug,
            "info" => log::LevelFilter::Info,
            "warn" => log::LevelFilter::Warn,
            "error" => log::LevelFilter::Error,
            "off" => log::LevelFilter::Off,
            _ => log::LevelFilter::Info,
        };

        let level = match actual_level {
            "trace" => Level::Trace,
            "debug" => Level::Debug,
            "info" => Level::Info,
            "warn" => Level::Warn,
            "error" => Level::Error,
            _ => Level::Trace, // Default to Trace for comprehensive diagnostics
        };

        (use_json, actual_level.to_string(), level_filter, level)
    }

    /// Initialize the logger with specified level and source
    pub fn init_with_level(level_str: &str, source: &str) -> (String, String) {
        let log_path = env::var(crate::env_vars::LOG_PATH).ok();
        let (use_json, actual_level, level_filter, level) = Self::parse_level_mode(level_str);

        if !use_json {
            // Use standard env_logger with custom format to add 🦀 prefix
            env_logger::Builder::new()
                .filter_level(level_filter)
                .format(|buf, record| {
                    use std::io::Write;

                    write!(buf, "🦀 ")?;
                    write!(
                        buf,
                        "[{} {} {}] ",
                        Local::now().format("%Y-%m-%dT%H:%M:%SZ"),
                        record.level(),
                        record.target()
                    )?;
                    writeln!(buf, "{}", record.args())
                })
                .init();
            return (actual_level.to_string(), source.to_string());
        }

        let logger = Box::new(JsonLogger::new(level, log_path));

        if let Err(e) = log::set_boxed_logger(logger) {
            eprintln!("Failed to initialize JSON logger: {e}");
            return (actual_level.to_string(), source.to_string());
        }

        log::set_max_level(level.to_level_filter());
        (actual_level.to_string(), source.to_string())
    }

    /// Initialize the JSON logger with default settings
    pub fn init() {
        // Check FLAVOR_LOG_LEVEL for JSON mode, default to trace for comprehensive diagnostics
        let log_level =
            env::var(crate::env_vars::LOG_LEVEL).unwrap_or_else(|_| "trace".to_string());
        Self::init_with_level(&log_level, crate::env_vars::LOG_LEVEL);
    }
}

impl Log for JsonLogger {
    fn enabled(&self, metadata: &Metadata<'_>) -> bool {
        metadata.level() <= self.level
    }

    fn log(&self, record: &Record<'_>) {
        if !self.enabled(record.metadata()) {
            return;
        }

        // Build JSON log entry
        let log_entry = json!({
            "@timestamp": Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Micros, true),
            "@level": record.level().to_string().to_lowercase(),
            "@message": record.args().to_string(),
            "@module": record.target(),
            "@pid": std::process::id(),
            "@file": record.file().unwrap_or("unknown"),
            "@line": record.line().unwrap_or(0),
        });

        let json_string = format!(
            "{}\n",
            serde_json::to_string(&log_entry).unwrap_or_default()
        );

        // Write to file or stderr
        if let Ok(mut file_guard) = self.target_file.lock() {
            if let Some(ref mut file) = *file_guard {
                let _ = file.write_all(json_string.as_bytes());
                let _ = file.flush();
            } else {
                // Write to stderr
                let _ = io::stderr().write_all(json_string.as_bytes());
                let _ = io::stderr().flush();
            }
        } else {
            // Fallback to stderr if lock fails
            let _ = io::stderr().write_all(json_string.as_bytes());
            let _ = io::stderr().flush();
        }
    }

    fn flush(&self) {
        if let Ok(mut file_guard) = self.target_file.lock() {
            if let Some(ref mut file) = *file_guard {
                let _ = file.flush();
            }
        }
        let _ = io::stderr().flush();
    }
}

/// Helper to check if JSON logging is enabled
pub fn is_json_logging() -> bool {
    is_json_logging_value(env::var(crate::env_vars::LOG_LEVEL).ok().as_deref())
}

fn is_json_logging_value(value: Option<&str>) -> bool {
    value.map(|v| v.starts_with("json")).unwrap_or(false)
}

#[cfg(test)]
#[allow(unsafe_code)]
mod tests {
    use super::*;
    use log::Log;
    use tempfile::tempdir;

    #[test]
    fn parse_level_mode_handles_plain_and_json_levels() {
        let (use_json, actual_level, level_filter, level) = JsonLogger::parse_level_mode("debug");
        assert!(!use_json);
        assert_eq!(actual_level, "debug");
        assert_eq!(level_filter, log::LevelFilter::Debug);
        assert_eq!(level, Level::Debug);

        let (use_json, actual_level, level_filter, level) =
            JsonLogger::parse_level_mode("json:warn");
        assert!(use_json);
        assert_eq!(actual_level, "warn");
        assert_eq!(level_filter, log::LevelFilter::Warn);
        assert_eq!(level, Level::Warn);
    }

    #[test]
    fn parse_level_mode_defaults_json_mode_to_info() {
        let (use_json, actual_level, level_filter, level) = JsonLogger::parse_level_mode("json");
        assert!(use_json);
        assert_eq!(actual_level, "info");
        assert_eq!(level_filter, log::LevelFilter::Info);
        assert_eq!(level, Level::Info);
    }

    #[test]
    fn parse_level_mode_defaults_invalid_json_level_to_trace() {
        let (use_json, actual_level, level_filter, level) =
            JsonLogger::parse_level_mode("json:bogus");
        assert!(use_json);
        assert_eq!(actual_level, "bogus");
        assert_eq!(level_filter, log::LevelFilter::Info);
        assert_eq!(level, Level::Trace);
    }

    #[test]
    fn json_logger_writes_structured_records_to_file() {
        let dir = tempdir().unwrap();
        let log_path = dir.path().join("flavor.jsonl");
        let logger = JsonLogger::new(Level::Info, Some(log_path.display().to_string()));
        let record = log::Record::builder()
            .args(format_args!("hello from flavor"))
            .level(Level::Info)
            .target("flavor::tests")
            .file(Some("logger.rs"))
            .line(Some(42))
            .build();

        logger.log(&record);

        let contents = std::fs::read_to_string(&log_path).unwrap();
        assert!(contents.contains("\"@level\":\"info\""));
        assert!(contents.contains("\"@message\":\"hello from flavor\""));
        assert!(contents.contains("\"@module\":\"flavor::tests\""));
        assert!(contents.contains("\"@line\":42"));
    }

    #[test]
    fn json_logger_handles_stderr_fallback_without_a_file() {
        let logger = JsonLogger::new(Level::Info, None);
        let debug_record = log::Record::builder()
            .args(format_args!("hidden"))
            .level(Level::Debug)
            .target("flavor::tests")
            .build();
        let info_record = log::Record::builder()
            .args(format_args!("stderr fallback"))
            .level(Level::Info)
            .target("flavor::tests")
            .build();

        assert!(logger.target_file.lock().unwrap().is_none());
        assert!(!logger.enabled(debug_record.metadata()));
        assert!(logger.enabled(info_record.metadata()));

        logger.log(&info_record);
        logger.flush();
    }

    #[test]
    fn init_with_level_json_mode_returns_actual_level_and_source() {
        let (actual_level, source) = JsonLogger::init_with_level("json:debug", "unit-test");

        assert_eq!(actual_level, "debug");
        assert_eq!(source, "unit-test");
    }

    #[test]
    fn is_json_logging_tracks_environment_prefix() {
        assert!(is_json_logging_value(Some("json:trace")));
        assert!(!is_json_logging_value(Some("debug")));
        assert!(!is_json_logging_value(None));
    }
}
