//! Carries `log` records into provide-telemetry.
//!
//! The crate publishes its own `Logger` and does not implement `log::Log`, so
//! nothing it offers is reachable from a `log::info!`. Every call site in this
//! crate — 454 of them across 28 files — is a `log` macro, and rewriting them
//! would be the whole adoption cost for none of the benefit.
//!
//! Installing this as the `log` backend gets it the other way round: the macros
//! stay, and the records they produce reach provide-telemetry's level gating,
//! event schema, and configured sink, which is what makes the Rust launcher's
//! output the same shape as the Go one's.

use log::{Level, Log, Metadata, Record};
use provide_telemetry::{LogSeverity, Logger};

/// A `log` backend that publishes each record through provide-telemetry.
#[derive(Debug)]
pub struct TelemetryBridge;

/// The severity provide-telemetry knows a `log` level by.
///
/// `log` has no `Critical`, so nothing maps to it; the telemetry side keeps the
/// rank for callers that reach its API directly.
pub(crate) fn severity_for(level: Level) -> LogSeverity {
    match level {
        Level::Error => LogSeverity::Error,
        Level::Warn => LogSeverity::Warn,
        Level::Info => LogSeverity::Info,
        Level::Debug => LogSeverity::Debug,
        Level::Trace => LogSeverity::Trace,
    }
}

impl Log for TelemetryBridge {
    fn enabled(&self, _metadata: &Metadata<'_>) -> bool {
        // provide-telemetry gates on its own configured level and module levels
        // when the record reaches it. Answering `true` here keeps one place
        // deciding what is emitted; a second threshold would only make the two
        // disagree, and `log::set_max_level` already stops the macro bodies
        // that are cheapest to skip.
        true
    }

    fn log(&self, record: &Record<'_>) {
        Logger::new(Some(record.target()))
            .log_at(severity_for(record.level()), &record.args().to_string());
    }

    fn flush(&self) {
        // The sink writes each record as it arrives and flushes its own writer
        // on shutdown, so there is nothing buffered here to push.
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_log_level_maps_to_the_matching_severity() {
        assert_eq!(severity_for(Level::Error), LogSeverity::Error);
        assert_eq!(severity_for(Level::Warn), LogSeverity::Warn);
        assert_eq!(severity_for(Level::Info), LogSeverity::Info);
        assert_eq!(severity_for(Level::Debug), LogSeverity::Debug);
        assert_eq!(severity_for(Level::Trace), LogSeverity::Trace);
    }

    #[test]
    fn severity_ordering_survives_the_mapping() {
        // A mapping that swapped two arms would still be total, and every arm
        // above would still pass. Rank order is what the gate actually uses.
        assert!(severity_for(Level::Error) > severity_for(Level::Warn));
        assert!(severity_for(Level::Warn) > severity_for(Level::Info));
        assert!(severity_for(Level::Info) > severity_for(Level::Debug));
        assert!(severity_for(Level::Debug) > severity_for(Level::Trace));
    }

    #[test]
    fn the_bridge_accepts_records_at_every_level() {
        // `enabled` deliberately defers to provide-telemetry rather than
        // applying a second threshold of its own.
        let bridge = TelemetryBridge;
        for level in [
            Level::Error,
            Level::Warn,
            Level::Info,
            Level::Debug,
            Level::Trace,
        ] {
            let metadata = Metadata::builder().level(level).target("flavor").build();
            assert!(bridge.enabled(&metadata));
        }
    }
}
