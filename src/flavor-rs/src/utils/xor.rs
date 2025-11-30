//! XOR encoding utilities for PSPF magic bytes obfuscation.

/// XOR key - digits of π (memorable, non-obvious)
pub const XOR_KEY: &[u8] = &[3, 1, 4, 1, 5, 9, 2, 6]; // First 8 digits of π

/// XOR encode data with repeating key
pub fn xor_encode(data: &[u8], key: &[u8]) -> Vec<u8> {
    let key = if key.is_empty() { XOR_KEY } else { key };
    data.iter()
        .enumerate()
        .map(|(i, &b)| b ^ key[i % key.len()])
        .collect()
}

/// XOR decode data with repeating key (XOR is symmetric)
pub fn xor_decode(data: &[u8], key: &[u8]) -> Vec<u8> {
    xor_encode(data, key) // XOR is its own inverse
}

/// XOR encode with default π key
pub fn xor_encode_default(data: &[u8]) -> Vec<u8> {
    xor_encode(data, XOR_KEY)
}

/// XOR decode with default π key
pub fn xor_decode_default(data: &[u8]) -> Vec<u8> {
    xor_encode(data, XOR_KEY)
}

/// Const function for compile-time XOR encoding (for fixed-size arrays)
pub const fn xor_const<const N: usize>(data: &[u8], key: &[u8]) -> [u8; N] {
    let mut result = [0u8; N];
    let mut i = 0;
    while i < N && i < data.len() {
        result[i] = data[i] ^ key[i % key.len()];
        i += 1;
    }
    result
}
