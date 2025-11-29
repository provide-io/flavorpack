package utils

// XORKey - digits of π (memorable, non-obvious)
var XORKey = []byte{3, 1, 4, 1, 5, 9, 2, 6} // First 8 digits of π

// XOREncode encodes data with repeating XOR key
func XOREncode(data []byte, key []byte) []byte {
	if key == nil || len(key) == 0 {
		key = XORKey
	}
	result := make([]byte, len(data))
	for i := range data {
		result[i] = data[i] ^ key[i%len(key)]
	}
	return result
}

// XORDecode decodes data with repeating XOR key (XOR is symmetric)
func XORDecode(data []byte, key []byte) []byte {
	return XOREncode(data, key) // XOR is its own inverse
}

// XOREncodeDefault encodes with default π key
func XOREncodeDefault(data []byte) []byte {
	return XOREncode(data, XORKey)
}

// XORDecodeDefault decodes with default π key
func XORDecodeDefault(data []byte) []byte {
	return XOREncode(data, XORKey)
}
