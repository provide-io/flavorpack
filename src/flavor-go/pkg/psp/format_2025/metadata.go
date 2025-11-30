package format_2025

type Metadata struct {
	Format          string               `json:"format"`
	FormatVersion   string               `json:"format_version"`
	Package         PackageInfo          `json:"package"`
	CacheValidation *CacheValidationInfo `json:"cache_validation,omitempty"`
	SetupCommands   []interface{}        `json:"setup_commands,omitempty"`
	Slots           []SlotMetadata       `json:"slots"`
	Execution       *ExecutionInfo       `json:"execution,omitempty"`
	Runtime         *RuntimeInfo         `json:"runtime,omitempty"`
	Verification    *VerificationInfo    `json:"verification,omitempty"`
	Build           *BuildInfo           `json:"build,omitempty"`
	Launcher        *LauncherInfo        `json:"launcher,omitempty"`
	Compatibility   *CompatibilityInfo   `json:"compatibility,omitempty"`
	Workenv         *WorkenvInfo         `json:"workenv,omitempty"`
}

type PackageInfo struct {
	Name        string `json:"name"`
	Version     string `json:"version"`
	Description string `json:"description"`
}

type CacheValidationInfo struct {
	CheckFile       string `json:"check_file"`
	ExpectedContent string `json:"expected_content,omitempty"`
}

type ExecutionInfo struct {
	PrimarySlot int               `json:"primary_slot"`
	Command     string            `json:"command"`
	Environment map[string]string `json:"environment"`
}

type RuntimeInfo struct {
	Env map[string]interface{} `json:"env,omitempty"`
}

type WorkenvInfo struct {
	Directories []DirectorySpec   `json:"directories,omitempty"`
	Env         map[string]string `json:"env,omitempty"`
}

type DirectorySpec struct {
	Path string `json:"path"`
	Mode string `json:"mode,omitempty"`
}

type VerificationInfo struct {
	IntegritySeal       IntegritySealInfo    `json:"integrity_seal"`
	Signed              bool                 `json:"signed"`
	RequireVerification bool                 `json:"require_verification"`
	TrustSignatures     *TrustSignaturesInfo `json:"trust_signatures,omitempty"`
}

type IntegritySealInfo struct {
	Required  bool   `json:"required"`
	Algorithm string `json:"algorithm"`
}

type TrustSignaturesInfo struct {
	Required bool         `json:"required"`
	Signers  []SignerInfo `json:"signers,omitempty"`
}

type SignerInfo struct {
	Name      string `json:"name"`
	KeyID     string `json:"key_id"`
	Algorithm string `json:"algorithm"`
}

type BuildInfo struct {
	Tool          string       `json:"tool"`
	ToolVersion   string       `json:"tool_version"`
	Timestamp     string       `json:"timestamp"`
	Deterministic bool         `json:"deterministic"`
	Platform      PlatformInfo `json:"platform"`
}

type PlatformInfo struct {
	OS   string `json:"os"`
	Arch string `json:"arch"`
	Host string `json:"host"`
}

type LauncherInfo struct {
	Tool         string   `json:"tool"`
	ToolVersion  string   `json:"tool_version"`
	Size         int64    `json:"size"`
	Checksum     string   `json:"checksum"`
	Capabilities []string `json:"capabilities"`
}

type CompatibilityInfo struct {
	MinFormatVersion string   `json:"min_format_version"`
	Features         []string `json:"features"`
}
