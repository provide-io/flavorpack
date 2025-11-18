//! PE Resource Embedding for Windows
//!
//! This module provides functionality to embed PSPF data as a PE resource
//! in Windows executables. This is necessary for Go launcher compatibility
//! on Windows, as Go binaries reject appended data.

#[cfg(target_os = "windows")]
use anyhow::Result;
#[cfg(target_os = "windows")]
use log::{debug, info};
#[cfg(target_os = "windows")]
use std::path::Path;

#[cfg(target_os = "windows")]
use windows::Win32::System::LibraryLoader::*;
#[cfg(target_os = "windows")]
use windows::core::PCWSTR;

#[cfg(target_os = "windows")]
const RT_RCDATA: u16 = 10; // Raw data resource type
#[cfg(target_os = "windows")]
const PSPF_RESOURCE_NAME: &str = "PSPF";

/// Embeds PSPF data as a PE resource in a Windows executable.
///
/// This uses the Windows UpdateResource API to add PSPF data to the
/// PE resource section, which allows Go launchers to read the data
/// without issues on Windows.
#[cfg(target_os = "windows")]
#[allow(unsafe_code)] // Required for Windows API FFI calls
pub fn embed_pspf_as_resource(exe_path: &Path, pspf_data: &[u8]) -> Result<()> {
    use std::fs;

    info!("🪟 Embedding PSPF data as PE resource");
    info!("   exe: {}", exe_path.display());
    info!("   pspf_size: {} bytes", pspf_data.len());
    info!("   resource_type: RT_RCDATA ({})", RT_RCDATA);
    info!("   resource_name: {}", PSPF_RESOURCE_NAME);

    // Verify the file exists and get its size before modification
    let file_size_before = fs::metadata(exe_path)
        .map_err(|e| anyhow::anyhow!("Failed to get file metadata before embedding: {}", e))?
        .len();
    debug!("   File size before embedding: {} bytes", file_size_before);

    // Convert path to wide string for Windows API
    let exe_path_str = exe_path
        .to_str()
        .ok_or_else(|| anyhow::anyhow!("Invalid path encoding"))?;

    let wide_path: Vec<u16> = exe_path_str
        .encode_utf16()
        .chain(std::iter::once(0))
        .collect();
    let wide_name: Vec<u16> = PSPF_RESOURCE_NAME
        .encode_utf16()
        .chain(std::iter::once(0))
        .collect();

    debug!("   Wide path length: {} chars", wide_path.len());
    debug!("   Wide name length: {} chars", wide_name.len());

    unsafe {
        // Begin update resource session
        debug!("📝 Beginning resource update session (preserve existing resources)");
        let update_handle = BeginUpdateResourceW(PCWSTR(wide_path.as_ptr()), false)
            .map_err(|e| anyhow::anyhow!("BeginUpdateResourceW failed: {}", e))?;

        debug!("   Got update handle: {:?}", update_handle);

        // Update the PSPF resource
        debug!("📦 Adding PSPF resource data ({} bytes)", pspf_data.len());
        let update_result = UpdateResourceW(
            update_handle,
            PCWSTR(RT_RCDATA as usize as *const u16), // Resource type (MAKEINTRESOURCE)
            PCWSTR(wide_name.as_ptr()),               // Resource name
            0x0409,                                   // Language ID (en-US)
            Some(pspf_data.as_ptr() as *const _),     // Resource data
            pspf_data.len() as u32,                   // Data size
        );

        if let Err(e) = update_result {
            debug!("   UpdateResourceW failed, discarding changes");
            let _ = EndUpdateResourceW(update_handle, true); // Discard changes on error
            return Err(anyhow::anyhow!("UpdateResourceW failed: {}", e));
        }

        debug!("   UpdateResourceW succeeded");

        // Commit the changes
        debug!("💾 Committing resource changes");
        EndUpdateResourceW(update_handle, false)
            .map_err(|e| anyhow::anyhow!("EndUpdateResourceW failed: {}", e))?;

        debug!("   EndUpdateResourceW succeeded");
    }

    // Verify the file still exists and check its size after modification
    let file_size_after = fs::metadata(exe_path)
        .map_err(|e| anyhow::anyhow!("Failed to get file metadata after embedding: {}", e))?
        .len();
    debug!("   File size after embedding: {} bytes", file_size_after);
    debug!(
        "   Size change: {} bytes",
        file_size_after as i64 - file_size_before as i64
    );

    info!("✅ Successfully embedded PSPF as PE resource");
    Ok(())
}

/// Stub for non-Windows platforms
#[cfg(not(target_os = "windows"))]
pub fn embed_pspf_as_resource(
    _exe_path: &std::path::Path,
    _pspf_data: &[u8],
) -> anyhow::Result<()> {
    anyhow::bail!("PE resource embedding is only supported on Windows")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_non_windows_stub() {
        #[cfg(not(target_os = "windows"))]
        {
            use std::path::Path;
            let result = embed_pspf_as_resource(Path::new("test.exe"), b"data");
            assert!(result.is_err());
        }
    }
}
