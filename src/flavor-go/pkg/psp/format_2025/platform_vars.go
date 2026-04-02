// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import "runtime"

// currentGOOS and currentGOARCH are package-level variables that mirror
// runtime.GOOS and runtime.GOARCH. They exist so tests can override them
// to exercise platform-specific branches without requiring that platform.
var currentGOOS = runtime.GOOS
var currentGOARCH = runtime.GOARCH
