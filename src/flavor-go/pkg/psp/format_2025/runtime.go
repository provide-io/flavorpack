package format_2025

import (
	"log/slog"
)

// processRuntimeEnv applies the package's declared environment operations to
// the host environment, in the order the format defines: pass decides what is
// protected, unset removes, map renames, set assigns.
func processRuntimeEnv(env []string, runtimeEnv map[string]interface{}, logger *slog.Logger) []string {
	envMap := envToMap(env)

	if currentGOOS == "windows" {
		addWindowsCriticalVars(runtimeEnv, logger)
	}

	// Built before any removal, so "unset everything except what passes" works.
	preserveVars := buildPreserveList(runtimeEnv, envMap, logger)

	applyUnsetOps(runtimeEnv, envMap, preserveVars, logger)
	applyMapOps(runtimeEnv, envMap, logger)
	applySetOps(runtimeEnv, envMap, logger)

	verifyPassPatterns(runtimeEnv, envMap, logger)

	return mapToEnv(envMap)
}
