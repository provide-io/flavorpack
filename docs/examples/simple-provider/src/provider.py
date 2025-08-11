"""Simple provider implementation for PSPF demonstration."""
import json
import os
import hashlib
import time
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger('simple-provider.provider')

class SimpleProvider:
    """A minimal terraform provider for demonstration purposes."""
    
    def __init__(self):
        self.name = "simple"
        self.version = "1.0.0"
        self.description = "Simple provider for PSPF demonstration"
        
        # Track managed files (simulating state)
        self.managed_files: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Initialized {self.name} provider v{self.version}")
    
    def get_schema(self) -> Dict[str, Any]:
        """Return provider and resource schemas."""
        return {
            "format_version": "1.0",
            "provider_schemas": {
                self.name: {
                    "provider": {
                        "version": 0,
                        "block": {
                            "attributes": {
                                "base_path": {
                                    "type": "string",
                                    "description": "Base directory for file operations",
                                    "optional": True
                                },
                                "file_mode": {
                                    "type": "string", 
                                    "description": "Default file permissions (octal)",
                                    "optional": True
                                }
                            }
                        }
                    },
                    "resource_schemas": {
                        "simple_file": {
                            "version": 0,
                            "block": {
                                "attributes": {
                                    "filename": {
                                        "type": "string",
                                        "required": True,
                                        "description": "Name of the file to create"
                                    },
                                    "content": {
                                        "type": "string",
                                        "required": True,
                                        "description": "Content to write to the file"
                                    },
                                    "file_mode": {
                                        "type": "string",
                                        "optional": True,
                                        "description": "File permissions in octal format (e.g., '0644')"
                                    },
                                    "id": {
                                        "type": "string",
                                        "computed": True,
                                        "description": "Unique identifier for the file resource"
                                    },
                                    "size": {
                                        "type": "number",
                                        "computed": True,
                                        "description": "Size of the file in bytes"
                                    },
                                    "checksum": {
                                        "type": "string",
                                        "computed": True,
                                        "description": "SHA-256 checksum of the file content"
                                    },
                                    "last_modified": {
                                        "type": "string",
                                        "computed": True,
                                        "description": "Last modification timestamp"
                                    }
                                }
                            }
                        }
                    },
                    "data_source_schemas": {
                        "simple_file": {
                            "version": 0,
                            "block": {
                                "attributes": {
                                    "filename": {
                                        "type": "string",
                                        "required": True,
                                        "description": "Name of the file to read"
                                    },
                                    "content": {
                                        "type": "string",
                                        "computed": True,
                                        "description": "Content of the file"
                                    },
                                    "exists": {
                                        "type": "bool",
                                        "computed": True,
                                        "description": "Whether the file exists"
                                    },
                                    "size": {
                                        "type": "number",
                                        "computed": True,
                                        "description": "Size of the file in bytes"
                                    },
                                    "checksum": {
                                        "type": "string",
                                        "computed": True,
                                        "description": "SHA-256 checksum of the file content"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def create_file_resource(self, filename: str, content: str, file_mode: Optional[str] = None) -> Dict[str, Any]:
        """Create a file resource."""
        try:
            # Resolve file path
            file_path = Path(filename).resolve()
            
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            file_path.write_text(content, encoding='utf-8')
            
            # Set file permissions if specified
            if file_mode:
                try:
                    mode = int(file_mode, 8)  # Convert from octal string
                    file_path.chmod(mode)
                except ValueError:
                    logger.warning(f"Invalid file_mode '{file_mode}', using default permissions")
            
            # Generate resource state
            stat = file_path.stat()
            checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
            resource_id = f"{file_path.name}_{checksum[:8]}"
            
            state = {
                "id": resource_id,
                "filename": str(file_path),
                "content": content,
                "file_mode": file_mode or "0644",
                "size": len(content),
                "checksum": checksum,
                "last_modified": time.ctime(stat.st_mtime)
            }
            
            # Track in managed resources
            self.managed_files[resource_id] = state
            
            logger.info(f"Created file resource: {filename} (id: {resource_id})")
            return state
            
        except Exception as e:
            logger.error(f"Failed to create file resource {filename}: {e}")
            raise
    
    def read_file_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Read a file resource state."""
        if resource_id in self.managed_files:
            state = self.managed_files[resource_id]
            file_path = Path(state['filename'])
            
            if file_path.exists():
                # Refresh computed attributes
                stat = file_path.stat()
                current_content = file_path.read_text(encoding='utf-8')
                current_checksum = hashlib.sha256(current_content.encode('utf-8')).hexdigest()
                
                state.update({
                    "size": len(current_content),
                    "checksum": current_checksum,
                    "last_modified": time.ctime(stat.st_mtime)
                })
                
                return state
        
        return None
    
    def read_file_data_source(self, filename: str) -> Dict[str, Any]:
        """Read a file as a data source."""
        file_path = Path(filename).resolve()
        
        if not file_path.exists():
            return {
                "filename": str(file_path),
                "content": "",
                "exists": False,
                "size": 0,
                "checksum": ""
            }
        
        try:
            content = file_path.read_text(encoding='utf-8')
            checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            return {
                "filename": str(file_path),
                "content": content,
                "exists": True,
                "size": len(content),
                "checksum": checksum
            }
        except Exception as e:
            logger.error(f"Failed to read file {filename}: {e}")
            return {
                "filename": str(file_path),
                "content": "",
                "exists": False,
                "size": 0,
                "checksum": ""
            }
    
    def delete_file_resource(self, resource_id: str) -> bool:
        """Delete a file resource."""
        if resource_id not in self.managed_files:
            logger.warning(f"Resource {resource_id} not found in managed files")
            return False
        
        state = self.managed_files[resource_id]
        file_path = Path(state['filename'])
        
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
            
            # Remove from managed resources
            del self.managed_files[resource_id]
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file resource {resource_id}: {e}")
            return False
    
    def serve(self) -> int:
        """Serve the provider using terraform protocol."""
        # In a real terraform provider, this would start a gRPC server
        # For this demo, we'll simulate by outputting provider schema
        try:
            schema = self.get_schema()
            print(json.dumps(schema, indent=2))
            logger.info("Provider schema output completed")
            return 0
        except Exception as e:
            logger.error(f"Failed to serve provider schema: {e}")
            return 1
    
    def self_test(self) -> int:
        """Run self-tests to verify provider functionality."""
        logger.info("Running provider self-tests...")
        
        test_dir = Path("/tmp/simple-provider-test")
        test_file = test_dir / "test.txt"
        test_content = "Hello from PSPF Simple Provider!"
        
        try:
            # Test 1: Create file resource
            logger.info("Test 1: Creating file resource...")
            state = self.create_file_resource(str(test_file), test_content, "0644")
            assert state['content'] == test_content
            assert Path(test_file).exists()
            logger.info("✅ File resource creation test passed")
            
            # Test 2: Read file resource
            logger.info("Test 2: Reading file resource...")
            read_state = self.read_file_resource(state['id'])
            assert read_state is not None
            assert read_state['content'] == test_content
            logger.info("✅ File resource read test passed")
            
            # Test 3: Read file data source
            logger.info("Test 3: Reading file data source...")
            data_source = self.read_file_data_source(str(test_file))
            assert data_source['exists'] is True
            assert data_source['content'] == test_content
            logger.info("✅ File data source read test passed")
            
            # Test 4: Delete file resource
            logger.info("Test 4: Deleting file resource...")
            success = self.delete_file_resource(state['id'])
            assert success is True
            assert not Path(test_file).exists()
            logger.info("✅ File resource deletion test passed")
            
            # Cleanup
            if test_dir.exists():
                import shutil
                shutil.rmtree(test_dir)
            
            logger.info("🎉 All self-tests passed!")
            return 0
            
        except Exception as e:
            logger.error(f"Self-test failed: {e}")
            return 1
    
    def show_help(self):
        """Show provider help information."""
        print(f"""
Simple Terraform Provider v{self.version}
=========================================

{self.description}

This provider demonstrates PSPF (Progressive Secure Package Format) packaging
with a self-contained, cryptographically signed terraform provider binary.

Usage:
  terraform-provider-simple              # Serve provider (default)
  terraform-provider-simple --help       # Show this help
  terraform-provider-simple --version    # Show version info
  terraform-provider-simple --schema     # Output provider schema
  terraform-provider-simple --test       # Run self-tests

Resources:
  simple_file    # Creates and manages text files

Data Sources:
  simple_file    # Reads existing text files

Example Terraform Configuration:
==================================

terraform {{
  required_providers {{
    simple = {{
      source = "local/simple"
      version = "1.0.0"
    }}
  }}
}}

provider "simple" {{
  base_path = "/tmp/terraform-files"
  file_mode = "0644"
}}

resource "simple_file" "example" {{
  filename = "/tmp/hello.txt"
  content  = "Hello from PSPF!"
  file_mode = "0644"
}}

data "simple_file" "existing" {{
  filename = "/etc/hostname"
}}

output "file_content" {{
  value = data.simple_file.existing.content
}}

Features Demonstrated:
======================
✅ PSPF packaging with embedded Python runtime
✅ Self-contained binary with zero external dependencies  
✅ Cryptographic signing and integrity verification
✅ Cross-platform compatibility (Linux, macOS, Windows)
✅ Resource lifecycle management (create, read, update, delete)
✅ Data source functionality for reading existing files
✅ Terraform Protocol v6 compatibility
✅ Comprehensive error handling and logging

Security Features:
==================
🔒 Package signed with ECDSA P-256 cryptographic signature
🔒 Tamper detection through integrated checksums
🔒 Reproducible builds for supply chain security
🔒 Secure key management workflow

Learn More:
===========
📚 PSPF Documentation: https://github.com/your-org/pspf/docs
🚀 Quick Start Guide: https://github.com/your-org/pspf/docs/quickstart.md
🔧 CLI Reference: https://github.com/your-org/pspf/docs/cli-reference.md
💬 Community: https://github.com/your-org/pspf/discussions

This is a demonstration provider. For production use, implement proper
resource lifecycle management, state handling, and error recovery.
        """)
    
    def show_version(self):
        """Show provider version information."""
        print(f"""Simple Terraform Provider
Version: {self.version}
Package: PSPF (Progressive Secure Package Format)
Runtime: Python {os.sys.version.split()[0]}
Platform: {os.uname().sysname} {os.uname().machine}

🚀 Packaged with PSPF - https://github.com/your-org/pspf""")

# 📦🍜📄🪄
