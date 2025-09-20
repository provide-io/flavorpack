package format_2025

import (
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"
)

// WorkenvPaths manages all paths for a workenv with instance and package metadata
type WorkenvPaths struct {
	cacheDir    string
	workenvName string
}

// NewWorkenvPaths creates a new WorkenvPaths from cache directory and package path
func NewWorkenvPaths(cacheDir string, packagePath string) *WorkenvPaths {
	// Extract workenv name from package filename
	workenvName := filepath.Base(packagePath)

	// Remove .psp or .pspf extension if present
	if strings.HasSuffix(workenvName, ".psp") {
		workenvName = workenvName[:len(workenvName)-4]
	} else if strings.HasSuffix(workenvName, ".pspf") {
		workenvName = workenvName[:len(workenvName)-5]
	}

	return &WorkenvPaths{
		cacheDir:    cacheDir,
		workenvName: workenvName,
	}
}

// ==================== Content Paths ====================

// Workenv returns the main workenv directory path (content location)
func (p *WorkenvPaths) Workenv() string {
	return filepath.Join(p.cacheDir, "workenv", p.workenvName)
}

// ==================== Metadata Paths ====================

// Metadata returns the hidden metadata directory path (.{name}.pspf)
func (p *WorkenvPaths) Metadata() string {
	metadataName := fmt.Sprintf("%s%s%s", PSPFHiddenPrefix, p.workenvName, PSPFSuffix)
	return filepath.Join(p.cacheDir, "workenv", metadataName)
}

// Instance returns the instance metadata directory (persistent)
func (p *WorkenvPaths) Instance() string {
	return filepath.Join(p.Metadata(), InstanceDir)
}

// PackageMetadata returns the package metadata directory (replaced each extraction)
func (p *WorkenvPaths) PackageMetadata() string {
	return filepath.Join(p.Metadata(), PackageDir)
}

// Tmp returns the temporary extraction directory root
func (p *WorkenvPaths) Tmp() string {
	return filepath.Join(p.Metadata(), TmpDir)
}

// TempExtraction returns a specific temp extraction directory for a PID
func (p *WorkenvPaths) TempExtraction(pid int) string {
	return filepath.Join(p.Tmp(), fmt.Sprintf("%d", pid))
}

// ==================== Instance Paths ====================

// Extract returns the extract operations directory
func (p *WorkenvPaths) Extract() string {
	return filepath.Join(p.Instance(), ExtractDir)
}

// Log returns the log directory
func (p *WorkenvPaths) Log() string {
	return filepath.Join(p.Instance(), LogDir)
}

// LockFile returns the lock file path
func (p *WorkenvPaths) LockFile() string {
	return filepath.Join(p.Extract(), LockFile)
}

// CompleteFile returns the completion marker file path
func (p *WorkenvPaths) CompleteFile() string {
	return filepath.Join(p.Extract(), CompleteFile)
}

// ChecksumFile returns the package checksum file path
func (p *WorkenvPaths) ChecksumFile() string {
	return filepath.Join(p.Instance(), PackageChecksumFile)
}

// IndexMetadataFile returns the index metadata file path
func (p *WorkenvPaths) IndexMetadataFile() string {
	return filepath.Join(p.Instance(), IndexMetadataFile)
}

// ==================== Package Metadata Paths ====================

// PSPMetadataFile returns the PSP metadata JSON file path
func (p *WorkenvPaths) PSPMetadataFile() string {
	return filepath.Join(p.PackageMetadata(), PSPMetadataFile)
}

// ==================== Utility Methods ====================

// Name returns the workenv name
func (p *WorkenvPaths) Name() string {
	return p.workenvName
}

// WorkenvExists checks if the workenv exists
func (p *WorkenvPaths) WorkenvExists() bool {
	_, err := os.Stat(p.Workenv())
	return err == nil
}

// MetadataExists checks if metadata directory exists
func (p *WorkenvPaths) MetadataExists() bool {
	_, err := os.Stat(p.Metadata())
	return err == nil
}

// ListTempExtractions returns all temp extraction directories
func (p *WorkenvPaths) ListTempExtractions() ([]string, error) {
	tmpDir := p.Tmp()

	// If tmp directory doesn't exist, return empty list
	if _, err := os.Stat(tmpDir); os.IsNotExist(err) {
		return []string{}, nil
	}

	entries, err := ioutil.ReadDir(tmpDir)
	if err != nil {
		return nil, err
	}

	var dirs []string
	for _, entry := range entries {
		if entry.IsDir() {
			dirs = append(dirs, filepath.Join(tmpDir, entry.Name()))
		}
	}

	return dirs, nil
}
