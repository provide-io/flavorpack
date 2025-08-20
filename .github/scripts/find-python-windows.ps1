#!/usr/bin/env pwsh
# Script to search Windows build agent for Python installations

Write-Host "=== Searching for Python installations on Windows build agent ===" -ForegroundColor Cyan

# Common Python locations to check
$searchPaths = @(
    "$env:USERPROFILE\AppData\Local\uv\python",
    "$env:USERPROFILE\.local\share\uv\python",
    "$env:LOCALAPPDATA\uv\python",
    "$env:ProgramFiles\Python*",
    "$env:ProgramFiles(x86)\Python*",
    "$env:USERPROFILE\AppData\Local\Programs\Python",
    "C:\hostedtoolcache\windows\Python",
    "C:\tools\python*",
    "C:\Python*"
)

Write-Host "`nSearching in common locations:" -ForegroundColor Yellow
foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        Write-Host "  ✓ Found: $path" -ForegroundColor Green
        Get-ChildItem -Path $path -Recurse -Filter "python*.exe" -ErrorAction SilentlyContinue | 
            Select-Object -First 5 | 
            ForEach-Object { Write-Host "      - $($_.FullName)" -ForegroundColor Gray }
    }
}

Write-Host "`n=== UV Python installations ===" -ForegroundColor Yellow
# Check UV installations specifically
$uvPythonBase = "$env:USERPROFILE\AppData\Local\uv\python"
if (Test-Path $uvPythonBase) {
    Write-Host "UV Python base found at: $uvPythonBase" -ForegroundColor Green
    Get-ChildItem -Path $uvPythonBase -Directory | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Cyan
        $pythonExe = Get-ChildItem -Path $_.FullName -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($pythonExe) {
            Write-Host "    Python exe: $($pythonExe.FullName)" -ForegroundColor Gray
            # Check for EXTERNALLY-MANAGED
            $libPath = Join-Path $_.FullName "Lib"
            $extManaged = Get-ChildItem -Path $libPath -Recurse -Filter "EXTERNALLY-MANAGED" -ErrorAction SilentlyContinue
            if ($extManaged) {
                Write-Host "    ⚠ EXTERNALLY-MANAGED found at: $($extManaged.FullName)" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host "`n=== System PATH Python ===" -ForegroundColor Yellow
# Check what's in PATH
$pythonInPath = Get-Command python -ErrorAction SilentlyContinue
if ($pythonInPath) {
    Write-Host "Python in PATH: $($pythonInPath.Source)" -ForegroundColor Green
    & python --version
}

$python3InPath = Get-Command python3 -ErrorAction SilentlyContinue
if ($python3InPath) {
    Write-Host "Python3 in PATH: $($python3InPath.Source)" -ForegroundColor Green
    & python3 --version
}

Write-Host "`n=== UV tool info ===" -ForegroundColor Yellow
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCommand) {
    Write-Host "UV found at: $($uvCommand.Source)" -ForegroundColor Green
    Write-Host "UV version:" -ForegroundColor Gray
    & uv --version
    
    Write-Host "`nUV Python list:" -ForegroundColor Gray
    & uv python list --only-installed
}

Write-Host "`n=== Checking extracted workenv paths ===" -ForegroundColor Yellow
# Check the actual extraction paths used by the runner
$tempPaths = @(
    "$env:TEMP\pspf",
    "$env:TMP\pspf",
    "$env:USERPROFILE\AppData\Local\Temp\pspf",
    "C:\Users\RUNNER~1\AppData\Local\Temp\pspf"
)

foreach ($path in $tempPaths) {
    if (Test-Path $path) {
        Write-Host "Found PSPF workenv at: $path" -ForegroundColor Green
        Get-ChildItem -Path $path -Recurse -Filter "python*.exe" -ErrorAction SilentlyContinue | 
            ForEach-Object { Write-Host "  - $($_.FullName)" -ForegroundColor Gray }
    }
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Script completed. Check the output above for Python locations." -ForegroundColor Green