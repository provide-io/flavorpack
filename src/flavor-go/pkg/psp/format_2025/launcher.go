package format_2025

import (
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// LauncherVersion is the launcher binary's own version, set by the binary at
// startup from its -ldflags-injected value. CLI mode's "version" command
// reports it so the builder can record which launcher it embedded.
var LauncherVersion = "unknown"

var syscallExecFn = syscall.Exec
var osExitFn = os.Exit
var osGetWdFn = os.Getwd
var launcherStderrWriter io.Writer = os.Stderr

// LaunchWithLogLevel launches with explicit log level control
func LaunchWithLogLevel(exePath string, args []string, cliLogLevel, cliLogSource string) {
	logger, actualLevel, logSource, closeLog := setupLauncherLogging(cliLogLevel, cliLogSource)
	defer closeLog()

	// Startup chatter belongs to CLI mode; otherwise stdout is the package's.
	if isEnvTrue(EnvLauncherCLI) {
		logger.Info("🐹🐹🐹 Hello from Flavor's Go Launcher 🐹🐹🐹")
		logger.Debug("Log level", "level", actualLevel, "source", logSource)
		logger.Info("PSPF Go Launcher starting...")
	}
	logger.Debug("📖 Reading PSPF bundle")

	traceEnvironment(logger)

	userCwd, err := osGetWdFn()
	if err != nil {
		logger.Error("❌ Failed to get current directory", "error", err)
		osExitFn(ExitIOError)
	}
	logger.Debug("📁 User working directory", "path", userCwd)

	if isEnvTrue(EnvLauncherCLI) {
		logger.Debug("💻 Running in CLI mode")
		if len(args) < 1 {
			// Default to info command when no args provided
			showBundleInfo(os.Stdout, exePath, logger)
			return
		}

		switch args[0] {
		// Reports the launcher's own version. Deliberately does not touch the
		// bundle, so the builder can probe a standalone launcher binary.
		case "version":
			fmt.Println(LauncherVersion)
		case "info":
			showBundleInfo(os.Stdout, exePath, logger)
		case "verify":
			verifyBundle(os.Stdout, exePath, logger)
		case "metadata":
			showMetadata(os.Stdout, exePath, logger)
		case "extract":
			if len(args) < 3 {
				fmt.Fprintf(os.Stderr, "Error: extract requires slot index and output directory\n")
				fmt.Fprintf(os.Stderr, "Usage: extract <slot_index> <output_dir>\n")
				osExitFn(ExitInvalidArgs)
			}
			extractSlot(os.Stdout, exePath, args[1], args[2], logger)
		case "run":
			// execBundle only returns when it has failed: a successful run either
			// replaces this process or exits with the child's status. Guarding the
			// result against nil would read as though returning is the normal case.
			err := execBundle(exePath, args[1:], userCwd, logger)
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			osExitFn(ExitExecutionError)
		case "help", "--help":
			fmt.Println("PSPF Package Launcher - CLI Mode")
			fmt.Println()
			fmt.Println("Available commands:")
			fmt.Println("  version           Show launcher version")
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
			fmt.Fprintf(os.Stderr, "Available commands: version, info, verify, metadata, extract, run, help\n")
			osExitFn(ExitInvalidArgs)
		}
		return
	}

	// Reaching the next line at all means the bundle did not run: on success
	// execBundle replaces this process or exits with the child's status.
	err = execBundle(exePath, args, userCwd, logger)
	logger.Error("❌ Failed to exec command", "error", err)

	// Determine error type based on error message
	errStr := err.Error()
	if strings.Contains(errStr, "PSPF") || strings.Contains(errStr, "magic") {
		osExitFn(ExitPSPFError)
	} else if strings.Contains(errStr, "extract") || strings.Contains(errStr, "slot") {
		osExitFn(ExitExtractionError)
	} else if strings.Contains(errStr, "file") || strings.Contains(errStr, "I/O") {
		osExitFn(ExitIOError)
	}
	osExitFn(ExitExecutionError)
}

// Launch is the backward-compatible entry point
func Launch(exePath string, args []string) {
	LaunchWithLogLevel(exePath, args, "", "")
}

// execBundle prepares and executes a bundle
func execBundle(exePath string, args []string, userCwd string, logger *slog.Logger) error {
	// Check execution mode
	execMode := os.Getenv(EnvExecMode)
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
func execBundleReplace(exePath string, args []string, userCwd string, logger *slog.Logger) error {
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
	logging.Trace(logger, "Binary path extracted from command", "path", binary)

	// exec.Command resolves PATH from the current process environment at call time,
	// before cmd.Env is populated with workenv/bin. If the binary lives in workenv/bin
	// (e.g. a console_script entry point like "taster"), cmd.Path will be the
	// unresolved name. syscall.Exec needs an absolute path, so re-resolve here
	// using the PATH from the command's own environment.
	if !filepath.IsAbs(binary) {
		if resolved, err := lookPathInEnv(binary, cmd.Env); err == nil {
			logger.Debug("✅ Re-resolved binary using cmd environment PATH",
				"input", binary, "resolved", resolved)
			binary = resolved
		} else {
			logger.Warn("⚠️ Could not re-resolve binary in cmd environment PATH",
				"binary", binary, "error", err)
		}
	}

	argv := cmd.Args
	if len(argv) == 0 {
		logger.Debug("Command args are nil/empty, using binary as sole argument")
		argv = []string{binary}
	}
	logging.Trace(logger, "Command arguments prepared", "argv", argv)

	// Convert environment to []string format
	envv := cmd.Env
	if envv == nil {
		logger.Debug("Command environment is nil, using os.Environ()")
		envv = os.Environ()
	}
	logging.Trace(logger, "Environment prepared", "env_count", len(envv))

	logger.Debug("🔄 Replacing process via exec", "binary", binary, "args", argv[1:])
	logging.Trace(logger, "About to call syscall.Exec - process will be replaced")

	// This replaces the current process and never returns on success
	err = syscallExecFn(binary, argv, envv)

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
