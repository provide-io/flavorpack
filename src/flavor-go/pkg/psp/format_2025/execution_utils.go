package format_2025

import (
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/hashicorp/go-hclog"
)

// copyFile copies a single file from src to dst
func copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destFile.Close()

	if _, err := io.Copy(destFile, sourceFile); err != nil {
		return err
	}

	// Copy file permissions
	sourceInfo, err := os.Stat(src)
	if err != nil {
		return err
	}
	return os.Chmod(dst, sourceInfo.Mode())
}

// copyDirAll recursively copies a directory tree
func copyDirAll(src, dst string) error {
	sourceInfo, err := os.Stat(src)
	if err != nil {
		return err
	}

	if err := os.MkdirAll(dst, sourceInfo.Mode()); err != nil {
		return err
	}

	entries, err := os.ReadDir(src)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())

		if entry.IsDir() {
			if err := copyDirAll(srcPath, dstPath); err != nil {
				return err
			}
		} else {
			if err := copyFile(srcPath, dstPath); err != nil {
				return err
			}
		}
	}
	return nil
}

// fixShebangs fixes shebang paths in scripts after atomic move
func fixShebangs(binDir, oldPrefix, newPrefix string, logger hclog.Logger) error {
	if _, err := os.Stat(binDir); os.IsNotExist(err) {
		return nil
	}

	entries, err := os.ReadDir(binDir)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		scriptPath := filepath.Join(binDir, entry.Name())

		// Read first few bytes to check for shebang
		file, err := os.Open(scriptPath)
		if err != nil {
			continue
		}

		header := make([]byte, 2)
		if _, err := file.Read(header); err != nil {
			file.Close()
			continue
		}
		file.Close()

		if string(header) != "#!" {
			continue
		}

		// Read entire file
		content, err := os.ReadFile(scriptPath)
		if err != nil {
			continue
		}

		// Find end of first line
		lines := strings.SplitN(string(content), "\n", 2)
		if len(lines) < 1 {
			continue
		}

		firstLine := lines[0]
		if strings.Contains(firstLine, oldPrefix) {
			// Replace old prefix with new prefix in shebang
			newFirstLine := strings.ReplaceAll(firstLine, oldPrefix, newPrefix)

			// Reconstruct content
			var newContent string
			if len(lines) > 1 {
				newContent = newFirstLine + "\n" + lines[1]
			} else {
				newContent = newFirstLine + "\n"
			}

			// Write back the modified content
			if err := os.WriteFile(scriptPath, []byte(newContent), entry.Type().Perm()); err != nil {
				logger.Debug("Failed to fix shebang", "script", entry.Name(), "error", err)
			} else {
				logger.Debug("Fixed shebang", "script", entry.Name())
			}
		}
	}

	return nil
}

// cleanupLifecycleSlots removes slots based on their lifecycle after setup
func cleanupLifecycleSlots(workenvDir string, metadata *Metadata, slotPaths map[int]string, logger hclog.Logger) {
	for i, slot := range metadata.Slots {
		// Clean up init lifecycle slots - they're only needed during setup
		if slot.Lifecycle == "init" {
			slotPath := filepath.Join(workenvDir, slot.ID)
			if err := os.RemoveAll(slotPath); err != nil {
				logger.Debug("⚠️ Failed to remove init slot", "slot", slot.ID, "path", slotPath, "error", err)
			} else {
				logger.Debug("✅ Removed init slot", "slot", slot.ID, "path", slotPath)
			}
			// Remove from slotPaths map so it's not used in execution
			delete(slotPaths, i)
		}
	}
}
