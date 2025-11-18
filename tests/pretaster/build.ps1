# build.ps1 - Windows build script for pretaster
# Compiles Go and Rust helper binaries into helpers/bin/

param(
    [string]$Platform = "windows_amd64"
)

$ErrorActionPreference = "Stop"

# --- Setup ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$BinDir = Join-Path $ProjectRoot "dist\bin"
$GoDir = Join-Path $ProjectRoot "src\flavor-go"
$RustDir = Join-Path $ProjectRoot "src\flavor-rs"

# --- Logging ---
function Log-Info { Write-Host "ℹ️  $args" -ForegroundColor Cyan }
function Log-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Log-Error { Write-Host "❌ $args" -ForegroundColor Red }

# --- Pre-flight Checks ---
function Check-Tool {
    param($Tool)
    if (-not (Get-Command $Tool -ErrorAction SilentlyContinue)) {
        Log-Error "Required tool '$Tool' is not installed or not in PATH."
        exit 1
    }
}

Log-Info "Checking for required build tools..."
Check-Tool go
Check-Tool cargo
Log-Success "All build tools found."

# --- Main Build ---
Log-Info "Starting build for Go and Rust helpers on Windows..."
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# --- Build Go Helpers ---
Log-Info "Building Go helpers..."
Push-Location $GoDir
try {
    $env:GOOS = "windows"
    $env:GOARCH = "amd64"
    $env:CGO_ENABLED = "0"

    # Build Go builder
    go build -o "$BinDir\flavor-go-builder-$Platform.exe" ./cmd/flavor-go-builder
    # Build Go launcher
    go build -o "$BinDir\flavor-go-launcher-$Platform.exe" ./cmd/flavor-go-launcher

    Log-Success "Go helpers built successfully."
}
finally {
    Pop-Location
}

# --- Build Rust Helpers ---
Log-Info "Building Rust helpers..."
Push-Location $RustDir
try {
    # Build for Windows
    cargo build --release --target x86_64-pc-windows-msvc

    # Copy binaries with proper naming
    Copy-Item -Path "target\x86_64-pc-windows-msvc\release\flavor-rs-builder.exe" -Destination "$BinDir\flavor-rs-builder-$Platform.exe" -Force
    Copy-Item -Path "target\x86_64-pc-windows-msvc\release\flavor-rs-launcher.exe" -Destination "$BinDir\flavor-rs-launcher-$Platform.exe" -Force

    Log-Success "Rust helpers built successfully."
}
finally {
    Pop-Location
}

# --- Finalization ---
Log-Success "All helpers are built and located in '$BinDir'."
Get-ChildItem $BinDir -Filter "*.exe" | ForEach-Object { Log-Info "  - $($_.Name)" }