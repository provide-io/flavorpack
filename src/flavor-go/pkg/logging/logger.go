// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package logging

import (
	"context"
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/hashicorp/go-hclog"
	"github.com/provide-io/flavor/go/flavor/pkg/envvars"
)

// Setup initialises the logger from flavorpack env vars.
// Must be called once at process startup before any logging.
// If output is non-nil, log records are written there instead of os.Stderr.
func Setup(logLevel string, output io.Writer) {
	format := provlog.LogFormatConsole
	if IsJSONFormat(logLevel) {
		format = provlog.LogFormatJSON
	}

	// Determine if JSON format should be used
	jsonFormat := os.Getenv(envvars.EnvJSONLog) == "1"

	// Add prefix for non-JSON output
	if !jsonFormat {
		output = NewPrefixWriter("🐹 ", output)
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

// NewDefaultLogger returns a named *slog.Logger using the current active configuration,
// evaluated at call time. Use for package-level loggers where no context is available.
func NewDefaultLogger(name string) *slog.Logger {
	return provlog.GetDefaultLogger(name)
}

// NewNullLogger returns a *slog.Logger that discards all output (for tests).
func NewNullLogger() *slog.Logger {
	return provlog.NewNullLogger()
}

// NewBufferLogger returns a *slog.Logger that writes to w at the given level (for tests).
func NewBufferLogger(w io.Writer, level slog.Level) *slog.Logger {
	return provlog.NewBufferLogger(w, level)
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
