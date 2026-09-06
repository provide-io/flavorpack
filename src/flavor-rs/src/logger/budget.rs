// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! A byte budget for the launcher's own diagnostics on stderr.
//!
//! stderr belongs to whoever launched us, and that reader may never drain it.
//! A plugin host is the case that matters: it spawns the launcher, waits for a
//! handshake line on stdout, and only starts reading stderr once the plugin is
//! up. Write more than the pipe holds -- 64KB on Linux and macOS -- and the
//! launcher blocks mid-write, before it has printed the handshake, and the host
//! is left waiting on a process that is waiting on the host.
//!
//! Logging must not be able to do that at any level. Capping the bytes that
//! reach stderr makes the deadlock unreachable by construction rather than by
//! keeping the default quiet enough, which only holds until someone sets
//! `FLAVOR_LOG_LEVEL=debug` to investigate the very launch that then hangs.
//!
//! Records past the cap are dropped, not buffered: holding them costs memory
//! for output nobody is reading. One line says so, and names the way to get
//! the whole log, so a truncated tail is never mistaken for the end of the
//! story. `FLAVOR_LOG_PATH` writes to a file, which has no such limit and is
//! not capped here.

use std::io::{self, Write};

/// Bytes of launcher diagnostics allowed onto an undrained stderr.
///
/// A quarter of the smallest pipe this runs against, so the plugin's own
/// stderr -- a Python traceback, which is the thing worth reading -- still has
/// room after the launcher has had its say.
pub const STDERR_BUDGET: usize = 16 * 1024;

const NOTICE: &[u8] =
    b"\n[flavor] launcher log truncated: stderr budget reached. Set FLAVOR_LOG_PATH for the full log.\n";

/// Passes writes through until the budget is spent, then drops them.
pub struct BudgetedWriter<W: Write> {
    inner: W,
    remaining: usize,
    noticed: bool,
}

impl<W: Write> std::fmt::Debug for BudgetedWriter<W> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("BudgetedWriter")
            .field("remaining", &self.remaining)
            .field("noticed", &self.noticed)
            .finish_non_exhaustive()
    }
}

impl<W: Write> BudgetedWriter<W> {
    pub fn new(inner: W, budget: usize) -> Self {
        Self {
            inner,
            remaining: budget,
            noticed: false,
        }
    }
}

impl<W: Write> BudgetedWriter<W> {
    /// Say once that the rest is missing.
    ///
    /// Best effort: the budget exists because this write can block, and failing
    /// to explain the truncation is not worth failing the launch over.
    fn announce_truncation(&mut self) {
        if self.noticed {
            return;
        }
        self.noticed = true;
        let _ = self.inner.write_all(NOTICE);
        let _ = self.inner.flush();
    }
}

impl<W: Write> Write for BudgetedWriter<W> {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if self.remaining == 0 {
            self.announce_truncation();
            // Reported as written. The caller is a logging backend, and a short
            // write would have it retry the remainder forever.
            return Ok(buf.len());
        }

        let take = buf.len().min(self.remaining);
        self.inner.write_all(&buf[..take])?;
        self.remaining -= take;

        // Announced here, not on the next write, because there may not be one:
        // the launcher execs into the payload once it is ready, and a record
        // that ran out of budget on the way is the last thing it writes. That
        // left the truncation unmarked in the case it mattered most.
        if self.remaining == 0 && take < buf.len() {
            self.announce_truncation();
        }
        Ok(buf.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        self.inner.flush()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The regression this exists for: a launch must not be able to write more
    /// than a pipe holds, whatever the log level, or an undrained reader
    /// deadlocks it before the handshake.
    #[test]
    fn stderr_can_never_exceed_the_budget() {
        let mut sink: Vec<u8> = Vec::new();
        {
            let mut writer = BudgetedWriter::new(&mut sink, 1024);
            // The launcher writes ~193KB at trace; this is that shape.
            for _ in 0..2000 {
                let record = b"2026-01-01 TRACE mmap read_at offset=0 size=64 zero_copy=true\n";
                assert_eq!(writer.write(record).unwrap(), record.len());
            }
        }
        assert!(
            sink.len() <= 1024 + NOTICE.len(),
            "wrote {} bytes against a 1024 budget",
            sink.len()
        );
    }

    /// The cap must not swallow the beginning, which is the part with the
    /// launch in it.
    #[test]
    fn everything_up_to_the_budget_still_arrives() {
        let mut sink: Vec<u8> = Vec::new();
        {
            let mut writer = BudgetedWriter::new(&mut sink, 32);
            writer.write_all(b"0123456789").unwrap();
            writer.write_all(b"abcdefghij").unwrap();
        }
        assert!(sink.starts_with(b"0123456789abcdefghij"));
    }

    /// Truncation is stated once, not on every dropped record.
    #[test]
    fn the_truncation_is_announced_exactly_once() {
        let mut sink: Vec<u8> = Vec::new();
        {
            let mut writer = BudgetedWriter::new(&mut sink, 4);
            for _ in 0..10 {
                writer.write_all(b"overflowing").unwrap();
            }
        }
        let text = String::from_utf8_lossy(&sink);
        assert_eq!(text.matches("truncated").count(), 1);
    }

    /// The record that exhausts the budget is the one most likely to be the
    /// last: the launcher execs into the payload shortly after, so waiting for
    /// a further write to announce the truncation leaves it unannounced. This
    /// is what a packaged provider actually did -- 16KB of log, no notice.
    #[test]
    fn truncation_is_announced_on_the_write_that_exhausts_the_budget() {
        let mut sink: Vec<u8> = Vec::new();
        {
            let mut writer = BudgetedWriter::new(&mut sink, 8);
            // One write, larger than the budget, and then nothing further.
            writer.write_all(b"0123456789abcdef").unwrap();
        }
        let text = String::from_utf8_lossy(&sink);
        assert!(text.contains("truncated"), "no notice in {text:?}");
    }

    /// A budget of zero still reports progress rather than looping.
    #[test]
    fn a_spent_budget_reports_the_write_as_done() {
        let mut sink: Vec<u8> = Vec::new();
        let mut writer = BudgetedWriter::new(&mut sink, 0);
        assert_eq!(writer.write(b"dropped").unwrap(), b"dropped".len());
    }
}
