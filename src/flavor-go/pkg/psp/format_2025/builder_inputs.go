// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"encoding/json"
	"log/slog"
	"os"
	"os/exec"
	"strings"
)

// loadBuildManifest reads and parses the manifest describing the package.
func loadBuildManifest(manifestPath string, logger *slog.Logger) (BuildOptions, bool) {
	var config BuildOptions

	manifestData, err := readFileValidated(manifestPath)
	if err != nil {
		logger.Error("❌ Failed to read manifest", "error", err)
		buildExitFn(1)
		return config, false
	}

	if err := json.Unmarshal(manifestData, &config); err != nil {
		logger.Error("❌ Failed to parse manifest", "error", err)
		buildExitFn(1)
		return config, false
	}

	return config, true
}

// resolveLauncherPath picks the launcher to embed: the command-line argument
// first, then FLAVOR_LAUNCHER_BIN.
func resolveLauncherPath(launcherBin string, logger *slog.Logger) string {
	launcherPath := launcherBin
	if launcherPath == "" {
		launcherPath = getLauncherPath("")
	}
	if launcherPath == "" {
		logger.Error("❌ Launcher binary path must be specified via --launcher-bin or FLAVOR_LAUNCHER_BIN environment variable")
		buildExitFn(1)
	}
	return launcherPath
}

// logLauncherVersion records which launcher this package is being built with.
//
// The probe goes through CLI mode. Launchers never intercept arguments outside
// it -- every argument belongs to the packaged application -- so probing a
// launcher with --version ran it as the package and always failed. CLI mode's
// "version" command does not touch the bundle. Only stdout is read; the
// launcher logs to stderr.
//
// A launcher that will not report its version is not a reason to stop: the
// version is provenance, not a prerequisite.
func logLauncherVersion(launcherPath string, logger *slog.Logger) {
	versionCmd := exec.Command(launcherPath, "version") // #nosec G204 -- launcherPath is operator-supplied and executed directly without shell expansion for a version probe.
	versionCmd.Env = append(os.Environ(), EnvLauncherCLI+"=1")

	versionOutput, err := versionCmd.Output()
	if err != nil {
		logger.Warn("⚠️ Failed to get launcher version", "error", err)
		return
	}
	logger.Info("🔍 Launcher version", "version", strings.TrimSpace(string(versionOutput)))
}

// loadLauncherBinary resolves, probes and reads the launcher, returning the
// bytes to prepend and the path they came from.
func loadLauncherBinary(launcherBin string, logger *slog.Logger) ([]byte, string) {
	launcherPath := resolveLauncherPath(launcherBin, logger)
	logger.Info("🚀 Loading launcher", "path", launcherPath)

	logLauncherVersion(launcherPath, logger)

	logger.Debug("🔍 Launcher path", "path", launcherPath)
	launcherData, err := readFileValidated(launcherPath)
	if err != nil {
		logger.Error("❌ Failed to read launcher", "error", err, "path", launcherPath)
		buildExitFn(1)
	}
	logger.Debug("✅ Launcher loaded", "size", len(launcherData))

	// Windows PE needs the launcher rewritten before anything is appended.
	launcherData, err = processLauncherFn(launcherData, logger)
	if err != nil {
		logger.Error("❌ Failed to process launcher for PSPF", "error", err)
		buildExitFn(1)
	}
	logger.Debug("✅ Launcher processed for PSPF", "size", len(launcherData))

	return launcherData, launcherPath
}
