// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"time"
)

// PolicyVersion is the current supported policy file version.
const PolicyVersion = 1

var (
	getSystemPolicyFileImpl = getSystemPolicyFile
	getUserPolicyFileImpl   = getUserPolicyFile
)

// EnforcementMode controls how a policy check violation is handled.
type EnforcementMode string

const (
	ModeDeny  EnforcementMode = "deny"
	ModeWarn  EnforcementMode = "warn"
	ModeAllow EnforcementMode = "allow"
)

// EnforcementPolicy holds per-check enforcement modes. Omitted checks inherit from Default.
type EnforcementPolicy struct {
	Default          EnforcementMode `json:"default"`
	PlatformMismatch EnforcementMode `json:"platform_mismatch,omitempty"`
	UntrustedKey     EnforcementMode `json:"untrusted_key,omitempty"`
	ExpiredPackage   EnforcementMode `json:"expired_package,omitempty"`
	MissingEnv       EnforcementMode `json:"missing_env,omitempty"`
	MissingSBOM      EnforcementMode `json:"missing_sbom,omitempty"`
	RootExecution    EnforcementMode `json:"root_execution,omitempty"`
	OsKeychain       EnforcementMode `json:"os_keychain,omitempty"`
}

// ModeFor returns the enforcement mode for a given check name.
// If the specific check mode is unset (empty), returns Default.
func (ep EnforcementPolicy) ModeFor(check string) EnforcementMode {
	var mode EnforcementMode
	switch check {
	case "platform_mismatch":
		mode = ep.PlatformMismatch
	case "untrusted_key":
		mode = ep.UntrustedKey
	case "expired_package":
		mode = ep.ExpiredPackage
	case "missing_env":
		mode = ep.MissingEnv
	case "missing_sbom":
		mode = ep.MissingSBOM
	case "root_execution":
		mode = ep.RootExecution
	case "os_keychain":
		mode = ep.OsKeychain
	}
	if mode == "" {
		return ep.Default
	}
	return mode
}

// NewDefaultEnforcementPolicy returns an EnforcementPolicy with Default set to "deny".
func NewDefaultEnforcementPolicy() EnforcementPolicy {
	return EnforcementPolicy{Default: ModeDeny}
}

// PackagePolicy mirrors the Python PackagePolicy struct.
type PackagePolicy struct {
	Platforms  []string `json:"platforms"`
	RefuseRoot bool     `json:"refuse_root"`
	MaxAgeDays *int     `json:"max_age_days"`
	RequireEnv []string `json:"require_env"`
}

// OperatorPolicy mirrors the Python OperatorPolicy struct.
type OperatorPolicy struct {
	RequireTrustedKey bool              `json:"require_trusted_key"`
	UseOsKeychain     bool              `json:"use_os_keychain"`
	RefuseRoot        bool              `json:"refuse_root"`
	MaxAgeDays        *int              `json:"max_age_days"`
	AllowPlatforms    []string          `json:"allow_platforms"`
	RequireSBOM       bool              `json:"require_sbom"`
	Enforcement       EnforcementPolicy `json:"enforcement"`
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
	Enforcement       EnforcementPolicy
}

// --- JSON policy file structs (typed parsing) ---

type trustSection struct {
	RequireTrustedKey *bool `json:"require_trusted_key,omitempty"`
	UseOsKeychain     *bool `json:"use_os_keychain,omitempty"`
}

type executionSection struct {
	RefuseRoot     *bool    `json:"refuse_root,omitempty"`
	MaxAgeDays     *int     `json:"max_age_days,omitempty"`
	AllowPlatforms []string `json:"allow_platforms,omitempty"`
}

type attestationSection struct {
	RequireSBOM *bool `json:"require_sbom,omitempty"`
}

type enforcementSectionJSON struct {
	Default          string `json:"default,omitempty"`
	PlatformMismatch string `json:"platform_mismatch,omitempty"`
	UntrustedKey     string `json:"untrusted_key,omitempty"`
	ExpiredPackage   string `json:"expired_package,omitempty"`
	MissingEnv       string `json:"missing_env,omitempty"`
	MissingSBOM      string `json:"missing_sbom,omitempty"`
	RootExecution    string `json:"root_execution,omitempty"`
	OsKeychain       string `json:"os_keychain,omitempty"`
}

type operatorPolicyJSON struct {
	Version     int                     `json:"version"`
	Trust       *trustSection           `json:"trust,omitempty"`
	Execution   *executionSection       `json:"execution,omitempty"`
	Attestation *attestationSection     `json:"attestation,omitempty"`
	Enforcement *enforcementSectionJSON `json:"enforcement,omitempty"`
}

// LoadOperatorPolicy reads system and user policy.json files.
// Missing files are allowed; unreadable or invalid files are errors.
func LoadOperatorPolicy() (OperatorPolicy, error) {
	policy := OperatorPolicy{Enforcement: NewDefaultEnforcementPolicy()}

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
		if err := applyOperatorPolicyJSON(data, &policy); err != nil {
			return policy, fmt.Errorf("parsing policy %s: %w", path, err)
		}
	}
	return policy, nil
}

func getSystemPolicyFile() string {
	if runtime.GOOS == "windows" {
		if pd := os.Getenv("PROGRAMDATA"); pd != "" {
			return filepath.Join(pd, "flavor", "policy.json")
		}
		return filepath.Join("C:\\ProgramData", "flavor", "policy.json")
	}
	return "/etc/flavor/policy.json"
}

func getUserPolicyFile() string {
	if configDir := os.Getenv(EnvConfigDir); configDir != "" {
		return filepath.Join(configDir, "policy.json")
	}
	if xdgConfig := os.Getenv("XDG_CONFIG_HOME"); xdgConfig != "" {
		return filepath.Join(xdgConfig, "flavor", "policy.json")
	}
	if home := os.Getenv("HOME"); home != "" {
		return filepath.Join(home, ".config", "flavor", "policy.json")
	}
	return ""
}

var validEnforcementModes = map[string]bool{
	"deny": true, "warn": true, "allow": true,
}

func validateEnforcementMode(field, value string) error {
	if value == "" {
		return nil
	}
	if !validEnforcementModes[value] {
		return fmt.Errorf("enforcement.%s must be one of [deny, warn, allow], got %q", field, value)
	}
	return nil
}

func applyOperatorPolicyJSON(data []byte, policy *OperatorPolicy) error {
	var pf operatorPolicyJSON
	if err := json.Unmarshal(data, &pf); err != nil {
		return err
	}

	// Version validation
	if pf.Version == 0 {
		return fmt.Errorf("missing required 'version' field")
	}
	if pf.Version > PolicyVersion {
		log.Printf("WARNING: policy version %d is newer than supported version %d — unknown fields will be ignored", pf.Version, PolicyVersion)
	}

	// Trust section
	if t := pf.Trust; t != nil {
		if t.RequireTrustedKey != nil {
			policy.RequireTrustedKey = *t.RequireTrustedKey
		}
		if t.UseOsKeychain != nil {
			policy.UseOsKeychain = *t.UseOsKeychain
		}
	}

	// Execution section
	if e := pf.Execution; e != nil {
		if e.RefuseRoot != nil {
			policy.RefuseRoot = *e.RefuseRoot
		}
		if e.MaxAgeDays != nil {
			policy.MaxAgeDays = e.MaxAgeDays
		}
		if e.AllowPlatforms != nil {
			policy.AllowPlatforms = e.AllowPlatforms
		}
	}

	// Attestation section
	if a := pf.Attestation; a != nil {
		if a.RequireSBOM != nil {
			policy.RequireSBOM = *a.RequireSBOM
		}
	}

	// Enforcement section
	if enf := pf.Enforcement; enf != nil {
		fields := map[string]string{
			"default":           enf.Default,
			"platform_mismatch": enf.PlatformMismatch,
			"untrusted_key":     enf.UntrustedKey,
			"expired_package":   enf.ExpiredPackage,
			"missing_env":       enf.MissingEnv,
			"missing_sbom":      enf.MissingSBOM,
			"root_execution":    enf.RootExecution,
			"os_keychain":       enf.OsKeychain,
		}
		for field, value := range fields {
			if err := validateEnforcementMode(field, value); err != nil {
				return err
			}
		}
		if enf.Default != "" {
			policy.Enforcement.Default = EnforcementMode(enf.Default)
		}
		if enf.PlatformMismatch != "" {
			policy.Enforcement.PlatformMismatch = EnforcementMode(enf.PlatformMismatch)
		}
		if enf.UntrustedKey != "" {
			policy.Enforcement.UntrustedKey = EnforcementMode(enf.UntrustedKey)
		}
		if enf.ExpiredPackage != "" {
			policy.Enforcement.ExpiredPackage = EnforcementMode(enf.ExpiredPackage)
		}
		if enf.MissingEnv != "" {
			policy.Enforcement.MissingEnv = EnforcementMode(enf.MissingEnv)
		}
		if enf.MissingSBOM != "" {
			policy.Enforcement.MissingSBOM = EnforcementMode(enf.MissingSBOM)
		}
		if enf.RootExecution != "" {
			policy.Enforcement.RootExecution = EnforcementMode(enf.RootExecution)
		}
		if enf.OsKeychain != "" {
			policy.Enforcement.OsKeychain = EnforcementMode(enf.OsKeychain)
		}
	}

	return nil
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
	effective.Enforcement = op.Enforcement

	return effective
}

// applyEnforcement applies the enforcement mode for a check.
// deny: returns error immediately. warn: appends to warnings. allow: silent pass.
func applyEnforcement(mode EnforcementMode, msg string, warnings *[]string) error {
	switch mode {
	case ModeDeny:
		return fmt.Errorf("%s", msg)
	case ModeWarn:
		*warnings = append(*warnings, msg)
		return nil
	case ModeAllow:
		return nil
	default:
		// Unknown mode treated as deny for safety
		return fmt.Errorf("%s", msg)
	}
}

// EnforcePolicy checks the effective policy against the current environment.
// Returns a list of warning messages and an optional hard error.
// keyTrusted is false only when the trusted store exists AND the key is explicitly absent from it.
func EnforcePolicy(policy EffectivePolicy, buildTimestamp int64, hasSBOM bool, keyTrusted bool) ([]string, error) {
	var warnings []string
	enf := policy.Enforcement
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
			msg := fmt.Sprintf("platform not permitted: %s not in %v", currentPlatform, policy.Platforms)
			if err := applyEnforcement(enf.ModeFor("platform_mismatch"), msg, &warnings); err != nil {
				return warnings, err
			}
		}
	}

	// 2. OS keychain check
	if policy.UseOsKeychain {
		msg := "use_os_keychain is not supported by this launcher"
		if err := applyEnforcement(enf.ModeFor("os_keychain"), msg, &warnings); err != nil {
			return warnings, err
		}
	}

	// 3. Root / Administrator check
	if policy.RefuseRoot && isPrivilegedUser() {
		msg := "refused to run as root or Administrator"
		if err := applyEnforcement(enf.ModeFor("root_execution"), msg, &warnings); err != nil {
			return warnings, err
		}
	}

	// 4. Age check
	if policy.MaxAgeDays != nil && buildTimestamp > 0 {
		ageDays := int(time.Since(time.Unix(buildTimestamp, 0)).Hours() / 24)
		if ageDays > *policy.MaxAgeDays {
			msg := fmt.Sprintf("package is %d days old — policy requires max %d days", ageDays, *policy.MaxAgeDays)
			if err := applyEnforcement(enf.ModeFor("expired_package"), msg, &warnings); err != nil {
				return warnings, err
			}
		}
	}

	// 5. Environment variable check
	for _, envVar := range policy.RequireEnv {
		if os.Getenv(envVar) == "" {
			msg := fmt.Sprintf("required environment variable not set: %s", envVar)
			if err := applyEnforcement(enf.ModeFor("missing_env"), msg, &warnings); err != nil {
				return warnings, err
			}
		}
	}

	// 6. SBOM check
	if policy.RequireSBOM && !hasSBOM {
		msg := "package built without attestation slot — operator policy requires SBOM"
		if err := applyEnforcement(enf.ModeFor("missing_sbom"), msg, &warnings); err != nil {
			return warnings, err
		}
	}

	// 7. Trusted key check
	if policy.RequireTrustedKey && !keyTrusted {
		msg := "operator policy requires a trusted signing key — package key is not in the trusted store"
		if err := applyEnforcement(enf.ModeFor("untrusted_key"), msg, &warnings); err != nil {
			return warnings, err
		}
	}

	return warnings, nil
}

func getCurrentPlatform() string {
	osName := runtime.GOOS
	switch runtime.GOOS {
	case "linux":
		osName = "linux"
	case "darwin":
		osName = "darwin"
	case "freebsd":
		osName = "freebsd"
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
