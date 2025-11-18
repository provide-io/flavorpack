package operations

import (
	"fmt"
	"io"
)

// Operation constants matching Python/Rust
const (
	// No operation - raw data
	OP_NONE = 0x00

	// Bundle operations (0x01-0x0F)
	OP_TAR = 0x01 // POSIX TAR archive

	// Compression operations (0x10-0x2F)
	OP_GZIP  = 0x10 // GZIP compression
	OP_BZIP2 = 0x13 // BZIP2 compression
	OP_XZ    = 0x16 // XZ/LZMA2 compression
	OP_ZSTD  = 0x1B // Zstandard compression
)

// Operation represents a single transformation operation
type Operation interface {
	// ID returns the operation identifier (e.g., OP_GZIP)
	ID() uint8

	// Name returns the human-readable name
	Name() string

	// Apply applies the operation to input data
	Apply(input []byte) ([]byte, error)

	// ApplyStream applies the operation to a stream
	ApplyStream(input io.Reader, output io.Writer) error

	// Reverse reverses the operation (e.g., decompress for compression)
	Reverse(input []byte) ([]byte, error)

	// ReverseStream reverses the operation on a stream
	ReverseStream(input io.Reader, output io.Writer) error

	// CanReverse returns true if the operation is reversible
	CanReverse() bool

	// EstimateSize estimates the output size given input size
	EstimateSize(inputSize int64) int64
}

// BaseOperation provides common functionality for operations
type BaseOperation struct {
	OpID   uint8
	OpName string
}

func (o *BaseOperation) ID() uint8 {
	return o.OpID
}

func (o *BaseOperation) Name() string {
	return o.OpName
}

func (o *BaseOperation) CanReverse() bool {
	return true // Most operations are reversible
}

func (o *BaseOperation) EstimateSize(inputSize int64) int64 {
	return inputSize // Default: same size
}

// Registry maps operation IDs to implementations
var Registry = make(map[uint8]Operation)

// Register registers an operation implementation
func Register(op Operation) {
	Registry[op.ID()] = op
}

// Get retrieves an operation by ID
func Get(id uint8) (Operation, error) {
	op, ok := Registry[id]
	if !ok {
		return nil, fmt.Errorf("unknown operation: 0x%02x", id)
	}
	return op, nil
}

// GetName returns the name of an operation by ID
func GetName(id uint8) string {
	switch id {
	case OP_NONE:
		return "NONE"
	case OP_TAR:
		return "TAR"
	case OP_GZIP:
		return "GZIP"
	case OP_BZIP2:
		return "BZIP2"
	case OP_XZ:
		return "XZ"
	case OP_ZSTD:
		return "ZSTD"
	default:
		return fmt.Sprintf("UNKNOWN_%02x", id)
	}
}
