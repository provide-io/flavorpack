package format_2025

// Environment variable names used by the Flavor launcher and builder.
// All FLAVOR_* env vars should be referenced via these constants, never as inline strings.
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
)
