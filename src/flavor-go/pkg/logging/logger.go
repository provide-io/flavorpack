package logging

import (
	"context"
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/provide-io/flavor/go/flavor/pkg/envvars"
	telemetry "github.com/provide-io/provide-telemetry/go"
)

// LevelTrace is re-exported for callers that need trace-level logging.
const LevelTrace = telemetry.LevelTrace

// Setup initialises the logger from flavorpack env vars.
// Must be called once at process startup before any logging.
// If output is non-nil, log records are written there instead of os.Stderr.
//
// The writer is what keeps launcher output legible when several language
// runtimes share one stream: the caller wraps it to prefix every line, and the
// Go and Rust launchers are told apart by 🐹 and 🦀.
func Setup(logLevel string, output io.Writer) {
	format := "console"
	if IsJSONFormat(logLevel) {
		format = "json"
	}

	cfg := telemetry.DefaultTelemetryConfig()
	cfg.ServiceName = "flavor-go"
	cfg.Logging.Level = strings.ToUpper(stripJSONPrefix(logLevel))
	cfg.Logging.Format = format

	opts := []telemetry.SetupOption{telemetry.WithConfig(cfg)}
	if output != nil {
		opts = append(opts, telemetry.WithLogOutput(output))
	}

	// SetupTelemetry runs once per process: a second call returns the first
	// config unchanged, so a later Setup would silently keep the first level and
	// the first writer. ReconfigureTelemetry does not help -- it applies the
	// config but ignores WithLogOutput. Shutting down first is what makes a
	// repeat Setup mean what it says; it no-ops when nothing is set up yet.
	_ = telemetry.ShutdownTelemetry(context.Background())

	// A telemetry setup that fails should not stop a package from running: the
	// launcher's job is to run the payload, and losing logs is not a reason to
	// refuse. The error is reported through the logger that setup leaves behind.
	if _, err := telemetry.SetupTelemetry(opts...); err != nil {
		telemetry.GetLogger(context.Background(), "flavor-go.logging").
			Warn("⚠️ Telemetry setup failed; continuing with defaults", "error", err)
	}
}

// stripJSONPrefix removes the transport prefix from a level string, leaving the
// severity. Bare "json" names no severity and means info.
func stripJSONPrefix(logLevel string) string {
	if after, found := strings.CutPrefix(logLevel, "json:"); found {
		return after
	}
	if logLevel == "json" {
		return "info"
	}
	return logLevel
}

// NewLogger returns a named *slog.Logger via provide-telemetry.
func NewLogger(ctx context.Context, name string) *slog.Logger {
	return telemetry.GetLogger(ctx, name)
}

// NewDefaultLogger returns a named *slog.Logger using the current active configuration,
// evaluated at call time. Use for package-level loggers where no context is available.
func NewDefaultLogger(name string) *slog.Logger {
	return telemetry.GetLogger(context.Background(), name)
}

// NewNullLogger returns a *slog.Logger that discards all output (for tests).
//
// provide-telemetry removed its own null and buffer loggers in 0.8.0 with no
// replacement. Both are a handler over a writer, so flavorpack keeps its own
// rather than holding the dependency back for two test helpers.
func NewNullLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, &slog.HandlerOptions{Level: LevelTrace}))
}

// NewBufferLogger returns a *slog.Logger that writes to w at the given level (for tests).
func NewBufferLogger(w io.Writer, level slog.Level) *slog.Logger {
	return slog.New(slog.NewTextHandler(w, &slog.HandlerOptions{Level: level}))
}

// IsJSONFormat reports whether the given logLevel string (or the FLAVOR_JSON_LOG
// environment variable) will result in JSON-formatted output. Entry points use this
// to decide whether to wrap the output writer in a PrefixWriter before calling Setup.
func IsJSONFormat(logLevel string) bool {
	return os.Getenv(envvars.EnvJSONLog) == "1" || strings.HasPrefix(logLevel, "json")
}

// GetLogLevel returns the configured log level from environment.
func GetLogLevel() string {
	level := os.Getenv(envvars.EnvLogLevel)
	if level == "" {
		level = "warn"
	}
	return level
}

// Trace emits a TRACE-level record on logger.
//
// provide-telemetry's own Trace is a tracing-span helper in 0.9.0 and does not
// emit a log record, so this writes one directly at LevelTrace.
func Trace(logger *slog.Logger, msg string, args ...any) {
	logger.Log(context.Background(), LevelTrace, msg, args...)
}

// IsEnabled reports whether logger would emit records at level.
func IsEnabled(logger *slog.Logger, level slog.Level) bool {
	return logger.Enabled(context.Background(), level)
}
