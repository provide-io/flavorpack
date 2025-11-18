// helpers/flavor-rs/src/psp/operations/chain.rs
// Operation chain packing/unpacking

use std::collections::HashMap;
use super::operation::OperationError;

/// Pack a list of operations into a 64-bit integer
pub fn pack_operations(operations: &[u8]) -> Result<u64, OperationError> {
    if operations.len() > 8 {
        return Err(OperationError::InvalidData(
            format!("Maximum 8 operations allowed, got {}", operations.len())
        ));
    }
    
    let mut packed = 0u64;
    for (i, &op) in operations.iter().enumerate() {
        packed |= (op as u64) << (i * 8);
    }
    
    Ok(packed)
}

/// Unpack a 64-bit integer into a list of operations
pub fn unpack_operations(packed: u64) -> Vec<u8> {
    let mut operations = Vec::new();
    
    for i in 0..8 {
        let op = ((packed >> (i * 8)) & 0xFF) as u8;
        if op == 0 { // OP_NONE terminates the chain
            break;
        }
        operations.push(op);
    }
    
    operations
}

/// Convert packed operations to human-readable string
pub fn operations_to_string(packed: u64) -> String {
    if packed == 0 {
        return "raw".to_string();
    }
    
    let operations = unpack_operations(packed);
    
    // Check for common operation chains
    let chain_key = operations_to_chain_key(&operations);
    if let Some(name) = COMMON_CHAINS.get(chain_key.as_str()) {
        return name.to_string();
    }
    
    // Fall back to pipe format
    let names: Vec<String> = operations
        .iter()
        .map(|&op| super::operation::get_name(op).to_lowercase())
        .collect();
    
    names.join("|")
}

/// Parse operation string to packed operations
pub fn string_to_operations(op_string: &str) -> Result<u64, OperationError> {
    if op_string.is_empty() || op_string.to_lowercase() == "raw" {
        return Ok(0);
    }
    
    let op_string = op_string.to_lowercase();
    
    // Check for exact match in named chains
    if let Some(ops) = NAMED_CHAINS.get(op_string.as_str()) {
        return pack_operations(ops);
    }
    
    // Handle pipe-separated operations
    if op_string.contains('|') {
        let mut operations = Vec::new();
        for part in op_string.split('|') {
            let part = part.trim().to_uppercase();
            if part.is_empty() {
                continue;
            }
            
            let op = match part.as_str() {
                "TAR" => super::OP_TAR,
                "GZIP" => super::OP_GZIP,
                "BZIP2" => super::OP_BZIP2,
                "XZ" => super::OP_XZ,
                "ZSTD" => super::OP_ZSTD,
                _ => return Err(OperationError::InvalidData(
                    format!("Unsupported v0 operation: {}", part)
                )),
            };
            operations.push(op);
        }
        return pack_operations(&operations);
    }
    
    Err(OperationError::InvalidData(
        format!("Unknown v0 operation string: {}", op_string)
    ))
}

fn operations_to_chain_key(ops: &[u8]) -> String {
    ops.iter()
        .map(|op| format!("{:02x}", op))
        .collect::<Vec<_>>()
        .join("-")
}

lazy_static::lazy_static! {
    static ref COMMON_CHAINS: HashMap<&'static str, &'static str> = {
        let mut m = HashMap::new();
        m.insert("01-10", "tar.gz");
        m.insert("01-13", "tar.bz2");
        m.insert("01-16", "tar.xz");
        m.insert("01-1b", "tar.zst");
        m.insert("10", "gzip");
        m.insert("13", "bzip2");
        m.insert("16", "xz");
        m.insert("1b", "zstd");
        m.insert("01", "tar");
        m
    };
    
    static ref NAMED_CHAINS: HashMap<&'static str, Vec<u8>> = {
        let mut m = HashMap::new();
        m.insert("raw", vec![]);
        m.insert("gzip", vec![super::OP_GZIP]);
        m.insert("bzip2", vec![super::OP_BZIP2]);
        m.insert("xz", vec![super::OP_XZ]);
        m.insert("zstd", vec![super::OP_ZSTD]);
        m.insert("tar", vec![super::OP_TAR]);
        m.insert("tar.gz", vec![super::OP_TAR, super::OP_GZIP]);
        m.insert("tar.bz2", vec![super::OP_TAR, super::OP_BZIP2]);
        m.insert("tar.xz", vec![super::OP_TAR, super::OP_XZ]);
        m.insert("tar.zst", vec![super::OP_TAR, super::OP_ZSTD]);
        m.insert("tgz", vec![super::OP_TAR, super::OP_GZIP]);
        m.insert("tbz2", vec![super::OP_TAR, super::OP_BZIP2]);
        m.insert("txz", vec![super::OP_TAR, super::OP_XZ]);
        m
    };
}