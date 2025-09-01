use std::fs::File;
use std::io::{self, Read, Seek, SeekFrom, Write};

// Import the constants
const PSPF_VERSION: u32 = 0x20250001;
const MAGIC_TRAILER_SIZE: usize = 8200;
const HEADER_SIZE: usize = 8192;
const PACKAGE_EMOJI_BYTES: &[u8] = &[0xF0, 0x9F, 0x93, 0xA6];  // 📦
const MAGIC_WAND_EMOJI_BYTES: &[u8] = &[0xF0, 0x9F, 0xAA, 0x84];  // 🪄

fn main() -> io::Result<()> {
    // Create test package
    let test_file = "/tmp/test_rust.psp";
    create_test_package(test_file)?;
    println!("✅ Created test package: {}", test_file);
    
    // Test reading it
    test_read_package(test_file)?;
    println!("🎉 All tests passed!");
    
    Ok(())
}

fn create_test_package(path: &str) -> io::Result<()> {
    let mut file = File::create(path)?;
    
    // Write minimal launcher
    let launcher = b"#!/bin/sh\necho test\n";
    file.write_all(launcher)?;
    
    // Create index (simplified - just zeros with version)
    let mut index = vec![0u8; HEADER_SIZE];
    // Write version at start
    index[0..4].copy_from_slice(&PSPF_VERSION.to_le_bytes());
    // Write launcher size at offset 16
    let launcher_size = launcher.len() as u64;
    index[16..24].copy_from_slice(&launcher_size.to_le_bytes());
    
    // Write MagicTrailer
    file.write_all(PACKAGE_EMOJI_BYTES)?;
    file.write_all(&index)?;
    file.write_all(MAGIC_WAND_EMOJI_BYTES)?;
    
    Ok(())
}

fn test_read_package(path: &str) -> io::Result<()> {
    let mut file = File::open(path)?;
    let file_size = file.metadata()?.len();
    
    // Check file size
    if file_size < MAGIC_TRAILER_SIZE as u64 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "File too small for MagicTrailer",
        ));
    }
    
    // Seek to MagicTrailer
    file.seek(SeekFrom::End(-(MAGIC_TRAILER_SIZE as i64)))?;
    
    let mut trailer = vec![0u8; MAGIC_TRAILER_SIZE];
    file.read_exact(&mut trailer)?;
    
    // Verify structure
    if &trailer[0..4] != PACKAGE_EMOJI_BYTES {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("Missing 📦 at start: {:x?}", &trailer[0..4]),
        ));
    }
    println!("✅ Found 📦 at trailer start");
    
    if &trailer[MAGIC_TRAILER_SIZE - 4..] != MAGIC_WAND_EMOJI_BYTES {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("Missing 🪄 at end: {:x?}", &trailer[MAGIC_TRAILER_SIZE - 4..]),
        ));
    }
    println!("✅ Found 🪄 at trailer end");
    
    // Extract index
    let index_data = &trailer[4..4 + HEADER_SIZE];
    
    // Verify version at start
    let version = u32::from_le_bytes([
        index_data[0],
        index_data[1],
        index_data[2],
        index_data[3],
    ]);
    
    if version != PSPF_VERSION {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("Version mismatch: 0x{:08x} != 0x{:08x}", version, PSPF_VERSION),
        ));
    }
    println!("✅ Index version correct: 0x{:08x}", version);
    println!("✅ Index starts with version field");
    
    Ok(())
}