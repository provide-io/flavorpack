// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"fmt"
	"log/slog"
	"path/filepath"
	"strings"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// windowsCriticalVars are needed for Python and other runtimes to start on
// Windows, so they are passed whether or not the package asked for them.
var windowsCriticalVars = []string{"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATHEXT", "COMSPEC"}

// isGlobPattern reports whether a name is a pattern rather than a literal.
func isGlobPattern(s string) bool {
	return strings.Contains(s, "*") || strings.Contains(s, "?")
}

// envToMap splits KEY=VALUE entries. An entry with no "=" is dropped, since
// there is no name to key it by.
func envToMap(env []string) map[string]string {
	envMap := make(map[string]string, len(env))
	for _, e := range env {
		if parts := strings.SplitN(e, "=", 2); len(parts) == 2 {
			envMap[parts[0]] = parts[1]
		}
	}
	return envMap
}

// mapToEnv renders the map back into KEY=VALUE entries.
func mapToEnv(envMap map[string]string) []string {
	result := make([]string, 0, len(envMap))
	for k, v := range envMap {
		result = append(result, fmt.Sprintf("%s=%s", k, v))
	}
	return result
}

// stringList reads one of the runtime env operations as a list of strings,
// dropping entries that are not strings.
func stringList(runtimeEnv map[string]any, key string) ([]string, bool) {
	raw, ok := runtimeEnv[key].([]any)
	if !ok {
		return nil, false
	}
	out := make([]string, 0, len(raw))
	for _, item := range raw {
		if s, ok := item.(string); ok {
			out = append(out, s)
		}
	}
	return out, true
}

// addWindowsCriticalVars adds the variables Windows runtimes need to the pass
// list, creating the list when the package declared none.
func addWindowsCriticalVars(runtimeEnv map[string]any, logger *slog.Logger) {
	passList, ok := runtimeEnv["pass"].([]any)
	if !ok {
		logger.Debug("💻 Creating pass list with Windows critical variables")
		created := make([]any, len(windowsCriticalVars))
		for i, v := range windowsCriticalVars {
			created[i] = v
		}
		runtimeEnv["pass"] = created
		return
	}

	existing := make(map[string]bool, len(passList))
	for _, pattern := range passList {
		if s, ok := pattern.(string); ok {
			existing[s] = true
		}
	}

	for _, criticalVar := range windowsCriticalVars {
		if !existing[criticalVar] {
			logger.Debug("💻 Auto-adding Windows critical variable", "var", criticalVar)
			passList = append(passList, criticalVar)
		}
	}
	runtimeEnv["pass"] = passList
}

// buildPreserveList names the variables the pass patterns protect. It runs
// before any unset operation, so "unset everything except what passes" works.
func buildPreserveList(runtimeEnv map[string]any, envMap map[string]string, logger *slog.Logger) map[string]bool {
	preserveVars := make(map[string]bool)

	patterns, ok := stringList(runtimeEnv, "pass")
	if !ok {
		return preserveVars
	}
	logger.Debug("🔍 Building preserve list from pass patterns", "count", len(patterns))

	for _, pattern := range patterns {
		if !isGlobPattern(pattern) {
			if _, exists := envMap[pattern]; exists {
				preserveVars[pattern] = true
				logging.Trace(logger, "  ✅ Preserving env var (exact)", "key", pattern)
			}
			continue
		}
		for key := range envMap {
			if matched, _ := filepath.Match(pattern, key); matched {
				preserveVars[key] = true
				logging.Trace(logger, "  ✅ Preserving env var (pattern match)", "key", key, "pattern", pattern)
			}
		}
	}

	return preserveVars
}

// applyUnsetOps removes variables, never one the pass patterns preserved. The
// pattern "*" means "remove everything not preserved", which is how a package
// asks for a whitelist rather than a blacklist.
func applyUnsetOps(
	runtimeEnv map[string]any,
	envMap map[string]string,
	preserveVars map[string]bool,
	logger *slog.Logger,
) {
	patterns, ok := stringList(runtimeEnv, "unset")
	if !ok {
		return
	}
	logger.Debug("🗑️ Processing unset operations", "count", len(patterns))

	for _, pattern := range patterns {
		switch {
		case pattern == "*":
			logger.Debug("🗑️ Whitelist mode: removing all variables except preserved")
			removed := 0
			for key := range envMap {
				if !preserveVars[key] {
					delete(envMap, key)
					logging.Trace(logger, "  🗑️ Removed env var", "key", key)
					removed++
				}
			}
			logger.Debug("  Removed variables", "count", removed, "preserved", len(preserveVars))

		case isGlobPattern(pattern):
			for key := range envMap {
				if matched, _ := filepath.Match(pattern, key); matched && !preserveVars[key] {
					delete(envMap, key)
					logging.Trace(logger, "🗑️ Unset env var (pattern)", "key", key, "pattern", pattern)
				}
			}

		default:
			if _, exists := envMap[pattern]; exists && !preserveVars[pattern] {
				delete(envMap, pattern)
				logging.Trace(logger, "🗑️ Unset env var", "key", pattern)
			}
		}
	}
}

// applyMapOps renames variables, carrying the value across.
func applyMapOps(runtimeEnv map[string]any, envMap map[string]string, logger *slog.Logger) {
	mapOps, ok := runtimeEnv["map"].(map[string]any)
	if !ok {
		return
	}
	logger.Debug("🔄 Processing map operations", "count", len(mapOps))

	for from, to := range mapOps {
		toStr, ok := to.(string)
		if !ok {
			continue
		}
		value, exists := envMap[from]
		if !exists {
			continue
		}
		envMap[toStr] = value
		if from != toStr {
			delete(envMap, from)
			logging.Trace(logger, "🔄 Mapped env var", "from", from, "to", toStr, "value", value)
		}
	}
}

// applySetOps assigns literal values, last so it wins over the rest.
func applySetOps(runtimeEnv map[string]any, envMap map[string]string, logger *slog.Logger) {
	setOps, ok := runtimeEnv["set"].(map[string]any)
	if !ok {
		return
	}
	logger.Debug("✏️ Processing set operations", "count", len(setOps))

	for key, value := range setOps {
		if valueStr, ok := value.(string); ok {
			envMap[key] = valueStr
			logging.Trace(logger, "✏️ Set env var", "key", key, "value", valueStr)
		}
	}
}

// verifyPassPatterns warns about anything the package asked to pass that is
// not in the final environment. It only reports: a package that names a
// variable the host does not set still runs.
func verifyPassPatterns(runtimeEnv map[string]any, envMap map[string]string, logger *slog.Logger) {
	patterns, ok := stringList(runtimeEnv, "pass")
	if !ok {
		return
	}
	logger.Debug("✅ Verifying pass patterns", "count", len(patterns))

	for _, pattern := range patterns {
		if !isGlobPattern(pattern) {
			if _, exists := envMap[pattern]; !exists {
				logger.Warn("⚠️ Required environment variable not found", "key", pattern)
			} else {
				logging.Trace(logger, "✅ Verified env var exists", "key", pattern)
			}
			continue
		}

		found := false
		for key := range envMap {
			if matched, _ := filepath.Match(pattern, key); matched {
				found = true
				break
			}
		}
		if !found {
			logger.Warn("⚠️ No environment variables match required pattern", "pattern", pattern)
		} else {
			logging.Trace(logger, "✅ Verified env vars match pattern", "pattern", pattern)
		}
	}
}
