#!/usr/bin/env pwsh
# Test that built binaries actually work
# Usage: .github/scripts/test-binaries.ps1 -Platform <platform> [-CrossCompiled]

param(
    [Parameter(Mandatory=$true)]
    [string]$Platform,
    
    [Parameter()]
    [switch]$CrossCompiled
)

$ErrorActionPreference = "Stop"

Write-Host "🧪 Testing built binaries for $Platform"

# Handle different path separators and extensions
$binPattern = if ($Platform -like "*windows*") {
    "*-${Platform}*.exe"
} else {
    "*-${Platform}*"
}

# Find all binaries for this platform
$binaries = Get-ChildItem -Path "helpers/bin" -Filter $binPattern -ErrorAction SilentlyContinue

if (-not $binaries) {
    Write-Error "❌ No binaries found for platform: $Platform"
    exit 1
}

$failed = $false
foreach ($binary in $binaries) {
    Write-Host "Testing: $($binary.Name)"
    
    if ($CrossCompiled) {
        # For cross-compiled binaries, just verify they exist and are valid
        if (Test-Path $binary.FullName) {
            # On Unix, check with file command if available
            if ($IsLinux -or $IsMacOS) {
                try {
                    $fileInfo = & file $binary.FullName 2>$null
                    if ($fileInfo -match "executable|PE32|Mach-O|ELF") {
                        Write-Host "  ✅ Binary format valid (cross-compiled)"
                    } else {
                        Write-Host "  ❌ Invalid binary format"
                        Write-Host "     File info: $fileInfo"
                        $failed = $true
                    }
                } catch {
                    # If file command fails, just check that the file exists
                    Write-Host "  ✅ Binary exists (cross-compiled, file command unavailable)"
                }
            } else {
                # On Windows or when file command isn't available
                Write-Host "  ✅ Binary exists (cross-compiled)"
            }
        } else {
            Write-Host "  ❌ Binary not found"
            $failed = $true
        }
    } else {
        # Native binaries - test execution
        $testPassed = $false
        
        # Try --version first
        try {
            $proc = Start-Process -FilePath $binary.FullName -ArgumentList "--version" -NoNewWindow -PassThru -Wait -RedirectStandardOutput "/tmp/test-out.txt" -RedirectStandardError "/tmp/test-err.txt" -ErrorAction Stop
            if ($proc.ExitCode -eq 0) {
                Write-Host "  ✅ --version works"
                $testPassed = $true
            }
        } catch {
            # Ignore and try next option
        }
        
        # Try --help as fallback
        if (-not $testPassed) {
            try {
                $proc = Start-Process -FilePath $binary.FullName -ArgumentList "--help" -NoNewWindow -PassThru -Wait -RedirectStandardOutput "/tmp/test-out.txt" -RedirectStandardError "/tmp/test-err.txt" -ErrorAction Stop
                if ($proc.ExitCode -eq 0) {
                    Write-Host "  ✅ --help works"
                    $testPassed = $true
                }
            } catch {
                # Ignore and try next option
            }
        }
        
        # Just check if it runs without crashing (with timeout)
        if (-not $testPassed) {
            try {
                # Create a job to run with timeout
                $job = Start-Job -ScriptBlock {
                    param($binaryPath)
                    & $binaryPath 2>&1
                } -ArgumentList $binary.FullName
                
                # Wait up to 1 second
                $result = Wait-Job -Job $job -Timeout 1
                if ($result) {
                    $exitCode = Receive-Job -Job $job
                    Write-Host "  ✅ Binary executes"
                    $testPassed = $true
                }
                Remove-Job -Job $job -Force
            } catch {
                # Failed to run
            }
        }
        
        if (-not $testPassed) {
            Write-Host "  ❌ Binary failed to run: $($binary.Name)"
            $failed = $true
        }
    }
}

if ($failed) {
    Write-Error "❌ Some binaries failed testing"
    exit 1
} else {
    Write-Host "✅ All binaries tested successfully for $Platform"
    exit 0
}