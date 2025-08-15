use chrono::Utc;
use log::{Level, Log, Metadata, Record};
use serde_json::json;
use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::path::PathBuf;
use std::sync::Mutex;

/// Custom logger that can output JSON or text format
pub struct FlavorLogger {
    level: Level,
    json_format: bool,
    output: Mutex<LogOutput>,
}

enum LogOutput {
    Stderr,
    File(File),
}

impl FlavorLogger {
    pub fn new(level: Level, json_format: bool, log_path: Option<PathBuf>) -> io::Result<Self> {
        let output = match log_path {
            Some(path) => {
                let file = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(&path)?;
                LogOutput::File(file)
            }
            None => LogOutput::Stderr,
        };

        Ok(FlavorLogger {
            level,
            json_format,
            output: Mutex::new(output),
        })
    }

    fn format_json(&self, record: &Record) -> String {
        let now = Utc::now();
        
        // Extract module name from target
        let module = record.target().split("::").next().unwrap_or("flavor");
        
        let mut log_entry = json!({
            "@timestamp": now.to_rfc3339(),
            "@level": record.level().to_string().to_lowercase(),
            "@message": record.args().to_string(),
            "@module": module,
        });

        // Add file and line information if available
        if let Some(file) = record.file() {
            log_entry["@file"] = json!(file);
        }
        if let Some(line) = record.line() {
            log_entry["@line"] = json!(line);
        }

        // Add process information
        log_entry["@pid"] = json!(std::process::id());

        serde_json::to_string(&log_entry).unwrap_or_else(|_| {
            format!("{{\"@level\":\"error\",\"@message\":\"Failed to serialize log entry\"}}")
        })
    }

    fn format_text(&self, record: &Record) -> String {
        let level_str = match record.level() {
            Level::Error => "ERROR",
            Level::Warn => "WARN ",
            Level::Info => "INFO ",
            Level::Debug => "DEBUG",
            Level::Trace => "TRACE",
        };

        // Check if message already contains emoji (for backwards compatibility)
        let msg = record.args().to_string();
        if msg.chars().any(|c| c as u32 >= 0x1F300) {
            // Message already has emoji formatting
            format!("[{}  {}] {}", level_str, record.target().split("::").next().unwrap_or(""), msg)
        } else {
            format!("[{}  {}] {}", level_str, record.target().split("::").next().unwrap_or(""), msg)
        }
    }
}

impl Log for FlavorLogger {
    fn enabled(&self, metadata: &Metadata) -> bool {
        metadata.level() <= self.level
    }

    fn log(&self, record: &Record) {
        if self.enabled(record.metadata()) {
            let formatted = if self.json_format {
                self.format_json(record)
            } else {
                self.format_text(record)
            };

            let mut output = self.output.lock().unwrap();
            let result = match *output {
                LogOutput::Stderr => {
                    writeln!(io::stderr(), "{}", formatted)
                }
                LogOutput::File(ref mut file) => {
                    writeln!(file, "{}", formatted)
                }
            };

            if let Err(e) = result {
                eprintln!("Failed to write log: {}", e);
            }
        }
    }

    fn flush(&self) {
        let mut output = self.output.lock().unwrap();
        let _ = match *output {
            LogOutput::Stderr => io::stderr().flush(),
            LogOutput::File(ref mut file) => file.flush(),
        };
    }
}

/// Initialize the logger based on environment variables
pub fn init_logger() -> Result<(), Box<dyn std::error::Error>> {
    let log_level_str = std::env::var("FLAVOR_LOG_LEVEL").unwrap_or_else(|_| "error".to_string());
    let log_path = std::env::var("FLAVOR_LOG_PATH").ok().map(PathBuf::from);
    
    // Parse the log level string - could be "json", "JSON", "json:debug", "JSON:info", etc.
    let (json_format, level) = if log_level_str.to_lowercase().starts_with("json") {
        // JSON format requested
        if log_level_str.contains(':') {
            // Format: "json:level" or "JSON:level"
            let parts: Vec<&str> = log_level_str.split(':').collect();
            if parts.len() >= 2 {
                (true, parse_log_level(parts[1]))
            } else {
                (true, Level::Info) // Default to info for json
            }
        } else {
            // Just "json" or "JSON" - default to info level
            (true, Level::Info)
        }
    } else {
        // Regular text format with specified level
        (false, parse_log_level(&log_level_str))
    };

    let logger = FlavorLogger::new(level, json_format, log_path)?;
    
    log::set_boxed_logger(Box::new(logger))
        .map(|()| log::set_max_level(level.to_level_filter()))?;
    
    Ok(())
}

fn parse_log_level(level_str: &str) -> Level {
    match level_str.to_lowercase().as_str() {
        "error" => Level::Error,
        "warn" | "warning" => Level::Warn,
        "info" => Level::Info,
        "debug" => Level::Debug,
        "trace" => Level::Trace,
        _ => Level::Info, // Default to info for unknown values
    }
}