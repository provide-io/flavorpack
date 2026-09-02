// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"fmt"
	"log/slog"
	"os"
	"runtime"
	"strconv"
	"time"
)

// resolveBuildProvenance produces the timestamp and host recorded in the
// package's build block.
//
// SOURCE_DATE_EPOCH pins the timestamp for a reproducible build, and its
// presence also drops the hostname from the build host, since a name that
// varies per machine defeats the reproducibility being asked for. An epoch
// that will not parse falls back to now rather than failing the build.
func resolveBuildProvenance(logger *slog.Logger) (timestamp string, host string) {
	platform := fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)

	if epochStr := os.Getenv("SOURCE_DATE_EPOCH"); epochStr != "" {
		if epochInt, err := strconv.ParseInt(epochStr, 10, 64); err == nil {
			return time.Unix(epochInt, 0).UTC().Format(time.RFC3339), platform
		}
		return time.Now().UTC().Format(time.RFC3339), platform
	}

	timestamp = time.Now().UTC().Format(time.RFC3339)

	hostname, err := hostnameFunc()
	if err != nil {
		logger.Warn("⚠️ Failed to resolve hostname, using platform-only build host", "error", err)
		return timestamp, platform
	}
	return timestamp, fmt.Sprintf("%s %s", platform, hostname)
}

// buildPackageMetadata assembles the metadata document from the manifest. The
// slots array is filled in later, once the slot processor has run.
func buildPackageMetadata(config *BuildOptions, logger *slog.Logger) *Metadata {
	buildTimestamp, buildHost := resolveBuildProvenance(logger)

	var cacheValidation *CacheValidationInfo
	if config.CacheValidation != nil {
		cacheValidation = &CacheValidationInfo{
			CheckFile:       config.CacheValidation.CheckFile,
			ExpectedContent: config.CacheValidation.ExpectedContent,
		}
	}

	var runtimeInfo *RuntimeInfo
	if config.Runtime != nil {
		runtimeInfo = &RuntimeInfo{Env: config.Runtime.Env}
	}

	return &Metadata{
		Format: "PSPF/2025",
		Package: PackageInfo{
			Name:        config.Package.Name,
			Version:     config.Package.Version,
			Description: config.Package.Description,
		},
		CacheValidation: cacheValidation,
		SetupCommands:   config.SetupCommands,
		Slots:           []SlotMetadata{},
		Execution: &ExecutionInfo{
			Command:     config.Execution.Command,
			Environment: config.Execution.Environment,
		},
		Runtime: runtimeInfo,
		Verification: &VerificationInfo{
			IntegritySeal: IntegritySealInfo{
				Required:  true,
				Algorithm: "ed25519",
			},
		},
		Build: &BuildInfo{
			Tool:          "flavor-go",
			ToolVersion:   "1.0.0",
			Timestamp:     buildTimestamp,
			Deterministic: false,
			Platform: PlatformInfo{
				OS:   runtime.GOOS,
				Arch: runtime.GOARCH,
				Host: buildHost,
			},
		},
	}
}
