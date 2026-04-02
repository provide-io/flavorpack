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
	sourceFile, err := openFileValidated(src, os.O_RDONLY, 0)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destFile, err := openFileValidated(dst, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.FileMode(FilePerms))
	if err != nil {
		return err
	}
	defer destFile.Close()

	if _, err := io.Copy(destFile, sourceFile); err != nil {
		return err
	}

	// Copy file permissions
	sourceInfo, err := sourceFile.Stat()
	if err != nil {
		return err
	}
	return os.Chmod(dst, sourceInfo.Mode()) // #nosec G703 -- dst is the validated destination path controlled by the caller.
}

// copyDirAll recursively copies a directory tree
func copyDirAll(src, dst string) error {
	sourceInfo, err := statValidated(src)
	if err != nil {
		return err
	}

	if err := mkdirAllValidated(dst, sourceInfo.Mode()); err != nil {
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
	if _, err := statValidated(binDir); err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
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
		file, err := openFileValidated(scriptPath, os.O_RDONLY, 0)
		if err != nil {
			continue
		}

		header := make([]byte, 2)
		if _, err := file.Read(header); err != nil {
			if closeErr := file.Close(); closeErr != nil {
				logger.Debug("Failed to close script during shebang probe", "script", entry.Name(), "error", closeErr)
			}
			continue
		}
		if closeErr := file.Close(); closeErr != nil {
			logger.Debug("Failed to close script after shebang probe", "script", entry.Name(), "error", closeErr)
		}

		if string(header) != "#!" {
			continue
		}

		// Read entire file
		content, err := readFileValidated(scriptPath)
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
			if err := writeFileValidated(scriptPath, []byte(newContent), entry.Type().Perm()); err != nil {
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
	for _, slot := range metadata.Slots {
		// Clean up init lifecycle slots - they're only needed during setup
		if slot.Lifecycle == "init" {
			slotPath := filepath.Join(workenvDir, slot.ID)
			if err := removeAllPath(slotPath); err != nil {
				logger.Debug("⚠️ Failed to remove init slot", "slot", slot.ID, "path", slotPath, "error", err)
			} else {
				logger.Debug("✅ Removed init slot", "slot", slot.ID, "path", slotPath)
			}
			// Remove from slotPaths map so it's not used in execution
			delete(slotPaths, slot.Slot)
		}
	}
}
