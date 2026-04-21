//! Integration tests for PSPF reader, extraction, debug, and launcher subsystems.
//!
//! These tests build real PSPF bundles via the builder, then exercise the reader,
//! extraction, debug-dump, and launcher cache-validation paths that have low
//! unit-test coverage.

use std::fs;
use std::path::{Path, PathBuf};

use flavor::api::{BuildOptions, LaunchOptions};
use flavor::psp::format_2025::{self, Reader};
use tempfile::tempdir;

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

/// Write a minimal launcher script that the builder can embed.
fn write_launcher_script(path: &Path) {
    #[cfg(unix)]
    {
        let script =
            b"#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then\n  echo launcher 1.0\nfi\nexit 0\n";
        fs::write(path, script).expect("write launcher script");
        let mut perms = fs::metadata(path).expect("launcher metadata").permissions();
        std::os::unix::fs::PermissionsExt::set_mode(&mut perms, 0o755);
        fs::set_permissions(path, perms).expect("set launcher executable");
    }

    #[cfg(windows)]
    {
        let script = b"@echo off\r\nif \"%1\"==\"--version\" echo launcher 1.0\r\nexit /b 0\r\n";
        fs::write(path, script).expect("write launcher script");
    }
}

/// Build a real PSPF bundle with a single payload slot (file, not tarball).
fn build_single_file_bundle(temp: &tempfile::TempDir) -> PathBuf {
    let payload = temp.path().join("payload.txt");
    fs::write(&payload, b"integration-test-payload").expect("write payload");

    let launcher = temp.path().join(if cfg!(windows) {
        "launcher.bat"
    } else {
        "launcher.sh"
    });
    write_launcher_script(&launcher);

    let manifest_path = temp.path().join("manifest.json");
    let output_path = temp.path().join("bundle.pspf");

    let manifest = serde_json::json!({
        "package": { "name": "integration-test", "version": "0.1.0" },
        "execution": {
            "command": if cfg!(windows) { "cmd /C exit 0" } else { "true" },
            "env": {}
        },
        "slots": [{
            "slot": 0,
            "id": "payload",
            "source": payload.display().to_string(),
            "target": "data/payload.txt",
            "operations": "",
            "purpose": "data",
            "lifecycle": "runtime",
            "permissions": "0644"
        }]
    });
    fs::write(
        &manifest_path,
        serde_json::to_vec_pretty(&manifest).expect("serialize manifest"),
    )
    .expect("write manifest");

    let options = BuildOptions {
        launcher_bin: Some(launcher),
        skip_verification: false,
        private_key_path: None,
        public_key_path: None,
        key_seed: Some("integration-test-seed".to_string()),
        workenv_base: None,
    };

    format_2025::build(&manifest_path, &output_path, options).expect("build bundle");
    output_path
}

/// Build a real PSPF bundle with multiple slots for richer coverage.
fn build_multi_slot_bundle(temp: &tempfile::TempDir) -> PathBuf {
    let payload_a = temp.path().join("payload_a.txt");
    fs::write(&payload_a, b"contents-of-slot-a").expect("write payload_a");
    let payload_b = temp.path().join("payload_b.bin");
    fs::write(&payload_b, vec![0xDE, 0xAD, 0xBE, 0xEF]).expect("write payload_b");

    let launcher = temp.path().join(if cfg!(windows) {
        "launcher.bat"
    } else {
        "launcher.sh"
    });
    write_launcher_script(&launcher);

    let manifest_path = temp.path().join("manifest.json");
    let output_path = temp.path().join("multi.pspf");

    let manifest = serde_json::json!({
        "package": { "name": "multi-slot-test", "version": "2.0.0" },
        "execution": {
            "command": if cfg!(windows) { "cmd /C exit 0" } else { "true" },
            "env": {}
        },
        "slots": [
            {
                "slot": 0,
                "id": "slot-a",
                "source": payload_a.display().to_string(),
                "target": "lib/slot_a.txt",
                "operations": "",
                "purpose": "data",
                "lifecycle": "runtime",
                "permissions": "0644"
            },
            {
                "slot": 1,
                "id": "slot-b",
                "source": payload_b.display().to_string(),
                "target": "bin/slot_b.bin",
                "operations": "",
                "purpose": "code",
                "lifecycle": "runtime",
                "permissions": "0755"
            }
        ]
    });
    fs::write(
        &manifest_path,
        serde_json::to_vec_pretty(&manifest).expect("serialize manifest"),
    )
    .expect("write manifest");

    let options = BuildOptions {
        launcher_bin: Some(launcher),
        skip_verification: false,
        private_key_path: None,
        public_key_path: None,
        key_seed: Some("multi-slot-test-seed".to_string()),
        workenv_base: None,
    };

    format_2025::build(&manifest_path, &output_path, options).expect("build multi-slot bundle");
    output_path
}

// ===========================================================================
// Reader integration tests
// ===========================================================================

#[test]
fn reader_reads_index_from_real_bundle() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let mut reader = Reader::new(&bundle).expect("open reader");
    let index = reader.read_index().expect("read_index");

    // Copy fields from packed struct to avoid unaligned references
    let slot_count = index.slot_count;
    let package_size = index.package_size;
    let launcher_size = index.launcher_size;
    let metadata_offset = index.metadata_offset;
    let metadata_size = index.metadata_size;

    assert_eq!(slot_count, 1);
    assert!(package_size > 0);
    assert!(launcher_size > 0);
    assert!(metadata_offset > 0);
    assert!(metadata_size > 0);
}

#[test]
fn reader_reads_metadata_from_real_bundle() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let mut reader = Reader::new(&bundle).expect("open reader");
    let metadata = reader.read_metadata().expect("read_metadata");

    assert_eq!(metadata.package.name, "integration-test");
    assert_eq!(metadata.package.version, "0.1.0");
    assert_eq!(metadata.slots.len(), 1);
    assert_eq!(metadata.slots[0].id, "payload");
    assert_eq!(
        metadata.execution.command,
        if cfg!(windows) {
            "cmd /C exit 0"
        } else {
            "true"
        }
    );
}

#[test]
fn reader_reads_slot_descriptors_from_real_bundle() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let mut reader = Reader::new(&bundle).expect("open reader");
    let descriptors = reader
        .read_slot_descriptors()
        .expect("read_slot_descriptors");

    assert_eq!(descriptors.len(), 1);
    let size = descriptors[0].size;
    let offset = descriptors[0].offset;
    assert!(size > 0, "slot should have nonzero stored size");
    assert!(offset > 0, "slot data should be at positive offset");
}

#[test]
fn reader_reads_slot_data_from_real_bundle() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let mut reader = Reader::new(&bundle).expect("open reader");
    let descriptors = reader
        .read_slot_descriptors()
        .expect("read_slot_descriptors");
    let slot_data = reader.read_slot(&descriptors[0]).expect("read_slot");

    // The builder compresses slot data; just check we get bytes back
    assert!(!slot_data.is_empty(), "slot data should be non-empty");
}

#[test]
fn reader_with_mmap_reads_index() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let mut reader = Reader::with_mmap(&bundle).expect("open mmap reader");
    let index = reader.read_index().expect("mmap read_index");
    let slot_count = index.slot_count;
    assert_eq!(slot_count, 1);
}

#[test]
fn reader_multi_slot_bundle_has_correct_descriptor_count() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_multi_slot_bundle(&temp);

    let mut reader = Reader::new(&bundle).expect("open reader");
    let index = reader.read_index().expect("read_index");
    let slot_count = index.slot_count;
    assert_eq!(slot_count, 2);

    let descriptors = reader
        .read_slot_descriptors()
        .expect("read_slot_descriptors");
    assert_eq!(descriptors.len(), 2);

    // Each slot should have distinct offsets
    let off0 = descriptors[0].offset;
    let off1 = descriptors[1].offset;
    assert_ne!(off0, off1);
}

#[test]
fn reader_metadata_checksum_verified() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    // Calling read_metadata implicitly verifies the SHA-256 checksum
    let mut reader = Reader::new(&bundle).expect("open reader");
    let metadata = reader
        .read_metadata()
        .expect("metadata checksum should verify");
    assert_eq!(metadata.format, "PSPF/2025");
}

#[test]
fn reader_rejects_corrupted_magic_trailer() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    // Corrupt the last 4 bytes (magic wand emoji)
    let mut bytes = fs::read(&bundle).expect("read bundle");
    let len = bytes.len();
    bytes[len - 1] = 0xFF;
    bytes[len - 2] = 0xFF;
    let corrupted = temp.path().join("corrupted.pspf");
    fs::write(&corrupted, &bytes).expect("write corrupted");

    let mut reader = Reader::new(&corrupted).expect("open reader");
    assert!(
        reader.read_index().is_err(),
        "corrupted trailer should fail"
    );
}

#[test]
fn reader_rejects_corrupted_metadata() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let mut reader = Reader::new(&bundle).expect("open reader");
    let index = reader.read_index().expect("read_index").clone();
    let meta_offset = index.metadata_offset;
    let meta_size = index.metadata_size;

    // Corrupt a byte in the metadata region
    let mut bytes = fs::read(&bundle).expect("read bundle");
    let meta_mid = meta_offset as usize + (meta_size as usize / 2);
    if meta_mid < bytes.len() {
        bytes[meta_mid] ^= 0xFF;
    }
    let corrupted = temp.path().join("meta_corrupted.pspf");
    fs::write(&corrupted, &bytes).expect("write corrupted");

    let mut bad_reader = Reader::new(&corrupted).expect("open reader");
    assert!(
        bad_reader.read_metadata().is_err(),
        "corrupted metadata should fail checksum"
    );
}

// ===========================================================================
// Extraction integration tests
// ===========================================================================

#[test]
fn extract_slot_writes_file_to_dest_dir() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let workenv = temp.path().join("workenv");

    let mut reader = Reader::new(&bundle).expect("open reader");
    reader.extract_slot(0, &workenv).expect("extract_slot");

    let extracted = workenv.join("data/payload.txt");
    assert!(extracted.exists(), "extracted file should exist");
    assert_eq!(
        fs::read_to_string(&extracted).expect("read extracted"),
        "integration-test-payload"
    );
}

#[test]
fn extract_slot_multi_slot_bundle_extracts_both() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_multi_slot_bundle(&temp);
    let workenv = temp.path().join("workenv");

    let mut reader = Reader::new(&bundle).expect("open reader");
    reader.extract_slot(0, &workenv).expect("extract slot 0");
    reader.extract_slot(1, &workenv).expect("extract slot 1");

    let slot_a = workenv.join("lib/slot_a.txt");
    let slot_b = workenv.join("bin/slot_b.bin");
    assert!(slot_a.exists(), "slot_a should be extracted");
    assert!(slot_b.exists(), "slot_b should be extracted");

    assert_eq!(
        fs::read_to_string(&slot_a).expect("read slot_a"),
        "contents-of-slot-a"
    );
    assert_eq!(
        fs::read(&slot_b).expect("read slot_b"),
        vec![0xDE, 0xAD, 0xBE, 0xEF]
    );
}

#[test]
fn extract_slot_out_of_range_returns_error() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let workenv = temp.path().join("workenv");

    let mut reader = Reader::new(&bundle).expect("open reader");
    assert!(
        reader.extract_slot(99, &workenv).is_err(),
        "out-of-range slot should error"
    );
}

#[cfg(unix)]
#[test]
fn extract_slot_sets_permissions_from_manifest() {
    use std::os::unix::fs::PermissionsExt;

    let temp = tempdir().expect("tempdir");
    let bundle = build_multi_slot_bundle(&temp);
    let workenv = temp.path().join("workenv");

    let mut reader = Reader::new(&bundle).expect("open reader");
    // slot 1 has permissions "0755"
    reader.extract_slot(1, &workenv).expect("extract slot 1");

    let slot_b = workenv.join("bin/slot_b.bin");
    let mode = fs::metadata(&slot_b)
        .expect("stat slot_b")
        .permissions()
        .mode()
        & 0o777;
    // Verify executable bits are set (the builder encodes permissions into descriptors)
    assert!(
        mode & 0o100 != 0 || mode & 0o010 != 0,
        "should have execute bit set; got {:o}",
        mode
    );
}

// ===========================================================================
// Debug dump integration tests
// ===========================================================================

#[test]
fn debug_dump_creates_expected_files_for_real_bundle() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let debug_dir = temp.path().join("debug_output");

    let mut reader = Reader::new(&bundle).expect("open reader");
    reader
        .debug_dump(&debug_dir)
        .expect("debug_dump should succeed on valid bundle");

    assert!(
        debug_dir.join("index.json").exists(),
        "index.json should be created"
    );
    assert!(
        debug_dir.join("metadata_raw.bin").exists(),
        "metadata_raw.bin should be created"
    );
    assert!(
        debug_dir.join("metadata.json").exists(),
        "metadata.json should be created"
    );
    assert!(
        debug_dir.join("slot_0_header.bin").exists(),
        "slot header should be created"
    );
}

#[test]
fn debug_dump_index_json_contains_expected_fields() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let debug_dir = temp.path().join("debug_output");

    let mut reader = Reader::new(&bundle).expect("open reader");
    reader.debug_dump(&debug_dir).expect("debug_dump");

    let index_json = fs::read_to_string(debug_dir.join("index.json")).expect("read index.json");
    assert!(
        index_json.contains("\"version\""),
        "should have version field"
    );
    assert!(
        index_json.contains("\"file_size\""),
        "should have file_size field"
    );
    assert!(
        index_json.contains("\"descriptor_count\": 1"),
        "should have 1 descriptor"
    );
    assert!(
        index_json.contains("\"public_key\""),
        "should have public_key"
    );
}

#[test]
fn debug_dump_metadata_json_matches_reader_metadata() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let debug_dir = temp.path().join("debug_output");

    let mut reader = Reader::new(&bundle).expect("open reader");
    reader.debug_dump(&debug_dir).expect("debug_dump");

    let metadata_json =
        fs::read_to_string(debug_dir.join("metadata.json")).expect("read metadata.json");
    let parsed: serde_json::Value =
        serde_json::from_str(&metadata_json).expect("parse metadata.json");

    assert_eq!(parsed["package"]["name"], "integration-test");
    assert_eq!(parsed["package"]["version"], "0.1.0");
}

#[test]
fn debug_dump_multi_slot_creates_headers_for_each_slot() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_multi_slot_bundle(&temp);
    let debug_dir = temp.path().join("debug_output");

    let mut reader = Reader::new(&bundle).expect("open reader");
    reader.debug_dump(&debug_dir).expect("debug_dump");

    assert!(debug_dir.join("slot_0_header.bin").exists());
    assert!(debug_dir.join("slot_1_header.bin").exists());

    let index_json = fs::read_to_string(debug_dir.join("index.json")).expect("read index.json");
    assert!(
        index_json.contains("\"descriptor_count\": 2"),
        "should have 2 descriptors"
    );
}

// ===========================================================================
// Launcher cache / workenv path tests
// ===========================================================================

#[cfg(unix)]
#[test]
fn launch_real_bundle_spawn_mode_returns_zero() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let workdir_hint = temp
        .path()
        .join("cache/workenv/integration-test")
        .display()
        .to_string();

    // Save and set environment for spawn mode with strict validation
    let saved_exec = std::env::var("FLAVOR_EXEC_MODE").ok();
    let saved_val = std::env::var("FLAVOR_VALIDATION").ok();
    let saved_we = std::env::var("FLAVOR_WORKENV").ok();

    unsafe {
        std::env::set_var("FLAVOR_EXEC_MODE", "spawn");
        std::env::set_var("FLAVOR_VALIDATION", "strict");
        std::env::remove_var("FLAVOR_WORKENV");
    }

    let options = LaunchOptions {
        workdir: Some(workdir_hint),
    };
    let result = format_2025::launch(&bundle, &[], options);

    // Restore environment
    unsafe {
        match saved_exec {
            Some(v) => std::env::set_var("FLAVOR_EXEC_MODE", v),
            None => std::env::remove_var("FLAVOR_EXEC_MODE"),
        }
        match saved_val {
            Some(v) => std::env::set_var("FLAVOR_VALIDATION", v),
            None => std::env::remove_var("FLAVOR_VALIDATION"),
        }
        match saved_we {
            Some(v) => std::env::set_var("FLAVOR_WORKENV", v),
            None => std::env::remove_var("FLAVOR_WORKENV"),
        }
    }

    assert_eq!(result.expect("launch should succeed"), 0);
}

#[cfg(unix)]
#[test]
fn launch_twice_uses_cache_on_second_run() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let cache_base = temp.path().join("cache/workenv/integration-cache-test");
    let workdir_hint = cache_base.display().to_string();

    let saved_exec = std::env::var("FLAVOR_EXEC_MODE").ok();
    let saved_val = std::env::var("FLAVOR_VALIDATION").ok();
    let saved_we = std::env::var("FLAVOR_WORKENV").ok();
    let saved_wc = std::env::var("FLAVOR_WORKENV_CACHE").ok();

    unsafe {
        std::env::set_var("FLAVOR_EXEC_MODE", "spawn");
        std::env::set_var("FLAVOR_VALIDATION", "strict");
        std::env::remove_var("FLAVOR_WORKENV");
        std::env::set_var("FLAVOR_WORKENV_CACHE", "true");
    }

    // First launch: extracts
    let opts1 = LaunchOptions {
        workdir: Some(workdir_hint.clone()),
    };
    let r1 = format_2025::launch(&bundle, &[], opts1).expect("first launch");
    assert_eq!(r1, 0);

    // Second launch: should use cache (exercises cache validation path)
    let opts2 = LaunchOptions {
        workdir: Some(workdir_hint),
    };
    let r2 = format_2025::launch(&bundle, &[], opts2).expect("second launch (cached)");
    assert_eq!(r2, 0);

    // Restore environment
    unsafe {
        match saved_exec {
            Some(v) => std::env::set_var("FLAVOR_EXEC_MODE", v),
            None => std::env::remove_var("FLAVOR_EXEC_MODE"),
        }
        match saved_val {
            Some(v) => std::env::set_var("FLAVOR_VALIDATION", v),
            None => std::env::remove_var("FLAVOR_VALIDATION"),
        }
        match saved_we {
            Some(v) => std::env::set_var("FLAVOR_WORKENV", v),
            None => std::env::remove_var("FLAVOR_WORKENV"),
        }
        match saved_wc {
            Some(v) => std::env::set_var("FLAVOR_WORKENV_CACHE", v),
            None => std::env::remove_var("FLAVOR_WORKENV_CACHE"),
        }
    }
}

#[cfg(unix)]
#[test]
fn launch_with_cache_disabled_forces_extraction() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let workdir_hint = temp
        .path()
        .join("cache/workenv/nocache-test")
        .display()
        .to_string();

    let saved_exec = std::env::var("FLAVOR_EXEC_MODE").ok();
    let saved_val = std::env::var("FLAVOR_VALIDATION").ok();
    let saved_we = std::env::var("FLAVOR_WORKENV").ok();
    let saved_wc = std::env::var("FLAVOR_WORKENV_CACHE").ok();

    unsafe {
        std::env::set_var("FLAVOR_EXEC_MODE", "spawn");
        std::env::set_var("FLAVOR_VALIDATION", "strict");
        std::env::remove_var("FLAVOR_WORKENV");
        std::env::set_var("FLAVOR_WORKENV_CACHE", "false");
    }

    let options = LaunchOptions {
        workdir: Some(workdir_hint),
    };
    let result = format_2025::launch(&bundle, &[], options).expect("launch with cache disabled");
    assert_eq!(result, 0);

    unsafe {
        match saved_exec {
            Some(v) => std::env::set_var("FLAVOR_EXEC_MODE", v),
            None => std::env::remove_var("FLAVOR_EXEC_MODE"),
        }
        match saved_val {
            Some(v) => std::env::set_var("FLAVOR_VALIDATION", v),
            None => std::env::remove_var("FLAVOR_VALIDATION"),
        }
        match saved_we {
            Some(v) => std::env::set_var("FLAVOR_WORKENV", v),
            None => std::env::remove_var("FLAVOR_WORKENV"),
        }
        match saved_wc {
            Some(v) => std::env::set_var("FLAVOR_WORKENV_CACHE", v),
            None => std::env::remove_var("FLAVOR_WORKENV_CACHE"),
        }
    }
}

// ===========================================================================
// Verify integration tests
// ===========================================================================

#[test]
fn verify_real_bundle_reports_valid() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let result = flavor::verify_package(&bundle).expect("verify should succeed");
    assert!(result.valid, "real bundle should be valid");
    assert!(result.checksums_valid, "checksums should be valid");
    assert_eq!(result.slot_count, 1);
    assert_eq!(result.package_name, "integration-test");
}

#[test]
fn verify_multi_slot_bundle_reports_correct_slot_count() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_multi_slot_bundle(&temp);

    let result = flavor::verify_package(&bundle).expect("verify should succeed");
    assert!(result.valid);
    assert_eq!(result.slot_count, 2);
    assert_eq!(result.package_name, "multi-slot-test");
}

// ===========================================================================
// Reader backend tests (exercises read_at paths in backends)
// ===========================================================================

#[test]
fn reader_backend_read_at_returns_correct_data() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let mut reader = Reader::new(&bundle).expect("open reader");
    // Read the first few bytes from the file (should be launcher script content)
    let data = reader.backend_mut().read_at(0, 4).expect("read_at");
    assert_eq!(data.len(), 4);
    // The launcher script starts with "#!/" on unix or "@ech" on windows
    #[cfg(unix)]
    assert_eq!(&data[..2], b"#!");
}

#[test]
fn reader_index_checksum_verification() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);

    let mut reader = Reader::new(&bundle).expect("open reader");
    let index = reader.read_index().expect("read_index");

    // The builder writes a valid index checksum; verify it is nonzero
    let checksum = index.index_checksum;
    assert_ne!(checksum, 0, "index checksum should be populated");
}

// ===========================================================================
// Round-trip: build -> read -> extract -> verify contents
// ===========================================================================

#[test]
fn full_roundtrip_build_read_extract_verify() {
    let temp = tempdir().expect("tempdir");
    let bundle = build_single_file_bundle(&temp);
    let workenv = temp.path().join("workenv");

    // Step 1: Read index and metadata
    let mut reader = Reader::new(&bundle).expect("open reader");
    let index = reader.read_index().expect("read_index").clone();
    let metadata = reader.read_metadata().expect("read_metadata").clone();

    assert_eq!(metadata.package.name, "integration-test");
    let slot_count = index.slot_count;
    assert_eq!(slot_count, 1);

    // Step 2: Read descriptors and slot data
    let descriptors = reader
        .read_slot_descriptors()
        .expect("read_slot_descriptors");
    assert_eq!(descriptors.len(), 1);
    let slot_data = reader.read_slot(&descriptors[0]).expect("read_slot");
    assert!(!slot_data.is_empty());

    // Step 3: Extract
    reader.extract_slot(0, &workenv).expect("extract_slot");
    let extracted = workenv.join("data/payload.txt");
    assert_eq!(
        fs::read_to_string(&extracted).expect("read extracted"),
        "integration-test-payload"
    );

    // Step 4: Debug dump
    let debug_dir = temp.path().join("debug");
    reader.debug_dump(&debug_dir).expect("debug_dump");
    assert!(debug_dir.join("index.json").exists());
    assert!(debug_dir.join("metadata.json").exists());

    // Step 5: Verify
    let verify_result = flavor::verify_package(&bundle).expect("verify");
    assert!(verify_result.valid);
}
