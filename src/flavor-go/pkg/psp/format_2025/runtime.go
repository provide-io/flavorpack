package format_2025

import (
	"fmt"
	"path/filepath"
	"strings"

	"log/slog"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func processRuntimeEnv(env []string, runtimeEnv map[string]interface{}, logger *slog.Logger) []string {
	envMap := make(map[string]string)
	for _, e := range env {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) == 2 {
			envMap[parts[0]] = parts[1]
		}
	}

	// On Windows, automatically add critical system variables to pass list
	// These are required for Python and other programs to initialize properly
	if currentGOOS == "windows" {
		windowsCriticalVars := []string{"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATHEXT", "COMSPEC"}

		if passList, ok := runtimeEnv["pass"].([]interface{}); ok {
			// Create a set of existing pass patterns for deduplication
			existingPatterns := make(map[string]bool)
			for _, pattern := range passList {
				if patternStr, ok := pattern.(string); ok {
					existingPatterns[patternStr] = true
				}
			}

			// Add missing critical vars
			for _, criticalVar := range windowsCriticalVars {
				if !existingPatterns[criticalVar] {
					logger.Debug("💻 Auto-adding Windows critical variable", "var", criticalVar)
					passList = append(passList, criticalVar)
				}
			}
			runtimeEnv["pass"] = passList
		} else {
			// No pass list exists, create one with critical vars
			logger.Debug("💻 Creating pass list with Windows critical variables")
			passListInterface := make([]interface{}, len(windowsCriticalVars))
			for i, v := range windowsCriticalVars {
				passListInterface[i] = v
			}
			runtimeEnv["pass"] = passListInterface
		}
	}

	// Build list of variables to preserve from pass patterns first
	preserveVars := make(map[string]bool)
	if passList, ok := runtimeEnv["pass"].([]interface{}); ok {
		logger.Debug("🔍 Building preserve list from pass patterns", "count", len(passList))
		for _, pattern := range passList {
			if patternStr, ok := pattern.(string); ok {
				if strings.Contains(patternStr, "*") || strings.Contains(patternStr, "?") {
					// Glob pattern - find matching vars
					for key := range envMap {
						if matched, _ := filepath.Match(patternStr, key); matched {
							preserveVars[key] = true
							logging.Trace(logger, "  ✅ Preserving env var (pattern match)", "key", key, "pattern", patternStr)
						}
					}
				} else {
					// Exact variable name
					if _, exists := envMap[patternStr]; exists {
						preserveVars[patternStr] = true
						logging.Trace(logger, "  ✅ Preserving env var (exact)", "key", patternStr)
					}
				}
			}
		}
	}

	if unsetList, ok := runtimeEnv["unset"].([]interface{}); ok {
		logger.Debug("🗑️ Processing unset operations", "count", len(unsetList))
		for _, pattern := range unsetList {
			if patternStr, ok := pattern.(string); ok {
				if patternStr == "*" {
					// Special case: unset all except those in preserve list
					logger.Debug("🗑️ Whitelist mode: removing all variables except preserved")
					toDelete := []string{}
					for key := range envMap {
						if !preserveVars[key] {
							toDelete = append(toDelete, key)
						}
					}
					for _, key := range toDelete {
						delete(envMap, key)
						logging.Trace(logger, "  🗑️ Removed env var", "key", key)
					}
					logger.Debug("  Removed variables", "count", len(toDelete), "preserved", len(preserveVars))
				} else if strings.Contains(patternStr, "*") || strings.Contains(patternStr, "?") {
					// Glob pattern
					toDelete := []string{}
					for key := range envMap {
						if matched, _ := filepath.Match(patternStr, key); matched && !preserveVars[key] {
							toDelete = append(toDelete, key)
						}
					}
					for _, key := range toDelete {
						delete(envMap, key)
						logging.Trace(logger, "🗑️ Unset env var (pattern)", "key", key, "pattern", patternStr)
					}
				} else {
					// Exact variable name
					if _, exists := envMap[patternStr]; exists && !preserveVars[patternStr] {
						delete(envMap, patternStr)
						logging.Trace(logger, "🗑️ Unset env var", "key", patternStr)
					}
				}
			}
		}
	}

	if mapOps, ok := runtimeEnv["map"].(map[string]interface{}); ok {
		logger.Debug("🔄 Processing map operations", "count", len(mapOps))
		for from, to := range mapOps {
			if toStr, ok := to.(string); ok {
				if value, exists := envMap[from]; exists {
					envMap[toStr] = value
					if from != toStr {
						delete(envMap, from)
						logging.Trace(logger, "🔄 Mapped env var", "from", from, "to", toStr, "value", value)
					}
				}
			}
		}
	}

	if setOps, ok := runtimeEnv["set"].(map[string]interface{}); ok {
		logger.Debug("✏️ Processing set operations", "count", len(setOps))
		for key, value := range setOps {
			if valueStr, ok := value.(string); ok {
				envMap[key] = valueStr
				logging.Trace(logger, "✏️ Set env var", "key", key, "value", valueStr)
			}
		}
	}

	// Verify pass patterns after all operations
	if passList, ok := runtimeEnv["pass"].([]interface{}); ok {
		logger.Debug("✅ Verifying pass patterns", "count", len(passList))
		for _, pattern := range passList {
			if patternStr, ok := pattern.(string); ok {
				if strings.Contains(patternStr, "*") || strings.Contains(patternStr, "?") {
					// Glob pattern - check if any vars match
					found := false
					for key := range envMap {
						if matched, _ := filepath.Match(patternStr, key); matched {
							found = true
							break
						}
					}
					if !found {
						logger.Warn("⚠️ No environment variables match required pattern", "pattern", patternStr)
					} else {
						logging.Trace(logger, "✅ Verified env vars match pattern", "pattern", patternStr)
					}
				} else {
					// Exact variable name
					if _, exists := envMap[patternStr]; !exists {
						logger.Warn("⚠️ Required environment variable not found", "key", patternStr)
					} else {
						logging.Trace(logger, "✅ Verified env var exists", "key", patternStr)
					}
				}
			}
		}
	}

	result := make([]string, 0, len(envMap))
	for k, v := range envMap {
		result = append(result, fmt.Sprintf("%s=%s", k, v))
	}

	return result
}
