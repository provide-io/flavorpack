// SPDX-License-Identifier: Apache-2.0
// Package format_2025 implements PSPF/2025 package format support
package format_2025

import (
	"fmt"
	"strings"

	"github.com/hashicorp/go-hclog"
)

const (
	defaultCacheSubdir = ".cache/flavor/workenv"
)

// setFlavorCacheBeforeWorkenv sets FLAVOR_CACHE to the HOST's cache directory.
// Must be called BEFORE workenv environment variables (which override HOME).
// This ensures packaged tools can access cached packages from the HOST.
func setFlavorCacheBeforeWorkenv(env []string, logger hclog.Logger) []string {
	// Check if FLAVOR_CACHE is already set
	if hasEnv(env, "FLAVOR_CACHE") {
		logger.Debug("🗂️ FLAVOR_CACHE already set, skipping")
		return env
	}

	// Get HOME from parent environment BEFORE it gets overwritten by workenv
	homeValue := getenv(env, "HOME", "")
	if homeValue == "" {
		logger.Warn("⚠️ HOME not found in environment, skipping FLAVOR_CACHE setup")
		return env
	}

	flavorCache := fmt.Sprintf("%s/%s", homeValue, defaultCacheSubdir)
	env = append(env, fmt.Sprintf("FLAVOR_CACHE=%s", flavorCache))
	logger.Debug("🗂️ Setting FLAVOR_CACHE to HOST cache", "path", flavorCache)
	return env
}

// getenv retrieves an environment variable value from the environment list.
func getenv(env []string, key string, defaultVal string) string {
	prefix := key + "="
	for _, e := range env {
		if strings.HasPrefix(e, prefix) {
			return strings.TrimPrefix(e, prefix)
		}
	}
	return defaultVal
}

// hasEnv checks if an environment variable is set in the environment list.
func hasEnv(env []string, key string) bool {
	prefix := key + "="
	for _, e := range env {
		if strings.HasPrefix(e, prefix) {
			return true
		}
	}
	return false
}

// logEnvironmentTrace logs environment variables at trace level, redacting sensitive values.
func logEnvironmentTrace(env []string, logger hclog.Logger) {
	if !logger.IsTrace() {
		return
	}

	logger.Trace("🌍 Environment variables being passed to subprocess:")
	for _, e := range env {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) == 2 {
			value := parts[1]
			if isSensitiveKey(parts[0]) {
				value = "***"
			}
			logger.Trace("  →", "key", parts[0], "value", value)
		}
	}
}

// isSensitiveKey checks if an environment variable key is sensitive and should be redacted in logs.
func isSensitiveKey(key string) bool {
	sensitiveKeys := map[string]bool{
		"SSH_AUTH_SOCK":         true,
		"AWS_SECRET_ACCESS_KEY": true,
		"GITHUB_TOKEN":          true,
		"HF_TOKEN":              true,
		"OPENAI_API_KEY":        true,
		"PASSWORD":              true,
	}
	return sensitiveKeys[key]
}

// 🌶️📦🖥️🪄
