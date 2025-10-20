package bundle

import (
	"archive/tar"
	"bytes"
	"fmt"
	"io"
	"time"

	"github.com/provide-io/flavor/go/flavor/pkg/psp/operations"
)

func init() {
	// Register TAR operation on package init
	operations.Register(&TarOperation{})
}

// TarOperation implements TAR archive operations
type TarOperation struct {
	operations.BaseOperation
}

// NewTarOperation creates a new TAR operation
func NewTarOperation() *TarOperation {
	return &TarOperation{
		BaseOperation: operations.BaseOperation{
			OpID:   operations.OP_TAR,
			OpName: "TAR",
		},
	}
}

// Apply creates a TAR archive from input data
// Note: This is a simplified implementation - real usage would need
// proper file metadata and multiple file support
func (o *TarOperation) Apply(input []byte) ([]byte, error) {
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)

	// Create a single file entry for the input data
	header := &tar.Header{
		Name:    "data",
		Mode:    0600,
		Size:    int64(len(input)),
		ModTime: time.Now(),
	}

	if err := tw.WriteHeader(header); err != nil {
		return nil, fmt.Errorf("writing tar header: %w", err)
	}

	if _, err := tw.Write(input); err != nil {
		return nil, fmt.Errorf("writing tar data: %w", err)
	}

	if err := tw.Close(); err != nil {
		return nil, fmt.Errorf("closing tar writer: %w", err)
	}

	return buf.Bytes(), nil
}

// ApplyStream creates a TAR archive from stream
func (o *TarOperation) ApplyStream(input io.Reader, output io.Writer) error {
	tw := tar.NewWriter(output)
	defer tw.Close()

	// Read all input for single file (simplified)
	data, err := io.ReadAll(input)
	if err != nil {
		return fmt.Errorf("reading input: %w", err)
	}

	header := &tar.Header{
		Name:    "data",
		Mode:    0600,
		Size:    int64(len(data)),
		ModTime: time.Now(),
	}

	if err := tw.WriteHeader(header); err != nil {
		return fmt.Errorf("writing tar header: %w", err)
	}

	if _, err := tw.Write(data); err != nil {
		return fmt.Errorf("writing tar data: %w", err)
	}

	return nil
}

// Reverse extracts data from a TAR archive
// Note: This extracts the first file only for simplicity
func (o *TarOperation) Reverse(input []byte) ([]byte, error) {
	buf := bytes.NewReader(input)
	tr := tar.NewReader(buf)

	// Read the first file
	header, err := tr.Next()
	if err != nil {
		if err == io.EOF {
			return nil, fmt.Errorf("empty tar archive")
		}
		return nil, fmt.Errorf("reading tar header: %w", err)
	}

	// Validate size
	if header.Size < 0 || header.Size > 1<<30 { // Max 1GB for safety
		return nil, fmt.Errorf("invalid file size: %d", header.Size)
	}

	// Read file contents
	data := make([]byte, header.Size)
	if _, err := io.ReadFull(tr, data); err != nil {
		return nil, fmt.Errorf("reading tar data: %w", err)
	}

	return data, nil
}

// ReverseStream extracts data from a TAR archive stream
func (o *TarOperation) ReverseStream(input io.Reader, output io.Writer) error {
	tr := tar.NewReader(input)

	// Read the first file
	header, err := tr.Next()
	if err != nil {
		if err == io.EOF {
			return fmt.Errorf("empty tar archive")
		}
		return fmt.Errorf("reading tar header: %w", err)
	}

	// Validate size
	if header.Size < 0 || header.Size > 1<<30 { // Max 1GB for safety
		return fmt.Errorf("invalid file size: %d", header.Size)
	}

	// Copy file contents to output
	if _, err := io.CopyN(output, tr, header.Size); err != nil {
		return fmt.Errorf("extracting tar data: %w", err)
	}

	return nil
}

// EstimateSize estimates TAR archive size
func (o *TarOperation) EstimateSize(inputSize int64) int64 {
	// TAR adds 512-byte header + padding to 512-byte boundary
	headerSize := int64(512)
	padding := (512 - (inputSize % 512)) % 512
	return headerSize + inputSize + padding + 1024 // +1024 for end blocks
}
