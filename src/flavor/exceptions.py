#!/usr/bin/env python3
"""
Custom exceptions for the flavor pack.
"""

from provide.foundation.errors import FoundationError


class FlavorException(FoundationError):
    """Base exception for all flavor-related errors."""

    pass


class BuildError(FlavorException):
    """Raised for errors during the package build process."""

    pass


class ValidationError(FlavorException):
    """Raised when build specification validation fails."""

    pass


class PackagingError(FlavorException):
    """Raised for errors during packaging orchestration."""

    pass


class CryptoError(FlavorException):
    """Raised for cryptographic errors."""

    pass


class VerificationError(FlavorException):
    """Raised for errors during package verification."""

    pass
