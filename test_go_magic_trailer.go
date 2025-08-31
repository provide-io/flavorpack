package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"log"
	"os"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

func main() {
	// Test reading a PSPF file with MagicTrailer
	if len(os.Args) < 2 {
		// Create a test file first
		testFile := "/tmp/test_go.psp"
		if err := createTestPackage(testFile); err != nil {
			log.Fatalf("Failed to create test package: %v", err)
		}
		fmt.Printf("✅ Created test package: %s\n", testFile)
		
		// Now test reading it
		if err := testReadPackage(testFile); err != nil {
			log.Fatalf("Failed to read package: %v", err)
		}
		fmt.Println("🎉 All tests passed!")
	} else {
		// Read specified file
		if err := testReadPackage(os.Args[1]); err != nil {
			log.Fatalf("Failed to read package: %v", err)
		}
	}
}

func createTestPackage(path string) error {
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()

	// Write minimal launcher
	launcher := []byte("#!/bin/sh\necho test\n")
	if _, err := file.Write(launcher); err != nil {
		return err
	}

	// Create index
	index := &format_2025.PSPFIndex{
		FormatVersion: format_2025.PSPFVersion,
		LauncherSize:  uint64(len(launcher)),
		PackageSize:   uint64(len(launcher) + format_2025.MagicTrailerSize),
	}

	// Write MagicTrailer
	if _, err := file.Write(format_2025.PackageEmojiBytes); err != nil {
		return err
	}
	if _, err := file.Write(index.Pack()); err != nil {
		return err
	}
	if _, err := file.Write(format_2025.MagicWandEmojiBytes); err != nil {
		return err
	}

	return nil
}

func testReadPackage(path string) error {
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()

	// Get file size
	info, err := file.Stat()
	if err != nil {
		return err
	}
	fileSize := info.Size()

	// Read MagicTrailer
	if fileSize < int64(format_2025.MagicTrailerSize) {
		return fmt.Errorf("file too small for MagicTrailer")
	}

	// Seek to MagicTrailer
	if _, err := file.Seek(-int64(format_2025.MagicTrailerSize), io.SeekEnd); err != nil {
		return err
	}

	trailer := make([]byte, format_2025.MagicTrailerSize)
	if _, err := file.Read(trailer); err != nil {
		return err
	}

	// Verify structure
	if !bytes.Equal(trailer[:4], format_2025.PackageEmojiBytes) {
		return fmt.Errorf("missing 📦 at start: %x", trailer[:4])
	}
	fmt.Println("✅ Found 📦 at trailer start")

	if !bytes.Equal(trailer[len(trailer)-4:], format_2025.MagicWandEmojiBytes) {
		return fmt.Errorf("missing 🪄 at end: %x", trailer[len(trailer)-4:])
	}
	fmt.Println("✅ Found 🪄 at trailer end")

	// Extract and verify index
	indexData := trailer[4 : 4+format_2025.IndexSize]
	index := &format_2025.PSPFIndex{}
	if err := index.Unpack(indexData); err != nil {
		return err
	}

	if index.FormatVersion != format_2025.PSPFVersion {
		return fmt.Errorf("version mismatch: 0x%08x != 0x%08x", index.FormatVersion, format_2025.PSPFVersion)
	}
	fmt.Printf("✅ Index version correct: 0x%08x\n", index.FormatVersion)

	// Also verify the first 4 bytes are the version
	version := binary.LittleEndian.Uint32(indexData[:4])
	if version != format_2025.PSPFVersion {
		return fmt.Errorf("first 4 bytes not version: 0x%08x", version)
	}
	fmt.Println("✅ Index starts with version field")

	return nil
}