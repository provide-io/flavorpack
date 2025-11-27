package format_2025

import (
	"bytes"
	"compress/gzip"
	"fmt"
	"io"
)

// Compress compresses data according to the specified codec.
// Supported codecs: "gzip", "none", ""
func Compress(data []byte, codec string) ([]byte, error) {
	switch codec {
	case "gzip":
		var buf bytes.Buffer
		gw := gzip.NewWriter(&buf)
		if _, err := gw.Write(data); err != nil {
			return nil, fmt.Errorf("gzip write failed: %w", err)
		}
		if err := gw.Close(); err != nil {
			return nil, fmt.Errorf("gzip close failed: %w", err)
		}
		return buf.Bytes(), nil
	case "none", "":
		return data, nil
	default:
		return nil, fmt.Errorf("unsupported codec: %s", codec)
	}
}

func Decompress(data []byte, codec string) ([]byte, error) {
	switch codec {
	case "gzip":
		gr, err := gzip.NewReader(bytes.NewReader(data))
		if err != nil {
			return nil, err
		}
		defer func() {
			if err := gr.Close(); err != nil {
				// Log error but don't fail - already returning data
				_ = err
			}
		}()
		return io.ReadAll(gr)
	case "none", "":
		return data, nil
	default:
		return data, nil
	}
}
