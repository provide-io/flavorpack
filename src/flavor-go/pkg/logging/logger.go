package logging

import (
	"io"
	"os"
	"time"

	"github.com/hashicorp/go-hclog"
)

// NewLogger creates a new hclog logger with standard settings
func NewLogger(name string, level string, output io.Writer) hclog.Logger {
	if output == nil {
		output = os.Stderr
	}

	// Determine if JSON format should be used
	jsonFormat := os.Getenv("FLAVOR_JSON_LOG") == "1"

	// Add prefix for non-JSON output
	if !jsonFormat {
		output = NewPrefixWriter("🐹 ", output)
	}

	opts := &hclog.LoggerOptions{
		Name:       name,
		Level:      hclog.LevelFromString(level),
		JSONFormat: jsonFormat,
		Output:     output,
		TimeFormat: "2006-01-02T15:04:05Z", // UTC ISO format
		TimeFn: func() time.Time {
			return time.Now().UTC()
		},
	}

	return hclog.New(opts)
}

// GetLogLevel returns the configured log level from environment
func GetLogLevel() string {
	level := os.Getenv("FLAVOR_LOG_LEVEL")
	if level == "" {
		level = "warn" // Default to warn for production safety
	}
	return level
}
