//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package pkg

import "errors"

var (
	// Security errors 🔒
	ErrIntegrityCheckFailed = errors.New("❌ integrity check failed")
	ErrSignatureInvalid     = errors.New("❌ invalid signature")
	ErrNoIntegritySeal      = errors.New("❌ no integrity seal found")
)
