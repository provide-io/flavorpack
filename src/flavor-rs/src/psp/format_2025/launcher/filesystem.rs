// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

//! Filesystem utilities for package extraction

use crate::exceptions::Result;
use log::debug;
use std::fs;
use std::io::{Read, Write};
use std::path::Path;

/// Helper function to recursively copy a directory
pub(super) fn copy_dir_all(src: &Path, dst: &Path) -> Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());

        if src_path.is_dir() {
            copy_dir_all(&src_path, &dst_path)?;
        } else {
            fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
}

/// Fix shebangs in scripts after atomic move
pub(super) fn fix_shebangs(bin_dir: &Path, old_prefix: &Path, new_prefix: &Path) -> Result<()> {
    if !bin_dir.exists() {
        return Ok(());
    }

    for entry in fs::read_dir(bin_dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.is_file() {
            // Read first few bytes to check for shebang
            let mut file = fs::File::open(&path)?;
            let mut header = [0u8; 2];
            if file.read_exact(&mut header).is_ok() && &header == b"#!" {
                // Read entire file
                file = fs::File::open(&path)?;
                let mut content = Vec::new();
                file.read_to_end(&mut content)?;

                // Find end of first line
                if let Some(newline_pos) = content.iter().position(|&b| b == b'\n') {
                    let first_line = &content[0..newline_pos];
                    let old_prefix_str = old_prefix.to_string_lossy();
                    let old_prefix_bytes = old_prefix_str.as_bytes();

                    // Check if the shebang contains the old prefix
                    if first_line
                        .windows(old_prefix_bytes.len())
                        .any(|window| window == old_prefix_bytes)
                    {
                        // Replace old prefix with new prefix in first line
                        let mut new_content = Vec::new();
                        let first_line_str = String::from_utf8_lossy(first_line);
                        let new_prefix_str = new_prefix.to_string_lossy();
                        let new_first_line = first_line_str
                            .replace(old_prefix_str.as_ref(), new_prefix_str.as_ref());
                        new_content.extend_from_slice(new_first_line.as_bytes());
                        new_content.extend_from_slice(&content[newline_pos..]);

                        // Write back the modified content
                        let mut file = fs::File::create(&path)?;
                        file.write_all(&new_content)?;

                        debug!(
                            "Fixed shebang in {:?}",
                            path.file_name().unwrap_or_default()
                        );
                    }
                }
            }
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{copy_dir_all, fix_shebangs};
    use std::fs;

    #[test]
    fn copy_dir_all_recursively_copies_tree() {
        let src = tempfile::tempdir().expect("src tempdir");
        let dst = tempfile::tempdir().expect("dst tempdir");
        let nested = src.path().join("nested");
        fs::create_dir_all(&nested).expect("create nested dir");
        fs::write(nested.join("file.txt"), b"payload").expect("write payload");

        copy_dir_all(src.path(), &dst.path().join("copied")).expect("copy tree");

        let copied = fs::read(dst.path().join("copied").join("nested").join("file.txt"))
            .expect("read copied file");
        assert_eq!(copied, b"payload");
    }

    #[test]
    fn fix_shebangs_rewrites_matching_scripts_only() {
        let temp = tempfile::tempdir().expect("tempdir");
        let bin_dir = temp.path().join("bin");
        fs::create_dir_all(&bin_dir).expect("create bin dir");
        let script = bin_dir.join("tool");
        let plain = bin_dir.join("README");
        fs::write(&script, b"#!/old/prefix/python\nprint('ok')\n").expect("write script");
        fs::write(&plain, b"plain file\n").expect("write plain file");

        fix_shebangs(&bin_dir, "/old/prefix".as_ref(), "/new/prefix".as_ref())
            .expect("fix shebangs");

        let rewritten = fs::read_to_string(&script).expect("read rewritten script");
        assert!(rewritten.starts_with("#!/new/prefix/python"));
        let untouched = fs::read_to_string(&plain).expect("read plain file");
        assert_eq!(untouched, "plain file\n");
    }
}
