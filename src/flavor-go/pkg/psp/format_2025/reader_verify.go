package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
)

// VerifyMagicTrailer verifies the MagicTrailer emoji bookends
func (r *Reader) VerifyMagicTrailer() (bool, error) {
	if err := r.Open(); err != nil {
		return false, err
	}

	info, err := r.file.Stat()
	if err != nil {
		return false, err
	}

	trailer := make([]byte, MagicTrailerSize)
	if _, err := r.file.ReadAt(trailer, info.Size()-MagicTrailerSize); err != nil {
		return false, err
	}

	if !bytes.Equal(trailer[:4], PackageEmojiBytes) {
		return false, ErrInvalidEmojiMagic
	}
	if !bytes.Equal(trailer[MagicTrailerSize-4:], MagicWandEmojiBytes) {
		return false, ErrInvalidEmojiMagic
	}

	return true, nil
}

// VerifyAllChecksums verifies all slot checksums
func (r *Reader) VerifyAllChecksums() error {
	index, err := r.ReadIndex()
	if err != nil {
		return err
	}

	for i := 0; i < int(index.SlotCount); i++ {
		if _, err := r.ReadSlot(i); err != nil {
			return fmt.Errorf("slot %d: %w", i, err)
		}
	}

	return nil
}

// VerifyIntegritySeal verifies the metadata integrity using Ed25519 signature
func (r *Reader) VerifyIntegritySeal() (bool, error) {
	index, err := r.ReadIndex()
	if err != nil {
		return false, err
	}

	// Read metadata archive
	metadataOffset, err := uint64ToInt64Checked(index.MetadataOffset, "metadata offset")
	if err != nil {
		return false, err
	}
	if _, err := r.file.Seek(metadataOffset, io.SeekStart); err != nil {
		return false, err
	}

	archiveData := make([]byte, index.MetadataSize)
	if _, err := r.file.Read(archiveData); err != nil {
		return false, err
	}

	// Extract psp.json and signature from archive
	// Decompress the gzipped JSON metadata
	gr, err := gzip.NewReader(bytes.NewReader(archiveData))
	if err != nil {
		return false, err
	}
	defer func() {
		if err := gr.Close(); err != nil {
			// Log error but don't fail - already returning data
			_ = err
		}
	}()

	// Read the JSON metadata
	jsonData, err := io.ReadAll(gr)
	if err != nil {
		return false, err
	}

	// IntegritySignature is a fixed [512]byte array; only the first 64 bytes carry
	// the Ed25519 signature (the rest are zero-padded). Slicing a fixed array is
	// always in-bounds, so this cannot panic.
	signature := index.IntegritySignature[:64]

	// Check if signature is present (not all zeros)
	allZeros := true
	for _, b := range signature {
		if b != 0 {
			allZeros = false
			break
		}
	}
	if allZeros {
		return false, ErrNoIntegritySeal
	}

	// Verify signature using public key from index
	publicKey := index.PublicKey[:]
	if !ed25519.Verify(publicKey, jsonData, signature) {
		return false, ErrSignatureInvalid
	}
	return true, nil
}

// VerifyAttestationSbomDigest checks that the attestation slot's content matches
// the SHA-256 digest stored in index.AttestationSbomDigest.
//
// Semantics (fail-closed):
//   - digest present + slot present  → verify; mismatch is a hard error
//   - digest present + slot absent   → hard error (digest cannot be satisfied)
//   - digest absent  + slot absent   → skip (backwards-compatible: no attestation)
//   - digest absent  + slot present  → skip (digest not bound yet, treat as no-op)
func (r *Reader) VerifyAttestationSbomDigest() error {
	index, err := r.ReadIndex()
	if err != nil {
		return err
	}

	// Check whether the stored digest is non-zero.
	digestField := index.AttestationSbomDigest[:]
	digestPresent := false
	for _, b := range digestField {
		if b != 0 {
			digestPresent = true
			break
		}
	}

	// Scan all slot descriptors for a slot with lifecycle == LifecycleAttestation.
	slotCount := int(index.SlotCount)
	var attestationDesc *SlotDescriptor
	for i := 0; i < slotCount; i++ {
		slotTableOffset, err := uint64ToInt64Checked(index.SlotTableOffset, "slot table offset")
		if err != nil {
			return fmt.Errorf("seeking slot descriptor %d: %w", i, err)
		}
		entryDelta, err := intToUint64Checked(i*SlotDescriptorSize, "slot descriptor entry offset")
		if err != nil {
			return fmt.Errorf("seeking slot descriptor %d: %w", i, err)
		}
		entryDeltaOffset, err := uint64ToInt64Checked(entryDelta, "slot descriptor entry offset")
		if err != nil {
			return fmt.Errorf("seeking slot descriptor %d: %w", i, err)
		}
		entryOffset := slotTableOffset + entryDeltaOffset
		if _, err := r.file.Seek(entryOffset, io.SeekStart); err != nil {
			return fmt.Errorf("seeking slot descriptor %d: %w", i, err)
		}
		var entryData [SlotDescriptorSize]byte
		if _, err := r.file.Read(entryData[:]); err != nil {
			return fmt.Errorf("reading slot descriptor %d: %w", i, err)
		}
		desc, err := UnpackSlotDescriptor(entryData[:])
		if err != nil {
			return fmt.Errorf("unpacking slot descriptor %d: %w", i, err)
		}
		if desc.Lifecycle == LifecycleAttestation {
			attestationDesc = desc
			break
		}
	}

	if !digestPresent {
		// No digest bound — nothing to verify.
		return nil
	}

	// Digest is present; the attestation slot must also be present.
	if attestationDesc == nil {
		return fmt.Errorf("attestation SBOM digest is set but no attestation slot (lifecycle=%d) found", LifecycleAttestation)
	}

	// Read the raw (as-stored) bytes of the attestation slot.
	attestationOffset, err := uint64ToInt64Checked(attestationDesc.Offset, "attestation slot offset")
	if err != nil {
		return fmt.Errorf("seeking attestation slot data: %w", err)
	}
	if _, err := r.file.Seek(attestationOffset, io.SeekStart); err != nil {
		return fmt.Errorf("seeking attestation slot data: %w", err)
	}
	slotBytes := make([]byte, attestationDesc.Size)
	if _, err := r.file.Read(slotBytes); err != nil {
		return fmt.Errorf("reading attestation slot data: %w", err)
	}

	// Verify the per-slot checksum first so we know the bytes are intact.
	hash := sha256.Sum256(slotBytes)
	actualChecksum := binary.LittleEndian.Uint64(hash[:8])
	if actualChecksum != attestationDesc.Checksum {
		return fmt.Errorf("attestation slot data checksum mismatch (slot integrity failure)")
	}

	// Compute SHA-256 of the raw (compressed-as-stored) slot content and compare
	// against the hex-ASCII digest stored in the index.
	slotDigest := sha256.Sum256(slotBytes)
	computedHex := hex.EncodeToString(slotDigest[:])

	// Strip trailing null bytes from the stored field and interpret as ASCII hex.
	storedHex := string(bytes.TrimRight(digestField, "\x00"))

	if computedHex != storedHex {
		return fmt.Errorf("attestation SBOM digest mismatch: stored %q, computed %q", storedHex, computedHex)
	}

	return nil
}

// VerifyAttestationPolicyHash checks that the package-declared policy JSON hashes
// to the value stored in index.AttestationPolicyHash. Returns nil if the field is
// zero-filled (absent).
//
// Semantics (fail-closed):
//   - hash present + policy present  → serialise policy to canonical JSON, hash it; mismatch = error
//   - hash present + policy absent   → error (hash cannot be satisfied without a policy)
//   - hash absent  + policy absent   → skip (backwards-compatible: no policy hash bound)
//   - hash absent  + policy present  → skip (hash not bound yet, treat as no-op)
func (r *Reader) VerifyAttestationPolicyHash() error {
	index, err := r.ReadIndex()
	if err != nil {
		return fmt.Errorf("reading index: %w", err)
	}

	stored := bytes.TrimRight(index.AttestationPolicyHash[:], "\x00")
	if len(stored) == 0 {
		return nil // field absent — skip
	}

	metadata, err := r.ReadMetadata()
	if err != nil {
		return fmt.Errorf("reading metadata: %w", err)
	}

	if len(metadata.PolicyRaw) == 0 {
		return fmt.Errorf("attestation_policy_hash is set but package has no policy in metadata")
	}

	// Unmarshal raw bytes to map[string]interface{}, then re-marshal.
	// encoding/json sorts map keys alphabetically, matching Python's sort_keys=True.
	var policyMap map[string]interface{}
	if err := json.Unmarshal(metadata.PolicyRaw, &policyMap); err != nil {
		return fmt.Errorf("parsing raw policy JSON: %w", err)
	}
	canonical, err := json.Marshal(policyMap)
	if err != nil {
		return fmt.Errorf("serialising policy to canonical JSON: %w", err)
	}
	computed := fmt.Sprintf("%x", sha256.Sum256(canonical))

	if computed != string(stored) {
		return fmt.Errorf("attestation_policy_hash mismatch: index=%s computed=%s", stored, computed)
	}
	return nil
}
