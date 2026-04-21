# Research: Go Compiler/Linker Options for Windows PE Compatibility

## Problem Statement

Windows rejects PSP files created with Go launchers (exit codes 126/139). The PSP format appends PSPF data to the launcher executable, creating a modified binary that Windows won't execute.

**Current build command:**
```bash
CGO_ENABLED=0 go build -buildvcs=false -ldflags="-s -w" -o launcher.exe
```

## Hypothesis

Go compiler/linker flags might produce PE binaries that are more tolerant of having data appended.

## Approaches to Investigate

### 1. Build Modes (`-buildmode`)

Go supports different build modes that affect PE structure:

#### Option A: `-buildmode=pie` (Position Independent Executable)
```bash
CGO_ENABLED=0 go build -buildmode=pie -ldflags="-s -w" -o launcher.exe
```

**Pros:**
- Creates relocatable code that might be more flexible
- Modern security feature (ASLR compatible)

**Cons:**
- May not work with `CGO_ENABLED=0` on Windows
- Might increase binary size
- Still appends data to the binary

**Worth trying:** ⭐⭐⭐

#### Option B: `-buildmode=exe` (explicit default)
```bash
CGO_ENABLED=0 go build -buildmode=exe -ldflags="-s -w" -o launcher.exe
```

**Pros:**
- Explicit control over build mode
- Can combine with other flags

**Worth trying:** ⭐

### 2. Linker Flags (`-ldflags`)

#### Option A: Remove stripping flags `-s -w`
```bash
CGO_ENABLED=0 go build -buildvcs=false -o launcher.exe
```

**Rationale:** Stripped binaries might be more sensitive to modifications. Keeping debug info might add sections that make Windows more tolerant.

**Pros:**
- Preserves DWARF debugging info
- Preserves symbol table
- Creates more "standard" PE structure

**Cons:**
- Significantly larger binaries (~3-5x size)
- Doesn't address the fundamental appending issue

**Worth trying:** ⭐⭐

#### Option B: Windows subsystem control
```bash
CGO_ENABLED=0 go build -ldflags="-s -w -H=windowsgui" -o launcher.exe
# or
CGO_ENABLED=0 go build -ldflags="-s -w -H=windows" -o launcher.exe
```

**Rationale:** Different PE subsystem settings might affect validation.

**Worth trying:** ⭐

#### Option C: Custom import path
```bash
CGO_ENABLED=0 go build -ldflags="-s -w -importcfg=custom.cfg" -o launcher.exe
```

**Worth trying:** ⭐

### 3. Windows-Specific Build Tags

#### Option A: Enable CGO for Windows resource embedding
```bash
# For Windows only
CGO_ENABLED=1 GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o launcher.exe
```

**Rationale:** With CGO, we could use Windows APIs to embed PSPF as a PE resource instead of appending.

**Pros:**
- Could embed data in PE resource section (industry standard)
- Windows loader understands resources
- No appending needed

**Cons:**
- Breaks static linking requirement
- Requires C compiler (MinGW on Windows)
- More complex build process

**Worth trying:** ⭐⭐⭐⭐⭐ (Different approach entirely)

### 4. Custom Linker Script

#### Option A: Reserve space in PE sections
```bash
CGO_ENABLED=0 go build -ldflags="-s -w -extldflags=-Wl,--section-alignment=4096" -o launcher.exe
```

**Rationale:** Control section alignment and padding.

**Worth trying:** ⭐⭐

### 5. Go Version / Toolchain Changes

#### Option A: Try older Go version
```bash
# Go 1.20 vs Go 1.21+ might have different PE generation
go1.20 build -o launcher.exe
```

**Worth trying:** ⭐⭐

#### Option B: Try newer Go version with PE improvements
```bash
# Latest Go might have fixes
go1.22.0 build -o launcher.exe
```

**Worth trying:** ⭐⭐

## Recommended Testing Order

### Phase 1: Low-effort, high-impact (Quick tests)

1. **Remove stripping** - Keep debug symbols
   ```bash
   CGO_ENABLED=0 go build -buildvcs=false -o launcher.exe
   ```

2. **Try PIE mode** - Position independent executable
   ```bash
   CGO_ENABLED=0 go build -buildmode=pie -ldflags="-s -w" -o launcher.exe
   ```

3. **Windows subsystem** - Try different subsystem
   ```bash
   CGO_ENABLED=0 go build -ldflags="-s -w -H=windowsgui" -o launcher.exe
   ```

### Phase 2: Alternative architecture (Requires code changes)

4. **PE Resource Embedding** - Embed PSPF as PE resource
   - Enable CGO for Windows builds
   - Use `github.com/josephspurrier/goversioninfo` or similar
   - Embed PSPF data in `.rsrc` section instead of appending
   - Modify launcher to read from resources instead of EOF

   This is the most promising approach but requires:
   - Builder changes to use resource embedding
   - Launcher changes to read from resources
   - Windows-specific build process

## Alternative: PE Resource Embedding (Deep Dive)

Instead of appending data, embed it in the PE resource section:

### How PE Resources Work

Windows PE files have a `.rsrc` section for resources (icons, manifests, custom data). This is **part of the PE structure**, not appended data.

```
PE File Structure:
┌─────────────────────┐
│ DOS Header          │
├─────────────────────┤
│ PE Headers          │
├─────────────────────┤
│ .text (code)        │
├─────────────────────┤
│ .data (data)        │
├─────────────────────┤
│ .rsrc (resources)   │  ← EMBED PSPF HERE
└─────────────────────┘
```

### Implementation Plan

**1. Builder Side:**
```go
import "github.com/tc-hib/winres"

func embedPSPFAsResource(exePath string, pspfData []byte) error {
    // Create resource set
    rs := winres.ResourceSet{}

    // Add PSPF data as custom resource
    // Type: 10 (RT_RCDATA - raw data)
    // Name: "PSPF"
    // Language: 0x0409 (en-US)
    err := rs.Set(
        winres.RT_RCDATA,
        winres.Name("PSPF"),
        0x0409,
        pspfData,
    )

    // Write resources to EXE
    return rs.WriteToEXE(exePath)
}
```

**2. Launcher Side:**
```go
import (
    "syscall"
    "unsafe"
)

func readPSPFFromResource() ([]byte, error) {
    // Get handle to current EXE
    exe, _ := syscall.UTF16PtrFromString(os.Args[0])
    handle, _ := syscall.LoadLibraryEx(exe, 0, syscall.LOAD_LIBRARY_AS_DATAFILE)
    defer syscall.FreeLibrary(handle)

    // Find PSPF resource
    name, _ := syscall.UTF16PtrFromString("PSPF")
    resInfo, _ := syscall.FindResource(handle, uintptr(unsafe.Pointer(name)), syscall.RT_RCDATA)

    // Load resource
    resData, _ := syscall.LoadResource(handle, resInfo)
    size := syscall.SizeofResource(handle, resInfo)

    // Lock and read
    ptr := syscall.LockResource(resData)
    data := (*[1 << 30]byte)(unsafe.Pointer(ptr))[:size:size]

    return data, nil
}
```

**3. Build Process:**
```bash
# Build launcher without PSPF
CGO_ENABLED=0 go build -o launcher.exe ./cmd/flavor-go-launcher

# Builder embeds PSPF as resource (no appending!)
flavor-go-builder --manifest manifest.json --output app.exe --embed-mode=resource
```

### Advantages of Resource Embedding

✅ **Windows-native** - `.rsrc` section is standard PE structure
✅ **No appending** - Data is part of the PE file, not trailing
✅ **Validated by Windows** - PE loader understands resources
✅ **Industry standard** - How installers (NSIS, Inno Setup) embed data
✅ **Inspectable** - Can view with Resource Hacker, PE tools

### Disadvantages

❌ **Windows-only** - Different approach than Unix (but they work fine)
❌ **Requires syscall** - Launcher needs Windows APIs
❌ **Build complexity** - Need resource embedding tool
❌ **Size limits** - Resources have theoretical limits (4GB should be fine)

## Recommendation

**Short-term (Quick test):** Try removing `-s -w` flags to see if debug symbols help.

**Long-term (Proper fix):** Implement PE resource embedding for Windows Go launcher.

This aligns with how Windows software actually works - installers like NSIS, 7-Zip SFX, and others all use PE resources to embed their payload data.

## Next Steps

1. Create test branch with various build flag combinations
2. Test each approach with Helper Prep + Pretaster
3. If simple flags don't work, implement PE resource embedding
4. Update build system to use different approaches per platform:
   - **Unix**: Keep appending (works fine)
   - **Windows + Rust launcher**: Keep appending with DOS stub expansion
   - **Windows + Go launcher**: Use PE resource embedding

## References

- [Go cmd/link documentation](https://pkg.go.dev/cmd/link)
- [Windows PE format specification](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)
- [github.com/tc-hib/winres](https://github.com/tc-hib/winres) - Go library for Windows resources
- [PE Resource Section](https://learn.microsoft.com/en-us/windows/win32/menurc/resources)
