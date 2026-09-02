// SPDX-License-Identifier: Apache-2.0
// Package format_2025 implements PSPF/2025 package format support
package format_2025

import (
	"fmt"
	"path/filepath"
	"strings"

	"log/slog"

	"github.com/provide-io/flavor/go/flavor/internal/workenv"
	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// setFlavorCacheBeforeWorkenv sets FLAVOR_CACHE to the HOST's cache directory.
// Must be called BEFORE workenv environment variables (which override HOME).
// This ensures packaged tools can access cached packages from the HOST.
func setFlavorCacheBeforeWorkenv(env []string, logger *slog.Logger) []string {
	// Check if FLAVOR_CACHE is already set
	if hasEnv(env, EnvCache) {
		logger.Debug("🗂️ FLAVOR_CACHE already set, skipping")
		return env
	}

	// Use workenv.GetCacheRoot() for cross-platform cache directory consistency
	flavorCache := filepath.Join(workenv.GetCacheRoot(), "workenv")
	env = setEnv(env, EnvCache, flavorCache)
	logger.Debug("🗂️ Setting FLAVOR_CACHE to HOST cache", "path", flavorCache)
	return env
}

// setEnv sets key to value, replacing an existing entry rather than adding a
// second one.
//
// The environment handed to a package starts as os.Environ(), so appending a
// FLAVOR_* variable that the caller already had set produces two entries for
// it. exec.Cmd deduplicates keeping the last, so the intended value does reach
// the process — but anything reading the slice directly sees the first, and the
// rule is Go's rather than the platform's.
func setEnv(env []string, key, value string) []string {
	entry := fmt.Sprintf("%s=%s", key, value)
	prefix := key + "="

	for i, existing := range env {
		if strings.HasPrefix(existing, prefix) {
			env[i] = entry
			return env
		}
	}

	return append(env, entry)
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
func logEnvironmentTrace(env []string, logger *slog.Logger) {
	if !logging.IsEnabled(logger, logging.LevelTrace) {
		return
	}

	logging.Trace(logger, "🌍 Environment variables being passed to subprocess:")
	for _, e := range env {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) == 2 {
			value := parts[1]
			if isSensitiveKey(parts[0]) {
				value = "***"
			}
			logging.Trace(logger, "  →", "key", parts[0], "value", value)
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
