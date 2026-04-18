// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"strings"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

func TestProcessRuntimeEnvWindowsAddsPassListToExisting(t *testing.T) {
	old := currentGOOS
	currentGOOS = "windows"
	t.Cleanup(func() { currentGOOS = old })

	logger := logging.NewNullLogger()
	env := []string{"EXISTING_VAR=value", "SYSTEMROOT=C:\\Windows", "WINDIR=C:\\Windows"}
	runtimeEnv := map[string]interface{}{
		"pass": []interface{}{"EXISTING_VAR"},
	}

	result := processRuntimeEnv(env, runtimeEnv, logger)

	// The Windows block should have appended the critical vars to the existing pass list.
	// With no unset rules, all env vars are preserved; SYSTEMROOT should appear in result.
	found := false
	for _, entry := range result {
		if strings.HasPrefix(entry, "SYSTEMROOT=") {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("expected SYSTEMROOT in result after Windows pass-list expansion, got: %v", result)
	}

	// EXISTING_VAR should still be present too.
	foundExisting := false
	for _, entry := range result {
		if strings.HasPrefix(entry, "EXISTING_VAR=") {
			foundExisting = true
			break
		}
	}
	if !foundExisting {
		t.Fatalf("expected EXISTING_VAR in result, got: %v", result)
	}

	// Verify the pass list was mutated to include the critical vars.
	passList, ok := runtimeEnv["pass"].([]interface{})
	if !ok {
		t.Fatal("expected runtimeEnv[\"pass\"] to be []interface{}")
	}
	patterns := make(map[string]bool)
	for _, p := range passList {
		if s, ok := p.(string); ok {
			patterns[s] = true
		}
	}
	for _, criticalVar := range []string{"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATHEXT", "COMSPEC"} {
		if !patterns[criticalVar] {
			t.Errorf("expected critical var %q in pass list after Windows expansion, list: %v", criticalVar, passList)
		}
	}
}

func TestProcessRuntimeEnvWindowsCreatesPassList(t *testing.T) {
	old := currentGOOS
	currentGOOS = "windows"
	t.Cleanup(func() { currentGOOS = old })

	logger := logging.NewNullLogger()
	env := []string{"PATH=C:\\Windows\\system32", "SYSTEMROOT=C:\\Windows"}
	runtimeEnv := map[string]interface{}{} // no pass list

	result := processRuntimeEnv(env, runtimeEnv, logger)

	// The Windows block should have created a pass list with critical vars.
	passList, ok := runtimeEnv["pass"].([]interface{})
	if !ok {
		t.Fatal("expected runtimeEnv[\"pass\"] to be created as []interface{}")
	}
	if len(passList) == 0 {
		t.Fatal("expected non-empty pass list after Windows critical var injection")
	}

	patterns := make(map[string]bool)
	for _, p := range passList {
		if s, ok := p.(string); ok {
			patterns[s] = true
		}
	}
	for _, criticalVar := range []string{"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATHEXT", "COMSPEC"} {
		if !patterns[criticalVar] {
			t.Errorf("expected critical var %q in newly-created pass list, list: %v", criticalVar, passList)
		}
	}

	// With no unset rules, SYSTEMROOT should be in the result.
	found := false
	for _, entry := range result {
		if strings.HasPrefix(entry, "SYSTEMROOT=") {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("expected SYSTEMROOT in result, got: %v", result)
	}
}
