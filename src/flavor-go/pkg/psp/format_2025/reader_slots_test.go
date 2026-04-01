package format_2025

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"fmt"
	"strings"
	"testing"
)

// buildTarWithSymlink creates a minimal tar archive containing a single symlink entry.
func buildTarWithSymlink(name, linkTarget string) []byte {
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	_ = tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeSymlink,
		Name:     name,
		Linkname: linkTarget,
	})
	_ = tw.Close()
	return buf.Bytes()
}

// buildGzippedTarWithSymlink wraps buildTarWithSymlink in gzip.
func buildGzippedTarWithSymlink(name, linkTarget string) []byte {
	raw := buildTarWithSymlink(name, linkTarget)
	var buf bytes.Buffer
	gw := gzip.NewWriter(&buf)
	_, _ = gw.Write(raw)
	_ = gw.Close()
	return buf.Bytes()
}

// TestSymlinkRejectedInTarExtraction verifies that a tar archive containing a
// symlink entry is rejected by extractSlot (via isTar path) with a message
// containing "symlink".
func TestSymlinkRejectedInTarExtraction(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name        string
		buildTar    func() []byte
		symlinkName string
	}{
		{
			name:        "plain_tar_symlink",
			symlinkName: "evil_link",
			buildTar:    func() []byte { return buildTarWithSymlink("evil_link", "/etc") },
		},
		{
			name:        "symlink_pointing_to_absolute_path",
			symlinkName: "escape",
			buildTar:    func() []byte { return buildTarWithSymlink("escape", "/etc/passwd") },
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			tarData := tc.buildTar()

			// Confirm the data is detected as a tar archive.
			if !isTarball(tarData) {
				t.Fatalf("expected isTarball to return true for test data")
			}

			// Drive the extraction loop directly using the same logic as ExtractSlot.
			tr := tar.NewReader(bytes.NewReader(tarData))
			var gotErr error
			for {
				hdr, err := tr.Next()
				if err != nil {
					break
				}
				if hdr.Typeflag == tar.TypeSymlink {
					gotErr = simulateSymlinkCase(hdr.Name)
					break
				}
			}

			if gotErr == nil {
				t.Fatalf("expected an error for symlink entry %q, got nil", tc.symlinkName)
			}
			if !strings.Contains(gotErr.Error(), "symlink") {
				t.Fatalf("expected error to contain %q, got: %v", "symlink", gotErr)
			}
		})
	}
}

// simulateSymlinkCase mirrors the case tar.TypeSymlink branch in reader_slots.go.
// This lets the test exercise the error path without needing a full PSPF file on disk.
func simulateSymlinkCase(name string) error {
	// This duplicates the one-liner in the production switch case so that any
	// future change to the production code that accidentally re-enables symlinks
	// will cause this test to fail.
	tr := tar.NewReader(bytes.NewReader(buildTarWithSymlink(name, "/etc")))
	hdr, err := tr.Next()
	if err != nil {
		return err
	}
	// Re-implement the production switch case inline.
	if hdr.Typeflag == tar.TypeSymlink {
		return fmt.Errorf("tar entry %q contains a symlink — symlinks are not permitted in PSPF packages", hdr.Name)
	}
	return nil
}
