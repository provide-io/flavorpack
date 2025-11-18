# Windows Troubleshooting

Platform-specific issues and solutions for Windows users.

!!! warning "Beta Support"
    Windows support is currently in beta. Some features may be limited or require additional configuration.

## Common Issues

### Execution Problems

#### Windows Defender SmartScreen

**Symptom**: "Windows protected your PC" warning

**Solution**:
1. Click "More info" on the warning dialog
2. Click "Run anyway"
3. Or permanently allow:

```powershell
# Add to Windows Defender exclusions (as Administrator)
Add-MpPreference -ExclusionPath "C:\Path\To\myapp.psp"

# Or disable SmartScreen for the file
Unblock-File -Path .\myapp.psp
```

#### Execution Policy Restrictions

**Symptom**: Scripts blocked by execution policy

**Solution**:
```powershell
# Check current policy
Get-ExecutionPolicy

# Set for current user (temporary)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Set for current user (permanent)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Permission Issues

#### Access Denied Errors

**Symptom**: Cannot execute or access package

**Solution**:
```powershell
# Run as Administrator
Start-Process myapp.psp -Verb RunAs

# Check file permissions
Get-Acl .\myapp.psp | Format-List

# Grant execute permission
$acl = Get-Acl .\myapp.psp
$permission = "Everyone","ReadAndExecute","Allow"
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
$acl.SetAccessRule($accessRule)
Set-Acl .\myapp.psp $acl
```

#### UAC (User Account Control)

**Symptom**: UAC prompts or blocks execution

**Solution**:
```powershell
# Create scheduled task to bypass UAC
$action = New-ScheduledTaskAction -Execute "C:\Path\To\myapp.psp"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Highest
Register-ScheduledTask -TaskName "MyApp" -Action $action -Trigger $trigger -Principal $principal
```

### Path and Environment

#### Command Not Found

**Symptom**: `flavor` not recognized as command

**Solution**:
```powershell
# Add to PATH (current session)
$env:Path += ";C:\Path\To\FlavorPack"

# Add to PATH (permanent)
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Path\To\FlavorPack",
    [EnvironmentVariableTarget]::User
)

# Verify PATH
$env:Path -split ';' | Select-String flavor
```

#### Python Version Issues

**Symptom**: Wrong Python version or not found

**Solution**:
```powershell
# Check Python versions
py -0

# Use specific version
py -3.11 -m flavor pack --manifest pyproject.toml

# Set default version
py -3.11 -m pip install --upgrade pip
```

### Antivirus Interference

#### Real-time Protection Blocking

**Symptom**: Package quarantined or deleted

**Solution**:
```powershell
# Windows Defender exclusions
Add-MpPreference -ExclusionPath "C:\FlavorPack"
Add-MpPreference -ExclusionProcess "myapp.psp"

# Check quarantine
Get-MpThreatDetection

# Restore from quarantine
Restore-MpThreatDetection -ThreatID <ID>
```

### File System Issues

#### Long Path Support

**Symptom**: Path too long errors

**Solution**:
```powershell
# Enable long paths (requires restart)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
    -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# Or use Group Policy:
# Computer Configuration > Administrative Templates > System > Filesystem
# Enable "Enable Win32 long paths"
```

#### NTFS Permissions

**Symptom**: Permission inheritance issues

**Solution**:
```powershell
# Reset permissions
icacls .\myapp.psp /reset

# Grant full control
icacls .\myapp.psp /grant "$env:USERNAME:(F)"

# Remove inheritance
icacls .\myapp.psp /inheritance:r
```

### Network Issues

#### Windows Firewall

**Symptom**: Network connections blocked

**Solution**:
{% raw %}
```powershell
# Allow through firewall
New-NetFirewallRule -DisplayName "FlavorPack" `
    -Direction Outbound -Program "C:\Path\To\myapp.psp" `
    -Action Allow

# Check firewall rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*flavor*"}

# Disable firewall temporarily (not recommended)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
```
{% endraw %}

#### Proxy Configuration

**Symptom**: Cannot download dependencies

**Solution**:
```powershell
# Set proxy
$env:HTTP_PROXY = "http://proxy.company.com:8080"
$env:HTTPS_PROXY = "http://proxy.company.com:8080"

# Set system proxy
netsh winhttp set proxy proxy.company.com:8080

# Check proxy settings
netsh winhttp show proxy
```

## Windows-Specific Features

### Creating Windows Service

```powershell
# Install as service using NSSM
nssm install MyApp "C:\Path\To\myapp.psp"
nssm set MyApp AppDirectory "C:\Path\To"
nssm set MyApp DisplayName "My FlavorPack App"
nssm set MyApp Description "FlavorPack application service"
nssm start MyApp

# Or using sc.exe
sc create MyApp binPath= "C:\Path\To\myapp.psp" DisplayName= "My FlavorPack App"
sc start MyApp
```

### Creating Desktop Shortcut

```powershell
# Create shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MyApp.lnk")
$Shortcut.TargetPath = "C:\Path\To\myapp.psp"
$Shortcut.WorkingDirectory = "C:\Path\To"
$Shortcut.IconLocation = "C:\Path\To\icon.ico"
$Shortcut.Description = "My FlavorPack Application"
$Shortcut.Save()
```

### Registry Integration

```powershell
# Add to context menu
$regPath = "Registry::HKEY_CLASSES_ROOT\*\shell\RunWithFlavorPack"
New-Item -Path $regPath -Force
New-ItemProperty -Path $regPath -Name "(Default)" -Value "Run with FlavorPack"
New-Item -Path "$regPath\command" -Force
New-ItemProperty -Path "$regPath\command" -Name "(Default)" `
    -Value '"C:\Path\To\myapp.psp" "%1"'
```

## Development Environment

### Visual Studio Code

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug FlavorPack",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/myapp.psp",
      "console": "integratedTerminal",
      "env": {
        "FLAVOR_LOG_LEVEL": "debug",
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

### Windows Terminal

```json
// Add to Windows Terminal settings.json
{
  "profiles": {
    "list": [
      {
        "name": "FlavorPack Dev",
        "commandline": "powershell.exe -NoExit -Command \"& {Set-Location 'C:\\FlavorPack'; $env:FLAVOR_LOG_LEVEL='debug'}\"",
        "startingDirectory": "C:\\FlavorPack",
        "icon": "🌶️"
      }
    ]
  }
}
```

## Debug Commands

### System Information

```powershell
# System info
systeminfo

# Windows version
Get-ComputerInfo | Select WindowsVersion, WindowsBuildLabEx, OsArchitecture

# Environment variables
Get-ChildItem Env: | Sort-Object Name

# Process information
Get-Process myapp | Format-List *
```

### Performance Monitoring

```powershell
# CPU usage
Get-Counter "\Process(myapp)\% Processor Time"

# Memory usage
Get-Counter "\Process(myapp)\Working Set"

# Disk I/O
Get-Counter "\Process(myapp)\IO Data Bytes/sec"
```

### Event Logs

{% raw %}
```powershell
# Check application events
Get-EventLog -LogName Application -Newest 50 | Where-Object {$_.Message -like "*flavor*"}

# Check system events
Get-EventLog -LogName System -EntryType Error -Newest 20

# Create custom event log
New-EventLog -LogName "FlavorPack" -Source "MyApp"
Write-EventLog -LogName "FlavorPack" -Source "MyApp" -EventId 1 -Message "Application started"
```
{% endraw %}

## Troubleshooting Script

{% raw %}
```powershell
# diagnose-flavor.ps1 - Diagnostic script for FlavorPack on Windows

Write-Host "=== System Information ===" -ForegroundColor Cyan
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "OS: $($os.Caption) $($os.Version)"
Write-Host "Architecture: $($os.OSArchitecture)"

Write-Host "`n=== Python Information ===" -ForegroundColor Cyan
py -0
python --version

Write-Host "`n=== Package Information ===" -ForegroundColor Cyan
Get-Item .\myapp.psp | Format-List Name, Length, LastWriteTime, Attributes

Write-Host "`n=== Security ===" -ForegroundColor Cyan
Get-ExecutionPolicy
Get-MpPreference | Select-Object ExclusionPath, ExclusionProcess

Write-Host "`n=== Environment ===" -ForegroundColor Cyan
$env:Path -split ';' | Select-String -Pattern "flavor|python"
Get-ChildItem Env: | Where-Object {$_.Name -like "FLAVOR*" -or $_.Name -like "PYTHON*"}

Write-Host "`n=== Network ===" -ForegroundColor Cyan
Test-NetConnection pypi.org -Port 443
netsh winhttp show proxy

Write-Host "`n=== Test Execution ===" -ForegroundColor Cyan
& .\myapp.psp --version
```
{% endraw %}

## Getting Help

- Check [Common Issues](../common/) for cross-platform problems
- Review [Security Troubleshooting](../../guide/concepts/security/) for permission issues
- Visit [Community Support](../../community/support/) for additional help

## Related Documentation

- [Installation Guide](../../getting-started/installation/)
- [Platform Support](../../guide/packaging/platforms/)
- [Building Helpers](../../development/helpers/)