package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"os"
	"testing"
)

func TestReaderVerifyMagicTrailer(t *testing.T) {
	t.Parallel()

	bundlePath := buildPolicyHashBundle(t, nil, "")
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	ok, err := reader.VerifyMagicTrailer()
	if err != nil || !ok {
		t.Fatalf("VerifyMagicTrailer() = %v, %v", ok, err)
	}
}

func TestReaderVerifyAllChecksumsAndMetadataArchive(t *testing.T) {
	t.Parallel()

	slotContent := []byte("sbom content")
	digest := sha256.Sum256(slotContent)
	bundlePath := buildAttestationBundle(t, slotContent, hex.EncodeToString(digest[:]))
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	if err := reader.VerifyAllChecksums(); err != nil {
		t.Fatalf("VerifyAllChecksums() error = %v", err)
	}

	archive, err := reader.ReadMetadataArchive()
	if err != nil {
		t.Fatalf("ReadMetadataArchive() error = %v", err)
	}
	gr, err := gzip.NewReader(bytes.NewReader(archive))
	if err != nil {
		t.Fatalf("gzip.NewReader() error = %v", err)
	}
	defer gr.Close()
	data, err := io.ReadAll(gr)
	if err != nil {
		t.Fatalf("ReadAll() error = %v", err)
	}
	if !json.Valid(data) {
		t.Fatalf("expected valid metadata json, got %q", string(data))
	}
}

func TestReaderVerifyIntegritySeal(t *testing.T) {
	t.Parallel()

	f, err := os.CreateTemp(t.TempDir(), "pspf-signed-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp(): %v", err)
	}
	defer f.Close()

	metaJSON := []byte(`{"package":{"name":"signed","version":"1.0.0"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)

	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey(): %v", err)
	}
	sig := ed25519.Sign(priv, metaJSON)

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		SlotTableOffset: uint64(len(gzMeta)),
		SlotTableSize:   0,
		SlotCount:       0,
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
	}
	metaHash := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], metaHash[:])
	copy(idx.PublicKey[:], pub)
	copy(idx.IntegritySignature[:], sig)

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	reader, err := NewReader(f.Name())
	if err != nil {
		t.Fatalf("NewReader(): %v", err)
	}
	defer reader.Close()

	ok, err := reader.VerifyIntegritySeal()
	if err != nil || !ok {
		t.Fatalf("VerifyIntegritySeal() = %v, %v", ok, err)
	}
}
