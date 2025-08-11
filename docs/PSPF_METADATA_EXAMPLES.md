# Flavor Metadata JSON Examples

## 1. flavor.json - Flavor Format Metadata
```json
{
  "format_version": "0.2",
  "format_name": "Progressive Secure Package Format",
  "created_at": "2024-01-20T15:45:32.123Z",
  "created_by": {
    "tool": "flavor",
    "version": "0.1.0",
    "command": "flavor package --manifest pyproject.toml"
  },
  "build_host": {
    "hostname": "build-server-01",
    "platform": "darwin_arm64",
    "os_version": "14.2.1",
    "python_version": "3.13.0"
  },
  "package_info": {
    "size_bytes": 125398400,
    "compression": {
      "uv": "zstd",
      "archives": "gzip"
    }
  },
  "flags_interpretation": {
    "raw_value": 11,
    "uv_compressed": true,
    "python_included": true,
    "signature_type": "ecdsa",
    "development_mode": false,
    "platform_specific": false,
    "archive_format": "tar.gz"
  },
  "sections": {
    "uv": {
      "included": true,
      "version": "0.1.18",
      "platform": "darwin_arm64"
    },
    "python": {
      "version": "3.13.0",
      "implementation": "cpython",
      "abi": "cp313"
    },
    "metadata": {
      "files": ["flavor.json", "package.json", "runtime.json", "dependencies.json", "checksums.json"]
    },
    "payload": {
      "packages_count": 47,
      "total_size": 18294720
    }
  }
}
```

## 2. package.json - Package Information
```json
{
  "name": "terraform-provider-aws",
  "version": "5.31.0",
  "description": "Terraform AWS provider with Python implementation using Pyvider framework",
  "author": {
    "name": "Example Corp",
    "email": "dev@example.com",
    "url": "https://example.com"
  },
  "license": "MPL-2.0",
  "homepage": "https://github.com/example/terraform-provider-aws",
  "repository": {
    "type": "git",
    "url": "https://github.com/example/terraform-provider-aws.git"
  },
  "bugs": {
    "url": "https://github.com/example/terraform-provider-aws/issues"
  },
  "keywords": ["terraform", "aws", "provider", "infrastructure", "cloud"],
  "terraform": {
    "protocol_version": 6,
    "provider_namespace": "example",
    "provider_type": "aws",
    "provider_version": "5.31.0"
  },
  "supported_platforms": [
    "darwin_amd64",
    "darwin_arm64", 
    "linux_amd64",
    "linux_arm64",
    "windows_amd64"
  ],
  "requirements": {
    "terraform": ">=1.0",
    "python": ">=3.9,<4.0"
  },
  "metadata": {
    "build_date": "2024-01-20T15:45:32Z",
    "git_commit": "a1b2c3d4e5f6",
    "ci_run_id": "12345",
    "release_notes": "https://github.com/example/terraform-provider-aws/releases/tag/v5.31.0"
  }
}
```

## 3. runtime.json - Runtime Configuration
```json
{
  "entry_point": "terraform_provider_aws.main:serve",
  "entry_module": "terraform_provider_aws",
  "entry_function": "serve",
  "working_directory": ".",
  "python_executable": "./python/bin/python3.13",
  "python_args": [
    "-u",
    "-W", "ignore::DeprecationWarning",
    "-O"
  ],
  "environment": {
    "PYTHONPATH": "./payload/site-packages:./payload",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUNBUFFERED": "1",
    "TF_PROVIDER_AWS_LOG": "${TF_LOG}",
    "GRPC_VERBOSITY": "ERROR",
    "GRPC_TRACE": "",
    "SSL_CERT_DIR": "./certificates",
    "AWS_SHARED_CREDENTIALS_FILE": "${HOME}/.aws/credentials",
    "AWS_CONFIG_FILE": "${HOME}/.aws/config"
  },
  "inherit_env": [
    "HOME",
    "USER",
    "PATH",
    "AWS_PROFILE",
    "AWS_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "TF_LOG",
    "TF_LOG_PATH"
  ],
  "capabilities": {
    "network": {
      "allowed": true,
      "restrictions": {
        "allowed_domains": ["*.amazonaws.com", "*.aws.amazon.com"],
        "blocked_ports": [25, 465, 587]
      }
    },
    "filesystem": {
      "allowed": true,
      "restrictions": {
        "read_paths": ["${HOME}/.aws", "${HOME}/.terraform"],
        "write_paths": ["./tmp", "${TMPDIR}"],
        "blocked_paths": ["/etc", "/usr", "/bin", "/sbin"]
      }
    },
    "subprocess": {
      "allowed": false
    }
  },
  "resource_limits": {
    "max_memory_mb": 2048,
    "max_cpu_percent": 100,
    "timeout_seconds": 300,
    "max_open_files": 1024
  },
  "logging": {
    "level": "${TF_LOG:-INFO}",
    "format": "json",
    "outputs": ["stderr"],
    "redact_patterns": [
      "aws_access_key_id=([A-Z0-9]+)",
      "aws_secret_access_key=([A-Za-z0-9/+=]+)"
    ]
  }
}
```

## 4. dependencies.json - Dependency Manifest
```json
{
  "resolver": "uv",
  "resolver_version": "0.1.18",
  "resolution_date": "2024-01-20T15:30:00Z",
  "python_version": "3.13.0",
  "platform": {
    "os": "darwin",
    "arch": "arm64",
    "libc": null
  },
  "direct_dependencies": [
    "terraform-provider-aws==5.31.0",
    "pyvider>=0.7.0,<0.8.0",
    "boto3>=1.34.0",
    "structlog>=24.0.0"
  ],
  "resolved_packages": {
    "terraform-provider-aws": {
      "version": "5.31.0",
      "source": "directory",
      "path": "./src",
      "hash": null
    },
    "pyvider": {
      "version": "0.7.11",
      "source": "pypi",
      "hash": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef12345678",
      "size_bytes": 145920,
      "requires": ["grpcio>=1.60.0", "attrs>=23.0.0", "structlog>=24.0.0"]
    },
    "boto3": {
      "version": "1.34.25",
      "source": "pypi", 
      "hash": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef123456",
      "size_bytes": 3854720,
      "requires": ["botocore>=1.34.25", "s3transfer>=0.10.0", "jmespath>=0.7.1"]
    },
    "botocore": {
      "version": "1.34.25",
      "source": "pypi",
      "hash": "sha256:fedcba0987654321fedcba0987654321fedcba0987654321fedcba09876543",
      "size_bytes": 12459008,
      "requires": ["jmespath>=0.7.1", "python-dateutil>=2.1", "urllib3>=1.25.4,<2.1"]
    },
    "structlog": {
      "version": "24.1.0",
      "source": "pypi",
      "hash": "sha256:9876543210fedcba9876543210fedcba9876543210fedcba9876543210fedc",
      "size_bytes": 98304,
      "requires": []
    },
    "grpcio": {
      "version": "1.60.1",
      "source": "pypi",
      "hash": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789ab",
      "size_bytes": 8745984,
      "requires": [],
      "platform_specific": true
    },
    "attrs": {
      "version": "23.2.0",
      "source": "pypi",
      "hash": "sha256:bcdef0123456789bcdef0123456789bcdef0123456789bcdef0123456789bc",
      "size_bytes": 61440,
      "requires": []
    }
  },
  "dependency_graph": {
    "terraform-provider-aws": ["pyvider", "boto3", "structlog"],
    "pyvider": ["grpcio", "attrs", "structlog"],
    "boto3": ["botocore", "s3transfer", "jmespath"],
    "botocore": ["jmespath", "python-dateutil", "urllib3"]
  },
  "total_packages": 23,
  "total_size_bytes": 38457344,
  "vulnerabilities_check": {
    "date": "2024-01-20T15:35:00Z",
    "found": 0,
    "database_version": "2024.01.20"
  }
}
```

## 5. checksums.json - Integrity Verification
```json
{
  "algorithm": "sha256",
  "generated_at": "2024-01-20T15:45:30Z",
  "sections": {
    "uv": {
      "size_bytes": 4587520,
      "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "compressed": true,
      "compression_algorithm": "zstd"
    },
    "python": {
      "size_bytes": 89234432,
      "checksum": "a665a45920422f83a63e5b7e0e5f3d7c8f3e9d2a4c5f8e9b0c1d2e3f4a5b6c7d8e9f0",
      "compressed": true,
      "compression_algorithm": "gzip"
    },
    "metadata": {
      "size_bytes": 12288,
      "checksum": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
      "compressed": true,
      "compression_algorithm": "gzip"
    },
    "payload": {
      "size_bytes": 31457280,
      "checksum": "fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
      "compressed": true,
      "compression_algorithm": "gzip"
    },
    "signature": {
      "size_bytes": 71,
      "checksum": "0987654321fedcba0987654321fedcba0987654321fedcba0987654321fedcba"
    },
    "public_key": {
      "size_bytes": 178,
      "checksum": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    }
  },
  "payload_contents": {
    "site-packages/terraform_provider_aws/__init__.py": "1a2b3c4d5e6f7890",
    "site-packages/terraform_provider_aws/main.py": "0f9e8d7c6b5a4321",
    "site-packages/terraform_provider_aws/resources/ec2.py": "1234abcd5678ef90",
    "site-packages/pyvider/__init__.py": "fedcba9876543210",
    "site-packages/boto3/__init__.py": "0123456789abcdef"
  },
  "total_package_checksum": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
}
```

## 6. Example: Minimal Development Package
```json
// flavor.json
{
  "format_version": "0.2",
  "created_at": "2024-01-20T10:00:00Z",
  "created_by": {
    "tool": "flavor",
    "version": "0.1.0"
  },
  "flags_interpretation": {
    "development_mode": true,
    "python_included": false
  }
}

// package.json
{
  "name": "terraform-provider-mytest",
  "version": "0.0.1-dev",
  "description": "Development test provider",
  "author": {
    "name": "Developer"
  },
  "license": "MIT"
}

// runtime.json
{
  "entry_point": "mytest_provider:main",
  "environment": {
    "PYTHONPATH": "./payload/site-packages",
    "TF_LOG": "DEBUG"
  },
  "capabilities": {
    "network": {"allowed": true},
    "filesystem": {"allowed": true}
  }
}

// dependencies.json
{
  "direct_dependencies": ["pyvider>=0.7.0"],
  "resolved_packages": {
    "pyvider": {"version": "0.7.11"},
    "mytest-provider": {"version": "0.0.1", "source": "directory"}
  }
}

// checksums.json
{
  "algorithm": "sha256",
  "sections": {
    "payload": {
      "size_bytes": 1024000,
      "checksum": "abcd1234..."
    }
  }
}
```