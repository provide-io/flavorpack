# Flavor (Progressive Secure Package Format) v0.1 Structure

## Binary Layout Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Flavor Binary File                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    UV Binary (Optional)                      │    │
│  │  - Package manager binary                                    │    │
│  │  - Can be compressed (zstd) if flag 0x0001 is set          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Python Installation Archive (.tar.gz)           │    │
│  │  - Complete Python runtime                                   │    │
│  │  - Standard library                                          │    │
│  │  - pip/setuptools                                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Metadata Archive (.tar.gz)                  │    │
│  │  - provider_manifest.json                                    │    │
│  │  - config.json                                               │    │
│  │  - Build information                                         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Payload Archive (.tar.gz)                   │    │
│  │  - Provider package and dependencies                         │    │
│  │  - Virtual environment                                       │    │
│  │  - All required Python packages                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Package Signature                          │    │
│  │  - ECDSA signature of entire package                         │    │
│  │  - Signs all content up to this point                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Public Key (PEM)                           │    │
│  │  - ECDSA public key for signature verification               │    │
│  │  - PEM encoded                                                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                 Flavor Footer (120 bytes)                       │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │ Offset  │ Size │ Field                          │ Type       │    │
│  ├─────────┼──────┼────────────────────────────────┼────────────┤    │
│  │ 0       │ 8    │ uv_binary_offset               │ uint64     │    │
│  │ 8       │ 8    │ uv_binary_size                 │ uint64     │    │
│  │ 16      │ 8    │ python_install_tgz_offset      │ uint64     │    │
│  │ 24      │ 8    │ python_install_tgz_size        │ uint64     │    │
│  │ 32      │ 8    │ metadata_tgz_offset            │ uint64     │    │
│  │ 40      │ 8    │ metadata_tgz_size              │ uint64     │    │
│  │ 48      │ 8    │ payload_tgz_offset             │ uint64     │    │
│  │ 56      │ 8    │ payload_tgz_size               │ uint64     │    │
│  │ 64      │ 8    │ package_signature_offset       │ uint64     │    │
│  │ 72      │ 8    │ package_signature_size         │ uint64     │    │
│  │ 80      │ 8    │ public_key_pem_offset          │ uint64     │    │
│  │ 88      │ 8    │ public_key_pem_size            │ uint64     │    │
│  │ 96      │ 2    │ pspf_version (0x0001)          │ uint16     │    │
│  │ 98      │ 2    │ flags                          │ uint16     │    │
│  │ 100     │ 4    │ footer_struct_checksum         │ uint32     │    │
│  │ 104     │ 4    │ internal_footer_magic (0x30505350) │ uint32 │    │
│  │ 108     │ 4    │ language_emoji                 │ [4]byte    │    │
│  │ 112     │ 4    │ type_emoji_1                   │ [4]byte    │    │
│  │ 116     │ 4    │ type_emoji_2                   │ [4]byte    │    │
│  └─────────┴──────┴────────────────────────────────┴────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              EOF Magic Delimiter (Variable)                  │    │
│  │                                                               │    │
│  │  Builder:  🏗️FLAVOR🏗️  (for build tools)                     │    │
│  │  Package:  📦FLAVOR📦  (for package files)                   │    │
│  │  Launcher: 🚀FLAVOR🚀  (for runtime executables)             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. **File Structure**
The Flavor format stores multiple components in a single binary file:
- Optional UV binary for package management
- Python runtime installation
- Metadata about the package
- The actual payload (provider code and dependencies)
- Cryptographic signature and public key

### 2. **Footer Navigation**
To read a Flavor file:
1. Seek to end of file minus EOF magic size
2. Read and verify EOF magic (identifies component type)
3. Seek back 120 bytes from EOF magic to read footer
4. Verify footer magic (0x30505350 = '0PSP')
5. Check Flavor version (currently 0x0001)
6. Validate footer checksum
7. Use offsets and sizes to extract components

### 3. **Component Types via Emoji Delimiters**
Different binaries use different EOF magic strings:
- **Builder** (🏗️FLAVOR🏗️): Used by packaging tools
- **Package** (📦FLAVOR📦): Standard Flavor package files
- **Launcher** (🚀FLAVOR🚀): Self-extracting executables

### 4. **Security Features**
- ECDSA signature validates package integrity
- Public key included for verification
- Checksum protects footer structure
- Magic numbers prevent misinterpretation

### 5. **Compression**
- UV binary can be zstd compressed (flag 0x0001)
- Other components use standard gzip compression

### 6. **Footer Emoji Fields**
The last 12 bytes of footer can store emoji metadata:
- `language_emoji`: Programming language (e.g., 💙 for Go, 🐍 for Python)
- `type_emoji_1`: Component type (e.g., 🏗️ for packager)
- `type_emoji_2`: Additional metadata (e.g., 📦 for payload)

## Example Reading Process

```python
# Read from end of file
with open("package.flavor", "rb") as f:
    # Check EOF magic
    f.seek(-len(FLAVOR_PACKAGE_MAGIC), 2)
    magic = f.read()
    assert magic == FLAVOR_PACKAGE_MAGIC
    
    # Read footer
    f.seek(-(FOOTER_SIZE + len(FLAVOR_PACKAGE_MAGIC)), 2)
    footer_bytes = f.read(FOOTER_SIZE)
    footer = FlavorFooter.unpack(footer_bytes)
    
    # Verify Flavor format
    assert footer.internal_footer_magic == 0x30505350  # '0PSP'
    assert footer.pspf_version == 0x0001
    
    # Extract components using offsets
    f.seek(footer.payload_tgz_offset)
    payload = f.read(footer.payload_tgz_size)
```

## Benefits

1. **Self-contained**: Everything needed in one file
2. **Cross-platform**: Works on any OS with Python
3. **Secure**: Cryptographic signatures ensure integrity
4. **Efficient**: Direct offset access to components
5. **Extensible**: Version field allows format evolution
6. **Type-aware**: Emoji delimiters identify binary purpose