//
// flavor/rust/flavor-packager-rs/src/commands.rs
//
use crate::{crypto, flavor, utils};
use anyhow::{Context, Result};
use std::fs::{self, File};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use tokio::task;

pub async fn keygen_command(out_dir: PathBuf) -> Result<()> {
    log::info!("Generating ECDSA P256 key pair...");
    
    // Create output directory if it doesn't exist
    fs::create_dir_all(&out_dir)
        .with_context(|| format!("Failed to create output directory: {:?}", out_dir))?;
    
    // Generate key pair
    let (signing_key, verifying_key) = task::spawn_blocking(|| crypto::generate_key_pair()).await??;
    
    // Save keys
    let private_key_path = out_dir.join("provider-private.key");
    let public_key_path = out_dir.join("provider-public.key");
    
    crypto::save_private_key(&signing_key, &private_key_path)?;
    crypto::save_public_key(&verifying_key, &public_key_path)?;
    
    log::info!("Key pair generated successfully!");
    log::info!("Private key: {:?}", private_key_path);
    log::info!("Public key: {:?}", public_key_path);
    
    Ok(())
}

pub async fn build_command(
    out: PathBuf,
    payload_dir: PathBuf,
    package_key: PathBuf,
    public_key: PathBuf,
    launcher_bin: PathBuf,
) -> Result<()> {
    log::info!("Building Flavor package...");
    
    // Validate inputs
    if !payload_dir.exists() {
        anyhow::bail!("Payload directory does not exist: {:?}", payload_dir);
    }
    if !package_key.exists() {
        anyhow::bail!("Private key file does not exist: {:?}", package_key);
    }
    if !public_key.exists() {
        anyhow::bail!("Public key file does not exist: {:?}", public_key);
    }
    if !launcher_bin.exists() {
        anyhow::bail!("Launcher binary does not exist: {:?}", launcher_bin);
    }
    
    // Create work directory 
    let work_dir = payload_dir.parent()
        .context("Unable to determine work directory")?;
    
    let payload_tgz_path = work_dir.join("payload.tgz");
    let uv_binary_path = work_dir.join("uv");
    let signature_path = work_dir.join("signature.bin");
    
    // Create payload archive
    log::info!("Creating payload archive...");
    let payload_tgz_size = utils::create_tar_gz(&payload_dir, &payload_tgz_path)?;
    
    // Hash the payload for signing
    log::info!("Signing payload...");
    let payload_data = utils::read_file_bytes(&payload_tgz_path)?;
    let signing_key = crypto::load_private_key(&package_key)?;
    let signature = task::spawn_blocking(move || {
        crypto::sign_data(&signing_key, &payload_data)
    }).await??;
    
    utils::write_file_bytes(&signature_path, &signature)?;
    
    // Ensure output directory exists
    utils::ensure_parent_dir(&out)?;
    
    // Copy launcher as the base executable
    log::info!("Creating self-extracting binary...");
    utils::copy_file(&launcher_bin, &out)?;
    
    // Convert emoji strings to 4-byte arrays
    let rust_bytes = flavor::EMOJI_RUST.as_bytes();
    let packager_bytes = flavor::EMOJI_PACKAGER.as_bytes();
    let payload_bytes = flavor::EMOJI_PAYLOAD.as_bytes();
    
    let mut language_emoji = [0u8; 4];
    let mut type_emoji_1 = [0u8; 4];
    let mut type_emoji_2 = [0u8; 4];
    
    // Copy emoji bytes (truncating or padding as needed)
    language_emoji[..rust_bytes.len().min(4)].copy_from_slice(&rust_bytes[..rust_bytes.len().min(4)]);
    type_emoji_1[..packager_bytes.len().min(4)].copy_from_slice(&packager_bytes[..packager_bytes.len().min(4)]);
    type_emoji_2[..payload_bytes.len().min(4)].copy_from_slice(&payload_bytes[..payload_bytes.len().min(4)]);
    
    // Append Flavor data
    append_flavor_data(
        &out,
        &uv_binary_path,
        None, // python_install_tgz_path
        None, // metadata_tgz_path  
        &payload_tgz_path,
        &signature_path,
        &public_key,
        language_emoji,
        type_emoji_1,
        type_emoji_2,
    ).await?;
    
    log::info!("Flavor package built successfully: {:?}", out);
    Ok(())
}

pub async fn verify_command(flavor_file: PathBuf) -> Result<()> {
    log::info!("Verifying Flavor package: {:?}", flavor_file);
    
    // Read and validate footer
    let (footer, flavor_data_offset) = flavor::read_footer_from_file(&flavor_file)?;
    log::info!("✅ Footer read and checksum verified");
    
    // Read and parse public key
    let mut file = File::open(&flavor_file)?;
    let public_key_offset = flavor_data_offset + footer.public_key_pem_offset as i64;
    file.seek(SeekFrom::Start(public_key_offset as u64))?;
    
    let mut public_key_pem = vec![0u8; footer.public_key_pem_size as usize];
    file.read_exact(&mut public_key_pem)?;
    
    // Write public key to temporary file for parsing
    let temp_pub_key = std::env::temp_dir().join("temp_public_key.pem");
    utils::write_file_bytes(&temp_pub_key, &public_key_pem)?;
    let verifying_key = crypto::load_public_key(&temp_pub_key)?;
    fs::remove_file(temp_pub_key)?;
    
    log::info!("✅ Public key parsed successfully");
    
    // Read signature
    let signature_offset = flavor_data_offset + footer.package_signature_offset as i64;
    file.seek(SeekFrom::Start(signature_offset as u64))?;
    
    let mut signature_bytes = vec![0u8; footer.package_signature_size as usize];
    file.read_exact(&mut signature_bytes)?;
    
    // Read payload data for verification
    let payload_offset = flavor_data_offset + footer.payload_tgz_offset as i64;
    file.seek(SeekFrom::Start(payload_offset as u64))?;
    
    let mut payload_data = vec![0u8; footer.payload_tgz_size as usize];
    file.read_exact(&mut payload_data)?;
    
    // Verify signature
    let is_valid = task::spawn_blocking(move || {
        crypto::verify_signature(&verifying_key, &payload_data, &signature_bytes)
    }).await??;
    
    if is_valid {
        log::info!("✅ Package signature is valid");
        log::info!("✅ Flavor file is valid and trusted");
        Ok(())
    } else {
        anyhow::bail!("❌ ECDSA signature verification failed");
    }
}

async fn append_flavor_data(
    output_file: &Path,
    uv_binary_path: &Path,
    python_install_tgz_path: Option<&Path>,
    metadata_tgz_path: Option<&Path>,
    payload_tgz_path: &Path,
    signature_path: &Path,
    public_key_path: &Path,
    language_emoji: [u8; 4],
    type_emoji_1: [u8; 4],
    type_emoji_2: [u8; 4],
) -> Result<()> {
    let mut file = fs::OpenOptions::new()
        .append(true)
        .open(output_file)?;
    
    let mut footer = flavor::FlavorFooter::new();
    let mut current_offset = 0u64;
    
    // Add UV binary (if exists, otherwise skip)
    if uv_binary_path.exists() {
        let uv_data = utils::read_file_bytes(uv_binary_path)?;
        footer.uv_binary_offset = current_offset;
        footer.uv_binary_size = uv_data.len() as u64;
        file.write_all(&uv_data)?;
        current_offset += uv_data.len() as u64;
    }
    
    // Add Python install tgz (if provided)
    if let Some(python_path) = python_install_tgz_path {
        if python_path.exists() {
            let python_data = utils::read_file_bytes(python_path)?;
            footer.python_install_tgz_offset = current_offset;
            footer.python_install_tgz_size = python_data.len() as u64;
            file.write_all(&python_data)?;
            current_offset += python_data.len() as u64;
        }
    }
    
    // Add metadata tgz (if provided)
    if let Some(metadata_path) = metadata_tgz_path {
        if metadata_path.exists() {
            let metadata_data = utils::read_file_bytes(metadata_path)?;
            footer.metadata_tgz_offset = current_offset;
            footer.metadata_tgz_size = metadata_data.len() as u64;
            file.write_all(&metadata_data)?;
            current_offset += metadata_data.len() as u64;
        }
    }
    
    // Add payload tgz
    let payload_data = utils::read_file_bytes(payload_tgz_path)?;
    footer.payload_tgz_offset = current_offset;
    footer.payload_tgz_size = payload_data.len() as u64;
    file.write_all(&payload_data)?;
    current_offset += payload_data.len() as u64;
    
    // Add signature
    let signature_data = utils::read_file_bytes(signature_path)?;
    footer.package_signature_offset = current_offset;
    footer.package_signature_size = signature_data.len() as u64;
    file.write_all(&signature_data)?;
    current_offset += signature_data.len() as u64;
    
    // Add public key
    let public_key_data = utils::read_file_bytes(public_key_path)?;
    footer.public_key_pem_offset = current_offset;
    footer.public_key_pem_size = public_key_data.len() as u64;
    file.write_all(&public_key_data)?;
    
    // Set emojis
    footer.language_emoji = language_emoji;
    footer.type_emoji_1 = type_emoji_1;
    footer.type_emoji_2 = type_emoji_2;

    // Calculate and set checksum
    footer.footer_struct_checksum = footer.calculate_checksum();
    
    // Write footer and EOF magic
    file.write_all(&footer.to_bytes())?;
    file.write_all(flavor::FLAVOR_MAGIC_EOF_STRING)?;
    
    log::info!("Flavor data appended successfully");
    Ok(())
}


// 📦🍜📄🪄
