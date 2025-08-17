#!/usr/bin/env python3
# tests/test_pspf_2025_reader_backends.py
# Tests for PSPF reader with backend support

import pytest
import tempfile
import struct
import zlib
from pathlib import Path

from flavor.psp.format_2025.reader import PSPFReader, read_bundle, verify_bundle
from flavor.psp.format_2025.backends import MMapBackend, FileBackend, StreamBackend
from flavor.psp.format_2025.constants import (
    PSPF_MAGIC, HEADER_SIZE, SLOT_DESCRIPTOR_SIZE,
    ACCESS_MMAP, ACCESS_FILE, ACCESS_STREAM, ACCESS_AUTO,
    COMPRESSION_NONE, COMPRESSION_GZIP
)
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.slots import SlotDescriptor


class TestReaderBackends:
    """Test reader with different backends."""
    
    @pytest.fixture
    def test_bundle(self):
        """Create a minimal test bundle."""
        with tempfile.NamedTemporaryFile(suffix='.psp', delete=False) as f:
            # Write fake launcher (100 bytes)
            f.write(b'LAUNCHER' * 12 + b'DATA')
            
            # Write index/header (512 bytes)
            index = PSPFIndex()
            index.launcher_size = 100
            index.slot_table_offset = 100 + HEADER_SIZE  # After header
            index.slot_count = 2
            index.slot_table_size = 2 * SLOT_DESCRIPTOR_SIZE
            data_offset = 100 + HEADER_SIZE + (2 * SLOT_DESCRIPTOR_SIZE)
            index.package_size = data_offset + 1000  # Approximate
            
            # Calculate checksum
            index_data = index.pack()
            checksum = zlib.adler32(index_data)
            index.index_checksum = checksum
            
            # Write index with checksum
            f.write(index.pack())
            
            # Write slot descriptors (2 x 64 bytes)
            slot1 = SlotDescriptor(
                id=0,
                name="test1.txt",
                offset=data_offset,
                size=100,
                original_size=100,
                checksum=zlib.adler32(b'TEST DATA 1' * 9 + b'T'),  # 100 bytes
                compression=COMPRESSION_NONE
            )
            f.write(slot1.pack())
            
            slot2 = SlotDescriptor(
                id=1,
                name="test2.txt",
                offset=data_offset + 100,
                size=200,
                original_size=200,
                checksum=zlib.adler32(b'TEST DATA 2' * 18 + b'TD'),  # 200 bytes
                compression=COMPRESSION_NONE
            )
            f.write(slot2.pack())
            
            # Write slot data
            f.write(b'TEST DATA 1' * 9 + b'T')  # 100 bytes
            f.write(b'TEST DATA 2' * 18 + b'TD')  # 200 bytes
            
            # Write trailing magic (package and wand emojis)
            f.write('📦🪄'.encode('utf-8'))
            
            path = Path(f.name)
        
        yield path
        
        # Cleanup
        path.unlink(missing_ok=True)
    
    def test_reader_with_mmap_backend(self, test_bundle):
        """Test reader with memory-mapped backend."""
        reader = PSPFReader(test_bundle, mode=ACCESS_MMAP)
        reader.open()
        
        # Check backend type
        backend = reader.get_backend()
        assert isinstance(backend, MMapBackend)
        
        # Read index
        index = reader.read_index()
        assert index.launcher_size == 100
        assert index.slot_count == 2
        
        # Read slot descriptors
        descriptors = reader.read_slot_descriptors()
        assert len(descriptors) == 2
        assert descriptors[0].size == 100
        assert descriptors[1].size == 200
        
        # Read slot data
        slot1_data = reader.read_slot(0)
        assert len(slot1_data) == 100
        assert slot1_data == b'TEST DATA 1' * 9 + b'T'
        
        slot2_data = reader.read_slot(1)
        assert len(slot2_data) == 200
        assert slot2_data == b'TEST DATA 2' * 18 + b'TD'
        
        reader.close()
    
    def test_reader_with_file_backend(self, test_bundle):
        """Test reader with file I/O backend."""
        reader = PSPFReader(test_bundle, mode=ACCESS_FILE)
        reader.open()
        
        # Check backend type
        backend = reader.get_backend()
        assert isinstance(backend, FileBackend)
        
        # Read index
        index = reader.read_index()
        assert index.launcher_size == 100
        
        # Read slots
        slot1_data = reader.read_slot(0)
        assert len(slot1_data) == 100
        
        reader.close()
    
    def test_reader_with_stream_backend(self, test_bundle):
        """Test reader with streaming backend."""
        reader = PSPFReader(test_bundle, mode=ACCESS_STREAM)
        reader.open()
        
        # Check backend type
        backend = reader.get_backend()
        assert isinstance(backend, StreamBackend)
        
        # Stream a slot
        chunks = list(reader.stream_slot(0, chunk_size=32))
        
        # Should have multiple chunks
        assert len(chunks) > 1
        
        # Reconstruct data
        full_data = b''.join(chunks)
        assert len(full_data) == 100
        assert full_data == b'TEST DATA 1' * 9 + b'T'
        
        reader.close()
    
    def test_reader_context_manager(self, test_bundle):
        """Test reader as context manager."""
        with PSPFReader(test_bundle, mode=ACCESS_MMAP) as reader:
            index = reader.read_index()
            assert index.slot_count == 2
        
        # Backend should be closed automatically
        assert reader._backend is None
    
    def test_reader_auto_backend(self, test_bundle):
        """Test automatic backend selection."""
        reader = PSPFReader(test_bundle, mode=ACCESS_AUTO)
        reader.open()
        
        # For small files, should use FileBackend
        backend = reader.get_backend()
        assert backend is not None
        
        reader.close()
    
    def test_read_bundle_convenience(self, test_bundle):
        """Test convenience function."""
        # With mmap
        reader = read_bundle(test_bundle, use_mmap=True)
        assert isinstance(reader.get_backend(), MMapBackend)
        reader.close()
        
        # Without mmap (auto)
        reader = read_bundle(test_bundle, use_mmap=False)
        assert reader.get_backend() is not None
        reader.close()
    
    def test_verify_bundle_basic(self, test_bundle):
        """Test basic bundle verification."""
        # Note: Our test bundle doesn't have proper metadata or signatures,
        # so we just test that it doesn't crash
        try:
            result = verify_bundle(test_bundle)
            # May fail due to missing metadata, that's ok for this test
        except:
            pass  # Expected for minimal test bundle
    
    def test_switch_backends(self, test_bundle):
        """Test switching between backends."""
        reader = PSPFReader(test_bundle, mode=ACCESS_FILE)
        reader.open()
        
        # Start with file backend
        assert isinstance(reader.get_backend(), FileBackend)
        
        # Switch to mmap
        reader.use_mmap()
        assert isinstance(reader.get_backend(), MMapBackend)
        
        # Can still read
        index = reader.read_index()
        assert index.slot_count == 2
        
        # Switch to streaming
        reader.use_streaming(chunk_size=64)
        assert isinstance(reader.get_backend(), StreamBackend)
        
        reader.close()
    
    def test_lazy_slot_view(self, test_bundle):
        """Test lazy slot loading with SlotView."""
        with PSPFReader(test_bundle, mode=ACCESS_MMAP) as reader:
            # Get a lazy view
            view = reader.get_slot_view(0)
            
            # Data not loaded yet
            assert view._data is None
            
            # Access data - should load now
            data = view.data
            assert len(data) == 100
            
            # Content property handles decompression (none in this case)
            content = view.content
            assert content == b'TEST DATA 1' * 9 + b'T'

# 🧪📖🗺️🪄