#![no_main]
// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

use flavor_rs::psp::format_2025::operations::{pack_operations, unpack_operations};
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    let operations: Vec<u8> = data
        .iter()
        .copied()
        .filter(|operation| *operation != 0)
        .take(8)
        .collect();
    let packed = pack_operations(&operations);
    let unpacked = unpack_operations(packed);

    assert_eq!(unpacked, operations);
});
