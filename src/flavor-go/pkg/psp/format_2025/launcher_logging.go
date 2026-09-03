// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"context"
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// resolveLogLevel picks the log level and records where it came from, so a
// launcher that is quieter than expected can say which setting made it so.
//
// The default is warn: a launcher's own logging is not the packaged
// application's output, and production runs should not mix the two.
func resolveLogLevel(cliLogLevel, cliLogSource string) (level, source string) {
	switch {
	case cliLogLevel != "":
		return cliLogLevel, cliLogSource
	case os.Getenv(EnvLauncherLogLevel) != "":
		return os.Getenv(EnvLauncherLogLevel), EnvLauncherLogLevel
	case os.Getenv(EnvLogLevel) != "":
		return os.Getenv(EnvLogLevel), EnvLogLevel
	default:
		return "warn", "default"
	}
}

// describeLogLevel strips the json: transport prefix, leaving the severity the
// operator actually chose. Bare "json" carries no severity and means info.
func describeLogLevel(logLevel string) string {
	if after, found := strings.CutPrefix(logLevel, "json:"); found {
		return after
	}
	if logLevel == "json" {
		return "info"
	}
	return logLevel
}

// openLogOutput chooses where launcher logging goes. It returns a close
// function, which is a no-op unless a log file was opened.
//
// A log file that will not open is not fatal: logging falls back to the
// default destination rather than stopping the launch.
func openLogOutput(logLevel string) (io.Writer, func()) {
	if logPath := os.Getenv(EnvLogPath); logPath != "" {
		file, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, FilePerms)
		if err == nil {
			return file, func() { _ = file.Close() }
		}
		return nil, func() {}
	}

	if !logging.IsJSONFormat(logLevel) {
		// The prefix marks launcher output apart from the package's own.
		return logging.NewPrefixWriter("🐹 ", launcherStderrWriter), func() {}
	}

	return nil, func() {}
}

// setupLauncherLogging configures logging and returns the launcher's logger,
// the severity to report, and a close function for any log file opened.
func setupLauncherLogging(cliLogLevel, cliLogSource string) (*slog.Logger, string, string, func()) {
	logLevel, logSource := resolveLogLevel(cliLogLevel, cliLogSource)
	actualLevel := describeLogLevel(logLevel)

	setUTF8ConsoleOutput()

	logOutput, closeLog := openLogOutput(logLevel)
	logging.Setup(logLevel, logOutput)

	return logging.NewLogger(context.Background(), "flavor-go.launcher"), actualLevel, logSource, closeLog
}

// traceEnvironment records every inherited variable, which is the only way to
// see what a package actually started with.
func traceEnvironment(logger *slog.Logger) {
	envVars := os.Environ()
	logger.Debug("🔧 Environment variables received from parent process", "count", len(envVars))

	if !logging.IsEnabled(logger, logging.LevelTrace) {
		return
	}
	for _, env := range envVars {
		if parts := strings.SplitN(env, "=", 2); len(parts) == 2 {
			logging.Trace(logger, "📝 Environment variable", "key", parts[0], "value", parts[1])
		}
	}
}
