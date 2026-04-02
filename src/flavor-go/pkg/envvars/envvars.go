// Package envvars defines FLAVOR_* environment variable name constants
// for use by packages that cannot import pkg/psp/format_2025 (e.g. pkg/logging, internal/workenv).
// All FLAVOR_* env vars must be referenced via these constants, never as inline strings.
package envvars

const (
	// Logging
	EnvLogLevel         = "FLAVOR_LOG_LEVEL"
	EnvLauncherLogLevel = "FLAVOR_LAUNCHER_LOG_LEVEL"
	EnvBuilderLogLevel  = "FLAVOR_BUILDER_LOG_LEVEL"
	EnvLogPath          = "FLAVOR_LOG_PATH"
	EnvJSONLog          = "FLAVOR_JSON_LOG"

	// Paths
	EnvCacheDir       = "FLAVOR_CACHE_DIR"
	EnvConfigDir      = "FLAVOR_CONFIG_DIR"
	EnvTrustedKeysDir = "FLAVOR_TRUSTED_KEYS_DIR"

	// Workenv
	EnvWorkenv      = "FLAVOR_WORKENV"
	EnvWorkenvCache = "FLAVOR_WORKENV_CACHE"
	EnvWorkenvBase  = "FLAVOR_WORKENV_BASE"

	// Execution
	EnvExecMode    = "FLAVOR_EXEC_MODE"
	EnvLauncherBin = "FLAVOR_LAUNCHER_BIN"
	EnvKeySeed     = "FLAVOR_KEY_SEED"
	EnvValidation  = "FLAVOR_VALIDATION"

	// Launcher IPC / CLI mode
	EnvLauncherCLI             = "FLAVOR_LAUNCHER_CLI"
	EnvLauncherArgs            = "FLAVOR_LAUNCHER_ARGS"
	EnvLauncherBundle          = "FLAVOR_LAUNCHER_BUNDLE"
	EnvLauncherMode            = "FLAVOR_LAUNCHER_MODE"
	EnvLauncherHelper          = "FLAVOR_LAUNCHER_HELPER"
	EnvLauncherSubprocess      = "FLAVOR_LAUNCHER_SUBPROCESS"
	EnvLauncherSpawnExitHelper = "FLAVOR_LAUNCHER_SPAWN_EXIT_HELPER"

	// Runtime env vars injected into the child process
	EnvCache           = "FLAVOR_CACHE"
	EnvOriginalCommand = "FLAVOR_ORIGINAL_COMMAND"
	EnvCommandName     = "FLAVOR_COMMAND_NAME"
)
