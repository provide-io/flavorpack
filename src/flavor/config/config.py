# flavor/config/config.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Structured configuration models for the `[tool.flavor]` section of `pyproject.toml`.

This module uses the `attrs` library to define typed, immutable classes that
represent the configuration for building a Flavor package. This approach provides
type safety, default values, and clearer code compared to using unstructured
dictionaries.



    DEFAULT_VALIDATION_LEVEL,
    VALIDATION_LEVELS,
)


"""


@define(frozen=True, kw_only=True)
class RuntimeRuntimeConfig:
    """Configuration for the sandboxed runtime environment variables."""
