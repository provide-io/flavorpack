// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build !windows

package format_2025

import "os"

var getuidFn = os.Getuid

// isPrivilegedUser returns true when the process is running as root (UID 0).
func isPrivilegedUser() bool {
	return getuidFn() == 0
}
