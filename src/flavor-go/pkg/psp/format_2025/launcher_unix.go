// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build !windows
// +build !windows

package format_2025

// setUTF8ConsoleOutput is a no-op on non-Windows platforms; UTF-8 is the default.
func setUTF8ConsoleOutput() {}
