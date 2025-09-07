# Security Troubleshooting

Common security-related issues and their solutions when working with FlavorPack packages.

## Signature Verification Errors

### Invalid Signature Error

**Symptom**: Package fails verification with "Invalid signature" error

**Solutions**:
1. Verify the package hasn't been corrupted during download
2. Ensure you're using the correct public key for verification
3. Check if the package was signed with the expected key

```bash
# Verify package integrity
flavor verify myapp.psp --key-file public.key

# Check package signature details
flavor inspect myapp.psp --show-signature
```

### Missing Signature

**Symptom**: Package has no signature when one is expected

**Solution**: Re-sign the package or build with signing enabled:

```bash
# Sign an existing package
flavor sign myapp.psp --key-file private.key

# Build with signing
flavor pack --manifest pyproject.toml --sign --key-file private.key
```

## Permission Issues

### Extraction Permission Denied

**Symptom**: Cannot extract package due to permission errors

**Solutions**:
1. Check file system permissions
2. Ensure sufficient disk space
3. Verify the extraction directory is writable

```bash
# Check permissions
ls -la ~/.cache/flavor/workenv/

# Fix permissions
chmod 755 ~/.cache/flavor/workenv/
```

### Execution Permission Denied

**Symptom**: Package executable cannot run

**Solution**: Ensure the package has execute permissions:

```bash
# Add execute permission
chmod +x myapp.psp

# Check permissions
ls -la myapp.psp
```

## Key Management Issues

### Lost Private Key

**Symptom**: Cannot sign packages due to missing private key

**Prevention**:
- Always backup private keys securely
- Use key management systems for production
- Rotate keys periodically

### Key Format Errors

**Symptom**: "Invalid key format" when signing or verifying

**Solution**: Ensure keys are in the correct Ed25519 format:

```bash
# Generate new key pair
flavor keygen --output keys/

# Convert existing keys if needed
flavor keys convert --input old.key --output new.key
```

## Security Best Practices

### Development Environment

```bash
# Use separate keys for development
flavor keygen --output dev-keys/

# Enable insecure mode for local testing only
export FLAVOR_INSECURE=1
```

### Production Environment

1. **Never share private keys**
2. **Use environment variables for sensitive data**
3. **Enable signature verification**
4. **Audit package contents before deployment**

```bash
# Audit package contents
flavor inspect myapp.psp --detailed

# Verify before running
flavor verify myapp.psp && ./myapp.psp
```

## Common Security Warnings

### Insecure Mode Warning

**Warning**: "Running in insecure mode - signatures not verified"

**Solution**: Remove `FLAVOR_INSECURE=1` from environment for production use

### Weak Key Warning

**Warning**: "Key strength below recommended minimum"

**Solution**: Generate new keys with proper entropy:

```bash
# Generate strong keys
flavor keygen --output keys/ --strength high
```

## Getting Additional Help

For security issues not covered here:

1. Review the [Security Model](../guide/concepts/security.md) documentation
2. Check the main [Troubleshooting Guide](index.md)
3. Report security vulnerabilities privately via GitHub Security Advisories

## Related Documentation

- [Security Model](../guide/concepts/security.md) - Complete security documentation
- [Signing Packages](../guide/packaging/signing.md) - Package signing guide
- [Key Management](../api/python/packaging/keys.md) - Key management API