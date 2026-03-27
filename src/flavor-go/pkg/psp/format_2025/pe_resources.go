// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build windows
// +build windows

package format_2025

import (
	"fmt"
	"os"

	"github.com/tc-hib/winres"
	"log/slog"
)

const (
	// PSPF_RESOURCE_TYPE is the resource type for PSPF data (RT_RCDATA = custom data)
	PSPF_RESOURCE_TYPE = winres.RT_RCDATA

	// PSPF_RESOURCE_NAME is the name identifier for the PSPF resource
	PSPF_RESOURCE_NAME = "PSPF"

	// PSPF_RESOURCE_LANG is the language ID (0x0409 = en-US)
	PSPF_RESOURCE_LANG = 0x0409
)

// EmbedPSPFAsResource embeds PSPF data into a Windows PE executable as a resource.
// This allows the data to be part of the PE structure instead of appended to the file.
//
// This approach is used instead of appending data because Go Windows executables
// are sensitive to modifications and Windows may reject binaries with appended data.
//
// Parameters:
//
//	exePath: Path to the PE executable
//	pspfData: Complete PSPF data (metadata + slots + trailer)
//	logger: Logger for diagnostic output
//
// Returns error if embedding fails
func EmbedPSPFAsResource(exePath string, pspfData []byte, logger *slog.Logger) error {
	logger.Info("Embedding PSPF data as PE resource",
		"exe", exePath,
		"pspf_size", len(pspfData),
		"resource_type", PSPF_RESOURCE_TYPE,
		"resource_name", PSPF_RESOURCE_NAME)

	// Open the EXE file for reading
	inputFile, err := os.Open(exePath)
	if err != nil {
		return fmt.Errorf("failed to open EXE for reading: %w", err)
	}
	// Note: Explicit close below, no defer needed

	// Load existing resources from the EXE
	rs, err := winres.LoadFromEXE(inputFile)
	if err != nil {
		// If file has no resources, create new ResourceSet
		logger.Debug("Creating new resource set (no existing resources)")
		rs = &winres.ResourceSet{}
	} else {
		logger.Debug("Loaded existing resources from EXE")
	}

	// Close input file as we're done reading (explicit close, no defer)
	if err := inputFile.Close(); err != nil {
		return fmt.Errorf("failed to close input file: %w", err)
	}

	// Add PSPF data as a custom resource (RT_RCDATA)
	logger.Debug("Setting PSPF resource data",
		"type", PSPF_RESOURCE_TYPE,
		"name", PSPF_RESOURCE_NAME,
		"lang", fmt.Sprintf("0x%04x", PSPF_RESOURCE_LANG),
		"size", len(pspfData))

	err = rs.Set(
		PSPF_RESOURCE_TYPE,
		winres.Name(PSPF_RESOURCE_NAME),
		PSPF_RESOURCE_LANG,
		pspfData,
	)
	if err != nil {
		return fmt.Errorf("failed to set PSPF resource: %w", err)
	}

	// Open the EXE for reading and writing resources
	// CRITICAL: No defer - must close explicitly before os.Remove() due to Windows file locking
	inputFile2, err := os.Open(exePath)
	if err != nil {
		return fmt.Errorf("failed to open EXE for reading (2nd pass): %w", err)
	}

	outputFile, err := os.Create(exePath + ".tmp")
	if err != nil {
		inputFile2.Close()
		return fmt.Errorf("failed to create temporary output file: %w", err)
	}

	// Write resources to temporary file
	logger.Debug("Writing resources to temporary file")
	if err := rs.WriteToEXE(outputFile, inputFile2); err != nil {
		outputFile.Close()
		inputFile2.Close()
		os.Remove(exePath + ".tmp")
		return fmt.Errorf("failed to write resources to EXE: %w", err)
	}

	// Close files explicitly (MUST happen before os.Remove on Windows)
	if err := outputFile.Close(); err != nil {
		inputFile2.Close()
		os.Remove(exePath + ".tmp")
		return fmt.Errorf("failed to close output file: %w", err)
	}

	if err := inputFile2.Close(); err != nil {
		os.Remove(exePath + ".tmp")
		return fmt.Errorf("failed to close input file: %w", err)
	}

	logger.Debug("Files closed, attempting atomic file replacement")

	// Use atomicReplace to safely replace the original file
	// This handles Windows file locking with retry logic
	if err := atomicReplace(exePath+".tmp", exePath, logger); err != nil {
		os.Remove(exePath + ".tmp")
		return fmt.Errorf("failed to replace EXE atomically: %w", err)
	}

	logger.Info("✅ Successfully embedded PSPF as PE resource",
		"exe", exePath,
		"pspf_size", len(pspfData))

	return nil
}

// ReadPSPFFromResource reads PSPF data from a Windows PE executable's resource section.
//
// This is used by the launcher to read embedded PSPF data instead of reading
// from the end of the file.
//
// Uses the winres library (pure-Go PE parser) to avoid any unsafe.Pointer conversions
// that would be required by the Windows LoadLibraryEx/LockResource API path.
//
// Parameters:
//
//	exePath: Path to the PE executable (usually os.Args[0])
//	logger: Logger for diagnostic output
//
// Returns the PSPF data or an error
func ReadPSPFFromResource(exePath string, logger *slog.Logger) ([]byte, error) {
	logger.Debug("Reading PSPF from PE resources", "exe", exePath)

	f, err := os.Open(exePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open EXE for resource read: %w", err)
	}
	defer f.Close()

	logger.Debug("Loaded EXE as data file", "handle", handle)

	// Find the PSPF resource by name (string) and type (ResourceID)
	resInfo, err := windows.FindResource(
		handle,
		PSPF_RESOURCE_NAME,
		windows.RT_RCDATA,
	)
	if err != nil {
		return nil, fmt.Errorf("PSPF resource not found in PE (type=%d, name=%s): %w",
			PSPF_RESOURCE_TYPE, PSPF_RESOURCE_NAME, err)
	}

	// Get returns nil when the resource does not exist.
	data := rs.Get(PSPF_RESOURCE_TYPE, winres.Name(PSPF_RESOURCE_NAME), PSPF_RESOURCE_LANG)
	if data == nil {
		return nil, fmt.Errorf("PSPF resource not found (type=%d, name=%s)", PSPF_RESOURCE_TYPE, PSPF_RESOURCE_NAME)
	}

	logger.Info("✅ Successfully read PSPF from PE resources",
		"exe", exePath,
		"pspf_size", len(data))

	return data, nil
}

// HasPSPFResource checks if a PE executable has the PSPF resource embedded.
// This is used to determine if we should read from resources or from EOF.
func HasPSPFResource(exePath string, logger *slog.Logger) bool {
	// Try to read the resource - if it exists, return true
	_, err := ReadPSPFFromResource(exePath, logger)
	return err == nil
}
