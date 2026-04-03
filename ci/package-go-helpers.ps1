# Package Go helper binaries into a zip archive (Windows).
#
# Usage: package-go-helpers.ps1 -Platform <platform> -Version <version>

param(
    [Parameter(Mandatory)][string]$Platform,
    [Parameter(Mandatory)][string]$Version
)

New-Item -ItemType Directory -Force -Path artifacts | Out-Null

$files = Get-ChildItem -Path "dist\bin" -Filter "flavor-go-*-$Version-$Platform.exe"
if ($files.Count -gt 0) {
    Compress-Archive -Path $files.FullName `
        -DestinationPath "artifacts\flavor-go-helpers-$Version-$Platform.zip" -Force
    Write-Host "📦 Packaged Go helpers for $Platform`:"
    Get-ChildItem artifacts
} else {
    Write-Host "⚠️  No Go binaries found to package for $Platform"
}
