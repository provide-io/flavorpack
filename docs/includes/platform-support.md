| Platform | Architecture | Status | Binary Type | Notes |
|----------|-------------|---------|------------|-------|
| Linux | x86_64 | ✅ Full | Static (musl) | CentOS 7+, Ubuntu, Alpine |
| Linux | aarch64 | ✅ Full | Static (musl) | ARM64 servers |
| macOS | x86_64 | ✅ Full | Dynamic | Intel Macs |
| macOS | arm64 | ✅ Full | Dynamic | Apple Silicon |
| Windows | x86_64 | ⚠️ Disabled | Dynamic | Currently disabled due to UTF-8 issues |

!!! warning "Windows Support Status"
    Windows support is currently **disabled** in FlavorPack due to UTF-8 encoding issues in the native helpers. Windows support is planned for a future release once these issues are resolved.
