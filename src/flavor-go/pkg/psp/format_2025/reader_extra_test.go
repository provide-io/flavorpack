//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"testing"
)

// TestReadMetadataArchiveReadIndexFails covers the ReadIndex error path (line 193-195)
// in ReadMetadataArchive by using a non-existent bundle.
func TestReadMetadataArchiveReadIndexFails(t *testing.T) {
	t.Parallel()

	reader, err := NewReader("/nonexistent/bundle-rma.pspf")
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadMetadataArchive()
	if err == nil {
		t.Fatal("expected error when ReadIndex fails in ReadMetadataArchive, got nil")
	}
}
