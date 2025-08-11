//
// flavor/rust/flavor-launcher-rs/src/flavor.rs
//
use anyhow::Result;
use std::mem;

/// Version of the Progressive Secure Package Format
pub const FLAVOR_VERSION: u16 = 0x0001;

/// InternalFooterMagic is the magic number '0PSP' that identifies the footer struct
pub const FLAVOR_INTERNAL_FOOTER_MAGIC: u32 = 0x30505350;

/// MagicEOFString is the magic byte sequence that marks the end of the file
/// Using emoji: 📦FLAVOR📦 for package files
pub const FLAVOR_MAGIC_EOF_STRING: &[u8] = b"\xf0\x9f\x93\xa6FLAVOR\xf0\x9f\x93\xa6";

/// FlavorFooter defines the structure of the 120-byte footer at the end of a Flavor file
#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
pub struct FlavorFooter {
    pub uv_binary_offset: u64,
    pub uv_binary_size: u64,
    pub python_install_tgz_offset: u64,
    pub python_install_tgz_size: u64,
    pub metadata_tgz_offset: u64,
    pub metadata_tgz_size: u64,
    pub payload_tgz_offset: u64,
    pub payload_tgz_size: u64,
    pub package_signature_offset: u64,
    pub package_signature_size: u64,
    pub public_key_pem_offset: u64,
    pub public_key_pem_size: u64,
    pub flavor_version: u16,
    pub flags: u16,
    pub footer_struct_checksum: u32,
    pub internal_footer_magic: u32,
    pub language_emoji: [u8; 4],
    pub type_emoji_1: [u8; 4],
    pub type_emoji_2: [u8; 4],
}

impl FlavorFooter {
    /// Check if the UV binary compression flag is set
    pub fn is_uv_binary_compressed(&self) -> bool {
        (self.flags & 0x0001) != 0
    }

    /// Create FlavorFooter from raw bytes (little-endian)
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        if bytes.len() != FOOTER_SIZE as usize {
            return Err(anyhow::anyhow!("Invalid footer size: expected {}, got {}", FOOTER_SIZE, bytes.len()));
        }

        let footer = unsafe {
            std::ptr::read_unaligned(bytes.as_ptr() as *const FlavorFooter)
        };

        // Convert from little-endian if necessary (on big-endian systems)
        #[cfg(target_endian = "big")]
        let footer = FlavorFooter {
            uv_binary_offset: footer.uv_binary_offset.swap_bytes(),
            uv_binary_size: footer.uv_binary_size.swap_bytes(),
            python_install_tgz_offset: footer.python_install_tgz_offset.swap_bytes(),
            python_install_tgz_size: footer.python_install_tgz_size.swap_bytes(),
            metadata_tgz_offset: footer.metadata_tgz_offset.swap_bytes(),
            metadata_tgz_size: footer.metadata_tgz_size.swap_bytes(),
            payload_tgz_offset: footer.payload_tgz_offset.swap_bytes(),
            payload_tgz_size: footer.payload_tgz_size.swap_bytes(),
            package_signature_offset: footer.package_signature_offset.swap_bytes(),
            package_signature_size: footer.package_signature_size.swap_bytes(),
            public_key_pem_offset: footer.public_key_pem_offset.swap_bytes(),
            public_key_pem_size: footer.public_key_pem_size.swap_bytes(),
            flavor_version: footer.flavor_version.swap_bytes(),
            flags: footer.flags.swap_bytes(),
            footer_struct_checksum: footer.footer_struct_checksum.swap_bytes(),
            internal_footer_magic: footer.internal_footer_magic.swap_bytes(),
            language_emoji: footer.language_emoji,
            type_emoji_1: footer.type_emoji_1,
            type_emoji_2: footer.type_emoji_2,
        };

        Ok(footer)
    }

    /// Calculate Adler-32 checksum for the footer data
    pub fn calculate_checksum(&self) -> u32 {
        let mut temp_footer = *self;
        temp_footer.footer_struct_checksum = 0;

        let bytes = unsafe {
            std::slice::from_raw_parts(
                &temp_footer as *const FlavorFooter as *const u8,
                mem::size_of::<FlavorFooter>()
            )
        };

        adler32(bytes)
    }
}

/// Footer size constant
pub const FOOTER_SIZE: i64 = mem::size_of::<FlavorFooter>() as i64;

/// Simple Adler-32 implementation
fn adler32(data: &[u8]) -> u32 {
    const MOD_ADLER: u32 = 65521;
    let mut a: u32 = 1;
    let mut b: u32 = 0;

    for byte in data {
        a = (a + *byte as u32) % MOD_ADLER;
        b = (b + a) % MOD_ADLER;
    }

    (b << 16) | a
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_footer_size() {
        assert_eq!(FOOTER_SIZE, 120);
    }

    #[test]
    fn test_magic_constants() {
        assert_eq!(FLAVOR_INTERNAL_FOOTER_MAGIC, 0x30505350);
        assert_eq!(FLAVOR_MAGIC_EOF_STRING, b"\xf0\x9f\x93\xa6FLAVOR\xf0\x9f\x93\xa6");
    }

    #[test]
    fn test_adler32() {
        let test_data = b"hello world";
        let checksum = adler32(test_data);
        assert_ne!(checksum, 0);
    }
}


// 📦🍜📄🪄
