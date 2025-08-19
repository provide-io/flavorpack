#!/usr/bin/env pwsh
# Integration test script for Windows

$ErrorActionPreference = "Stop"

Write-Host "🧪 Starting Windows integration tests..." -ForegroundColor Green

# Activate virtual environment
& workenv\Scripts\Activate.ps1

Set-Location helpers\taster

# Debug: List available binaries
Write-Host "📦 Available binaries in ..\bin:" -ForegroundColor Yellow
Get-ChildItem ..\bin\ -ErrorAction SilentlyContinue | Format-Table Name, Length

# Find launchers for Windows
$launchers = Get-ChildItem ..\bin\*launcher*.exe -ErrorAction SilentlyContinue

if ($launchers.Count -eq 0) {
    # Try looking for launchers without .exe extension (shouldn't happen on Windows but just in case)
    $launchers = Get-ChildItem ..\bin\*launcher*windows* -ErrorAction SilentlyContinue
}

if ($launchers.Count -eq 0) {
    Write-Host "❌ No compatible launchers found for Windows!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found $($launchers.Count) launcher(s):" -ForegroundColor Green
foreach ($launcher in $launchers) {
    Write-Host "  - $($launcher.Name)" -ForegroundColor Cyan
}

# Test each launcher
foreach ($launcher in $launchers) {
    $launcherName = $launcher.Name
    Write-Host ""
    Write-Host "🔨 Testing with $launcherName..." -ForegroundColor Yellow
    
    # Build package
    $outputPath = "C:\temp\test-$launcherName.psp"
    
    try {
        & python -m flavor package `
            --manifest pyproject.toml `
            --output $outputPath `
            --launcher-bin $launcher.FullName `
            --key-seed test123 `
            --quiet
        
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed with exit code $LASTEXITCODE"
        }
        
        Write-Host "  ✅ Package built successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "  ❌ Failed to build package: $_" -ForegroundColor Red
        exit 1
    }
    
    # Test version command
    Write-Host "  Testing --version..." -ForegroundColor Gray
    try {
        $output = & $outputPath --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Version command failed with exit code $LASTEXITCODE"
        }
        Write-Host "  ✅ Version command succeeded" -ForegroundColor Green
    }
    catch {
        Write-Host "  ❌ Version command failed: $_" -ForegroundColor Red
        exit 1
    }
    
    # Test info command
    Write-Host "  Testing info..." -ForegroundColor Gray
    try {
        $output = & $outputPath info 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Info command failed with exit code $LASTEXITCODE"
        }
        Write-Host "  ✅ Info command succeeded" -ForegroundColor Green
    }
    catch {
        Write-Host "  ❌ Info command failed: $_" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ $launcherName test passed" -ForegroundColor Green
    
    # Clean up
    Remove-Item $outputPath -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "✅ All Windows integration tests passed!" -ForegroundColor Green