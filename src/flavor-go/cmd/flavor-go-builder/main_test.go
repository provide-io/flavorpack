package main

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

func TestBuilderMainVersionFlag(t *testing.T) {
	t.Parallel()

	cmd := exec.Command(os.Args[0], "-test.run=TestBuilderMainHelperProcess", "--", "--version")
	cmd.Env = append(os.Environ(), "GO_WANT_BUILDER_HELPER=1")

	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("helper command failed: %v\n%s", err, out)
	}
	output := string(out)
	if !strings.Contains(output, "flavor-go-builder "+version) {
		t.Fatalf("expected version output, got %q", output)
	}
	if !strings.Contains(output, "Built: ") {
		t.Fatalf("expected build timestamp output, got %q", output)
	}
}

func TestBuilderBuildBundleVersionFlag(t *testing.T) {
	t.Parallel()

	old := versionFlag
	versionFlag = true
	t.Cleanup(func() {
		versionFlag = old
	})

	cmd := exec.Command(os.Args[0], "-test.run=TestBuilderBundleHelperProcess")
	cmd.Env = append(os.Environ(), "GO_WANT_BUILDER_BUNDLE_HELPER=1")

	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("helper command failed: %v\n%s", err, out)
	}
	output := string(out)
	if !strings.Contains(output, "flavor-go-builder "+version) {
		t.Fatalf("expected version output, got %q", output)
	}
}

func TestBuilderMainHelperProcess(t *testing.T) {
	if os.Getenv("GO_WANT_BUILDER_HELPER") != "1" {
		return
	}
	os.Args = []string{"flavor-go-builder", "--version"}
	main()
}

func TestBuilderBundleHelperProcess(t *testing.T) {
	if os.Getenv("GO_WANT_BUILDER_BUNDLE_HELPER") != "1" {
		return
	}
	versionFlag = true
	buildBundle(rootCmd, nil)
	os.Exit(0)
}
