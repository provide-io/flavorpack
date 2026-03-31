package format_2025

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDetectLauncherType(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	cases := []struct {
		name    string
		content []byte
		want    string
	}{
		{name: "go", content: []byte("go.buildid\x00runtime.main"), want: "go"},
		{name: "rust", content: []byte("rust_panic and _ZN"), want: "rust"},
		{name: "python", content: []byte("#!/usr/bin/env python3\n"), want: "python"},
		{name: "node", content: []byte("#!/usr/bin/env node\n"), want: "node"},
		{name: "unknown", content: []byte("plain bytes"), want: "unknown"},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			path := filepath.Join(dir, tc.name+".bin")
			if err := os.WriteFile(path, tc.content, 0o600); err != nil {
				t.Fatalf("WriteFile() error = %v", err)
			}

			if got := detectLauncherType(path); got != tc.want {
				t.Fatalf("detectLauncherType() = %q, want %q", got, tc.want)
			}
		})
	}
}
