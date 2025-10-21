package shellparse

import (
	"errors"
	"testing"
)

func TestSplit_Basic(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected []string
	}{
		{
			name:     "empty string",
			input:    "",
			expected: []string{},
		},
		{
			name:     "single word",
			input:    "command",
			expected: []string{"command"},
		},
		{
			name:     "two words",
			input:    "cmd arg",
			expected: []string{"cmd", "arg"},
		},
		{
			name:     "multiple words",
			input:    "cmd arg1 arg2 arg3",
			expected: []string{"cmd", "arg1", "arg2", "arg3"},
		},
		{
			name:     "leading spaces",
			input:    "  cmd arg",
			expected: []string{"cmd", "arg"},
		},
		{
			name:     "trailing spaces",
			input:    "cmd arg  ",
			expected: []string{"cmd", "arg"},
		},
		{
			name:     "multiple spaces between words",
			input:    "cmd   arg1    arg2",
			expected: []string{"cmd", "arg1", "arg2"},
		},
		{
			name:     "tabs and spaces",
			input:    "cmd\targ1\t  arg2",
			expected: []string{"cmd", "arg1", "arg2"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := Split(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !slicesEqual(result, tt.expected) {
				t.Errorf("Split(%q) = %v, want %v", tt.input, result, tt.expected)
			}
		})
	}
}

func TestSplit_DoubleQuotes(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected []string
	}{
		{
			name:     "simple double quotes",
			input:    `cmd "arg with spaces"`,
			expected: []string{"cmd", "arg with spaces"},
		},
		{
			name:     "double quotes at start",
			input:    `"cmd with spaces" arg`,
			expected: []string{"cmd with spaces", "arg"},
		},
		{
			name:     "multiple double quoted args",
			input:    `"arg1" "arg2" "arg3"`,
			expected: []string{"arg1", "arg2", "arg3"},
		},
		{
			name:     "double quotes with tabs",
			input:    `cmd "arg	with	tabs"`,
			expected: []string{"cmd", "arg	with	tabs"},
		},
		{
			name:     "empty double quotes",
			input:    `cmd ""`,
			expected: []string{"cmd", ""},
		},
		{
			name:     "double quotes adjacent to word",
			input:    `prefix"quoted"suffix`,
			expected: []string{"prefixquotedsuffix"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := Split(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !slicesEqual(result, tt.expected) {
				t.Errorf("Split(%q) = %v, want %v", tt.input, result, tt.expected)
			}
		})
	}
}

func TestSplit_SingleQuotes(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected []string
	}{
		{
			name:     "simple single quotes",
			input:    `cmd 'arg with spaces'`,
			expected: []string{"cmd", "arg with spaces"},
		},
		{
			name:     "single quotes at start",
			input:    `'cmd with spaces' arg`,
			expected: []string{"cmd with spaces", "arg"},
		},
		{
			name:     "single quotes preserve backslashes",
			input:    `cmd 'arg\with\backslashes'`,
			expected: []string{"cmd", `arg\with\backslashes`},
		},
		{
			name:     "empty single quotes",
			input:    `cmd ''`,
			expected: []string{"cmd", ""},
		},
		{
			name:     "single quotes adjacent to word",
			input:    `prefix'quoted'suffix`,
			expected: []string{"prefixquotedsuffix"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := Split(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !slicesEqual(result, tt.expected) {
				t.Errorf("Split(%q) = %v, want %v", tt.input, result, tt.expected)
			}
		})
	}
}

func TestSplit_Escapes(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected []string
	}{
		{
			name:     "escape space",
			input:    `cmd arg\ with\ spaces`,
			expected: []string{"cmd", "arg with spaces"},
		},
		{
			name:     "escape quote",
			input:    `cmd arg\"quoted`,
			expected: []string{"cmd", `arg"quoted`},
		},
		{
			name:     "escape backslash",
			input:    `cmd arg\\backslash`,
			expected: []string{"cmd", `arg\backslash`},
		},
		{
			name:     "escape in double quotes",
			input:    `cmd "arg \"quoted\""`,
			expected: []string{"cmd", `arg "quoted"`},
		},
		{
			name:     "escape backslash in double quotes",
			input:    `cmd "arg\\backslash"`,
			expected: []string{"cmd", `arg\backslash`},
		},
		{
			name:     "non-special escape in double quotes",
			input:    `cmd "arg\n"`,
			expected: []string{"cmd", `arg\n`},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := Split(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !slicesEqual(result, tt.expected) {
				t.Errorf("Split(%q) = %v, want %v", tt.input, result, tt.expected)
			}
		})
	}
}

func TestSplit_Mixed(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected []string
	}{
		{
			name:     "single and double quotes",
			input:    `cmd "arg1" 'arg2' arg3`,
			expected: []string{"cmd", "arg1", "arg2", "arg3"},
		},
		{
			name:     "quotes and escapes",
			input:    `cmd "arg 1" arg\ 2 'arg 3'`,
			expected: []string{"cmd", "arg 1", "arg 2", "arg 3"},
		},
		{
			name:     "nested quotes",
			input:    `python -c "print('hello')"`,
			expected: []string{"python", "-c", "print('hello')"},
		},
		{
			name:     "complex command",
			input:    `npm install --save-dev "@babel/core"`,
			expected: []string{"npm", "install", "--save-dev", "@babel/core"},
		},
		{
			name:     "path with spaces",
			input:    `"/Program Files/app.exe" --option value`,
			expected: []string{"/Program Files/app.exe", "--option", "value"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := Split(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !slicesEqual(result, tt.expected) {
				t.Errorf("Split(%q) = %v, want %v", tt.input, result, tt.expected)
			}
		})
	}
}

func TestSplit_RealWorld(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected []string
	}{
		{
			name:     "python one-liner",
			input:    `python -c "import sys; print(sys.version)"`,
			expected: []string{"python", "-c", "import sys; print(sys.version)"},
		},
		{
			name:     "grep with pattern",
			input:    `grep -E "pattern|other" file.txt`,
			expected: []string{"grep", "-E", "pattern|other", "file.txt"},
		},
		{
			name:     "echo with quotes",
			input:    `echo "test string with spaces"`,
			expected: []string{"echo", "test string with spaces"},
		},
		{
			name:     "node script",
			input:    `node -e 'console.log("hello")'`,
			expected: []string{"node", "-e", `console.log("hello")`},
		},
		{
			name:     "docker command",
			input:    `docker run --name "my container" ubuntu:latest`,
			expected: []string{"docker", "run", "--name", "my container", "ubuntu:latest"},
		},
		{
			name:     "git command",
			input:    `git commit -m "feat: add new feature"`,
			expected: []string{"git", "commit", "-m", "feat: add new feature"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := Split(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !slicesEqual(result, tt.expected) {
				t.Errorf("Split(%q) = %v, want %v", tt.input, result, tt.expected)
			}
		})
	}
}

func TestSplit_Errors(t *testing.T) {
	tests := []struct {
		name        string
		input       string
		expectError error
	}{
		{
			name:        "unclosed double quote",
			input:       `cmd "arg`,
			expectError: ErrUnclosedQuote,
		},
		{
			name:        "unclosed single quote",
			input:       `cmd 'arg`,
			expectError: ErrUnclosedQuote,
		},
		{
			name:        "trailing escape",
			input:       `cmd arg\`,
			expectError: ErrTrailingEscape,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := Split(tt.input)
			if err == nil {
				t.Fatalf("expected error containing %v, got nil", tt.expectError)
			}
			// Check if the error is or wraps the expected error
			if !errors.Is(err, tt.expectError) {
				t.Errorf("expected error %v, got %v", tt.expectError, err)
			}
		})
	}
}

func TestMustSplit(t *testing.T) {
	// Test successful case
	result := MustSplit("cmd arg1 arg2")
	expected := []string{"cmd", "arg1", "arg2"}
	if !slicesEqual(result, expected) {
		t.Errorf("MustSplit() = %v, want %v", result, expected)
	}

	// Test panic case
	defer func() {
		if r := recover(); r == nil {
			t.Error("MustSplit should panic on error")
		}
	}()
	MustSplit(`cmd "unclosed`)
}

func TestJoin(t *testing.T) {
	tests := []struct {
		name     string
		input    []string
		expected string
	}{
		{
			name:     "empty slice",
			input:    []string{},
			expected: "",
		},
		{
			name:     "simple args",
			input:    []string{"cmd", "arg1", "arg2"},
			expected: "cmd arg1 arg2",
		},
		{
			name:     "arg with spaces",
			input:    []string{"cmd", "arg with spaces"},
			expected: `cmd 'arg with spaces'`,
		},
		{
			name:     "arg with single quote",
			input:    []string{"cmd", "arg's value"},
			expected: `cmd "arg's value"`,
		},
		{
			name:     "empty arg",
			input:    []string{"cmd", ""},
			expected: "cmd ''",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := Join(tt.input)
			if result != tt.expected {
				t.Errorf("Join(%v) = %q, want %q", tt.input, result, tt.expected)
			}
		})
	}
}

func TestRoundTrip(t *testing.T) {
	// Test that Split and Join are compatible
	tests := []struct {
		name string
		args []string
	}{
		{
			name: "simple args",
			args: []string{"cmd", "arg1", "arg2"},
		},
		{
			name: "args with spaces",
			args: []string{"cmd", "arg with spaces", "another arg"},
		},
		{
			name: "complex args",
			args: []string{"python", "-c", "print('hello world')"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			joined := Join(tt.args)
			split, err := Split(joined)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !slicesEqual(split, tt.args) {
				t.Errorf("roundtrip failed: %v -> %q -> %v", tt.args, joined, split)
			}
		})
	}
}

// Helper functions

func slicesEqual(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
