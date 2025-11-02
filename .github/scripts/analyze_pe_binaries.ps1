#!/usr/bin/env pwsh
<#
.SYNOPSIS
Windows PE Binary Analysis using dumpbin

.DESCRIPTION
Analyzes PE binaries using dumpbin.exe (MSVC) and compares working vs failing binaries.

.PARAMETER WorkingBinary
Path to working binary (Rust+Rust launcher)

.PARAMETER FailingBinary
Path to failing binary (Go launcher after expansion)

.PARAMETER OutputDir
Output directory for analysis reports

.EXAMPLE
.\analyze_pe_binaries.ps1 -WorkingBinary "pretaster-rs-rs.psp" -FailingBinary "pretaster-rs-go.psp" -OutputDir "analysis"
#>

param(
    [string]$WorkingBinary,
    [string]$FailingBinary,
    [string]$OutputDir = "pe-analysis"
)

function Test-DumpbinAvailable {
    <# Check if dumpbin.exe is available #>
    try {
        $result = & dumpbin /? 2>&1 | Select-String "Microsoft" | Measure-Object -Line
        return $result.Lines -gt 0
    }
    catch {
        return $false
    }
}

function Analyze-PEWithDumpbin {
    param([string]$FilePath)

    Write-Host "Analyzing $FilePath with dumpbin..."

    $analysis = @{
        file = $FilePath
        size = (Get-Item $FilePath).Length
        headers = @()
        sections = @()
        directories = @()
    }

    # Get headers
    $headerOutput = & dumpbin /headers $FilePath
    $analysis.headers = $headerOutput

    # Get sections
    $sectionOutput = & dumpbin /sections $FilePath
    $analysis.sections = $sectionOutput

    # Get ALL information including data directories
    $allOutput = & dumpbin /all $FilePath
    $analysis.all = $allOutput

    # Parse data directories from output
    $inDataDir = $false
    foreach ($line in $allOutput) {
        if ($line -match "Data Directories") {
            $inDataDir = $true
            continue
        }
        if ($inDataDir -and $line -match "^\s*$") {
            break
        }
        if ($inDataDir -and $line -match "^\s+\d+") {
            $analysis.directories += $line.Trim()
        }
    }

    return $analysis
}

function Analyze-PEWithPython {
    param([string]$FilePath)

    Write-Host "Analyzing $FilePath with Python pefile..."

    $pythonScript = @'
import sys
import json
from pathlib import Path

try:
    import pefile
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pefile", "-q"])
    import pefile

filepath = sys.argv[1]
pe = pefile.PE(filepath)

analysis = {
    "file": filepath,
    "size": Path(filepath).stat().st_size,
    "pe_offset": pe.DOS_HEADER.e_lfanew,
    "num_sections": pe.FILE_HEADER.NumberOfSections,
    "machine": hex(pe.FILE_HEADER.Machine),
    "sections": []
}

for section in pe.sections:
    analysis["sections"].append({
        "name": section.Name.decode('utf-8', errors='ignore').rstrip('\0'),
        "va": hex(section.VirtualAddress),
        "size": hex(section.SizeOfRawData),
        "raw_ptr": hex(section.PointerToRawData)
    })

# Data directories
analysis["data_directories"] = []
names = ["Export", "Import", "Resource", "Exception", "Certificate", "Base Relocation",
         "Debug", "Architecture", "Global Ptr", "TLS", "Load Config", "Bound Import",
         "IAT", "Delay Import", "COM Runtime", "Reserved"]

for i, entry in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
    analysis["data_directories"].append({
        "index": i,
        "name": names[i] if i < len(names) else f"Dir {i}",
        "va": hex(entry.VirtualAddress),
        "size": hex(entry.Size)
    })

print(json.dumps(analysis, indent=2))
'@

    $tempScript = New-TemporaryFile -Suffix ".py"
    $pythonScript | Set-Content $tempScript

    try {
        $output = & python $tempScript $FilePath 2>&1
        $analysis = $output | ConvertFrom-Json
        return $analysis
    }
    finally {
        Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
    }
}

function Generate-Report {
    param(
        [hashtable]$Working,
        [hashtable]$Failing,
        [string]$OutputPath
    )

    $report = @"
# Windows PE Binary Analysis Report
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## Working Binary (Rust+Rust)
- File: $($Working.file)
- Size: $($Working.size) bytes
- PE Offset: 0x$($Working.pe_offset:x)
- Sections: $($Working.num_sections)
- Machine: $($Working.machine)

### Sections:
$($Working.sections | Format-Table -AutoSize | Out-String)

### Data Directories (with data):
$($Working.data_directories | Where-Object { $_.size -ne '0x0' } | Format-Table -AutoSize | Out-String)

---

## Failing Binary (Rust+Go)
- File: $($Failing.file)
- Size: $($Failing.size) bytes
- PE Offset: 0x$($Failing.pe_offset:x)
- Sections: $($Failing.num_sections)
- Machine: $($Failing.machine)

### Sections:
$($Failing.sections | Format-Table -AutoSize | Out-String)

### Data Directories (with data):
$($Failing.data_directories | Where-Object { $_.size -ne '0x0' } | Format-Table -AutoSize | Out-String)

---

## Key Differences
- PE Offset changed: $(if ($Working.pe_offset -ne $Failing.pe_offset) { "YES (0x$($Working.pe_offset:x) -> 0x$($Failing.pe_offset:x))" } else { "NO" })
- Section count changed: $(if ($Working.num_sections -ne $Failing.num_sections) { "YES ($($Working.num_sections) -> $($Failing.num_sections))" } else { "NO" })
"@

    $report | Set-Content $OutputPath
    Write-Host "Report saved to: $OutputPath"
}

# Main execution
Write-Host "=== Windows PE Binary Analysis ==="
Write-Host ""

if (-not (Test-Path $WorkingBinary)) {
    Write-Error "Working binary not found: $WorkingBinary"
    exit 1
}

if (-not (Test-Path $FailingBinary)) {
    Write-Error "Failing binary not found: $FailingBinary"
    exit 1
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    mkdir $OutputDir | Out-Null
}

# Try dumpbin first, fall back to Python
if (Test-DumpbinAvailable) {
    Write-Host "Using dumpbin.exe for analysis..."
    $working = Analyze-PEWithDumpbin $WorkingBinary
    $failing = Analyze-PEWithDumpbin $FailingBinary
}
else {
    Write-Host "dumpbin.exe not found, using Python pefile..."
    $working = Analyze-PEWithPython $WorkingBinary
    $failing = Analyze-PEWithPython $FailingBinary
}

# Generate report
$reportPath = Join-Path $OutputDir "pe_analysis_report.txt"
Generate-Report $working $failing $reportPath

Write-Host ""
Write-Host "Analysis complete!"
Write-Host "Report: $reportPath"
