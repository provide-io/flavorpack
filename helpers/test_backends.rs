// Quick test of backend compilation
use flavor::psp::format_2025::backends::{MMapBackend, Backend};
use flavor::psp::format_2025::slots::SlotDescriptor;
use std::path::Path;

fn main() {
    println!("Testing backend compilation...");
    
    // Create backend
    let mut backend = MMapBackend::new();
    
    // Test basic operations
    let path = Path::new("test.pspf");
    if let Err(e) = backend.open(path) {
        println!("Expected error opening non-existent file: {:?}", e);
    }
    
    // Create a slot descriptor
    let slot = SlotDescriptor::new(1)
        .with_name("test_slot");
    
    println!("Slot descriptor created: id={}, hash={:x}", slot.id, slot.name_hash);
    
    println!("✅ Basic structures compile successfully!");
}