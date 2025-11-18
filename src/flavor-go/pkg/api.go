package pkg

import (
	"github.com/provide-io/flavor/go/flavor/pkg/psp/format_2025"
)

func BuildPackage(manifestPath, outputPath, launcherBin string) {
	format_2025.BuildWithOptions(manifestPath, outputPath, launcherBin, "", "", "")
}

func BuildPackageWithOptions(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {
	format_2025.BuildWithOptions(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed)
}

func BuildPackageWithLogLevel(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed, logLevel string) {
	format_2025.BuildWithLogLevel(manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed, logLevel)
}

func VerifyPackage(packagePath string) (bool, error) {
	return true, nil
}

func LaunchPackage(packagePath string, args []string) (int, error) {
	return 0, nil
}
