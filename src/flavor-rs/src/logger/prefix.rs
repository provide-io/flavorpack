//! A writer that marks every line with the runtime that produced it.
//!
//! The pretaster runs all four builder×launcher combinations into one stream,
//! and the prefix is what makes that output readable: `🦀 ` is the Rust
//! launcher, `🐹 ` the Go one. `flavor-go` gets this by wrapping its telemetry
//! writer in a `PrefixWriter`; this is the same thing on the Rust side, handed
//! to `provide_telemetry::set_log_output`.

use std::fmt;
use std::io::{self, Write};

/// Wraps a writer and starts every line with a fixed prefix.
///
/// Records arrive one line at a time from the telemetry sink, but a `Write` is
/// not obliged to be called a line at a time, so the prefix is decided by
/// position in the stream rather than by call: written at the very start, and
/// again after each newline that is not the last byte. A trailing newline arms
/// the next line instead of emitting a prefix that might never be followed by
/// anything.
pub struct PrefixWriter<W: Write> {
    prefix: &'static str,
    inner: W,
    at_line_start: bool,
}

/// Written by hand rather than derived: the wrapped writer is a destination,
/// not data, and requiring it to be `Debug` would rule out `Stderr` and `File`
/// — which are the two this is ever constructed with.
impl<W: Write> fmt::Debug for PrefixWriter<W> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("PrefixWriter")
            .field("prefix", &self.prefix)
            .field("at_line_start", &self.at_line_start)
            .finish_non_exhaustive()
    }
}

impl<W: Write> PrefixWriter<W> {
    pub fn new(prefix: &'static str, inner: W) -> Self {
        Self {
            prefix,
            inner,
            at_line_start: true,
        }
    }
}

impl<W: Write> Write for PrefixWriter<W> {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if buf.is_empty() {
            return Ok(0);
        }

        for line in buf.split_inclusive(|byte| *byte == b'\n') {
            if self.at_line_start {
                self.inner.write_all(self.prefix.as_bytes())?;
            }
            self.inner.write_all(line)?;
            self.at_line_start = line.ends_with(b"\n");
        }

        // The whole buffer was consumed or an error was returned above; a short
        // count here would have the caller resend bytes already written, and
        // prefix the resent tail as though it began a line.
        Ok(buf.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        self.inner.flush()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn written(chunks: &[&str]) -> String {
        let mut sink = Vec::new();
        {
            let mut writer = PrefixWriter::new("🦀 ", &mut sink);
            for chunk in chunks {
                writer.write_all(chunk.as_bytes()).expect("write");
            }
        }
        String::from_utf8(sink).expect("utf-8")
    }

    #[test]
    fn prefixes_a_single_line() {
        assert_eq!(written(&["hello\n"]), "🦀 hello\n");
    }

    #[test]
    fn prefixes_every_line_of_one_write() {
        assert_eq!(
            written(&["one\ntwo\nthree\n"]),
            "🦀 one\n🦀 two\n🦀 three\n"
        );
    }

    #[test]
    fn prefixes_once_across_a_split_line() {
        // A line delivered in pieces is still one line, so it takes one prefix.
        assert_eq!(written(&["par", "tial\n"]), "🦀 partial\n");
    }

    #[test]
    fn prefixes_a_line_with_no_trailing_newline() {
        assert_eq!(written(&["no newline"]), "🦀 no newline");
    }

    #[test]
    fn a_trailing_newline_does_not_emit_a_dangling_prefix() {
        // The prefix for the next line is written when that line arrives, so a
        // stream that ends here ends clean.
        assert_eq!(written(&["done\n"]), "🦀 done\n");
    }

    #[test]
    fn an_empty_write_writes_nothing() {
        assert_eq!(written(&[""]), "");
    }

    #[test]
    fn a_blank_line_is_still_a_line() {
        assert_eq!(written(&["\n\n"]), "🦀 \n🦀 \n");
    }

    #[test]
    fn reports_every_byte_it_was_given_as_written() {
        let mut sink = Vec::new();
        let mut writer = PrefixWriter::new("🦀 ", &mut sink);
        let buf = b"a\nb\n";

        assert_eq!(writer.write(buf).expect("write"), buf.len());
    }
}
