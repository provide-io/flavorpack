# uv + FlavorPack Integration Plan
## "uv pack" - Standalone Python Executable Generation

**Version:** 1.0
**Date:** 2025-10-22
**Status:** Design Document
**Author:** FlavorPack Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [flavor-rs Library Integration](#flavor-rs-library-integration)
4. [Implementation Phases](#implementation-phases)
5. [Detailed Checklist](#detailed-checklist)
6. [Launcher Strategy](#launcher-strategy)
7. [Testing Strategy](#testing-strategy)
8. [Success Criteria](#success-criteria)

---

## Executive Summary

This document outlines the integration of FlavorPack's PSPF/2025 packaging system into the `uv` package manager as a native `uv pack` command. The integration leverages the existing `flavor-rs` Rust library to provide standalone executable generation capabilities directly within uv's workflow.

### Key Points

- **Library Integration**: uv will depend on the `flavor` crate (src/flavor-rs) as a library dependency
- **Native Rust**: No Python dependency - pure Rust implementation using existing flavor-rs API
- **MVP Strategy**: Start with reading PSP files (proves integration), then add building (uses same library)
- **Embedded Launchers**: Both flavor-go-launcher and flavor-rs-launcher binaries embedded in uv
- **User Choice**: `--launcher` flag allows selection between rust/go/auto
- **Cross-Compatibility**: Packages created by `uv pack` work with both launcher types
- **Progressive Implementation**: 6 phases from prototype to production

### MVP Approach: Reading First, Building Second

**Why this order?**
1. **Lower Risk**: Reading PSP files is simpler - proves flavor-rs integration works
2. **Same Library**: If `flavor::verify_package()` works, `flavor::build_package()` will too
3. **Testable**: Can test with existing FlavorPack-created PSP files immediately
4. **Logical Flow**: Must understand the format before building it

**Phase 1 delivers both:**
- `uv pack inspect <file.psp>` - Read and display package info
- `uv pack verify <file.psp>` - Validate signatures/integrity
- `uv pack extract <file.psp>` - Extract contents
- `uv pack build` - Create new packages

This proves round-trip compatibility: FlavorPack → uv (read) → uv (build) → Both launchers (execute)

### Value Proposition

```
Before:  uv sync → uv build → pyinstaller → docker build
After:   uv sync → uv pack → scp to server → done
```

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          uv CLI                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ uv pack [OPTIONS]                                          │ │
│  │  --platform linux_x86_64                                   │ │
│  │  --launcher rust|go|auto                                   │ │
│  │  --sign --compression zstd                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    uv-pack (new crate)                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ pub fn pack(config: PackConfig) -> Result<PathBuf>         │ │
│  │                                                             │ │
│  │ Uses:                                                       │ │
│  │ - uv-workspace (project discovery)                         │ │
│  │ - uv-resolver (dependency resolution)                      │ │
│  │ - uv-build-frontend (wheel building)                       │ │
│  │ - uv-python (Python runtime acquisition)                   │ │
│  │ - flavor (PSPF package building) ← NEW DEPENDENCY         │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│           flavor-rs (existing Rust library)                     │
│  /REDACTED_ABS_PATH        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ pub fn build_package(                                      │ │
│  │     manifest: &Path,                                       │ │
│  │     output: &Path,                                         │ │
│  │     options: BuildOptions                                  │ │
│  │ ) -> Result<()>                                            │ │
│  │                                                             │ │
│  │ Modules:                                                    │ │
│  │ - psp::format_2025::builder (package assembly)             │ │
│  │ - psp::format_2025::slots (slot management)                │ │
│  │ - psp::format_2025::crypto (Ed25519 signing)               │ │
│  │ - psp::operations (operation chains)                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Embedded Launcher Binaries                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ const LAUNCHER_RS_LINUX_X86_64: &[u8] =                   │ │
│  │     include_bytes!("launchers/flavor-rs-launcher-linux");  │ │
│  │                                                             │ │
│  │ const LAUNCHER_GO_LINUX_X86_64: &[u8] =                   │ │
│  │     include_bytes!("launchers/flavor-go-launcher-linux");  │ │
│  │                                                             │ │
│  │ Platform matrix: linux/darwin/windows × x86_64/arm64       │ │
│  │ Launcher types: rust, go                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                             ↓
                  ┌──────────────────────┐
                  │   myapp.psp          │
                  │ (PSPF/2025 Package)  │
                  └──────────────────────┘
```

### Integration Points with uv

| uv Component | Integration Point | Purpose |
|--------------|-------------------|---------|
| `uv-cli` | Add `Commands::Pack(PackArgs)` | New CLI command |
| `uv-workspace` | Parse `pyproject.toml` | Discover project metadata, entry points |
| `uv-resolver` | Resolve dependency graph | Determine all wheels to bundle |
| `uv-build-frontend` | Build wheels | Create wheel files for bundling |
| `uv-python` | Download Python runtime | Acquire target Python version for embedding |
| `uv-platform-tags` | Platform detection | Determine target platforms |
| `uv-configuration` | Configuration management | Extend with `[tool.uv.pack]` settings |
| `uv-distribution` | Wheel introspection | Analyze wheels for metadata |

---

## flavor-rs Library Integration

### Library Structure

The `flavor-rs` library (located at `src/flavor-rs/`) is a complete Rust implementation of PSPF/2025:

```toml
# src/flavor-rs/Cargo.toml
[package]
name = "flavor"
version = "0.3.0"
edition = "2024"

[lib]
name = "flavor"
path = "src/lib.rs"

[[bin]]
name = "flavor-rs-launcher"
path = "src/bin/flavor-rs-launcher.rs"

[[bin]]
name = "flavor-rs-builder"
path = "src/bin/flavor-rs-builder.rs"
```

### Public API

```rust
// flavor-rs/src/api.rs
pub struct BuildOptions {
    pub launcher_bin: Option<PathBuf>,
    pub skip_verification: bool,
    pub private_key_path: Option<PathBuf>,
    pub public_key_path: Option<PathBuf>,
    pub key_seed: Option<String>,
    pub workenv_base: Option<PathBuf>,
}

pub fn build_package(
    manifest_path: &Path,
    output_path: &Path,
    options: BuildOptions,
) -> Result<()>

pub fn verify_package(package_path: &Path) -> Result<VerifyResult>

pub fn launch_package(
    package_path: &Path,
    args: &[String],
    options: LaunchOptions
) -> Result<i32>
```

### Integration Approach

#### Option 1: Git Dependency (Recommended for Prototype)

```toml
# uv/Cargo.toml
[dependencies]
flavor = { git = "https://github.com/provide-io/flavorpack", path = "src/flavor-rs" }
```

#### Option 2: Path Dependency (Development)

```toml
# uv/Cargo.toml
[dependencies]
flavor = { path = "../flavorpack/src/flavor-rs" }
```

#### Option 3: Published Crate (Production)

```toml
# uv/Cargo.toml
[dependencies]
flavor = "0.3"
```

### Key Modules Used by uv

```rust
// In uv-pack/src/lib.rs
use flavor::{
    BuildOptions,
    build_package,
    verify_package,
};
use flavor::psp::format_2025::{
    constants,
    slots::SlotDescriptor,
    manifest::BuildManifest,
};
use flavor::exceptions::FlavorError;
```

### Manifest Generation

uv will generate PSPF manifests from `pyproject.toml`:

```rust
// uv-pack/src/manifest.rs
pub fn generate_manifest(
    project: &Workspace,
    wheels: &[PathBuf],
    python_runtime: &Path,
) -> BuildManifest {
    BuildManifest {
        format: "PSPF/2025".into(),
        name: project.package.name.clone(),
        version: project.package.version.clone(),
        slots: vec![
            // Slot 0: Python runtime
            SlotConfig {
                id: "python".into(),
                source: python_runtime.to_str().unwrap().into(),
                purpose: "runtime".into(),
                lifecycle: "runtime".into(),
                operations: "tgz".into(),
                target: "{workenv}".into(),
            },
            // Slot 1: Wheels
            SlotConfig {
                id: "wheels".into(),
                source: create_wheels_tarball(wheels)?,
                purpose: "payload".into(),
                lifecycle: "cache".into(),
                operations: "tgz".into(),
                target: "wheels".into(),
            },
        ],
        execution: ExecutionConfig {
            command: format!("python -m {}", project.package.entry_point),
            environment: HashMap::new(),
        },
    }
}
```

---

## Implementation Phases

### Phase 0: Preparation (Week 1)

**Goal:** Set up development environment and validate approach

**Tasks:**
1. ✅ Research uv codebase structure
2. ✅ Validate flavor-rs API compatibility
3. ✅ Create this design document
4. ⬜ Set up development fork of uv
5. ⬜ Create feature branch: `feature/uv-pack-integration`
6. ⬜ Verify flavor-rs builds and tests pass
7. ⬜ Extract launcher binaries from flavorpack builds

**Deliverables:**
- Development environment ready
- flavor-rs library validated
- Launcher binaries collected
- Design document approved

---

### Phase 1: PSP Reading & Basic Building (Week 2-3)

**Goal:** Create working prototype that can read existing PSP files and build simple packages

**Rationale:** Reading and building use the same `flavor-rs` library - if we integrate the library to read PSP files, building capability comes nearly for free. The MVP demonstrates both directions of the format.

**Tasks:**

#### 1.1 Create uv-pack Crate
```bash
cd uv/crates
cargo new uv-pack --lib
```

File: `crates/uv-pack/Cargo.toml`
```toml
[package]
name = "uv-pack"
version = "0.1.0"
edition = "2021"

[dependencies]
flavor = { path = "../../../flavorpack/src/flavor-rs" }
uv-workspace = { path = "../uv-workspace" }
uv-python = { path = "../uv-python" }
anyhow = "1.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tempfile = "3.0"
```

#### 1.2 Create PSP Reading Commands (PRIORITY)
File: `crates/uv-pack/src/reader.rs`
```rust
use flavor::{verify_package, VerifyResult};
use std::path::Path;

/// Inspect PSP package contents
pub fn inspect(package_path: &Path) -> Result<()> {
    let result = verify_package(package_path)?;

    println!("Package: {} v{}", result.package_name, result.package_version);
    println!("Format: {} ({})", result.format, result.version);
    println!("Slots: {}", result.slot_count);
    println!("Signature: {}", if result.signature_valid { "✅ Valid" } else { "❌ Invalid" });

    // Read and display detailed slot information
    let reader = flavor::psp::format_2025::reader::PSPFReader::new(package_path)?;
    for slot in reader.slots() {
        println!("  - {}: {} ({} bytes)", slot.id, slot.purpose, slot.size);
    }

    Ok(())
}

/// Verify PSP package integrity
pub fn verify(package_path: &Path) -> Result<bool> {
    let result = verify_package(package_path)?;

    if result.signature_valid {
        println!("✅ Package signature is valid");
        println!("✅ All checksums verified");
        Ok(true)
    } else {
        println!("❌ Package signature invalid or missing");
        Ok(false)
    }
}

/// Extract PSP package contents
pub fn extract(package_path: &Path, output_dir: &Path) -> Result<()> {
    use flavor::psp::format_2025::extraction;

    extraction::extract_package(package_path, output_dir)?;
    println!("✅ Extracted to: {}", output_dir.display());

    Ok(())
}
```

#### 1.3 Add CLI Subcommands
File: `crates/uv-cli/src/lib.rs`
```rust
#[derive(Subcommand)]
pub enum Commands {
    // ... existing commands

    /// Work with PSPF packages
    Pack(PackCommand),
}

#[derive(Args)]
pub struct PackCommand {
    #[command(subcommand)]
    pub command: PackSubcommand,
}

#[derive(Subcommand)]
pub enum PackSubcommand {
    /// Inspect package contents
    Inspect(InspectArgs),

    /// Verify package integrity
    Verify(VerifyArgs),

    /// Extract package contents
    Extract(ExtractArgs),

    /// Build new package (comes later in Phase 1)
    Build(BuildArgs),
}

#[derive(Args)]
pub struct InspectArgs {
    /// Path to PSP package
    pub package: PathBuf,
}

#[derive(Args)]
pub struct VerifyArgs {
    /// Path to PSP package
    pub package: PathBuf,
}

#[derive(Args)]
pub struct ExtractArgs {
    /// Path to PSP package
    pub package: PathBuf,

    /// Output directory
    #[arg(short, long)]
    pub output: PathBuf,
}
```

**Test Reading Commands:**
```bash
# Get an existing PSP package from flavorpack
cp /path/to/flavorpack/tests/fixtures/example.psp /tmp/

# Test inspect
uv pack inspect /tmp/example.psp

# Test verify
uv pack verify /tmp/example.psp

# Test extract
uv pack extract /tmp/example.psp --output /tmp/extracted
```

#### 1.4 Create Launcher Embedding Module
File: `crates/uv-pack/src/launchers.rs`
```rust
/// Embedded launcher binaries
/// Generated during build from flavorpack artifacts

// Rust launchers
pub const LAUNCHER_RS_LINUX_X86_64: &[u8] =
    include_bytes!("../launchers/flavor-rs-launcher-linux_x86_64");
pub const LAUNCHER_RS_DARWIN_ARM64: &[u8] =
    include_bytes!("../launchers/flavor-rs-launcher-darwin_arm64");
pub const LAUNCHER_RS_WINDOWS_X86_64: &[u8] =
    include_bytes!("../launchers/flavor-rs-launcher-windows_x86_64.exe");

// Go launchers
pub const LAUNCHER_GO_LINUX_X86_64: &[u8] =
    include_bytes!("../launchers/flavor-go-launcher-linux_x86_64");
pub const LAUNCHER_GO_DARWIN_ARM64: &[u8] =
    include_bytes!("../launchers/flavor-go-launcher-darwin_arm64");
pub const LAUNCHER_GO_WINDOWS_X86_64: &[u8] =
    include_bytes!("../launchers/flavor-go-launcher-windows_x86_64.exe");

pub enum LauncherType {
    Rust,
    Go,
    Auto,
}

pub fn select_launcher(
    platform: &str,
    launcher_type: LauncherType,
) -> &'static [u8] {
    // Implementation
}
```

#### 1.3 Create Core Pack Function
File: `crates/uv-pack/src/lib.rs`
```rust
pub struct PackConfig {
    pub project_dir: PathBuf,
    pub output: PathBuf,
    pub platform: String,
    pub launcher_type: LauncherType,
    pub sign: bool,
    pub compression: String,
}

pub fn pack(config: PackConfig) -> Result<PathBuf> {
    // 1. Discover project
    let workspace = Workspace::discover(&config.project_dir)?;

    // 2. Build wheels (reuse uv-build-frontend)
    let wheels = build_wheels(&workspace)?;

    // 3. Get Python runtime (reuse uv-python)
    let python = download_python(&workspace.python_version)?;

    // 4. Generate PSPF manifest
    let manifest = generate_manifest(&workspace, &wheels, &python)?;

    // 5. Select launcher
    let launcher = select_launcher(&config.platform, config.launcher_type);

    // 6. Build package using flavor-rs
    let options = BuildOptions {
        launcher_bin: Some(write_launcher_temp(launcher)?),
        skip_verification: false,
        private_key_path: if config.sign { /* ... */ } else { None },
        ..Default::default()
    };

    flavor::build_package(&manifest, &config.output, options)?;

    Ok(config.output)
}
```

#### 1.4 Add CLI Command
File: `crates/uv-cli/src/lib.rs`
```rust
#[derive(Subcommand)]
pub enum Commands {
    // ... existing commands

    /// Create standalone executable package
    Pack(PackArgs),
}

#[derive(Args)]
pub struct PackArgs {
    /// Source directory (default: current directory)
    #[arg(long)]
    pub src: Option<PathBuf>,

    /// Output path (default: dist/{name}.psp)
    #[arg(short, long)]
    pub output: Option<PathBuf>,

    /// Target platform (default: current)
    #[arg(long)]
    pub platform: Option<String>,

    /// Launcher type: rust, go, auto
    #[arg(long, default_value = "auto")]
    pub launcher: String,

    /// Sign package
    #[arg(long)]
    pub sign: bool,
}
```

#### 1.5 Implement Command Handlers
File: `crates/uv/src/commands/pack.rs`
```rust
use uv_pack::{reader, builder};

pub async fn pack(command: PackCommand) -> Result<ExitStatus> {
    match command.command {
        PackSubcommand::Inspect(args) => {
            reader::inspect(&args.package)?;
            Ok(ExitStatus::Success)
        }

        PackSubcommand::Verify(args) => {
            let valid = reader::verify(&args.package)?;
            Ok(if valid { ExitStatus::Success } else { ExitStatus::Failure })
        }

        PackSubcommand::Extract(args) => {
            reader::extract(&args.package, &args.output)?;
            Ok(ExitStatus::Success)
        }

        PackSubcommand::Build(args) => {
            let config = PackConfig {
                project_dir: args.src.unwrap_or_else(|| PathBuf::from(".")),
                output: args.output.unwrap_or_else(|| /* default */),
                platform: args.platform.unwrap_or_else(|| current_platform()),
                launcher_type: parse_launcher_type(&args.launcher)?,
                sign: args.sign,
                compression: "gzip".into(),
            };

            let package_path = builder::pack(config)?;

            writeln!(
                stdout,
                "✅ Package created: {}",
                package_path.display()
            )?;

            Ok(ExitStatus::Success)
        }
    }
}
```

**Phase 1 Testing Strategy:**
```bash
# Step 1: Test reading existing PSP files (FIRST)
# Get a PSP package from flavorpack
cd /path/to/flavorpack
make test  # This creates test PSP files
cp tests/pretaster/packages/*.psp /tmp/test.psp

# Test uv pack reading commands
uv pack inspect /tmp/test.psp
uv pack verify /tmp/test.psp
uv pack extract /tmp/test.psp --output /tmp/extracted

# Step 2: Test building (SECOND - once reading works)
cd /tmp/hello-world-app
uv pack build --output hello.psp

# Step 3: Test round-trip (build then read)
uv pack inspect hello.psp
uv pack verify hello.psp
./hello.psp
# → "Hello, World!"
```

**Deliverables:**
- ✅ Working `uv pack inspect` command (reads existing PSP files)
- ✅ Working `uv pack verify` command (validates signatures)
- ✅ Working `uv pack extract` command (extracts contents)
- ✅ Working `uv pack build` command (creates simple Python apps)
- ✅ Supports both Rust and Go launchers
- ✅ Round-trip works: build → inspect → verify → execute

---

### Phase 2: Dependency Resolution & Bundling (Week 4-5)

**Goal:** Properly resolve and bundle all dependencies

**Tasks:**

#### 2.1 Integrate uv-resolver
```rust
// uv-pack/src/resolver.rs
use uv_resolver::{Resolver, InMemoryIndex};

pub async fn resolve_dependencies(
    workspace: &Workspace,
    platform: &Platform,
) -> Result<Vec<Wheel>> {
    let index = InMemoryIndex::default();

    let resolution = Resolver::new(
        workspace.requirements(),
        &index,
        /* ... */
    )
    .with_platform(platform)
    .resolve()
    .await?;

    // Convert resolution to wheel paths
    Ok(resolution.wheels())
}
```

#### 2.2 Wheel Bundling
```rust
// uv-pack/src/bundler.rs
pub fn create_wheels_slot(wheels: &[PathBuf]) -> Result<SlotConfig> {
    let temp_dir = tempfile::tempdir()?;
    let tarball = temp_dir.path().join("wheels.tar.gz");

    // Create tar.gz of all wheels
    let tar_gz = File::create(&tarball)?;
    let enc = GzEncoder::new(tar_gz, Compression::default());
    let mut tar = tar::Builder::new(enc);

    for wheel in wheels {
        tar.append_path_with_name(wheel, wheel.file_name().unwrap())?;
    }

    tar.finish()?;

    Ok(SlotConfig {
        id: "wheels".into(),
        source: tarball.to_str().unwrap().into(),
        purpose: "payload".into(),
        lifecycle: "cache".into(),
        operations: "tgz".into(),
        target: "wheels".into(),
    })
}
```

#### 2.3 Python Runtime Embedding
```rust
// uv-pack/src/python.rs
use uv_python::{PythonDownload, PythonVersion};

pub async fn prepare_python_runtime(
    version: &PythonVersion,
    platform: &Platform,
) -> Result<PathBuf> {
    // Download Python if needed
    let python = PythonDownload::fetch(version, platform).await?;

    // Extract minimal runtime
    let minimal = extract_minimal_runtime(&python)?;

    // Create tarball
    let tarball = create_tarball(&minimal)?;

    Ok(tarball)
}
```

**Test:**
```bash
# App with dependencies
cd /tmp/flask-app
cat pyproject.toml
# [project]
# dependencies = ["flask", "requests"]

uv pack --output app.psp

# Verify all dependencies bundled
uv pack inspect app.psp
# ✅ flask-3.0.0-py3-none-any.whl
# ✅ requests-2.31.0-py3-none-any.whl
# ✅ ... (all transitive dependencies)
```

**Deliverables:**
- Full dependency resolution
- Wheel bundling
- Python runtime embedding
- Complex apps work

---

### Phase 3: Cross-Platform Support (Week 6-7)

**Goal:** Enable building for multiple platforms from single host

**Tasks:**

#### 3.1 Platform Matrix
```rust
// uv-pack/src/platform.rs
pub struct PlatformMatrix {
    platforms: Vec<Platform>,
}

pub enum Platform {
    LinuxX86_64,
    LinuxAarch64,
    DarwinX86_64,
    DarwinArm64,
    WindowsX86_64,
}

impl Platform {
    pub fn launcher_name(&self, launcher_type: LauncherType) -> &str {
        match (self, launcher_type) {
            (Platform::LinuxX86_64, LauncherType::Rust) =>
                "flavor-rs-launcher-linux_x86_64",
            (Platform::LinuxX86_64, LauncherType::Go) =>
                "flavor-go-launcher-linux_x86_64",
            // ... all combinations
        }
    }
}
```

#### 3.2 Multi-Platform Build
```rust
// uv-pack/src/multi.rs
pub async fn pack_multi_platform(
    workspace: &Workspace,
    platforms: &[Platform],
    base_config: &PackConfig,
) -> Result<Vec<PathBuf>> {
    let mut packages = vec![];

    for platform in platforms {
        // Resolve platform-specific dependencies
        let wheels = resolve_dependencies(workspace, platform).await?;

        // Get platform-specific Python
        let python = prepare_python_runtime(&workspace.python_version, platform).await?;

        // Build platform-specific package
        let output = format!("dist/{}-{}.psp", workspace.name, platform);
        let config = PackConfig {
            platform: platform.to_string(),
            output: PathBuf::from(&output),
            ..base_config.clone()
        };

        packages.push(pack(config)?);
    }

    Ok(packages)
}
```

**Test:**
```bash
# Build for all platforms
uv pack --platform linux_x86_64 --platform darwin_arm64 --platform windows_x86_64

# Output:
# ✅ dist/myapp-linux_x86_64.psp
# ✅ dist/myapp-darwin_arm64.psp
# ✅ dist/myapp-windows_x86_64.psp
```

**Deliverables:**
- Cross-platform builds
- Platform-specific dependency resolution
- All platform/launcher combinations work

---

### Phase 4: Configuration & Optimization (Week 8-9)

**Goal:** Add pyproject.toml configuration and optimization features

#### 4.1 pyproject.toml Configuration
```toml
# pyproject.toml
[tool.uv.pack]
# Output configuration
output = "dist/{name}-{version}-{platform}.psp"
platforms = ["linux_x86_64", "darwin_arm64"]

# Python configuration
python-version = "3.12"
embed-python = true
minimal-runtime = false

# Entry points (or use [project.scripts])
entry-point = "myapp.cli:main"

# Bundling
standalone = true
include-tests = false

# Optimization
compression = "zstd"
compression-level = 6
strip-binaries = true

# Security
sign = true
private-key = "${UV_PACK_PRIVATE_KEY}"

# Custom slots
[[tool.uv.pack.slots]]
id = "config"
source = "config/"
purpose = "config"
lifecycle = "runtime"
target = "{workenv}/config"
```

#### 4.2 Configuration Parser
```rust
// uv-pack/src/config.rs
#[derive(Deserialize)]
pub struct UvPackConfig {
    pub output: Option<String>,
    pub platforms: Option<Vec<String>>,
    pub python_version: Option<String>,
    pub compression: Option<String>,
    pub slots: Option<Vec<SlotConfig>>,
    // ...
}

pub fn load_config(workspace: &Workspace) -> Result<UvPackConfig> {
    workspace.pyproject
        .tool
        .get("uv")
        .and_then(|uv| uv.get("pack"))
        .map(serde_json::from_value)
        .transpose()?
        .unwrap_or_default()
}
```

#### 4.3 Optimization Options
```rust
// uv-pack/src/optimize.rs
pub fn optimize_package(
    package: &Path,
    options: &OptimizeOptions,
) -> Result<()> {
    if options.strip_binaries {
        strip_launcher(package)?;
    }

    if let Some(level) = options.compression_level {
        recompress_slots(package, level)?;
    }

    Ok(())
}
```

**Test:**
```bash
# Use configuration
cat pyproject.toml | grep -A5 "\[tool.uv.pack\]"
uv pack  # Uses config from pyproject.toml

# Override via CLI
uv pack --compression zstd --compression-level 9
```

**Deliverables:**
- pyproject.toml configuration support
- Compression options
- Binary stripping
- Custom slots

---

### Phase 5: Production Readiness (Week 10-12)

**Goal:** Polish, testing, documentation, and CI integration

#### 5.1 Comprehensive Testing
```rust
// uv-pack/tests/integration_test.rs
#[test]
fn test_pack_simple_app() {
    let fixture = Fixture::new("hello_world");
    let result = pack(PackConfig {
        project_dir: fixture.path(),
        ..Default::default()
    }).unwrap();

    assert!(result.exists());

    // Verify package runs
    let output = Command::new(&result).output().unwrap();
    assert_eq!(output.stdout, b"Hello, World!\n");
}

#[test]
fn test_pack_with_dependencies() {
    let fixture = Fixture::new("flask_app");
    // ...
}

#[test]
fn test_cross_platform_build() {
    // ...
}

#[test]
fn test_launcher_compatibility() {
    // Test both Rust and Go launchers
    for launcher in [LauncherType::Rust, LauncherType::Go] {
        // ...
    }
}
```

#### 5.2 Documentation
```markdown
# docs/uv-pack.md

## Usage

### Basic Example
\`\`\`bash
uv pack
\`\`\`

### Advanced Usage
\`\`\`bash
uv pack \
  --platform linux_x86_64 \
  --launcher rust \
  --sign \
  --compression zstd
\`\`\`

### Configuration
See pyproject.toml configuration...
```

#### 5.3 CI Integration
```yaml
# .github/workflows/test-pack.yml
name: Test uv pack
on: [push, pull_request]

jobs:
  test-pack:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        launcher: [rust, go]

    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable

      - name: Build uv with pack support
        run: cargo build --release

      - name: Test pack
        run: cargo test --package uv-pack

      - name: Integration test
        run: |
          ./target/release/uv pack \
            --launcher ${{ matrix.launcher }} \
            tests/fixtures/hello_world
```

**Deliverables:**
- Comprehensive test suite
- Documentation
- CI/CD integration
- Performance benchmarks

---

## Detailed Checklist

### Phase 0: Preparation ✅

- [x] Research uv codebase structure
- [x] Validate flavor-rs API compatibility
- [x] Create design document
- [ ] Fork uv repository
- [ ] Create feature branch: `feature/uv-pack-integration`
- [ ] Build flavor-rs and verify tests pass
- [ ] Extract launcher binaries from flavorpack:
  - [ ] flavor-rs-launcher (Linux x86_64, macOS arm64, Windows x86_64)
  - [ ] flavor-go-launcher (Linux x86_64, macOS arm64, Windows x86_64)
- [ ] Create `uv/launchers/` directory structure

### Phase 1: PSP Reading & Basic Building ⬜

**MVP Focus:** Prove we can integrate flavor-rs by reading PSP files first, then building

#### Crate Setup
- [ ] Create `crates/uv-pack/` directory
- [ ] Write `crates/uv-pack/Cargo.toml` with dependencies
- [ ] Add flavor-rs as dependency (path or git)
- [ ] Create `crates/uv-pack/src/lib.rs` with module structure
- [ ] Add uv-pack to workspace in root `Cargo.toml`

#### PSP Reading (FIRST - Core MVP)
- [ ] Create `crates/uv-pack/src/reader.rs`
- [ ] Implement `inspect()` function using `flavor::verify_package()`
- [ ] Implement `verify()` function for signature validation
- [ ] Implement `extract()` function for package extraction
- [ ] Add CLI subcommands: `inspect`, `verify`, `extract`
- [ ] Test with existing PSP files from flavorpack
- [ ] Verify slot reading works
- [ ] Verify signature validation works
- [ ] Verify extraction works

#### Launcher Embedding (SECOND)
- [ ] Create `crates/uv-pack/launchers/` directory
- [ ] Copy launcher binaries to launchers directory
- [ ] Create `crates/uv-pack/src/launchers.rs`
- [ ] Implement `include_bytes!` for all launchers
- [ ] Implement `select_launcher()` function
- [ ] Add tests for launcher selection

#### Core Functionality
- [ ] Create `crates/uv-pack/src/manifest.rs`
- [ ] Implement `generate_manifest()` function
- [ ] Create `crates/uv-pack/src/lib.rs`
- [ ] Implement basic `pack()` function
- [ ] Add project discovery using uv-workspace
- [ ] Add Python runtime handling using uv-python

#### CLI Integration
- [ ] Modify `crates/uv-cli/src/lib.rs`
- [ ] Add `PackArgs` struct
- [ ] Add `Commands::Pack` variant
- [ ] Create `crates/uv/src/commands/pack.rs`
- [ ] Implement `pack()` command handler
- [ ] Wire up command in `crates/uv/src/lib.rs`

#### Testing
- [ ] Create test fixture: simple hello world app
- [ ] Test `uv pack` with Rust launcher
- [ ] Test `uv pack` with Go launcher
- [ ] Verify package executes correctly
- [ ] Test `--help` output

### Phase 2: Dependency Resolution ⬜

#### Resolver Integration
- [ ] Create `crates/uv-pack/src/resolver.rs`
- [ ] Integrate uv-resolver for dependency resolution
- [ ] Handle platform-specific dependencies
- [ ] Test with app that has dependencies (e.g., Flask)

#### Wheel Bundling
- [ ] Create `crates/uv-pack/src/bundler.rs`
- [ ] Implement `create_wheels_slot()`
- [ ] Create tar.gz of all wheel files
- [ ] Add wheel slot to manifest
- [ ] Test bundling with complex dependency tree

#### Python Runtime
- [ ] Create `crates/uv-pack/src/python.rs`
- [ ] Implement Python runtime acquisition
- [ ] Create minimal Python runtime extraction
- [ ] Create Python runtime slot
- [ ] Test with different Python versions (3.9, 3.10, 3.11, 3.12)

#### Build System Integration
- [ ] Integrate uv-build-frontend for wheel building
- [ ] Handle project wheel building
- [ ] Handle dependency wheel downloads
- [ ] Test with source distributions (sdists)

### Phase 3: Cross-Platform Support ⬜

#### Platform Abstraction
- [ ] Create `crates/uv-pack/src/platform.rs`
- [ ] Define `Platform` enum
- [ ] Implement platform detection
- [ ] Implement launcher selection per platform
- [ ] Test platform parsing

#### Multi-Platform Builds
- [ ] Create `crates/uv-pack/src/multi.rs`
- [ ] Implement `pack_multi_platform()`
- [ ] Add `--platform` CLI flag (can be repeated)
- [ ] Resolve dependencies per platform
- [ ] Test building for all platforms from single host

#### Platform Testing
- [ ] Test Linux x86_64 packages
- [ ] Test macOS arm64 packages
- [ ] Test Windows x86_64 packages
- [ ] Test launcher compatibility across platforms
- [ ] Test both Rust and Go launchers per platform

### Phase 4: Configuration & Optimization ⬜

#### Configuration
- [ ] Create `crates/uv-pack/src/config.rs`
- [ ] Define `UvPackConfig` struct
- [ ] Implement `[tool.uv.pack]` parsing from pyproject.toml
- [ ] Implement configuration merging (file + CLI + env vars)
- [ ] Add configuration validation
- [ ] Document all configuration options

#### Compression Options
- [ ] Add `--compression` flag (gzip/zstd/xz/brotli)
- [ ] Add `--compression-level` flag
- [ ] Wire up to flavor-rs compression options
- [ ] Test compression types
- [ ] Benchmark compression ratios and speeds

#### Optimization
- [ ] Create `crates/uv-pack/src/optimize.rs`
- [ ] Implement `--strip-binaries` flag
- [ ] Implement binary stripping
- [ ] Add minimal runtime mode
- [ ] Test size reductions

#### Custom Slots
- [ ] Support `[[tool.uv.pack.slots]]` in pyproject.toml
- [ ] Implement custom slot generation
- [ ] Test with config files
- [ ] Test with static assets

### Phase 5: Production Readiness ⬜

#### Testing
- [ ] Create `crates/uv-pack/tests/` directory
- [ ] Write unit tests for all modules
- [ ] Create integration test fixtures
- [ ] Test simple apps
- [ ] Test apps with dependencies
- [ ] Test multi-platform builds
- [ ] Test launcher compatibility (Rust vs Go)
- [ ] Test signing and verification
- [ ] Test compression options
- [ ] Add performance benchmarks

#### Security
- [ ] Implement `--sign` flag
- [ ] Integrate Ed25519 key generation
- [ ] Support `--private-key` and `--public-key` flags
- [ ] Support deterministic `--key-seed`
- [ ] Implement `uv pack verify` subcommand
- [ ] Test signature validation
- [ ] Document security best practices

#### Documentation
- [ ] Write `docs/uv-pack.md`
- [ ] Document CLI commands
- [ ] Document configuration options
- [ ] Add usage examples
- [ ] Add troubleshooting guide
- [ ] Update main README with `uv pack`
- [ ] Create migration guide from PyInstaller

#### CI/CD
- [ ] Add `test-pack.yml` workflow
- [ ] Test on Linux, macOS, Windows
- [ ] Test all launcher types
- [ ] Add release workflow for launchers
- [ ] Add integration test matrix
- [ ] Add performance regression tests

#### Polish
- [ ] Improve error messages
- [ ] Add progress indicators
- [ ] Add `--verbose` flag for debugging
- [ ] Implement `uv pack inspect` subcommand
- [ ] Implement `uv pack extract` subcommand
- [ ] Add shell completion
- [ ] Optimize build performance

### Phase 6: Release ⬜

- [ ] Code review
- [ ] Update CHANGELOG
- [ ] Create release notes
- [ ] Write blog post
- [ ] Submit PR to uv
- [ ] Address review feedback
- [ ] Merge to main
- [ ] Release announcement

---

## Launcher Strategy

### Both Launchers Supported

Packages created by `uv pack` will work with **both** flavor-go-launcher and flavor-rs-launcher because:

1. **Common Format**: Both launchers implement PSPF/2025 reader
2. **Compatible Operations**: Both support the same operation chains (tar, gzip, etc.)
3. **Identical Structure**: Packages have the same binary layout
4. **Standard Index**: Both read the 8192-byte index block

### Launcher Selection

```rust
pub enum LauncherType {
    Rust,  // Use flavor-rs-launcher
    Go,    // Use flavor-go-launcher
    Auto,  // Choose best for platform (default: Rust)
}
```

**Auto Selection Logic:**
1. Prefer Rust launcher (better performance, smaller size)
2. Fall back to Go launcher if Rust not available for platform
3. Respect user override via `--launcher` flag

### Usage Examples

```bash
# Default (auto = Rust)
uv pack

# Explicit Rust launcher
uv pack --launcher rust

# Explicit Go launcher
uv pack --launcher go

# Per-platform launcher selection
uv pack \
  --platform linux_x86_64 --launcher rust \
  --platform windows_x86_64 --launcher go
```

### Compatibility Matrix

| Platform | Rust Launcher | Go Launcher | Default |
|----------|--------------|-------------|---------|
| Linux x86_64 | ✅ | ✅ | Rust |
| Linux arm64 | ✅ | ✅ | Rust |
| macOS x86_64 | ✅ | ✅ | Rust |
| macOS arm64 | ✅ | ✅ | Rust |
| Windows x86_64 | ✅ | ✅ | Rust |
| Windows arm64 | ✅ | ❌ | Rust |

### Binary Embedding

Launchers are embedded using `include_bytes!`:

```rust
// Compile-time embedding
const LAUNCHERS: &[(&str, &str, &[u8])] = &[
    // (platform, launcher_type, binary_data)
    ("linux_x86_64", "rust", include_bytes!("../launchers/flavor-rs-launcher-linux_x86_64")),
    ("linux_x86_64", "go", include_bytes!("../launchers/flavor-go-launcher-linux_x86_64")),
    // ... all combinations
];
```

**Build Process:**
1. FlavorPack builds launchers: `make build-ingredients`
2. Copy launchers to uv: `cp dist/bin/flavor-*-launcher* uv/crates/uv-pack/launchers/`
3. uv build embeds them: `cargo build --release`
4. uv binary contains all launchers (~20-30 MB total)

---

## Testing Strategy

### Test Pyramid

```
                    ┌─────────────────┐
                    │   E2E Tests     │  Manual testing
                    │  (pretaster)    │  Real-world apps
                    └────────┬────────┘
                             │
                   ┌─────────┴──────────┐
                   │ Integration Tests  │  uv pack full flow
                   │  (cargo test)      │  Fixtures + execution
                   └─────────┬──────────┘
                             │
              ┌──────────────┴───────────────┐
              │      Unit Tests              │  Individual modules
              │   (inline + tests/)          │  Isolated logic
              └──────────────────────────────┘
```

### Test Categories

#### 1. Unit Tests
Location: `crates/uv-pack/src/*.rs` (inline) + `tests/unit/`

```rust
#[cfg(test)]
mod tests {
    #[test]
    fn test_platform_detection() { /* ... */ }

    #[test]
    fn test_launcher_selection() { /* ... */ }

    #[test]
    fn test_manifest_generation() { /* ... */ }
}
```

#### 2. Integration Tests
Location: `crates/uv-pack/tests/`

```rust
// tests/integration_test.rs
#[test]
fn test_pack_hello_world() {
    let fixture = TestFixture::new("hello_world");
    let result = uv_pack::pack(PackConfig {
        project_dir: fixture.path(),
        output: fixture.output("app.psp"),
        ..Default::default()
    }).unwrap();

    // Verify package exists and executes
    assert!(result.exists());
    let output = Command::new(&result).output().unwrap();
    assert_eq!(output.stdout, b"Hello, World!\n");
}
```

#### 3. Cross-Launcher Tests
```rust
#[test]
fn test_launcher_compatibility() {
    let fixture = TestFixture::new("simple_app");

    // Build with Rust launcher
    let rust_pkg = pack_with_launcher(&fixture, LauncherType::Rust)?;

    // Build with Go launcher
    let go_pkg = pack_with_launcher(&fixture, LauncherType::Go)?;

    // Both should produce identical output
    let rust_out = execute(&rust_pkg)?;
    let go_out = execute(&go_pkg)?;
    assert_eq!(rust_out, go_out);
}
```

#### 4. Cross-Platform Tests
```bash
# GitHub Actions matrix
for os in ubuntu-latest macos-latest windows-latest; do
    for launcher in rust go; do
        uv pack --launcher $launcher
        ./dist/app.psp --version
    done
done
```

#### 5. Pretaster Integration
Use FlavorPack's existing pretaster for PSPF validation:

```bash
# After building with uv pack
cp dist/myapp.psp /path/to/flavorpack/tests/pretaster/packages/

# Run pretaster validation
cd /path/to/flavorpack
pytest tests/pretaster/ -k myapp
```

### Test Fixtures

```
crates/uv-pack/tests/fixtures/
├── hello_world/          # Minimal app, no dependencies
├── flask_app/            # Web app with dependencies
├── cli_tool/             # Entry points, console scripts
├── multi_entry/          # Multiple entry points
├── native_deps/          # Apps with native dependencies
├── complex_deps/         # Large dependency tree
└── signed_app/           # Pre-signed for verification tests
```

### CI Pipeline

```yaml
# .github/workflows/test-uv-pack.yml
test-pack:
  strategy:
    matrix:
      os: [ubuntu-latest, macos-latest, windows-latest]
      python: ["3.9", "3.10", "3.11", "3.12"]
      launcher: [rust, go]

  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Setup Rust
      uses: dtolnay/rust-toolchain@stable

    - name: Build uv
      run: cargo build --release

    - name: Run unit tests
      run: cargo test --package uv-pack

    - name: Run integration tests
      run: cargo test --package uv-pack --test '*'

    - name: Test real app
      run: |
        cd tests/fixtures/flask_app
        ../../../target/release/uv pack \
          --launcher ${{ matrix.launcher }} \
          --python-version ${{ matrix.python }}
        ./dist/app.psp --version
```

---

## Success Criteria

### MVP (Phase 1) - Reading + Building
- [ ] `uv pack inspect` reads and displays PSP package information
- [ ] `uv pack verify` validates package signatures and checksums
- [ ] `uv pack extract` extracts package contents to directory
- [ ] `uv pack build` creates a simple Python app package (hello world)
- [ ] Package executes and produces correct output
- [ ] Works with both Rust and Go launchers
- [ ] Round-trip works: build → inspect → verify → execute
- [ ] Basic documentation exists

**Success Metric:** Can read FlavorPack-created PSP files AND create new ones that both launchers can execute

### Feature Complete (Phase 4)
- [ ] Full dependency resolution and bundling
- [ ] Multi-platform builds from single host
- [ ] pyproject.toml configuration support
- [ ] Compression and optimization options
- [ ] Package signing and verification
- [ ] Comprehensive test coverage (>80%)

### Production Ready (Phase 6)
- [ ] All tests pass on CI across all platforms
- [ ] Documentation complete and reviewed
- [ ] Performance benchmarks meet targets:
  - Package size < 20 MB for simple apps
  - Startup time < 100ms
  - Build time < 10s for simple apps
- [ ] Security audit completed
- [ ] Approved for merge to uv main branch
- [ ] Release announcement published

---

## Architecture Decisions

### Why flavor-rs as Library Dependency?

**Decision:** Use flavor-rs as a Rust library dependency, not Python orchestrator

**Rationale:**
1. **No Python Dependency**: uv is pure Rust, adding Python would break that
2. **Performance**: Native Rust is faster than calling Python
3. **Integration**: Rust library integrates cleanly with uv's architecture
4. **Maintenance**: Shared codebase with standalone FlavorPack
5. **Type Safety**: Rust type system catches errors at compile time

**Implementation:**
```toml
# uv/Cargo.toml
[dependencies]
flavor = { git = "https://github.com/provide-io/flavorpack", path = "src/flavor-rs" }
```

### Why Embed Launchers?

**Decision:** Embed launcher binaries using `include_bytes!`

**Rationale:**
1. **Offline Operation**: No network required after uv installation
2. **Determinism**: Exact launcher versions guaranteed
3. **Simplicity**: No download/cache management
4. **Speed**: Instant access, no download time

**Tradeoff:**
- Larger uv binary (~20-30 MB additional)
- But: acceptable given uv already ~15 MB

### Why Support Both Go and Rust Launchers?

**Decision:** Support both, default to Rust

**Rationale:**
1. **Compatibility**: Existing FlavorPack users may need Go launcher
2. **Flexibility**: Different launchers may have different strengths
3. **Testing**: Validates PSPF format is truly cross-implementation
4. **Migration**: Easier for existing users to adopt uv pack

**Default Choice:** Rust launcher (smaller, faster, more maintainable)

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 0: Preparation | 1 week | Setup, validation, design doc |
| Phase 1: MVP | 2 weeks | Working `uv pack` command |
| Phase 2: Dependencies | 2 weeks | Full dependency resolution |
| Phase 3: Cross-Platform | 2 weeks | Multi-platform builds |
| Phase 4: Configuration | 2 weeks | Config + optimization |
| Phase 5: Production | 3 weeks | Testing, docs, polish |
| **Total** | **12 weeks** | Production-ready integration |

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| flavor-rs API incompatible with uv needs | High | Low | Early API validation, flexible adapter layer |
| Launcher binary size too large | Medium | Low | Use compression, strip debug symbols |
| Cross-platform builds fail | High | Medium | Extensive CI testing, early platform validation |
| Performance slower than PyInstaller | Medium | Low | Benchmark early, optimize hot paths |
| uv maintainers reject PR | High | Medium | Early engagement, clear value proposition |

---

## Next Steps

### Immediate (This Week)
1. ✅ Complete design document
2. ⬜ Share with stakeholders for feedback
3. ⬜ Fork uv repository
4. ⬜ Create feature branch
5. ⬜ Set up development environment

### Short Term (Next 2 Weeks)
1. ⬜ Phase 1: Implement MVP
2. ⬜ Get basic `uv pack` working
3. ⬜ Validate approach with simple apps
4. ⬜ Share prototype for early feedback

### Medium Term (Month 2-3)
1. ⬜ Complete Phase 2-4
2. ⬜ Full feature implementation
3. ⬜ Comprehensive testing
4. ⬜ Documentation

### Long Term (Month 3-4)
1. ⬜ Production readiness
2. ⬜ PR submission
3. ⬜ Review and iteration
4. ⬜ Release

---

## Contact & Resources

**FlavorPack Repository:** https://github.com/provide-io/flavorpack
**uv Repository:** https://github.com/astral-sh/uv
**PSPF Specification:** `flavorpack/spec/pspf_2025/`
**flavor-rs Library:** `flavorpack/src/flavor-rs/`

**Questions?** Open an issue in the FlavorPack repository.

---

**End of Document**
