// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build windows

package format_2025

import (
	"golang.org/x/sys/windows"
)

// isPrivilegedUser returns true when the process token has the Administrators
// group enabled (i.e. the process is running as a Windows Administrator).
func isPrivilegedUser() bool {
	var sid *windows.SID
	// Build the well-known Administrators SID (S-1-5-32-544).
	if err := windows.AllocateAndInitializeSid(
		&windows.SECURITY_NT_AUTHORITY,
		2,
		windows.SECURITY_BUILTIN_DOMAIN_RID,
		windows.DOMAIN_ALIAS_RID_ADMINS,
		0, 0, 0, 0, 0, 0,
		&sid,
	); err != nil {
		return false
	}
	defer windows.FreeSid(sid)

	token, err := windows.OpenCurrentProcessToken()
	if err != nil {
		return false
	}
	defer token.Close()

	member, err := token.IsMember(sid)
	if err != nil {
		return false
	}
	return member
}
