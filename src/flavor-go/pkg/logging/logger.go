package logging

import (
	"context"
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/provide-io/flavor/go/flavor/pkg/envvars"
	provlog "github.com/provide-io/provide-telemetry/go/logger"
)

// Setup initialises the logger from flavorpack env vars.
// Must be called once at process startup before any logging.
// If output is non-nil, log records are written there instead of os.Stderr.
func Setup(logLevel string, output io.Writer) {
	format := provlog.LogFormatConsole
	if os.Getenv(envvars.EnvJSONLog) == "1" || strings.HasPrefix(logLevel, "json") {
		format = provlog.LogFormatJSON
	}
	// Strip the "json:" prefix from the level string if present.
	actualLevel := logLevel
	if strings.HasPrefix(logLevel, "json:") {
		actualLevel = logLevel[len("json:"):]
	} else if logLevel == "json" {
		actualLevel = "info"
	}
	provlog.Configure(provlog.LogConfig{
		ServiceName: "flavor-go",
		Level:       strings.ToUpper(actualLevel),
		Format:      format,
		Output:      output,
	})
}

// NewLogger returns a named *slog.Logger via provide-telemetry/go/logger.
func NewLogger(ctx context.Context, name string) *slog.Logger {
	return provlog.GetLogger(ctx, name)
}

// NewNullLogger returns a *slog.Logger that discards all output (for tests).
func NewNullLogger() *slog.Logger {
	return provlog.NewNullLogger()
}

// NewBufferLogger returns a *slog.Logger that writes to w at the given level (for tests).
func NewBufferLogger(w io.Writer, level slog.Level) *slog.Logger {
	return provlog.NewBufferLogger(w, level)
}

// GetLogLevel returns the configured log level from environment.
func GetLogLevel() string {
	level := os.Getenv(envvars.EnvLogLevel)
	if level == "" {
		level = "warn"
	}
	return level
}

// LevelTrace is re-exported for callers that need trace-level logging.
const LevelTrace = provlog.LevelTrace

// Trace emits a TRACE-level record on logger.
func Trace(logger *slog.Logger, msg string, args ...any) {
	provlog.Trace(logger, msg, args...)
}

// IsEnabled reports whether logger would emit records at level.
func IsEnabled(logger *slog.Logger, level slog.Level) bool {
	return provlog.IsEnabled(logger, level)
}
