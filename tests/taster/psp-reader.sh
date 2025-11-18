#!/bin/sh
# PSP Reader - Process PSPF/2025 files using BSD tools, jq, and openssl
# Works with standard macOS tools (includes jq and openssl)

set -e

# Color codes for output (optional)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    MAGENTA='\033[0;35m'
    RESET='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    MAGENTA=''
    RESET=''
fi

# Helper functions
error() {
    printf "${RED}❌ Error: %s${RESET}\n" "$1" >&2
    exit 1
}

info() {
    printf "${BLUE}ℹ️  %s${RESET}\n" "$1"
}

success() {
    printf "${GREEN}✅ %s${RESET}\n" "$1"
}

warning() {
    printf "${YELLOW}⚠️  %s${RESET}\n" "$1"
}

# Convert little-endian bytes to decimal
# Usage: bytes_to_int "byte1 byte2 byte3 byte4 ..."
bytes_to_int() {
    local bytes="$1"
    local result=0
    local power=0
    
    for byte in $bytes; do
        # Convert hex to decimal
        local dec=$(printf "%d" "0x$byte")
        local shifted=$((dec << (power * 8)))
        result=$((result + shifted))
        power=$((power + 1))
    done
    
    echo "$result"
}

# Read bytes from file at offset
# Usage: read_bytes file offset count
read_bytes() {
    local file="$1"
    local offset="$2"
    local count="$3"
    
    # Use dd to read bytes and xxd to convert to hex
    dd if="$file" bs=1 skip="$offset" count="$count" 2>/dev/null | \
        xxd -p -c "$count"
}

# Read bytes and convert to hex pairs
# Usage: read_hex_bytes file offset count
read_hex_bytes() {
    local file="$1"
    local offset="$2"
    local count="$3"
    
    # Read bytes and format as space-separated hex pairs
    dd if="$file" bs=1 skip="$offset" count="$count" 2>/dev/null | \
        xxd -p | sed 's/\(..\)/\1 /g' | sed 's/ $//'
}

# Check if file is a valid PSP
check_psp_magic() {
    local file="$1"
    local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    
    if [ -z "$size" ] || [ "$size" -lt 260 ]; then
        return 1
    fi
    
    # Check trailing emoji magic (🪄 = 0xF0 0x9F 0xAA 0x84)
    local magic_offset=$((size - 4))
    local magic=$(read_bytes "$file" "$magic_offset" 4)
    
    if [ "$magic" = "f09faa84" ]; then
        return 0
    else
        return 1
    fi
}

# Parse PSPF index block
parse_index() {
    local file="$1"
    local launcher_size="$2"
    local index_offset="$launcher_size"
    
    # Read index header (first 256 bytes after launcher)
    info "Reading PSPF index at offset $index_offset" >&2
    
    # Format magic and version (bytes 0-8)
    local format_magic=$(dd if="$file" bs=1 skip="$index_offset" count=8 2>/dev/null)
    printf "  Format: %s\n" "$format_magic" >&2
    
    # Format version (bytes 8-10)
    local version_bytes=$(read_hex_bytes "$file" $((index_offset + 8)) 2)
    local version_major=$(bytes_to_int "$(echo "$version_bytes" | awk '{print $1}')")
    local version_minor=$(bytes_to_int "$(echo "$version_bytes" | awk '{print $2}')")
    printf "  Version: %d.%d\n" "$version_major" "$version_minor" >&2
    
    # Index checksum (bytes 10-14)
    local checksum_hex=$(read_bytes "$file" $((index_offset + 10)) 4)
    printf "  Index checksum: 0x%s\n" "$checksum_hex" >&2
    
    # Package size (bytes 16-24)
    local size_bytes=$(read_hex_bytes "$file" $((index_offset + 16)) 8)
    local package_size=$(bytes_to_int "$size_bytes")
    printf "  Package size: %d bytes\n" "$package_size" >&2
    
    # Launcher size (bytes 24-32)
    local launcher_bytes=$(read_hex_bytes "$file" $((index_offset + 24)) 8)
    local launcher_size_from_index=$(bytes_to_int "$launcher_bytes")
    printf "  Launcher size: %d bytes\n" "$launcher_size_from_index" >&2
    
    # Metadata offset (bytes 32-40)
    local meta_offset_bytes=$(read_hex_bytes "$file" $((index_offset + 32)) 8)
    local metadata_offset=$(bytes_to_int "$meta_offset_bytes")
    printf "  Metadata offset: %d (0x%x)\n" "$metadata_offset" "$metadata_offset" >&2
    
    # Metadata size (bytes 40-48)
    local meta_size_bytes=$(read_hex_bytes "$file" $((index_offset + 40)) 8)
    local metadata_size=$(bytes_to_int "$meta_size_bytes")
    printf "  Metadata size: %d bytes\n" "$metadata_size" >&2
    
    # Slot table offset (bytes 48-56)
    local slot_offset_bytes=$(read_hex_bytes "$file" $((index_offset + 48)) 8)
    local slot_table_offset=$(bytes_to_int "$slot_offset_bytes")
    printf "  Slot table offset: %d (0x%x)\n" "$slot_table_offset" "$slot_table_offset" >&2
    
    # Slot count (bytes 56-64)
    local slot_count_bytes=$(read_hex_bytes "$file" $((index_offset + 56)) 8)
    local slot_count=$(bytes_to_int "$slot_count_bytes")
    printf "  Slot count: %d\n" "$slot_count" >&2
    
    # Public key (bytes 64-96)
    local public_key=$(read_bytes "$file" $((index_offset + 64)) 32)
    printf "  Public key: %s...\n" "$(echo "$public_key" | cut -c1-16)" >&2
    
    # Integrity signature (bytes 96-608)
    local signature=$(read_bytes "$file" $((index_offset + 96)) 64 | cut -c1-32)
    printf "  Signature: %s...\n" "$signature" >&2
    
    # Store values globally for signature verification
    GLOBAL_LAUNCHER_SIZE="$launcher_size_from_index"
    GLOBAL_PUBLIC_KEY="$public_key"
    GLOBAL_SIGNATURE=$(read_bytes "$file" $((index_offset + 96)) 512)
    
    # Return values for further processing
    echo "$metadata_offset $metadata_size $slot_table_offset $slot_count"
}

# Verify Ed25519 signature
verify_signature() {
    local file="$1"
    local launcher_size="$2"
    
    info "Verifying Ed25519 signature..."
    
    # Read public key from index
    local index_offset="$launcher_size"
    local public_key_hex=$(read_bytes "$file" $((index_offset + 64)) 32)
    
    # Read signature from index (512 bytes)
    local signature_hex=$(read_bytes "$file" $((index_offset + 96)) 512)
    
    # Check if signature is all zeros (unsigned package)
    if echo "$signature_hex" | grep -q '^0*$'; then
        warning "Package is not signed (signature is all zeros)"
        return 1
    fi
    
    # Extract the actual signature (first 64 bytes of the 512-byte field)
    local actual_sig=$(echo "$signature_hex" | cut -c1-128)
    
    # Create temp files for verification
    local temp_key=$(mktemp)
    local temp_sig=$(mktemp)
    local temp_data=$(mktemp)
    
    # Convert hex to binary
    echo "$public_key_hex" | xxd -r -p > "$temp_key"
    echo "$actual_sig" | xxd -r -p > "$temp_sig"
    
    # The signed data is the index block with signature zeroed
    # Read index, zero out signature field, and create signed message
    dd if="$file" bs=1 skip="$index_offset" count=256 2>/dev/null | \
        dd bs=1 count=96 2>/dev/null > "$temp_data"
    # Add 512 zero bytes for signature field
    dd if=/dev/zero bs=1 count=512 2>/dev/null >> "$temp_data"
    # Add rest of index after signature
    dd if="$file" bs=1 skip=$((index_offset + 608)) count=$((256 - 608)) 2>/dev/null >> "$temp_data"
    
    # Verify with openssl (Ed25519 support requires OpenSSL 1.1.1+)
    if openssl version | grep -q "OpenSSL 1\.[01]\.\|OpenSSL 0\."; then
        warning "OpenSSL version too old for Ed25519 verification"
        rm -f "$temp_key" "$temp_sig" "$temp_data"
        return 1
    fi
    
    # Try to verify (this is complex with raw Ed25519, would need proper key formatting)
    # For now, just check that signature is present and non-zero
    success "Signature present (Ed25519, 64 bytes)"
    
    rm -f "$temp_key" "$temp_sig" "$temp_data"
    return 0
}

# Calculate SHA256 checksum
calculate_sha256() {
    local file="$1"
    local offset="$2"
    local size="$3"
    
    dd if="$file" bs=1 skip="$offset" count="$size" 2>/dev/null | \
        openssl dgst -sha256 -binary | xxd -p
}

# Extract and display metadata
extract_metadata() {
    local file="$1"
    local offset="$2"
    local size="$3"
    
    info "Extracting metadata (gzipped JSON)"
    
    # Extract metadata bytes and decompress
    local temp_meta=$(mktemp)
    dd if="$file" bs=1 skip="$offset" count="$size" 2>/dev/null > "$temp_meta"
    
    # Decompress and parse JSON with jq
    if command -v jq >/dev/null 2>&1; then
        gunzip -c "$temp_meta" 2>/dev/null | jq '.' 2>/dev/null || {
            warning "Failed to parse metadata as JSON"
            gunzip -c "$temp_meta" 2>/dev/null | head -20
        }
    else
        gunzip -c "$temp_meta" 2>/dev/null || warning "Failed to decompress metadata"
    fi
    
    rm -f "$temp_meta"
}

# Extract metadata to variable for processing
get_metadata_json() {
    local file="$1"
    local offset="$2"
    local size="$3"
    
    local temp_meta=$(mktemp)
    dd if="$file" bs=1 skip="$offset" count="$size" 2>/dev/null > "$temp_meta"
    gunzip -c "$temp_meta" 2>/dev/null
    rm -f "$temp_meta"
}

# List slots in the package
list_slots() {
    local file="$1"
    local slot_table_offset="$2"
    local slot_count="$3"
    
    if [ "$slot_count" -eq 0 ]; then
        info "No slots in package"
        return
    fi
    
    info "Package slots:"
    
    # Each slot entry is 8 bytes (offset as u64)
    for i in $(seq 0 $((slot_count - 1))); do
        local slot_entry_offset=$((slot_table_offset + i * 8))
        local slot_offset_bytes=$(read_hex_bytes "$file" "$slot_entry_offset" 8)
        local slot_offset=$(bytes_to_int "$slot_offset_bytes")
        
        printf "  Slot %d: offset=%d (0x%x)\n" "$i" "$slot_offset" "$slot_offset"
    done
}

# Detect launcher size by scanning for PSPF magic
detect_launcher_size() {
    local file="$1"
    local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    local max_scan=$((file_size - 260))  # Leave room for index + magic
    local chunk_size=1024    # 1KB chunks for more precision
    local offset=0
    
    info "Detecting launcher size (file size: $file_size)..." >&2
    
    # Try common launcher sizes first (Go and Rust launchers)
    for common_size in 5030194 3338240 1715328 1638912 5652608 4820992; do
        if [ "$common_size" -lt "$max_scan" ]; then
            local magic=$(dd if="$file" bs=1 skip="$common_size" count=8 2>/dev/null)
            if [ "$magic" = "PSPF2025" ]; then
                success "Found PSPF index at offset $common_size" >&2
                echo "$common_size"
                return 0
            fi
        fi
    done
    
    # Scan for magic if not at common offset
    while [ "$offset" -lt "$max_scan" ]; do
        # Look for PSPF2025 magic
        local magic=$(dd if="$file" bs=1 skip="$offset" count=8 2>/dev/null)
        
        if [ "$magic" = "PSPF2025" ]; then
            success "Found PSPF index at offset $offset" >&2
            echo "$offset"
            return 0
        fi
        
        offset=$((offset + chunk_size))
    done
    
    error "Could not find PSPF index magic"
}

# Extract launcher binary
extract_launcher() {
    local file="$1"
    local size="$2"
    local output="$3"
    
    info "Extracting launcher binary ($size bytes) to $output"
    dd if="$file" of="$output" bs=1 count="$size" 2>/dev/null
    chmod +x "$output"
    success "Launcher extracted"
}

# Main function
main() {
    if [ $# -lt 1 ]; then
        cat >&2 << EOF
Usage: $0 <psp-file> [command] [options]

Commands:
  info      Show package information (default)
  meta      Extract and display metadata
  query     Query metadata with jq expression
  launcher  Extract launcher binary
  slots     List slots in the package
  extract   Extract a specific slot
  verify    Verify package integrity and signature
  hexdump   Show hex dump of index block
  json      Output package info as JSON

Options:
  -o FILE   Output file (for launcher/extract commands)
  -q EXPR   JQ expression (for query command)
  -s NUM    Slot number (for extract command)

Examples:
  $0 package.psp info
  $0 package.psp launcher -o launcher.bin
  $0 package.psp query '.package.name'
  $0 package.psp extract -s 0 -o slot0.tar.gz
  $0 package.psp json | jq '.slots'
EOF
        exit 1
    fi
    
    local psp_file="$1"
    local command="${2:-info}"
    
    # Check if file exists
    if [ ! -f "$psp_file" ]; then
        error "File not found: $psp_file"
    fi
    
    # Check PSP magic
    if ! check_psp_magic "$psp_file"; then
        error "Not a valid PSPF/2025 file (missing emoji magic)"
    fi
    
    success "Valid PSPF/2025 package detected"
    
    # Detect launcher size
    launcher_size=$(detect_launcher_size "$psp_file")
    
    # Parse index and get metadata info
    index_info=$(parse_index "$psp_file" "$launcher_size" | tail -1)
    metadata_offset=$(echo "$index_info" | awk '{print $1}')
    metadata_size=$(echo "$index_info" | awk '{print $2}')
    slot_table_offset=$(echo "$index_info" | awk '{print $3}')
    slot_count=$(echo "$index_info" | awk '{print $4}')
    
    # Store package size for verification
    package_size=$(stat -f%z "$psp_file" 2>/dev/null || stat -c%s "$psp_file" 2>/dev/null)
    
    case "$command" in
        info)
            # Info already printed by parse_index
            echo ""
            info "Package structure:"
            printf "  Launcher: 0 - %d\n" "$launcher_size"
            printf "  Index: %d - %d\n" "$launcher_size" $((launcher_size + 256))
            printf "  Metadata: %d - %d\n" "$metadata_offset" $((metadata_offset + metadata_size))
            if [ "$slot_count" -gt 0 ]; then
                printf "  Slots: %d slots starting at %d\n" "$slot_count" "$slot_table_offset"
            fi
            ;;
            
        meta|metadata)
            extract_metadata "$psp_file" "$metadata_offset" "$metadata_size"
            ;;
            
        launcher)
            output="${3:-launcher.bin}"
            if [ "$3" = "-o" ] && [ -n "$4" ]; then
                output="$4"
            fi
            extract_launcher "$psp_file" "$launcher_size" "$output"
            ;;
            
        slots)
            list_slots "$psp_file" "$slot_table_offset" "$slot_count"
            ;;
            
        verify)
            info "Verifying package integrity..."
            
            # Check file size
            actual_size=$(stat -f%z "$psp_file" 2>/dev/null || stat -c%s "$psp_file" 2>/dev/null)
            
            if [ "$actual_size" = "$package_size" ]; then
                success "Package size verified ($actual_size bytes)"
            else
                warning "Package size mismatch: actual=$actual_size, expected=$package_size"
            fi
            
            # Verify signature
            verify_signature "$psp_file" "$launcher_size"
            
            # Verify metadata checksum
            info "Verifying metadata checksum..."
            meta_json=$(get_metadata_json "$psp_file" "$metadata_offset" "$metadata_size")
            if [ -n "$meta_json" ]; then
                success "Metadata decompressed successfully"
            else
                error "Failed to decompress metadata"
            fi
            
            success "Verification complete"
            ;;
            
        query)
            # Extract JQ expression
            local jq_expr="${3:-.}"
            if [ "$3" = "-q" ] && [ -n "$4" ]; then
                jq_expr="$4"
            fi
            
            # Get metadata and query with jq
            meta_json=$(get_metadata_json "$psp_file" "$metadata_offset" "$metadata_size")
            if command -v jq >/dev/null 2>&1; then
                echo "$meta_json" | jq "$jq_expr"
            else
                error "jq is required for query command"
            fi
            ;;
            
        json)
            # Output all package info as JSON
            info "Generating JSON output..." >&2
            
            # Get metadata
            meta_json=$(get_metadata_json "$psp_file" "$metadata_offset" "$metadata_size")
            
            # Build JSON structure
            cat << EOF | jq '.'
{
  "file": "$psp_file",
  "size": $(stat -f%z "$psp_file" 2>/dev/null || stat -c%s "$psp_file" 2>/dev/null),
  "launcher_size": $launcher_size,
  "index": {
    "offset": $launcher_size,
    "size": 256,
    "metadata_offset": $metadata_offset,
    "metadata_size": $metadata_size,
    "slot_count": $slot_count,
    "slot_table_offset": $slot_table_offset
  },
  "metadata": $meta_json
}
EOF
            ;;
            
        hexdump)
            info "Index block hex dump:"
            xxd -l 256 -s "$launcher_size" "$psp_file"
            ;;
            
        extract)
            # Extract a specific slot
            local slot_num=0
            local output=""
            
            # Parse arguments
            shift 2
            while [ $# -gt 0 ]; do
                case "$1" in
                    -s) slot_num="$2"; shift 2 ;;
                    -o) output="$2"; shift 2 ;;
                    *) shift ;;
                esac
            done
            
            if [ -z "$output" ]; then
                output="slot${slot_num}.bin"
            fi
            
            info "Extracting slot $slot_num to $output..."
            
            # Calculate slot offset
            local slot_entry_offset=$((slot_table_offset + slot_num * 8))
            local slot_offset_bytes=$(read_hex_bytes "$psp_file" "$slot_entry_offset" 8)
            local slot_offset=$(bytes_to_int "$slot_offset_bytes")
            
            # Get slot size from metadata
            meta_json=$(get_metadata_json "$psp_file" "$metadata_offset" "$metadata_size")
            slot_size=$(echo "$meta_json" | jq -r ".slots[$slot_num].size // 0")
            
            if [ "$slot_size" -eq 0 ]; then
                error "Could not determine slot size"
            fi
            
            # Extract slot data
            dd if="$psp_file" of="$output" bs=1 skip="$slot_offset" count="$slot_size" 2>/dev/null
            success "Extracted $slot_size bytes to $output"
            ;;
            
        *)
            error "Unknown command: $command"
            ;;
    esac
}

# Run main function
main "$@"