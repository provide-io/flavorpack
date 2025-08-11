# env.ps1 - Flavor Development Environment Setup
#
# This script sets up a clean, isolated development environment for Flavor
# using 'uv' for high-performance virtual environment and dependency management.
#
# Usage: .\env.ps1
#

# --- Configuration ---
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Helper functions for formatted output
function Write-Header {
    param([string]$Message)
    Write-Host "`n--- $Message ---" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

# --- Cleanup Previous Environment ---
Write-Header "🧹 Cleaning Previous Environment"

# Remove any existing Python aliases
Remove-Alias -Name python -ErrorAction SilentlyContinue
Remove-Alias -Name python3 -ErrorAction SilentlyContinue
Remove-Alias -Name pip -ErrorAction SilentlyContinue
Remove-Alias -Name pip3 -ErrorAction SilentlyContinue

# Clear existing PYTHONPATH
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

Write-Success "Cleared Python aliases and PYTHONPATH"

# --- Project Validation ---
if (-not (Test-Path "pyproject.toml")) {
    Write-Error "No 'pyproject.toml' found in current directory"
    Write-Host "Please run this script from the Flavor root directory"
    exit 1
}

$ProjectName = Split-Path -Leaf (Get-Location)

# --- UV Installation ---
Write-Header "🚀 Checking UV Package Manager"

$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCommand) {
    Write-Host "Installing UV..."
    
    try {
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        
        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        # Check if UV is now available
        $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
        if ($uvCommand) {
            Write-Success "UV installed successfully"
        } else {
            Write-Error "UV installation failed"
            exit 1
        }
    }
    catch {
        Write-Error "UV installation failed: $_"
        exit 1
    }
} else {
    Write-Success "UV already installed"
}

# --- Platform Detection ---
$TFOS = if ($IsWindows) { "windows" } elseif ($IsMacOS) { "darwin" } else { "linux" }
$TFARCH = switch ([System.Environment]::Is64BitOperatingSystem) {
    $true { 
        if ([System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -eq [System.Runtime.InteropServices.Architecture]::Arm64) {
            "arm64"
        } else {
            "amd64"
        }
    }
    $false { "386" }
}

# Workenv directory setup
$Profile = if ($env:FLAVOR_WORKENV_PROFILE) { $env:FLAVOR_WORKENV_PROFILE } else { "default" }
if ($Profile -eq "default") {
    $VenvDir = "workenv/flavor_${TFOS}_${TFARCH}"
} else {
    $VenvDir = "workenv/${Profile}_${TFOS}_${TFARCH}"
}

$env:UV_PROJECT_ENVIRONMENT = $VenvDir

# --- Virtual Environment ---
Write-Header "🐍 Setting Up Virtual Environment"
Write-Host "Directory: $VenvDir"

$VenvExists = (Test-Path $VenvDir) -and (Test-Path "$VenvDir/Scripts/activate.ps1") -and (Test-Path "$VenvDir/Scripts/python.exe")

if ($VenvExists) {
    Write-Success "Virtual environment exists"
} else {
    Write-Host "Creating virtual environment..."
    try {
        & uv venv $VenvDir
        Write-Success "Virtual environment created"
    }
    catch {
        Write-Error "Virtual environment creation failed: $_"
        exit 1
    }
}

# Activate virtual environment - handle cross-platform paths
if ($IsWindows) {
    $ActivateScript = Join-Path $VenvDir "Scripts/Activate.ps1"
} else {
    # On macOS/Linux, activation script is in bin directory with lowercase name
    $ActivateScript = Join-Path $VenvDir "bin/activate.ps1"
}

if (Test-Path $ActivateScript) {
    & $ActivateScript
    $env:VIRTUAL_ENV = Join-Path (Get-Location) $VenvDir
} else {
    Write-Error "Could not find activation script at $ActivateScript"
    Write-Host "Note: Virtual environment created but activation failed."
    Write-Host "For macOS/Linux, you may need to use: source $VenvDir/bin/activate"
    exit 1
}

# --- Dependency Installation ---
Write-Header "📦 Installing Dependencies"

Write-Host "Syncing dependencies..."
try {
    & uv sync --all-groups
    Write-Success "Dependencies synced"
}
catch {
    Write-Error "Dependency sync failed"
    exit 1
}

Write-Host "Installing Flavor in editable mode..."
try {
    & uv pip install --no-deps -e .
    Write-Success "Flavor installed"
}
catch {
    Write-Error "Installation failed"
    exit 1
}

# --- Sibling Packages ---
Write-Header "🤝 Installing Sibling Packages"

$ParentDir = Split-Path -Parent (Get-Location)
$SiblingCount = 0

# Install pyvider packages
Get-ChildItem -Path $ParentDir -Directory -Filter "pyvider*" | ForEach-Object {
    $SiblingName = $_.Name
    Write-Host "Installing $SiblingName..."
    try {
        & uv pip install --no-deps -e $_.FullName
        Write-Success "$SiblingName installed"
        $SiblingCount++
    }
    catch {
        Write-Warning "Failed to install $SiblingName"
    }
}

# Special handling for tofusoup
$TofusoupDir = Join-Path $ParentDir "tofusoup"
if (Test-Path $TofusoupDir) {
    Write-Host "Found tofusoup package. Installing in editable mode with dependencies..."
    try {
        & uv pip install -e $TofusoupDir
        Write-Success "tofusoup installed"
        $SiblingCount++
    }
    catch {
        Write-Warning "Failed to install tofusoup package"
    }
}

if ($SiblingCount -eq 0) {
    Write-Warning "No sibling packages found"
}

# --- Environment Configuration ---
Write-Header "🔧 Configuring Environment"

# Set clean PYTHONPATH
$env:PYTHONPATH = "$(Get-Location)/src;$(Get-Location)"
Write-Host "PYTHONPATH: $env:PYTHONPATH"

# Clean up PATH - remove duplicates
$PathArray = $env:PATH -split ';' | Where-Object { $_ -ne '' } | Select-Object -Unique
$VenvBin = Join-Path $VenvDir "Scripts"
$NewPath = @($VenvBin) + ($PathArray | Where-Object { $_ -ne $VenvBin })
$env:PATH = $NewPath -join ';'

# --- Final Summary ---
Write-Header "✅ Environment Ready!"

Write-Host "`nFlavor development environment activated" -ForegroundColor Green
Write-Host "Virtual environment: $VenvDir"
Write-Host "Profile: $Profile"
Write-Host "`nUseful commands:"
Write-Host "  flavor --help     # Flavor CLI"
Write-Host "  pytest            # Run tests"
Write-Host "  deactivate        # Exit environment"

# Return success
exit 0

# 📦🍜⚡🪄
