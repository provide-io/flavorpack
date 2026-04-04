// tastesh-win: minimal POSIX sh interpreter for Windows, built on mvdan.cc/sh/v3.
// Used as the embedded shell executor in PSP packages on Windows so that test
// scripts can run without depending on bash/PowerShell being installed on the host.
//
// Invocation (same as dash/sh):
//   tastesh-win -c "script"
//   tastesh-win script_file [args...]
//   tastesh-win             (reads from stdin)
package main

import (
	"context"
	"fmt"
	"os"
	"strings"

	"mvdan.cc/sh/v3/interp"
	"mvdan.cc/sh/v3/syntax"
)

func main() {
	args := os.Args[1:]

	var src string
	var name string
	var scriptArgs []string

	switch {
	case len(args) == 0:
		// Read script from stdin
		name = "stdin"
		var sb strings.Builder
		buf := make([]byte, 4096)
		for {
			n, err := os.Stdin.Read(buf)
			if n > 0 {
				sb.Write(buf[:n])
			}
			if err != nil {
				break
			}
		}
		src = sb.String()

	case args[0] == "-c":
		// -c "script" [argv0] [args...]
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "sh: -c requires an argument")
			os.Exit(2)
		}
		src = args[1]
		name = "sh"
		if len(args) >= 3 {
			name = args[2]
		}
		if len(args) >= 4 {
			scriptArgs = args[3:]
		}

	default:
		// script_file [args...]
		data, err := os.ReadFile(args[0])
		if err != nil {
			fmt.Fprintf(os.Stderr, "sh: %s: %v\n", args[0], err)
			os.Exit(127)
		}
		src = string(data)
		name = args[0]
		if len(args) > 1 {
			scriptArgs = args[1:]
		}
	}

	parser := syntax.NewParser()
	prog, err := parser.Parse(strings.NewReader(src), name)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	runner, err := interp.New(
		interp.StdIO(os.Stdin, os.Stdout, os.Stderr),
		interp.Params(append([]string{name}, scriptArgs...)...),
	)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	ctx := context.Background()
	if err := runner.Run(ctx, prog); err != nil {
		if exit, ok := interp.IsExitStatus(err); ok {
			os.Exit(int(exit))
		}
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
