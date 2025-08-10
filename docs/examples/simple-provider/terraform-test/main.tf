# Terraform configuration for testing the Simple Provider PSPF package
terraform {
  required_version = ">= 1.0"
  required_providers {
    simple = {
      source  = "local/simple"
      version = "1.0.0"
    }
  }
}

provider "simple" {
  # Provider configuration
  base_path = "/tmp/terraform-simple-provider"
  file_mode = "0644"
}

# Example resource using the simple provider
# Note: This is a demonstration - the simple provider creates actual files
resource "simple_file" "example" {
  filename  = "/tmp/terraform-simple-provider/hello.txt"
  content   = "Hello from PSPF Simple Provider!\n\nThis file was created by a Terraform provider\npackaged with PSPF (Progressive Secure Package Format).\n\nFeatures demonstrated:\n✅ Self-contained binary with embedded Python runtime\n✅ Cryptographic signing and verification\n✅ Zero external dependencies\n✅ Cross-platform compatibility\n\nTimestamp: ${timestamp()}"
  file_mode = "0644"
}

# Another example file with different content
resource "simple_file" "readme" {
  filename = "/tmp/terraform-simple-provider/README.md"
  content = <<-EOT
# Simple Provider Demo

This directory was created by the PSPF Simple Provider example.

## Files created:
- hello.txt - Demo file with timestamp
- README.md - This file

## Provider Information:
- Name: Simple Provider
- Version: 1.0.0
- Package Format: PSPF v0.1
- Runtime: Embedded Python

## Learn More:
- PSPF Documentation: https://github.com/your-org/pspf/docs
- Examples: https://github.com/your-org/pspf/docs/examples

This demonstrates how PSPF enables secure, self-contained
distribution of Terraform providers.
EOT
  file_mode = "0644"
}

# Data source example - reads an existing file
data "simple_file" "system_info" {
  filename = "/etc/hostname"
}

# Outputs to display information about created resources
output "example_file_info" {
  description = "Information about the created example file"
  value = {
    id       = simple_file.example.id
    filename = simple_file.example.filename
    size     = simple_file.example.size
    checksum = simple_file.example.checksum
  }
}

output "readme_file_info" {
  description = "Information about the created README file"
  value = {
    id       = simple_file.readme.id
    filename = simple_file.readme.filename
    size     = simple_file.readme.size
    checksum = simple_file.readme.checksum
  }
}

output "system_hostname" {
  description = "System hostname read from /etc/hostname (if exists)"
  value = {
    content = data.simple_file.system_info.content
    exists  = data.simple_file.system_info.exists
    size    = data.simple_file.system_info.size
  }
}

output "provider_demo_summary" {
  description = "Summary of the PSPF Simple Provider demonstration"
  value = {
    message              = "🎉 PSPF Simple Provider demonstration completed successfully!"
    files_created        = 2
    provider_version     = "1.0.0"
    package_format       = "PSPF (Progressive Secure Package Format)"
    security_features    = ["ECDSA P-256 signatures", "Tamper detection", "Integrity verification"]
    runtime_features     = ["Embedded Python", "Zero dependencies", "Self-contained binary"]
    next_steps          = "Try the AWS Resources example or Database Provider example for more advanced features"
  }
}

# 📦🍜🏗️🪄
