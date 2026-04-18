// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"math"
	"os"
	"path/filepath"
	"testing"
)

func TestExecutionHelperConversions(t *testing.T) {
	t.Run("build timestamp conversion", func(t *testing.T) {
		got, err := buildTimestampToInt64(12345)
		if err != nil {
			t.Fatalf("buildTimestampToInt64() error = %v", err)
		}
		if got != 12345 {
			t.Fatalf("buildTimestampToInt64() = %d, want %d", got, 12345)
		}

		if _, err := buildTimestampToInt64(math.MaxUint64); err == nil {
			t.Fatal("expected overflow error from buildTimestampToInt64")
		}
	})

	t.Run("mode conversion", func(t *testing.T) {
		cases := []struct {
			name string
			in   float64
			want os.FileMode
		}{
			{name: "zero", in: 0, want: 0},
			{name: "regular mode", in: 0o755, want: 0o755},
			{name: "large mode", in: 0o1777, want: 0o1777},
		}

		for _, tc := range cases {
			tc := tc
			t.Run(tc.name, func(t *testing.T) {
				got, err := modeFromJSONNumber(tc.in)
				if err != nil {
					t.Fatalf("modeFromJSONNumber() error = %v", err)
				}
				if got != tc.want {
					t.Fatalf("modeFromJSONNumber() = %v, want %v", got, tc.want)
				}
			})
		}

		for _, tc := range []float64{math.NaN(), math.Inf(1), -1, 12.5, 4294967296.0} {
			if _, err := modeFromJSONNumber(tc); err == nil {
				t.Fatalf("expected error from modeFromJSONNumber(%v)", tc)
			}
		}
	})

	t.Run("safe join within base", func(t *testing.T) {
		base := filepath.Join(t.TempDir(), "workenv")

		got, err := safeJoinWithinBase(base, "metadata", "info.json")
		if err != nil {
			t.Fatalf("safeJoinWithinBase() error = %v", err)
		}
		want := filepath.Join(base, "metadata", "info.json")
		if got != want {
			t.Fatalf("safeJoinWithinBase() = %q, want %q", got, want)
		}

		if _, err := safeJoinWithinBase(base, "..", "escape"); err == nil {
			t.Fatal("expected escape detection from safeJoinWithinBase")
		}

		// No parts: joined == base, rel == ".", covers the dot-return branch.
		got, err = safeJoinWithinBase(base)
		if err != nil {
			t.Fatalf("safeJoinWithinBase() with no parts error = %v", err)
		}
		if got != filepath.Clean(base) {
			t.Fatalf("safeJoinWithinBase() with no parts = %q, want %q", got, filepath.Clean(base))
		}
	})

	t.Run("resolve workenv target", func(t *testing.T) {
		workenvDir := filepath.Join(t.TempDir(), "workenv", "demo")

		got, err := resolveWorkenvTarget(workenvDir, "{workenv}/bin/tool")
		if err != nil {
			t.Fatalf("resolveWorkenvTarget() error = %v", err)
		}
		want := filepath.Join(workenvDir, "bin", "tool")
		if got != want {
			t.Fatalf("resolveWorkenvTarget() = %q, want %q", got, want)
		}

		got, err = resolveWorkenvTarget(workenvDir, "relative/config.json")
		if err != nil {
			t.Fatalf("resolveWorkenvTarget() relative error = %v", err)
		}
		want = filepath.Join(workenvDir, "relative", "config.json")
		if got != want {
			t.Fatalf("resolveWorkenvTarget() relative = %q, want %q", got, want)
		}

		if _, err := resolveWorkenvTarget(workenvDir, "../escape"); err == nil {
			t.Fatal("expected escape detection from resolveWorkenvTarget")
		}
	})
}
