package format_2025

import (
	"bufio"
	"crypto/ed25519"
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/pem"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/provide-io/flavor/go/flavor/internal/workenv"
)

// TrustedKey holds metadata about a trusted public key loaded from the key store.
type TrustedKey struct {
	Fingerprint string
	Name        string
	Path        string
}

// GetTrustedKeysDir returns the user-level trusted-keys directory.
// Priority: FLAVOR_TRUSTED_KEYS_DIR → FLAVOR_CONFIG_DIR/trusted-keys
//
//	→ XDG_CONFIG_HOME/flavor/trusted-keys → ~/.config/flavor/trusted-keys
func GetTrustedKeysDir() string {
	if dir := os.Getenv("FLAVOR_TRUSTED_KEYS_DIR"); dir != "" {
		return dir
	}
	return filepath.Join(workenv.GetConfigRoot(), "trusted-keys")
}

// ComputeKeyFingerprint returns the SHA-256 fingerprint of a raw 32-byte Ed25519 public key.
// Input must be exactly 32 bytes. Returns lowercase hex string (64 chars), error if wrong size.
func ComputeKeyFingerprint(rawPublicKey []byte) (string, error) {
	if len(rawPublicKey) != ed25519.PublicKeySize {
		return "", fmt.Errorf("invalid Ed25519 public key size: expected %d bytes, got %d", ed25519.PublicKeySize, len(rawPublicKey))
	}
	hash := sha256.Sum256(rawPublicKey)
	return hex.EncodeToString(hash[:]), nil
}

// extractNameFromPEM parses lines starting with "# Name:" before the PEM block
// and returns the name value. Returns empty string if not found.
func extractNameFromPEM(data []byte) string {
	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "# Name:") {
			return strings.TrimSpace(strings.TrimPrefix(line, "# Name:"))
		}
		// Stop looking once we hit the PEM block start
		if strings.HasPrefix(line, "-----BEGIN") {
			break
		}
	}
	return ""
}

// stripCommentLines removes lines starting with "#" to produce clean PEM for decoding.
func stripCommentLines(data []byte) []byte {
	var lines []string
	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "#") {
			lines = append(lines, line)
		}
	}
	return []byte(strings.Join(lines, "\n"))
}

// loadKeyFromFile reads a .pub PEM file and returns a TrustedKey.
// The file may contain "# Name: <label>" comment lines before the PEM block.
func loadKeyFromFile(path string) (TrustedKey, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return TrustedKey{}, fmt.Errorf("reading key file %s: %w", path, err)
	}

	name := extractNameFromPEM(data)
	cleaned := stripCommentLines(data)

	block, _ := pem.Decode(cleaned)
	if block == nil {
		return TrustedKey{}, fmt.Errorf("no PEM block found in %s", path)
	}

	pub, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return TrustedKey{}, fmt.Errorf("parsing public key in %s: %w", path, err)
	}

	edPub, ok := pub.(ed25519.PublicKey)
	if !ok {
		return TrustedKey{}, fmt.Errorf("key in %s is not an Ed25519 public key", path)
	}

	fp, err := ComputeKeyFingerprint([]byte(edPub))
	if err != nil {
		return TrustedKey{}, fmt.Errorf("computing fingerprint for %s: %w", path, err)
	}

	return TrustedKey{
		Fingerprint: fp,
		Name:        name,
		Path:        path,
	}, nil
}

// loadKeysFromDir loads all .pub files from dir into the provided map.
// Returns (false, nil) if the directory does not exist (not an error).
// Returns (true, nil) on success, (true, err) on read/parse errors.
func loadKeysFromDir(dir string, keys map[string]TrustedKey) (bool, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return true, fmt.Errorf("reading trusted-keys dir %s: %w", dir, err)
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if !strings.HasSuffix(name, ".pub") {
			continue
		}
		path := filepath.Join(dir, name)
		tk, err := loadKeyFromFile(path)
		if err != nil {
			// Skip unparsable files with a best-effort approach
			continue
		}
		keys[tk.Fingerprint] = tk
	}
	return true, nil
}

// LoadTrustedKeys loads all .pub PEM files from user and (optionally) system trusted-keys dirs.
// Returns map of fingerprint → TrustedKey. Returns empty map (not error) if dir doesn't exist.
func LoadTrustedKeys(includeSystem bool) (map[string]TrustedKey, error) {
	keys := make(map[string]TrustedKey)

	if _, err := loadKeysFromDir(GetTrustedKeysDir(), keys); err != nil {
		return keys, err
	}

	if includeSystem {
		sysDir := filepath.Join(workenv.GetSystemConfigRoot(), "trusted-keys")
		if _, err := loadKeysFromDir(sysDir, keys); err != nil {
			return keys, err
		}
	}

	return keys, nil
}

// IsKeyTrusted checks if a fingerprint is in the trusted store.
// Returns *bool where nil = no store exists, *true = trusted, *false = not trusted.
func IsKeyTrusted(fingerprint string, includeSystem bool) (*bool, error) {
	userDir := GetTrustedKeysDir()
	userExists := false
	if _, err := os.Stat(userDir); err == nil {
		userExists = true
	}

	sysExists := false
	if includeSystem {
		sysDir := filepath.Join(workenv.GetSystemConfigRoot(), "trusted-keys")
		if _, err := os.Stat(sysDir); err == nil {
			sysExists = true
		}
	}

	if !userExists && !sysExists {
		return nil, nil
	}

	keys, err := LoadTrustedKeys(includeSystem)
	if err != nil {
		return nil, err
	}

	_, found := keys[fingerprint]
	result := found
	return &result, nil
}
