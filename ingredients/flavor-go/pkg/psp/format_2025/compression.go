package format_2025

import (
	"bytes"
	"compress/gzip"
	"io"
)

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
