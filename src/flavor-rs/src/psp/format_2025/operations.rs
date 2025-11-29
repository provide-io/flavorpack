// helpers/flavor-rs/src/psp/format_2025/operations.rs
// PSPF 2025 Operations - Protobuf-based operation chains

use log::{debug, trace};

/// Pack operation chain into 64-bit integer
/// Operations are packed as 8-bit values in little-endian order
/// Up to 8 operations can be packed (8 bytes × 8 operations = 64 bits)
pub fn pack_operations(operations: &[u8]) -> u64 {
    trace!(
        "📦 Packing operations: count={} operations={:?}",
        operations.len(),
        operations
    );

    let mut packed: u64 = 0;

    for (index, &op) in operations.iter().enumerate() {
        if index >= 8 {
            log::warn!(
                "⚠️ Too many operations, truncating to 8: provided={}",
                operations.len()
            );
            break;
        }

        let shift = index * 8;
        let op_value = (op as u64) << shift;
        packed |= op_value;

        trace!(
            "🔧 Packed operation: index={} op={} shift={} current={}",
            index, op, shift, packed
        );
    }

    debug!("✅ Operations packed: result={}", packed);
    packed
}

/// Unpack operations from 64-bit integer
/// Returns vector of operation codes in execution order
pub fn unpack_operations(packed: u64) -> Vec<u8> {
    trace!("📂 Unpacking operations: packed={}", packed);

    let mut operations = Vec::new();

    for index in 0..8 {
        let shift = index * 8;
        let mask = 0xFF_u64 << shift;
        let op = ((packed & mask) >> shift) as u8;

        if op != 0 {
            trace!("🔍 Unpacked operation: index={} op={}", index, op);
            operations.push(op);
        }
    }

    debug!(
        "✅ Operations unpacked: count={} operations={:?}",
        operations.len(),
        operations
    );
    operations
}

#[cfg(test)]
mod tests {
    use super::super::constants::{OP_GZIP, OP_TAR};
    use super::*;

    #[test]
    fn test_pack_single_operation() {
        let ops = vec![OP_GZIP];
        let packed = pack_operations(&ops);
        assert_eq!(packed, 0x0000000000000010);
    }

    #[test]
    fn test_pack_multiple_operations() {
        let ops = vec![OP_TAR, OP_GZIP];
        let packed = pack_operations(&ops);
        assert_eq!(packed, 0x0000000000001001);
    }

    #[test]
    fn test_unpack_single_operation() {
        let packed = 0x0000000000000010_u64;
        let ops = unpack_operations(packed);
        assert_eq!(ops, vec![0x10]); // OP_GZIP value
    }

    #[test]
    fn test_unpack_multiple_operations() {
        let packed = 0x0000000000001001_u64;
        let ops = unpack_operations(packed);
        assert_eq!(ops, vec![0x01, 0x10]); // OP_TAR, OP_GZIP values
    }

    #[test]
    fn test_round_trip() {
        let original = vec![OP_TAR, OP_GZIP];
        let packed = pack_operations(&original);
        let unpacked = unpack_operations(packed);
        assert_eq!(original, unpacked);
    }

    #[test]
    fn test_empty_operations() {
        let ops: Vec<u8> = vec![];
        let packed = pack_operations(&ops);
        assert_eq!(packed, 0);

        let unpacked = unpack_operations(0);
        let expected: Vec<u8> = vec![];
        assert_eq!(unpacked, expected);
    }

    #[test]
    fn test_too_many_operations() {
        let ops = vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10]; // 10 operations
        let packed = pack_operations(&ops);
        let unpacked = unpack_operations(packed);
        assert_eq!(unpacked.len(), 8); // Should only have 8
        assert_eq!(unpacked, vec![1, 2, 3, 4, 5, 6, 7, 8]);
    }
}
