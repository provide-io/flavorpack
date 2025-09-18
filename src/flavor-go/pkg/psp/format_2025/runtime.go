package format_2025

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/hashicorp/go-hclog"
)

func processRuntimeEnv(env []string, runtimeEnv map[string]interface{}, logger hclog.Logger) []string {
	envMap := make(map[string]string)
	for _, e := range env {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) == 2 {
			envMap[parts[0]] = parts[1]
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
							logger.Trace("  ✅ Preserving env var (pattern match)", "key", key, "pattern", patternStr)
						}
					}
				} else {
					// Exact variable name
					if _, exists := envMap[patternStr]; exists {
						preserveVars[patternStr] = true
						logger.Trace("  ✅ Preserving env var (exact)", "key", patternStr)
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
						logger.Trace("  🗑️ Removed env var", "key", key)
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
						logger.Trace("🗑️ Unset env var (pattern)", "key", key, "pattern", patternStr)
					}
				} else {
					// Exact variable name
					if _, exists := envMap[patternStr]; exists && !preserveVars[patternStr] {
						delete(envMap, patternStr)
						logger.Trace("🗑️ Unset env var", "key", patternStr)
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
						logger.Trace("🔄 Mapped env var", "from", from, "to", toStr, "value", value)
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
				logger.Trace("✏️ Set env var", "key", key, "value", valueStr)
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
						logger.Trace("✅ Verified env vars match pattern", "pattern", patternStr)
					}
				} else {
					// Exact variable name
					if _, exists := envMap[patternStr]; !exists {
						logger.Warn("⚠️ Required environment variable not found", "key", patternStr)
					} else {
						logger.Trace("✅ Verified env var exists", "key", patternStr)
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
