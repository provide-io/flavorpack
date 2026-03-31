package format_2025

import "testing"

func TestGetLauncherPath(t *testing.T) {
	t.Setenv(EnvLauncherBin, "/opt/flavor/bin/launcher")
	if got, want := getLauncherPath("ignored"), "/opt/flavor/bin/launcher"; got != want {
		t.Fatalf("getLauncherPath env override mismatch: got %q want %q", got, want)
	}

	t.Setenv(EnvLauncherBin, "")
	if got := getLauncherPath("ignored"); got != "" {
		t.Fatalf("expected empty launcher path fallback, got %q", got)
	}
}

func TestAlignOffset(t *testing.T) {
	tests := []struct {
		name      string
		offset    int64
		alignment int64
		want      int64
	}{
		{name: "already aligned", offset: 16, alignment: 8, want: 16},
		{name: "rounds up", offset: 17, alignment: 8, want: 24},
		{name: "small alignment", offset: 3, alignment: 1, want: 3},
		{name: "zero offset", offset: 0, alignment: 8, want: 0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := AlignOffset(tt.offset, tt.alignment); got != tt.want {
				t.Fatalf("AlignOffset(%d, %d) = %d, want %d", tt.offset, tt.alignment, got, tt.want)
			}
		})
	}
}
