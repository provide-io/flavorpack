# package-artifacts.ps1 - Package helper binaries into structured artifacts (Windows)
# Usage: .\package-artifacts.ps1 -Language <lang> -Platform <platform> -BinDir <dir> -OutputDir <dir>

param(
    [Parameter(Mandatory=$true)]
    [string]$Language,
    
    [Parameter(Mandatory=$true)]
    [string]$Platform,
    
    [Parameter(Mandatory=$true)]
    [string]$BinDir,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputDir,
    
    [Parameter(Mandatory=$false)]
    [string]$Version = "0.0.0"
)

# Warn if using default version
if ($Version -eq "0.0.0" -and -not $PSBoundParameters.ContainsKey('Version')) {
    Write-Warning "No version specified, using default 0.0.0"
}

# Create artifact directory with version
$artifactDir = Join-Path $OutputDir "flavor-$Language-helpers-${Version}_$Platform"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

Write-Host "📦 Creating artifact structure for flavor-$Language-helpers-${Version}_$Platform"

# Copy binaries
$pattern = "flavor-$Language-*.exe"
$binaries = Get-ChildItem -Path $BinDir -Filter $pattern
foreach ($binary in $binaries) {
    Copy-Item $binary.FullName -Destination $artifactDir
}

# Create README content based on language
$buildTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss UTC")

if ($Language -eq "go") {
    $readmeContent = @"
# Flavor Go Helpers

Version: $Version
Platform: $Platform
Built: $buildTime

## Contents

- ``flavor-go-builder.exe``: Go-based PSPF package builder
- ``flavor-go-launcher.exe``: Go-based PSPF package launcher

## Installation

1. Extract this archive to your desired location
2. Add the directory to your PATH or copy binaries to a directory in PATH

## Usage

### Builder
``````powershell
.\flavor-go-builder.exe --manifest manifest.json --output package.psp
``````

### Launcher
The launcher is embedded in PSPF packages and executes them.

## Cross-compilation

These binaries were cross-compiled for $Platform using Go's built-in cross-compilation support.

## Version Info

Run with ``--version`` flag to see version information:
``````powershell
.\flavor-go-builder.exe --version
.\flavor-go-launcher.exe --version
``````

## Requirements

- No external dependencies required
- Binaries are statically linked

## Windows Notes

- Built on Windows Server 2025
- Requires Windows 10 or later
- Compatible with PowerShell 5.1 and PowerShell Core 7+

## More Information

- Repository: https://github.com/provide-io/flavor
- Documentation: https://github.com/provide-io/flavor/tree/main/helpers/flavor-go
"@
} else {
    $readmeContent = @"
# Flavor Rust Helpers

Version: $Version
Platform: $Platform
Built: $buildTime

## Contents

- ``flavor-rs-builder.exe``: Rust-based PSPF package builder
- ``flavor-rs-launcher.exe``: Rust-based PSPF package launcher

## Installation

1. Extract this archive to your desired location
2. Add the directory to your PATH or copy binaries to a directory in PATH

## Usage

### Builder
``````powershell
.\flavor-rs-builder.exe --manifest manifest.json --output package.psp
``````

### Launcher
The launcher is embedded in PSPF packages and executes them.

## Cross-compilation

These binaries were cross-compiled for $Platform using Rust's cross-compilation toolchain.

## Version Info

Run with ``--version`` flag to see version information:
``````powershell
.\flavor-rs-builder.exe --version
.\flavor-rs-launcher.exe --version
``````

## Requirements

- No external dependencies required
- May require Visual C++ Redistributables

## Windows Notes

- Built on Windows Server 2025
- Requires Windows 10 or later
- Compatible with PowerShell 5.1 and PowerShell Core 7+

## More Information

- Repository: https://github.com/provide-io/flavor
- Documentation: https://github.com/provide-io/flavor/tree/main/helpers/flavor-rs
"@
}

# Write README
$readmePath = Join-Path $artifactDir "README.md"
$readmeContent | Out-File -FilePath $readmePath -Encoding UTF8

# List contents
Write-Host "📋 Artifact contents:"
Get-ChildItem $artifactDir

# Count binaries
$binaryCount = (Get-ChildItem -Path $artifactDir -Filter "*.exe").Count
Write-Host "✅ Packaged $binaryCount binaries for $Platform"

# Return success if we have binaries
if ($binaryCount -gt 0) {
    exit 0
} else {
    Write-Host "⚠️ Warning: No binaries found for $Platform"
    exit 1
}