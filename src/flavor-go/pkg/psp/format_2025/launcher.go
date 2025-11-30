package format_2025

// Cache invalidation: Force rebuild to include Windows spawn mode fix (2025-10-31)

import (
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"syscall"
	"time"

	"github.com/hashicorp/go-hclog"
	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// LaunchWithLogLevel launches with explicit log level control
func LaunchWithLogLevel(exePath string, args []string, cliLogLevel, cliLogSource string) {
	// Determine log level and source
	var logLevel string
	var logSource string

	if cliLogLevel != "" {
		logLevel = cliLogLevel
		logSource = cliLogSource
	} else if envLevel := os.Getenv("FLAVOR_LAUNCHER_LOG_LEVEL"); envLevel != "" {
		logLevel = envLevel
		logSource = "FLAVOR_LAUNCHER_LOG_LEVEL"
	} else if envLevel := os.Getenv("FLAVOR_LOG_LEVEL"); envLevel != "" {
		logLevel = envLevel
		logSource = "FLAVOR_LOG_LEVEL"
	} else {
		logLevel = "trace" // Default to trace for comprehensive diagnostics
		logSource = "default"
	}

	// Parse JSON format from log level (e.g., "json:debug" or just "debug")
	jsonFormat := false
	actualLevel := logLevel
	if strings.HasPrefix(logLevel, "json") {
		jsonFormat = true
		parts := strings.Split(logLevel, ":")
		if len(parts) > 1 {
			actualLevel = parts[1]
		} else {
			actualLevel = "info"
		}
	}

	// Configure logger with JSON if requested
	var output io.Writer = os.Stderr

	// Support log file output
	if logPath := os.Getenv("FLAVOR_LOG_PATH"); logPath != "" {
		if file, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644); err == nil {
			output = file
		}
	}

	// Add prefix to non-JSON output (ASCII on Windows, emoji on Unix)
	if !jsonFormat {
		prefix := "[GO] "
		if runtime.GOOS != "windows" {
			prefix = "🐹 "
		}
		output = logging.NewPrefixWriter(prefix, output)
	}

	loggerOpts := &hclog.LoggerOptions{
		Name:       "flavor-go-launcher",
		Level:      hclog.LevelFromString(actualLevel),
		JSONFormat: jsonFormat,
		Output:     output,
		TimeFormat: "2006-01-02T15:04:05Z", // UTC ISO format without timezone
		TimeFn: func() time.Time {
			return time.Now().UTC() // Force UTC time
		},
	}

	logger := hclog.New(loggerOpts)

	// Only log startup messages in CLI mode
	if isEnvTrue("FLAVOR_LAUNCHER_CLI") {
		logger.Info("🐹🐹🐹 Hello from Flavor's Go Launcher 🐹🐹🐹")
		logger.Debug("Log level", "level", actualLevel, "source", logSource)
		logger.Info("PSPF Go Launcher starting...")
	}
	logger.Debug("📖 Reading PSPF bundle")

	envVars := os.Environ()
	logger.Debug("🔧 Environment variables received from parent process", "count", len(envVars))

	if logger.IsTrace() {
		for _, env := range envVars {
			parts := strings.SplitN(env, "=", 2)
			if len(parts) == 2 {
				logger.Trace("📝 Environment variable", "key", parts[0], "value", parts[1])
			}
		}
	}

	userCwd, err := os.Getwd()
	if err != nil {
		logger.Error("❌ Failed to get current directory", "error", err)
		os.Exit(ExitIOError)
	}
	logger.Debug("📁 User working directory", "path", userCwd)

	if isEnvTrue("FLAVOR_LAUNCHER_CLI") {
		logger.Debug("💻 Running in CLI mode")
		if len(args) < 1 {
			// Default to info command when no args provided
			showBundleInfo(exePath, logger)
			return
		}

		switch args[0] {
		case "info":
			showBundleInfo(exePath, logger)
		case "verify":
			verifyBundle(exePath, logger)
		case "metadata":
			showMetadata(exePath, logger)
		case "extract":
			if len(args) < 3 {
				fmt.Fprintf(os.Stderr, "Error: extract requires slot index and output directory\n")
				fmt.Fprintf(os.Stderr, "Usage: extract <slot_index> <output_dir>\n")
				os.Exit(ExitInvalidArgs)
			}
			extractSlot(exePath, args[1], args[2], logger)
		case "run":
			// Run with remaining arguments
			if err := execBundle(exePath, args[1:], userCwd, logger); err != nil {
				fmt.Fprintf(os.Stderr, "Error: %v\n", err)
				os.Exit(ExitExecutionError)
			}
			// If we reach here, exec failed
			os.Exit(ExitExecutionError)
		case "help", "--help":
			fmt.Println("PSPF Package Launcher - CLI Mode")
			fmt.Println()
			fmt.Println("Available commands:")
			fmt.Println("  info              Show package information (default)")
			fmt.Println("  verify            Verify package integrity")
			fmt.Println("  metadata          Show raw package metadata")
			fmt.Println("  extract INDEX DIR Extract slot to directory")
			fmt.Println("  run [args...]     Execute package with arguments")
			fmt.Println("  help              Show this help message")
			fmt.Println()
			fmt.Println("Usage:")
			fmt.Println("  FLAVOR_LAUNCHER_CLI=1 ./package.psp <command>")
			fmt.Println()
			fmt.Println("Examples:")
			fmt.Println("  FLAVOR_LAUNCHER_CLI=1 ./package.psp info")
			fmt.Println("  FLAVOR_LAUNCHER_CLI=1 ./package.psp verify")
			fmt.Println("  FLAVOR_LAUNCHER_CLI=1 ./package.psp extract 0 /tmp/output")
		default:
			fmt.Fprintf(os.Stderr, "Error: Unknown command '%s'\n", args[0])
			fmt.Fprintf(os.Stderr, "Available commands: info, verify, metadata, extract, run, help\n")
			os.Exit(ExitInvalidArgs)
		}
		return
	}

	if err := execBundle(exePath, args, userCwd, logger); err != nil {
		logger.Error("❌ Failed to exec command", "error", err)
		// Determine error type based on error message
		errStr := err.Error()
		if strings.Contains(errStr, "PSPF") || strings.Contains(errStr, "magic") {
			os.Exit(ExitPSPFError)
		} else if strings.Contains(errStr, "extract") || strings.Contains(errStr, "slot") {
			os.Exit(ExitExtractionError)
		} else if strings.Contains(errStr, "file") || strings.Contains(errStr, "I/O") {
			os.Exit(ExitIOError)
		}
		os.Exit(ExitExecutionError)
	}
	// If we reach here, exec failed (shouldn't happen on Unix)
	os.Exit(ExitExecutionError)
}

// Launch is the backward-compatible entry point
func Launch(exePath string, args []string) {
	LaunchWithLogLevel(exePath, args, "", "")
}

// execBundle prepares and executes a bundle
func execBundle(exePath string, args []string, userCwd string, logger hclog.Logger) error {
	// Check execution mode
	execMode := os.Getenv("FLAVOR_EXEC_MODE")
	useSpawn := strings.ToLower(execMode) == "spawn"

	// Force spawn mode on Windows (exec mode not supported)
	if runtime.GOOS == "windows" && !useSpawn {
		logger.Info("💻 Windows detected - using spawn mode (exec mode not supported on Windows)")
		useSpawn = true
	}

	if useSpawn {
		logger.Debug("👶 Using spawn mode (child process)")
		return spawnBundle(exePath, args, userCwd, logger)
	}

	logger.Debug("🔄 Using exec mode (process replacement)")
	return execBundleReplace(exePath, args, userCwd, logger)
}

// execBundleReplace prepares and executes a bundle using syscall.Exec (process replacement)
func execBundleReplace(exePath string, args []string, userCwd string, logger hclog.Logger) error {
	// Prepare the command (do all extraction and setup)
	logger.Debug("Preparing command for exec mode", "exe", exePath, "args", args, "cwd", userCwd)
	var cmd *exec.Cmd
	cmd, err := runBundleWithCwd(exePath, args, userCwd, logger)
	if err != nil {
		logger.Error("Failed to prepare command for exec", "error", err)
		return err
	}

	// Convert exec.Cmd to syscall.Exec arguments
	binary := cmd.Path
	logger.Trace("Binary path extracted from command", "path", binary)

	argv := cmd.Args
	if argv == nil || len(argv) == 0 {
		logger.Debug("Command args are nil/empty, using binary as sole argument")
		argv = []string{binary}
	}
	logger.Trace("Command arguments prepared", "argv", argv)

	// Convert environment to []string format
	envv := cmd.Env
	if envv == nil {
		logger.Debug("Command environment is nil, using os.Environ()")
		envv = os.Environ()
	}
	logger.Trace("Environment prepared", "env_count", len(envv))

	logger.Debug("🔄 Replacing process via exec", "binary", binary, "args", argv[1:])
	logger.Trace("About to call syscall.Exec - process will be replaced")

	// This replaces the current process and never returns on success
	err = syscall.Exec(binary, argv, envv)

	// If we reach here, syscall.Exec failed
	logger.Error("🚨 syscall.Exec failed", "error", err, "binary", binary, "argv", argv)
	if err != nil {
		return fmt.Errorf("syscall.Exec failed: %w", err)
	}

	// This should never be reached (even on error, we return above)
	logger.Error("🚨 CRITICAL: syscall.Exec returned with nil error - this should be impossible")
	return errors.New("syscall.Exec returned unexpectedly with no error")
}

// Note: Signal handling and cleanup are not compatible with syscall.Exec.
// When using exec, the process is replaced entirely - the new process handles its own signals.
