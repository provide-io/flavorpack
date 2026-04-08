### Build Tools

Building from source requires standard build tools and compilers.

**Linux:**
```bash
# Debian/Ubuntu
sudo apt update
sudo apt install build-essential make git

# RHEL/CentOS/Fedora
sudo yum groupinstall "Development Tools"
sudo yum install make git

# Alpine
sudo apk add build-base make git
```

**macOS:**
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Verify installation
make --version
gcc --version
```

**Windows:**
```powershell
# Install Visual Studio Build Tools
# Download from: https://visualstudio.microsoft.com/downloads/
# Select "Desktop development with C++"

# Or use MinGW-w64
# Download from: https://www.mingw-w64.org/
```

**Verify Build Environment:**
```bash
# Check required tools are available
make --version
git --version
```
