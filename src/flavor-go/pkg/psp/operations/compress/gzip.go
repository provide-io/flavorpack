package compress

import (
	"bytes"
	"compress/gzip"
	"fmt"
	"io"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/operations"
)

func init() {
	// Register GZIP operation on package init
	operations.Register(&GzipOperation{})
}

// GzipOperation implements GZIP compression
type GzipOperation struct {
	operations.BaseOperation
}

// NewGzipOperation creates a new GZIP operation
func NewGzipOperation() *GzipOperation {
	return &GzipOperation{
		BaseOperation: operations.BaseOperation{
			OpID:   operations.OP_GZIP,
			OpName: "GZIP",
		},
	}
}

// Apply compresses data using GZIP
func (o *GzipOperation) Apply(input []byte) ([]byte, error) {
	var buf bytes.Buffer

	gw := gzip.NewWriter(&buf)
	if _, err := gw.Write(input); err != nil {
		gw.Close()
		return nil, fmt.Errorf("writing gzip data: %w", err)
	}

	if err := gw.Close(); err != nil {
		return nil, fmt.Errorf("closing gzip writer: %w", err)
	}

	return buf.Bytes(), nil
}

// ApplyStream compresses a stream using GZIP
func (o *GzipOperation) ApplyStream(input io.Reader, output io.Writer) error {
	gw := gzip.NewWriter(output)
	defer gw.Close()

	if _, err := io.Copy(gw, input); err != nil {
		return fmt.Errorf("compressing stream: %w", err)
	}

	return gw.Close()
}

// Reverse decompresses GZIP data
func (o *GzipOperation) Reverse(input []byte) ([]byte, error) {
	buf := bytes.NewReader(input)

	gr, err := gzip.NewReader(buf)
	if err != nil {
		return nil, fmt.Errorf("creating gzip reader: %w", err)
	}
	defer gr.Close()

	data, err := io.ReadAll(gr)
	if err != nil {
		return nil, fmt.Errorf("reading gzip data: %w", err)
	}

	return data, nil
}

// ReverseStream decompresses a GZIP stream
func (o *GzipOperation) ReverseStream(input io.Reader, output io.Writer) error {
	gr, err := gzip.NewReader(input)
	if err != nil {
		return fmt.Errorf("creating gzip reader: %w", err)
	}
	defer gr.Close()

	if _, err := io.Copy(output, gr); err != nil {
		return fmt.Errorf("decompressing stream: %w", err)
	}

	return nil
}

// EstimateSize estimates compressed size
func (o *GzipOperation) EstimateSize(inputSize int64) int64 {
	// GZIP typically achieves 60-70% compression on text
	// Use conservative 80% for binary data
	return (inputSize*8)/10 + 18 // +18 for gzip header/trailer
}
