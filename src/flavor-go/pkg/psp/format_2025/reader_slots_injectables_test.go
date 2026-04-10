package format_2025

import (
	"archive/tar"
	"bytes"
	"errors"
	"io"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// buildMinimalTarArchive creates a minimal tar archive containing a single regular file.
func buildMinimalTarArchive(t *testing.T, name string, content []byte) []byte {
	t.Helper()
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	hdr := &tar.Header{
		Typeflag: tar.TypeReg,
		Name:     name,
		Size:     int64(len(content)),
		Mode:     0o644,
	}
	if err := tw.WriteHeader(hdr); err != nil {
		t.Fatalf("tar.WriteHeader() error = %v", err)
	}
	if _, err := tw.Write(content); err != nil {
		t.Fatalf("tar.Write() error = %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("tar.Close() error = %v", err)
	}
	return buf.Bytes()
}

// TestReadSlotSeekFails covers reader_slots.go:37-39
// (file.Seek for slot table entry fails → error returned from ReadSlot).
func TestReadSlotSeekFails(t *testing.T) {

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	old := fileSeekFn
	t.Cleanup(func() { fileSeekFn = old })
	fileSeekFn = func(_ *os.File, _ int64, _ int) (int64, error) {
		return 0, errors.New("injected seek failure")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error from ReadSlot when file.Seek fails")
	}
}

// TestReadSlotReadDescriptorFails covers reader_slots.go:45-47
// (file.Read for slot descriptor fails → error returned from ReadSlot).
func TestReadSlotReadDescriptorFails(t *testing.T) {

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	callCount := 0
	old := fileSeekFn
	t.Cleanup(func() { fileSeekFn = old })
	// Let seek succeed so we get to the Read call
	fileSeekFn = func(f *os.File, offset int64, whence int) (int64, error) {
		return f.Seek(offset, whence)
	}

	oldRead := fileReadFn
	t.Cleanup(func() { fileReadFn = oldRead })
	fileReadFn = func(f *os.File, buf []byte) (int, error) {
		callCount++
		return 0, errors.New("injected read failure")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error from ReadSlot when file.Read (descriptor) fails")
	}
}

// TestReadSlotSeekToDataFails covers reader_slots.go:51-53
// (second Seek — to slot data offset — fails → error returned from ReadSlot).
func TestReadSlotSeekToDataFails(t *testing.T) {

	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	seekCallCount := 0
	old := fileSeekFn
	t.Cleanup(func() { fileSeekFn = old })
	// Allow the first seek (slot table entry), fail the second (slot data offset)
	fileSeekFn = func(f *os.File, offset int64, whence int) (int64, error) {
		seekCallCount++
		if seekCallCount == 1 {
			return f.Seek(offset, whence) // first seek succeeds
		}
		return 0, errors.New("injected seek-to-data failure")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error from ReadSlot when second file.Seek (data) fails")
	}
}

// TestReadSlotReadDataFails covers reader_slots.go:77-79
// (second file.Read — for slot data — fails → error returned from ReadSlot).
func TestReadSlotReadDataFails(t *testing.T) {
	bundle := buildSingleSlotBundleForTests(t, []byte("data"), []byte("data"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	readCallCount := 0
	old := fileReadFn
	t.Cleanup(func() { fileReadFn = old })
	// Allow the first read (64-byte slot descriptor), fail the second (slot data)
	fileReadFn = func(f *os.File, buf []byte) (int, error) {
		readCallCount++
		if readCallCount == 1 {
			return f.Read(buf) // first read (descriptor) succeeds
		}
		return 0, errors.New("injected read failure for slot data")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error from ReadSlot when slot data read fails")
	}
}

// TestExtractSlotPermissionsSeekFails covers reader_slots.go:197-199
// (fileSeekFn fails for the permissions read in ExtractSlot → error returned).
// ReadSlot is allowed to succeed; we fail only the subsequent seek for permissions.
func TestExtractSlotPermissionsSeekFails(t *testing.T) {
	bundle := buildSingleSlotBundleForTests(t, []byte("hello world"), []byte("hello world"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	// ReadSlot uses fileSeekFn twice (slot table seek + slot data seek).
	// After ReadSlot succeeds, ExtractSlot does one more fileSeekFn call (permissions seek).
	// We count calls and fail on the 3rd seek.
	seekCallCount := 0
	old := fileSeekFn
	t.Cleanup(func() { fileSeekFn = old })
	fileSeekFn = func(f *os.File, offset int64, whence int) (int64, error) {
		seekCallCount++
		if seekCallCount <= 2 {
			return f.Seek(offset, whence) // first 2 seeks (from ReadSlot) succeed
		}
		return 0, errors.New("injected seek failure for permissions read in ExtractSlot")
	}

	_, err := reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when permissions seek fails")
	}
}

// TestExtractSlotPermissionsReadFails covers reader_slots.go:202-204
// (fileReadFn fails for the permissions read in ExtractSlot → error returned).
func TestExtractSlotPermissionsReadFails(t *testing.T) {
	bundle := buildSingleSlotBundleForTests(t, []byte("hello world"), []byte("hello world"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	// ReadSlot uses fileReadFn twice (descriptor + slot data).
	// After ReadSlot succeeds, ExtractSlot does one more fileReadFn call (permissions read).
	// We count calls and fail on the 3rd read.
	readCallCount := 0
	old := fileReadFn
	t.Cleanup(func() { fileReadFn = old })
	fileReadFn = func(f *os.File, buf []byte) (int, error) {
		readCallCount++
		if readCallCount <= 2 {
			return f.Read(buf) // first 2 reads (from ReadSlot) succeed
		}
		return 0, errors.New("injected read failure for permissions in ExtractSlot")
	}

	_, err := reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when permissions read fails")
	}
}

// TestExtractSlotReadDescriptorFails covers reader_slots.go:176-178
// (file.Read for slot descriptor in ExtractSlot fails → error returned).
func TestExtractSlotReadDescriptorFails(t *testing.T) {

	bundle := buildSingleSlotBundleForTests(t, []byte("hello world"), []byte("hello world"), nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	// Warm the index cache
	_, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}

	// Allow seek but fail the read (for descriptor in ExtractSlot permissions read)
	old := fileReadFn
	t.Cleanup(func() { fileReadFn = oldFileReadFn() })
	_ = old
	fileReadFn = func(_ *os.File, _ []byte) (int, error) {
		return 0, errors.New("injected read failure in ExtractSlot descriptor")
	}

	_, err = reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when fileReadFn fails (descriptor)")
	}
}

// oldFileReadFn returns the original fileReadFn for cleanup.
func oldFileReadFn() func(*os.File, []byte) (int, error) {
	return func(f *os.File, buf []byte) (int, error) {
		return f.Read(buf)
	}
}

// TestTarExtractionMkdirAllFails covers reader_slots.go:260-262
// (MkdirAll for parent directory fails during tar extraction → error returned).
func TestTarExtractionMkdirAllFails(t *testing.T) {

	// We need a bundle with a tar slot so the tar extraction path is taken.
	// Build a tar archive containing a regular file.
	tarData := buildMinimalTarArchive(t, "subdir/file.txt", []byte("content"))

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	old := tarMkdirAllFn
	t.Cleanup(func() { tarMkdirAllFn = old })
	tarMkdirAllFn = func(_ string, _ os.FileMode) error {
		return errors.New("injected MkdirAll failure during tar extraction")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when tarMkdirAllFn fails")
	}
}

// TestTarExtractionIoCopyFails covers reader_slots.go:269-274
// (io.Copy fails during tar extraction → error returned).
func TestTarExtractionIoCopyFails(t *testing.T) {

	tarData := buildMinimalTarArchive(t, "file.txt", []byte("content"))
	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	old := tarIoCopyFn
	t.Cleanup(func() { tarIoCopyFn = old })
	tarIoCopyFn = func(_ io.Writer, _ io.Reader) (int64, error) {
		return 0, errors.New("injected io.Copy failure during tar extraction")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when tarIoCopyFn fails")
	}
}

// TestTarExtractionIoCopyFailsWithCloseError covers reader_slots.go:283-286
// (io.Copy fails AND out.Close also fails → closeErr path is exercised, original error returned).
func TestTarExtractionIoCopyFailsWithCloseError(t *testing.T) {

	tarData := buildMinimalTarArchive(t, "file.txt", []byte("content"))
	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	oldCopy := tarIoCopyFn
	t.Cleanup(func() { tarIoCopyFn = oldCopy })
	tarIoCopyFn = func(_ io.Writer, _ io.Reader) (int64, error) {
		return 0, errors.New("injected io.Copy failure")
	}

	oldClose := tarOutCloseFn
	t.Cleanup(func() { tarOutCloseFn = oldClose })
	tarOutCloseFn = func(f *os.File) error {
		_ = f.Close() // close for real to avoid FD leak
		return errors.New("injected out.Close failure (secondary)")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when both tarIoCopyFn and tarOutCloseFn fail")
	}
	// The returned error should be the io.Copy error, not the close error.
	if err.Error() != "injected io.Copy failure" {
		t.Fatalf("expected io.Copy error to be returned, got: %v", err)
	}
}

// TestTarExtractionOutCloseFails covers reader_slots.go:289-291
// (out.Close fails during tar extraction → error returned).
func TestTarExtractionOutCloseFails(t *testing.T) {

	tarData := buildMinimalTarArchive(t, "file.txt", []byte("content"))
	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	old := tarOutCloseFn
	t.Cleanup(func() { tarOutCloseFn = old })
	tarOutCloseFn = func(f *os.File) error {
		_ = f.Close() // close for real to avoid FD leak
		return errors.New("injected out.Close failure during tar extraction")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	_, err := reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when tarOutCloseFn fails")
	}
}

// TestTarExtractionChmodFails covers reader_slots.go:295-298
// (best-effort Chmod on executable tar entry fails → error is silently ignored, extraction succeeds).
func TestTarExtractionChmodFails(t *testing.T) {

	// Build a tar archive with an executable file (mode 0o755) so the chmod path is taken.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	hdr := &tar.Header{
		Typeflag: tar.TypeReg,
		Name:     "script.sh",
		Size:     int64(len("#!/bin/sh\n")),
		Mode:     0o755, // executable
	}
	if err := tw.WriteHeader(hdr); err != nil {
		t.Fatalf("tar.WriteHeader() error = %v", err)
	}
	if _, err := tw.Write([]byte("#!/bin/sh\n")); err != nil {
		t.Fatalf("tar.Write() error = %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("tar.Close() error = %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, nil, SlotMetadata{
		ID:     "slot",
		Target: "{workenv}",
	}, 0, false)

	old := tarChmodFn
	t.Cleanup(func() { tarChmodFn = old })
	tarChmodFn = func(_ string, _ os.FileMode) error {
		return errors.New("injected Chmod failure (best-effort, should be ignored)")
	}

	reader, _ := NewReaderWithLogger(bundle, logging.NewNullLogger())
	defer func() { _ = reader.Close() }()

	// Extraction should succeed despite Chmod failure (best-effort, error is silenced).
	_, err := reader.ExtractSlot(0, t.TempDir())
	if err != nil {
		t.Fatalf("expected ExtractSlot to succeed despite Chmod failure, got: %v", err)
	}
}
