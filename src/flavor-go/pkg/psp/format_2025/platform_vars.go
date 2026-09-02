// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import "runtime"

// currentGOOS mirrors runtime.GOOS as a package-level variable so tests can
// override it and exercise platform-specific branches without that platform.
var currentGOOS = runtime.GOOS
