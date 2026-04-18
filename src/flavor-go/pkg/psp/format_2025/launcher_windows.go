// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//go:build windows
// +build windows

package format_2025

import "golang.org/x/sys/windows"

// setUTF8ConsoleOutput sets Windows console stdout/stderr to UTF-8 (codepage 65001)
// so that emoji log prefixes (e.g. 🐹) render correctly without mojibake.
func setUTF8ConsoleOutput() {
	windows.SetConsoleOutputCP(65001)
}
