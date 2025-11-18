#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Custom exceptions for FlavorPack."""

from __future__ import annotations

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


# 🌶️📦🔚
