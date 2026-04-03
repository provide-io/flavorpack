// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"time"

	toml "github.com/BurntSushi/toml"
)

var (
	getSystemPolicyFileImpl = getSystemPolicyFile
	getUserPolicyFileImpl   = getUserPolicyFile
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
	UseOsKeychain     bool
	RequireSBOM       bool
}

// LoadOperatorPolicy reads system and user policy.toml files.
// Missing files are allowed; unreadable or invalid files are errors.
func LoadOperatorPolicy() (OperatorPolicy, error) {
	policy := OperatorPolicy{}

	paths := []string{
		getSystemPolicyFileImpl(),
		getUserPolicyFileImpl(),
	}

	for _, path := range paths {
		if path == "" {
			continue
		}
		data, err := os.ReadFile(path) // #nosec G304 -- policy files come from fixed config locations
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return policy, fmt.Errorf("reading policy %s: %w", path, err)
		}
		if err := applyOperatorPolicyTOML(data, &policy); err != nil {
			return policy, fmt.Errorf("parsing policy %s: %w", path, err)
		}
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

func applyOperatorPolicyTOML(data []byte, policy *OperatorPolicy) error {
	var raw map[string]any
	if _, err := toml.Decode(string(data), &raw); err != nil {
		return err
	}

	for key := range raw {
		switch key {
		case "trust", "execution", "attestation":
		default:
			return fmt.Errorf("unknown policy section %q", key)
		}
	}

	if section, ok := raw["trust"]; ok {
		if err := applyTrustPolicySection(section, policy); err != nil {
			return err
		}
	}
	if section, ok := raw["execution"]; ok {
		if err := applyExecutionPolicySection(section, policy); err != nil {
			return err
		}
	}
	if section, ok := raw["attestation"]; ok {
		if err := applyAttestationPolicySection(section, policy); err != nil {
			return err
		}
	}

	return nil
}

func applyTrustPolicySection(raw any, policy *OperatorPolicy) error {
	section, err := mustPolicySection("trust", raw)
	if err != nil {
		return err
	}
	for key := range section {
		switch key {
		case "require_trusted_key", "use_os_keychain":
		default:
			return fmt.Errorf("unknown key %q in [trust]", key)
		}
	}

	if value, ok := section["require_trusted_key"]; ok {
		b, err := mustBool("trust.require_trusted_key", value)
		if err != nil {
			return err
		}
		policy.RequireTrustedKey = b
	}
	if value, ok := section["use_os_keychain"]; ok {
		b, err := mustBool("trust.use_os_keychain", value)
		if err != nil {
			return err
		}
		policy.UseOsKeychain = b
	}

	return nil
}

func applyExecutionPolicySection(raw any, policy *OperatorPolicy) error {
	section, err := mustPolicySection("execution", raw)
	if err != nil {
		return err
	}
	for key := range section {
		switch key {
		case "refuse_root", "max_age_days", "allow_platforms":
		default:
			return fmt.Errorf("unknown key %q in [execution]", key)
		}
	}

	if value, ok := section["refuse_root"]; ok {
		b, err := mustBool("execution.refuse_root", value)
		if err != nil {
			return err
		}
		policy.RefuseRoot = b
	}
	if value, ok := section["max_age_days"]; ok {
		n, err := mustInt("execution.max_age_days", value)
		if err != nil {
			return err
		}
		policy.MaxAgeDays = &n
	}
	if value, ok := section["allow_platforms"]; ok {
		platforms, err := mustStringList("execution.allow_platforms", value)
		if err != nil {
			return err
		}
		policy.AllowPlatforms = platforms
	}

	return nil
}

func applyAttestationPolicySection(raw any, policy *OperatorPolicy) error {
	section, err := mustPolicySection("attestation", raw)
	if err != nil {
		return err
	}
	for key := range section {
		switch key {
		case "require_sbom":
		default:
			return fmt.Errorf("unknown key %q in [attestation]", key)
		}
	}

	if value, ok := section["require_sbom"]; ok {
		b, err := mustBool("attestation.require_sbom", value)
		if err != nil {
			return err
		}
		policy.RequireSBOM = b
	}

	return nil
}

func mustPolicySection(sectionName string, raw any) (map[string]any, error) {
	if raw == nil {
		return nil, nil
	}
	section, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("policy section %q must be a table, got %T", sectionName, raw)
	}
	return section, nil
}

func mustBool(fieldName string, raw any) (bool, error) {
	value, ok := raw.(bool)
	if !ok {
		return false, fmt.Errorf("policy field %s must be a boolean, got %T", fieldName, raw)
	}
	return value, nil
}

func mustInt(fieldName string, raw any) (int, error) {
	maxInt := int(^uint(0) >> 1)
	switch value := raw.(type) {
	case int:
		return value, nil
	case int8:
		return int(value), nil // #nosec G115 -- bounded integer conversion
	case int16:
		return int(value), nil // #nosec G115 -- bounded integer conversion
	case int32:
		return int(value), nil // #nosec G115 -- bounded integer conversion
	case int64:
		if value > int64(maxInt) || value < -int64(maxInt)-1 {
			return 0, fmt.Errorf("policy field %s is out of range for int", fieldName)
		}
		return int(value), nil // #nosec G115 -- range checked above
	case uint:
		if value > uint(maxInt) {
			return 0, fmt.Errorf("policy field %s is out of range for int", fieldName)
		}
		return int(value), nil // #nosec G115 -- range checked above
	case uint8:
		return int(value), nil // #nosec G115 -- bounded integer conversion
	case uint16:
		return int(value), nil // #nosec G115 -- bounded integer conversion
	case uint32:
		return int(value), nil // #nosec G115 -- bounded integer conversion
	case uint64:
		if value > uint64(maxInt) {
			return 0, fmt.Errorf("policy field %s is out of range for int", fieldName)
		}
		return int(value), nil // #nosec G115 -- range checked above
	default:
		return 0, fmt.Errorf("policy field %s must be an integer, got %T", fieldName, raw)
	}
}

func mustStringList(fieldName string, raw any) ([]string, error) {
	switch value := raw.(type) {
	case []string:
		result := make([]string, len(value))
		copy(result, value)
		return result, nil
	case []any:
		result := make([]string, 0, len(value))
		for _, item := range value {
			s, ok := item.(string)
			if !ok {
				return nil, fmt.Errorf("policy field %s must contain only strings, got %T", fieldName, item)
			}
			result = append(result, s)
		}
		return result, nil
	default:
		return nil, fmt.Errorf("policy field %s must be a string list, got %T", fieldName, raw)
	}
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
	effective.UseOsKeychain = op.UseOsKeychain
	effective.RequireSBOM = op.RequireSBOM

	return effective
}

// EnforcePolicy checks the effective policy against the current environment.
// Returns a descriptive error on the first violation.
// keyTrusted is false only when the trusted store exists AND the key is explicitly absent from it.
func EnforcePolicy(policy EffectivePolicy, buildTimestamp int64, hasSBOM bool, keyTrusted bool) error {
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

	if policy.UseOsKeychain {
		return fmt.Errorf("use_os_keychain is not supported by this launcher")
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

	// 6. Trusted key check
	if policy.RequireTrustedKey && !keyTrusted {
		return fmt.Errorf("operator policy requires a trusted signing key — package key is not in the trusted store")
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
