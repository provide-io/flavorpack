# Package Rust helper binaries into a zip archive (Windows).
#
# Usage: package-rust-helpers.ps1 -Platform <platform> -Version <version>

param(
    [Parameter(Mandatory)][string]$Platform,
    [Parameter(Mandatory)][string]$Version
)

New-Item -ItemType Directory -Force -Path artifacts | Out-Null

$files = Get-ChildItem -Path "dist\bin" -Filter "flavor-rs-*-$Version-$Platform.exe"
if ($files.Count -gt 0) {
    Compress-Archive -Path $files.FullName `
        -DestinationPath "artifacts\flavor-rust-helpers-$Version-$Platform.zip" -Force
    Write-Host "📦 Packaged Rust helpers for $Platform`:"
    Get-ChildItem artifacts
} else {
    Write-Host "⚠️  No Rust binaries found to package for $Platform"
}
