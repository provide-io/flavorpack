// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

// PackagePolicy mirrors the Python PackagePolicy struct.
type PackagePolicy struct {
	Platforms  []string `json:"platforms"`
	RefuseRoot bool     `json:"refuse_root"`
	MaxAgeDays *int     `json:"max_age_days"`
	RequireEnv []string `json:"require_env"`
}

// OperatorPolicy mirrors the Python OperatorPolicy struct.
type OperatorPolicy struct {
	RequireTrustedKey bool     `json:"require_trusted_key"`
	UseOsKeychain     bool     `json:"use_os_keychain"`
	RefuseRoot        bool     `json:"refuse_root"`
	MaxAgeDays        *int     `json:"max_age_days"`
	AllowPlatforms    []string `json:"allow_platforms"`
	RequireSBOM       bool     `json:"require_sbom"`
}

// EffectivePolicy is the merged result.
type EffectivePolicy struct {
	Platforms         []string
	RefuseRoot        bool
	MaxAgeDays        *int
	RequireEnv        []string
	RequireTrustedKey bool
	RequireSBOM       bool
}

// LoadOperatorPolicy reads system and user policy.toml files.
// Returns permissive defaults if the files do not exist.
func LoadOperatorPolicy() (OperatorPolicy, error) {
	policy := OperatorPolicy{}

	paths := []string{
		getSystemPolicyFile(),
		getUserPolicyFile(),
	}

	for _, path := range paths {
		if path == "" {
			continue
		}
		data, err := os.ReadFile(path)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return policy, fmt.Errorf("reading policy %s: %w", path, err)
		}
		parseMinimalTOML(data, &policy)
	}
	return policy, nil
}

func getSystemPolicyFile() string {
	if runtime.GOOS == "windows" {
		if pd := os.Getenv("PROGRAMDATA"); pd != "" {
			return filepath.Join(pd, "flavor", "policy.toml")
		}
		return filepath.Join("C:\\ProgramData", "flavor", "policy.toml")
	}
	return "/etc/flavor/policy.toml"
}

func getUserPolicyFile() string {
	if configDir := os.Getenv(EnvConfigDir); configDir != "" {
		return filepath.Join(configDir, "policy.toml")
	}
	if xdgConfig := os.Getenv("XDG_CONFIG_HOME"); xdgConfig != "" {
		return filepath.Join(xdgConfig, "flavor", "policy.toml")
	}
	if home := os.Getenv("HOME"); home != "" {
		return filepath.Join(home, ".config", "flavor", "policy.toml")
	}
	return ""
}

// parseMinimalTOML is a line-by-line parser for the small subset of TOML used
// in policy.toml: [section] headers and key = value bool/int/string-list lines.
func parseMinimalTOML(data []byte, policy *OperatorPolicy) {
	section := ""
	for _, rawLine := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(rawLine)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			section = strings.ToLower(line[1 : len(line)-1])
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])
		// Strip inline comments
		if idx := strings.Index(val, "#"); idx != -1 {
			val = strings.TrimSpace(val[:idx])
		}

		switch section + "." + key {
		case "trust.require_trusted_key":
			policy.RequireTrustedKey = val == "true"
		case "trust.use_os_keychain":
			policy.UseOsKeychain = val == "true"
		case "execution.refuse_root":
			policy.RefuseRoot = val == "true"
		case "execution.max_age_days":
			var n int
			if _, err := fmt.Sscanf(val, "%d", &n); err == nil {
				policy.MaxAgeDays = &n
			}
		case "execution.allow_platforms":
			// Parse a TOML string list: ["linux_amd64", "linux_arm64"]
			policy.AllowPlatforms = parseTOMLStringList(val)
		case "attestation.require_sbom":
			policy.RequireSBOM = val == "true"
		}
	}
}

// parseTOMLStringList parses a TOML array like ["a", "b"] or ['a', 'b'].
func parseTOMLStringList(val string) []string {
	val = strings.TrimSpace(val)
	if !strings.HasPrefix(val, "[") || !strings.HasSuffix(val, "]") {
		return nil
	}
	inner := val[1 : len(val)-1]
	var result []string
	for _, item := range strings.Split(inner, ",") {
		item = strings.TrimSpace(item)
		item = strings.Trim(item, `"'`)
		if item != "" {
			result = append(result, item)
		}
	}
	return result
}

// MergePolicy produces an EffectivePolicy where stricter always wins.
func MergePolicy(pkg PackagePolicy, op OperatorPolicy) EffectivePolicy {
	effective := EffectivePolicy{}

	// Platforms: intersection
	if len(pkg.Platforms) > 0 && len(op.AllowPlatforms) > 0 {
		opSet := make(map[string]bool)
		for _, p := range op.AllowPlatforms {
			opSet[p] = true
		}
		for _, p := range pkg.Platforms {
			if opSet[p] {
				effective.Platforms = append(effective.Platforms, p)
			}
		}
	} else if len(op.AllowPlatforms) > 0 {
		effective.Platforms = op.AllowPlatforms
	} else {
		effective.Platforms = pkg.Platforms
	}

	// refuse_root
	effective.RefuseRoot = pkg.RefuseRoot || op.RefuseRoot

	// max_age_days: minimum
	if pkg.MaxAgeDays != nil && op.MaxAgeDays != nil {
		if *pkg.MaxAgeDays < *op.MaxAgeDays {
			effective.MaxAgeDays = pkg.MaxAgeDays
		} else {
			effective.MaxAgeDays = op.MaxAgeDays
		}
	} else if pkg.MaxAgeDays != nil {
		effective.MaxAgeDays = pkg.MaxAgeDays
	} else {
		effective.MaxAgeDays = op.MaxAgeDays
	}

	effective.RequireEnv = pkg.RequireEnv
	effective.RequireTrustedKey = op.RequireTrustedKey
	effective.RequireSBOM = op.RequireSBOM

	return effective
}

// EnforcePolicy checks the effective policy against the current environment.
// Returns a descriptive error on the first violation.
func EnforcePolicy(policy EffectivePolicy, buildTimestamp int64, hasSBOM bool) error {
	currentPlatform := getCurrentPlatform()

	// 1. Platform check
	if len(policy.Platforms) > 0 {
		found := false
		for _, p := range policy.Platforms {
			if p == currentPlatform {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("platform not permitted: %s not in %v", currentPlatform, policy.Platforms)
		}
	}

	// 2. Root / Administrator check
	if policy.RefuseRoot && isPrivilegedUser() {
		return fmt.Errorf("refused to run as root or Administrator")
	}

	// 3. Age check
	if policy.MaxAgeDays != nil && buildTimestamp > 0 {
		ageDays := int(time.Since(time.Unix(buildTimestamp, 0)).Hours() / 24)
		if ageDays > *policy.MaxAgeDays {
			return fmt.Errorf("package is %d days old — policy requires max %d days", ageDays, *policy.MaxAgeDays)
		}
	}

	// 4. Environment variable check
	for _, envVar := range policy.RequireEnv {
		if os.Getenv(envVar) == "" {
			return fmt.Errorf("required environment variable not set: %s", envVar)
		}
	}

	// 5. SBOM check
	if policy.RequireSBOM && !hasSBOM {
		return fmt.Errorf("package built without attestation slot — operator policy requires SBOM")
	}

	return nil
}

func getCurrentPlatform() string {
	osName := "linux"
	switch runtime.GOOS {
	case "darwin":
		osName = "darwin"
	case "windows":
		osName = "windows"
	}
	arch := "amd64"
	if runtime.GOARCH == "arm64" {
		arch = "arm64"
	}
	return osName + "_" + arch
}

// ParsePackagePolicyJSON parses package-declared policy from the metadata JSON.
func ParsePackagePolicyJSON(raw []byte) (PackagePolicy, error) {
	var policy PackagePolicy
	if len(raw) == 0 {
		return policy, nil
	}
	err := json.Unmarshal(raw, &policy)
	return policy, err
}
