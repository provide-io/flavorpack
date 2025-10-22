#!/usr/bin/env python3
# tests/test_mmap_performance.py
# Performance benchmarks and large file tests for mmap

from contextlib import contextmanager
import os
from pathlib import Path
import random
import tempfile
import time

import pytest

from flavor.config.defaults import DEFAULT_PAGE_SIZE
from flavor.psp.format_2025.backends import (
    ACCESS_FILE,
    ACCESS_MMAP,
    FileBackend,
    MMapBackend,
    create_backend,
)


@contextmanager
def measure_time(description):
    """Context manager to measure execution time."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"\n⏱️ {description}: {elapsed:.4f}s")
    return elapsed


@pytest.mark.mmap
@pytest.mark.slow
