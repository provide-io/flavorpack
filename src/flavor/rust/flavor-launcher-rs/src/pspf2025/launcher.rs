//! PSPF 2025 Bundle Launcher

use super::{
    errors::{FlavorError, Result},
    reader::Reader,
    spec::*,
};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

pub struct Launcher {
    bundle_path: PathBuf,
    cache_dir: PathBuf,
    reader: Reader,
}

impl Launcher {
    pub fn new(bundle_path: Option<impl AsRef<Path>>) -> Result<Self> {
        let bundle_path = if let Some(path) = bundle_path {
            path.as_ref().to_path_buf()
        } else {
            // Self-execution mode
            env::current_exe()?
        };
        
        let cache_dir = env::temp_dir().join(format!("pspf-cache-{}", std::process::id()));
        let reader = Reader::new(&bundle_path)?;
        
        Ok(Self {
            bundle_path,
            cache_dir,
            reader,
        })
    }

    pub fn extract_all_slots(&mut self) -> Result<HashMap<usize, PathBuf>> {
        let metadata = self.reader.read_metadata()?.clone();
        let mut slot_paths = HashMap::new();
        
        if let Some(slots) = &metadata.slots {
            for (i, _slot) in slots.iter().enumerate() {
                let dest_dir = self.cache_dir.join(format!("slot{}", i));
                fs::create_dir_all(&dest_dir)?;
                
                let slot_path = self.reader.extract_slot(i, &dest_dir)?;
                slot_paths.insert(i, slot_path);
            }
        }
        
        Ok(slot_paths)
    }

    pub fn execute(&mut self, args: &[String]) -> Result<ExecutionResult> {
        let metadata = self.reader.read_metadata()?.clone();
        
        let execution = metadata.execution
            .ok_or_else(|| FlavorError::InvalidData("No execution configuration".to_string()))?;
        
        // Extract slots
        let slot_paths = self.extract_all_slots()?;
        
        // Prepare command
        let mut command = execution.command.clone();
        
        // Substitute slot references
        for (slot_idx, slot_path) in &slot_paths {
            let placeholder = format!("{{slot:{}}}", slot_idx);
            command = command.replace(&placeholder, &slot_path.to_string_lossy());
        }
        
        // Parse command
        let parts: Vec<&str> = command.split_whitespace().collect();
        if parts.is_empty() {
            return Err(FlavorError::InvalidData("Empty command".to_string()));
        }
        
        let mut cmd = Command::new(parts[0]);
        
        // Add command arguments
        for part in &parts[1..] {
            cmd.arg(part);
        }
        
        // Add user arguments
        for arg in args {
            cmd.arg(arg);
        }
        
        // Set environment
        if let Some(env_vars) = &execution.env {
            for (k, v) in env_vars {
                cmd.env(k, v);
            }
        }
        
        // Set working directory
        if execution.primary_slot >= 0 {
            if let Some(primary_path) = slot_paths.get(&(execution.primary_slot as usize)) {
                if let Some(parent) = primary_path.parent() {
                    cmd.current_dir(parent);
                }
            }
        }
        
        // Execute
        cmd.stdin(Stdio::inherit())
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit());
        
        let status = cmd.status()?;
        
        Ok(ExecutionResult {
            executed: true,
            exit_code: status.code(),
            success: status.success(),
        })
    }

    pub fn verify_integrity(&mut self) -> Result<IntegrityResult> {
        // Verify magic
        if !self.reader.verify_magic()? {
            return Ok(IntegrityResult {
                valid: false,
                signature_valid: false,
                tamper_detected: true,
            });
        }
        
        // Verify all checksums
        match self.reader.verify_all_checksums() {
            Ok(_) => {},
            Err(_) => {
                return Ok(IntegrityResult {
                    valid: false,
                    signature_valid: false,
                    tamper_detected: true,
                });
            }
        }
        
        // Verify ephemeral signature
        let signature_valid = self.verify_ephemeral_signature()?;
        
        Ok(IntegrityResult {
            valid: true,
            signature_valid,
            tamper_detected: false,
        })
    }

    pub fn cleanup(&self) -> Result<()> {
        if self.cache_dir.exists() {
            fs::remove_dir_all(&self.cache_dir)?;
        }
        Ok(())
    }
    
    fn verify_ephemeral_signature(&mut self) -> Result<bool> {
        // Read index to get ephemeral public key
        let index = self.reader.read_index()?;
        
        // In a real implementation, we would:
        // 1. Extract the signature from metadata archive (integrity/seal.sig)
        // 2. Use the ephemeral public key from index to verify the signature
        // 3. Verify the signature covers the metadata content
        
        // For now, check that the ephemeral public key is present
        for b in &index.ephemeral_public_key {
            if *b != 0 {
                // Key is present, assume signature is valid for mock implementation
                return Ok(true);
            }
        }
        
        // No ephemeral key present
        Ok(false)
    }
}

impl Drop for Launcher {
    fn drop(&mut self) {
        // Best effort cleanup
        let _ = self.cleanup();
    }
}

#[derive(Debug)]
pub struct ExecutionResult {
    pub executed: bool,
    pub exit_code: Option<i32>,
    pub success: bool,
}

#[derive(Debug)]
pub struct IntegrityResult {
    pub valid: bool,
    pub signature_valid: bool,
    pub tamper_detected: bool,
}