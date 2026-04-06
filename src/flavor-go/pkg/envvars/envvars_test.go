package envvars

import "testing"

// TestEnvVarConstantsAreNonEmpty verifies that all exported FLAVOR_*
// environment variable constants are non-empty strings.
func TestEnvVarConstantsAreNonEmpty(t *testing.T) {
	t.Parallel()

	constants := map[string]string{
		"EnvLogLevel":                EnvLogLevel,
		"EnvLauncherLogLevel":        EnvLauncherLogLevel,
		"EnvBuilderLogLevel":         EnvBuilderLogLevel,
		"EnvLogPath":                 EnvLogPath,
		"EnvJSONLog":                 EnvJSONLog,
		"EnvCacheDir":                EnvCacheDir,
		"EnvConfigDir":               EnvConfigDir,
		"EnvTrustedKeysDir":          EnvTrustedKeysDir,
		"EnvWorkenv":                 EnvWorkenv,
		"EnvWorkenvCache":            EnvWorkenvCache,
		"EnvWorkenvBase":             EnvWorkenvBase,
		"EnvExecMode":                EnvExecMode,
		"EnvLauncherBin":             EnvLauncherBin,
		"EnvKeySeed":                 EnvKeySeed,
		"EnvValidation":              EnvValidation,
		"EnvLauncherCLI":             EnvLauncherCLI,
		"EnvLauncherArgs":            EnvLauncherArgs,
		"EnvLauncherBundle":          EnvLauncherBundle,
		"EnvLauncherMode":            EnvLauncherMode,
		"EnvLauncherHelper":          EnvLauncherHelper,
		"EnvLauncherSubprocess":      EnvLauncherSubprocess,
		"EnvLauncherSpawnExitHelper": EnvLauncherSpawnExitHelper,
		"EnvCache":                   EnvCache,
		"EnvOriginalCommand":         EnvOriginalCommand,
		"EnvCommandName":             EnvCommandName,
	}

	for name, value := range constants {
		if value == "" {
			t.Errorf("constant %s is empty", name)
		}
	}
}

// TestEnvVarConstantsHaveFLAVORPrefix verifies all constants start with "FLAVOR_".
func TestEnvVarConstantsHaveFLAVORPrefix(t *testing.T) {
	t.Parallel()

	constants := map[string]string{
		"EnvLogLevel":                EnvLogLevel,
		"EnvLauncherLogLevel":        EnvLauncherLogLevel,
		"EnvBuilderLogLevel":         EnvBuilderLogLevel,
		"EnvLogPath":                 EnvLogPath,
		"EnvJSONLog":                 EnvJSONLog,
		"EnvCacheDir":                EnvCacheDir,
		"EnvConfigDir":               EnvConfigDir,
		"EnvTrustedKeysDir":          EnvTrustedKeysDir,
		"EnvWorkenv":                 EnvWorkenv,
		"EnvWorkenvCache":            EnvWorkenvCache,
		"EnvWorkenvBase":             EnvWorkenvBase,
		"EnvExecMode":                EnvExecMode,
		"EnvLauncherBin":             EnvLauncherBin,
		"EnvKeySeed":                 EnvKeySeed,
		"EnvValidation":              EnvValidation,
		"EnvLauncherCLI":             EnvLauncherCLI,
		"EnvLauncherArgs":            EnvLauncherArgs,
		"EnvLauncherBundle":          EnvLauncherBundle,
		"EnvLauncherMode":            EnvLauncherMode,
		"EnvLauncherHelper":          EnvLauncherHelper,
		"EnvLauncherSubprocess":      EnvLauncherSubprocess,
		"EnvLauncherSpawnExitHelper": EnvLauncherSpawnExitHelper,
		"EnvCache":                   EnvCache,
		"EnvOriginalCommand":         EnvOriginalCommand,
		"EnvCommandName":             EnvCommandName,
	}

	for name, value := range constants {
		if len(value) < 7 || value[:7] != "FLAVOR_" {
			t.Errorf("constant %s = %q does not start with FLAVOR_", name, value)
		}
	}
}

// TestEnvVarConstantsAreUnique verifies that no two constants share the same value.
func TestEnvVarConstantsAreUnique(t *testing.T) {
	t.Parallel()

	values := []string{
		EnvLogLevel,
		EnvLauncherLogLevel,
		EnvBuilderLogLevel,
		EnvLogPath,
		EnvJSONLog,
		EnvCacheDir,
		EnvConfigDir,
		EnvTrustedKeysDir,
		EnvWorkenv,
		EnvWorkenvCache,
		EnvWorkenvBase,
		EnvExecMode,
		EnvLauncherBin,
		EnvKeySeed,
		EnvValidation,
		EnvLauncherCLI,
		EnvLauncherArgs,
		EnvLauncherBundle,
		EnvLauncherMode,
		EnvLauncherHelper,
		EnvLauncherSubprocess,
		EnvLauncherSpawnExitHelper,
		EnvCache,
		EnvOriginalCommand,
		EnvCommandName,
	}

	seen := make(map[string]bool)
	for _, v := range values {
		if seen[v] {
			t.Errorf("duplicate env var value: %q", v)
		}
		seen[v] = true
	}
}
