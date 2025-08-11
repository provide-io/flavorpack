# Terraform version and provider requirements
# This file defines the terraform and provider version constraints

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    simple = {
      source  = "local/simple"
      version = "1.0.0"
    }
  }
  
  # Optional: Configure backend for state storage
  # For this demo, we use local state (default)
  # backend "local" {
  #   path = "./terraform.tfstate"
  # }
}

# Provider-specific configuration
# These settings apply to all resources using this provider
provider "simple" {
  # Base directory where the provider will create files
  # This helps organize created files and avoid conflicts
  base_path = "/tmp/terraform-simple-provider"
  
  # Default file permissions for created files (octal notation)
  file_mode = "0644"
}

# Local values for reuse across resources
locals {
  # Common metadata for all files
  creation_info = {
    created_by = "PSPF Simple Provider"
    created_at = timestamp()
    terraform_workspace = terraform.workspace
  }
  
  # Base directory for organized file creation
  demo_dir = "/tmp/terraform-simple-provider"
  
  # Demo content template
  demo_content_template = <<-EOT
Created by: ${local.creation_info.created_by}
Timestamp: ${local.creation_info.created_at}
Workspace: ${local.creation_info.terraform_workspace}

This file demonstrates PSPF packaging capabilities:
%s
EOT
}

# 📦🍜🔧🪄
