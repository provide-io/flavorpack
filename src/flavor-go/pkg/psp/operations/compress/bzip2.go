package compress

import (
	"bytes"
	"fmt"
	"io"

	"github.com/dsnet/compress/bzip2"
	"github.com/provide-io/flavor/go/flavor/pkg/psp/operations"
)

func init() {
	operations.Register(&Bzip2Operation{})
}

// Bzip2Operation implements BZIP2 compression
type Bzip2Operation struct {
	operations.BaseOperation
}

// NewBzip2Operation creates a new BZIP2 operation
func NewBzip2Operation() *Bzip2Operation {
	return &Bzip2Operation{
		BaseOperation: operations.BaseOperation{
			OpID:   operations.OP_BZIP2,
			OpName: "BZIP2",
		},
	}
}

// Apply compresses data using BZIP2
func (o *Bzip2Operation) Apply(input []byte) ([]byte, error) {
	var buf bytes.Buffer

	bw, err := bzip2.NewWriter(&buf, &bzip2.WriterConfig{Level: 9})
	if err != nil {
		return nil, fmt.Errorf("creating bzip2 writer: %w", err)
	}

	if _, err := bw.Write(input); err != nil {
		bw.Close()
		return nil, fmt.Errorf("writing bzip2 data: %w", err)
	}

	if err := bw.Close(); err != nil {
		return nil, fmt.Errorf("closing bzip2 writer: %w", err)
	}

	return buf.Bytes(), nil
}

// ApplyStream compresses a stream using BZIP2
func (o *Bzip2Operation) ApplyStream(input io.Reader, output io.Writer) error {
	bw, err := bzip2.NewWriter(output, &bzip2.WriterConfig{Level: 9})
	if err != nil {
		return fmt.Errorf("creating bzip2 writer: %w", err)
	}
	defer bw.Close()

	if _, err := io.Copy(bw, input); err != nil {
		return fmt.Errorf("compressing stream: %w", err)
	}

	return bw.Close()
}

// Reverse decompresses BZIP2 data
func (o *Bzip2Operation) Reverse(input []byte) ([]byte, error) {
	buf := bytes.NewReader(input)

	br, err := bzip2.NewReader(buf, &bzip2.ReaderConfig{})
	if err != nil {
		return nil, fmt.Errorf("creating bzip2 reader: %w", err)
	}
	defer br.Close()

	data, err := io.ReadAll(br)
	if err != nil {
		return nil, fmt.Errorf("reading bzip2 data: %w", err)
	}

	return data, nil
}

// ReverseStream decompresses a BZIP2 stream
func (o *Bzip2Operation) ReverseStream(input io.Reader, output io.Writer) error {
	br, err := bzip2.NewReader(input, &bzip2.ReaderConfig{})
	if err != nil {
		return fmt.Errorf("creating bzip2 reader: %w", err)
	}
	defer br.Close()

	if _, err := io.Copy(output, br); err != nil {
		return fmt.Errorf("decompressing stream: %w", err)
	}

	return nil
}

// EstimateSize estimates compressed size
func (o *Bzip2Operation) EstimateSize(inputSize int64) int64 {
	// BZIP2 typically achieves better compression than GZIP
	return (inputSize*7)/10 + 32 // +32 for bzip2 overhead
}
