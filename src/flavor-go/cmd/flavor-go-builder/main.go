package main

import (
	"fmt"
	"os"
	"runtime/debug"
	"time"

	"github.com/provide-io/flavor/go/flavor/pkg"
	"github.com/spf13/cobra"
)

const version = "0.3.0"

var (
	manifestPath   string
	outputPath     string
	launcherBin    string
	privateKeyPath string
	publicKeyPath  string
	keySeed        string
	logLevel       string
	workenvBase    string
	rootCmd        *cobra.Command
	versionFlag    bool
)

func getBuilderTimestamp() string {
	// Try to get vcs.time from build info
	if info, ok := debug.ReadBuildInfo(); ok {
		for _, setting := range info.Settings {
			if setting.Key == "vcs.time" {
				if t, err := time.Parse(time.RFC3339, setting.Value); err == nil {
					return t.UTC().Format(time.RFC3339)
				}
			}
		}
	}
	// Fallback to binary modification time
	if exePath, err := os.Executable(); err == nil {
		if stat, err := os.Stat(exePath); err == nil {
			return stat.ModTime().UTC().Format(time.RFC3339)
		}
	}
	return time.Now().UTC().Format(time.RFC3339)
}

func init() {
	rootCmd = &cobra.Command{
		Use:   "flavor-go-builder",
		Short: "Build PSPF packages",
		Long:  `Build PSPF packages`,
		Run:   buildBundle,
	}

	rootCmd.Flags().StringVarP(&manifestPath, "manifest", "m", "", "Path to manifest.json (required)")
	rootCmd.Flags().StringVarP(&outputPath, "output", "o", "", "Output path for PSPF bundle (required)")
	rootCmd.Flags().StringVar(&launcherBin, "launcher-bin", "", "Path to launcher binary")
	rootCmd.Flags().StringVar(&privateKeyPath, "private-key", "", "Path to private key (PEM format)")
	rootCmd.Flags().StringVar(&publicKeyPath, "public-key", "", "Path to public key (PEM format, optional if private key provided)")
	rootCmd.Flags().StringVar(&keySeed, "key-seed", "", "Seed for deterministic key generation")
	rootCmd.Flags().StringVar(&logLevel, "log-level", "", "Log level (trace, debug, info, warn, error)")
	rootCmd.Flags().StringVar(&workenvBase, "workenv-base", "", "Base directory for {workenv} resolution (defaults to CWD)")
	rootCmd.Flags().BoolVarP(&versionFlag, "version", "V", false, "Show version information")

	if err := rootCmd.MarkFlagRequired("manifest"); err != nil {
		panic(err)
	}
	if err := rootCmd.MarkFlagRequired("output"); err != nil {
		panic(err)
	}
}

func main() {
	// Handle --version or -V before cobra parses other flags
	if len(os.Args) > 1 && (os.Args[1] == "--version" || os.Args[1] == "-V") {
		fmt.Printf("flavor-go-builder %s\n", version)
		fmt.Printf("Built: %s\n", getBuilderTimestamp())
		os.Exit(0)
	}

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func buildBundle(cmd *cobra.Command, args []string) {
	if versionFlag {
		fmt.Printf("flavor-go-builder %s\n", version)
		fmt.Printf("Built: %s\n", getBuilderTimestamp())
		return
	}
	// Set workenv base if provided via flag
	if workenvBase != "" {
		os.Setenv("FLAVOR_WORKENV_BASE", workenvBase)
	}
	pkg.BuildPackageWithLogLevel(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed, logLevel)
}
