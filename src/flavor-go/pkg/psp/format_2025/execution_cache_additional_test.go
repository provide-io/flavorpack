package format_2025

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/hashicorp/go-hclog"
)

func TestExecutionCacheHelpers(t *testing.T) {
	logger := hclog.NewNullLogger()
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/demo.pspf")

	t.Run("disk space validation", func(t *testing.T) {
		oldGetAvailableDiskSpaceFn := getAvailableDiskSpaceFn
		getAvailableDiskSpaceFn = func(string) (int64, error) {
			return 4096, nil
		}
		t.Cleanup(func() {
			getAvailableDiskSpaceFn = oldGetAvailableDiskSpaceFn
		})

		metadata := &Metadata{
			Slots: []SlotMetadata{
				{Size: 1},
			},
		}
		if err := checkDiskSpace(paths, metadata, logger); err != nil {
			t.Fatalf("checkDiskSpace() small payload error = %v", err)
		}

		getAvailableDiskSpaceFn = func(string) (int64, error) {
			return 0, nil
		}
		if err := checkDiskSpace(paths, metadata, logger); err == nil {
			t.Fatal("expected insufficient disk space error")
		}
	})

	t.Run("checksum validation by validation level", func(t *testing.T) {
		checksumFile := paths.ChecksumFile()
		if err := os.MkdirAll(filepath.Dir(checksumFile), 0o700); err != nil {
			t.Fatalf("MkdirAll(checksum dir) error = %v", err)
		}
		if err := os.WriteFile(checksumFile, []byte("12345678"), 0o600); err != nil {
			t.Fatalf("WriteFile(checksum) error = %v", err)
		}

		if valid, err := validatePackageChecksum(paths, 0x12345678, logger); err != nil || !valid {
			t.Fatalf("validatePackageChecksum() match = valid=%v err=%v", valid, err)
		}

		if err := os.WriteFile(checksumFile, []byte("87654321"), 0o600); err != nil {
			t.Fatalf("WriteFile(mismatch checksum) error = %v", err)
		}

		cases := []struct {
			name    string
			level   string
			wantErr bool
		}{
			{name: "none", level: "none", wantErr: false},
			{name: "minimal", level: "minimal", wantErr: false},
			{name: "relaxed", level: "relaxed", wantErr: false},
			{name: "standard", level: "standard", wantErr: false},
			{name: "strict", level: "strict", wantErr: true},
		}

		for _, tc := range cases {
			tc := tc
			t.Run(tc.name, func(t *testing.T) {
				t.Setenv(EnvValidation, tc.level)
				valid, err := validatePackageChecksum(paths, 0x12345678, logger)
				if tc.wantErr {
					if err == nil || valid {
						t.Fatalf("expected strict checksum error, got valid=%v err=%v", valid, err)
					}
					return
				}
				if err != nil {
					t.Fatalf("validatePackageChecksum() error = %v", err)
				}
				if valid {
					t.Fatal("expected checksum mismatch to be treated as invalid")
				}
			})
		}
	})

	t.Run("workenv validity", func(t *testing.T) {
		workenvDir := paths.Workenv()
		if err := os.MkdirAll(workenvDir, 0o700); err != nil {
			t.Fatalf("MkdirAll(workenv) error = %v", err)
		}
		index := &PSPFIndex{IndexChecksum: 0x12345678}

		valid, err := checkWorkenvValidity(paths, index, nil, logger)
		if err != nil {
			t.Fatalf("checkWorkenvValidity() missing marker error = %v", err)
		}
		if valid {
			t.Fatal("expected missing completion marker to invalidate workenv")
		}

		if err := os.MkdirAll(filepath.Dir(paths.CompleteFile()), 0o700); err != nil {
			t.Fatalf("MkdirAll(complete dir) error = %v", err)
		}
		if err := os.WriteFile(paths.CompleteFile(), []byte("done"), 0o600); err != nil {
			t.Fatalf("WriteFile(complete) error = %v", err)
		}
		if err := os.WriteFile(paths.ChecksumFile(), []byte(strings.TrimSpace("12345678")), 0o600); err != nil {
			t.Fatalf("WriteFile(checksum) error = %v", err)
		}
		if err := os.WriteFile(filepath.Join(workenvDir, "payload.txt"), []byte("payload"), 0o600); err != nil {
			t.Fatalf("WriteFile(workenv payload) error = %v", err)
		}

		valid, err = checkWorkenvValidity(paths, index, nil, logger)
		if err != nil {
			t.Fatalf("checkWorkenvValidity() valid error = %v", err)
		}
		if !valid {
			t.Fatal("expected complete workenv to be valid")
		}
	})
}
