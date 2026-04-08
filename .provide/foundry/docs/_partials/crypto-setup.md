### Cryptography and Security Setup

Configuration for certificates, signing keys, and secure communication.

#### Ed25519 Key Generation

For package signing and authentication:

```bash
# Generate Ed25519 key pair
python -c "
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Generate private key
private_key = ed25519.Ed25519PrivateKey.generate()

# Generate public key
public_key = private_key.public_key()

# Serialize private key
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Serialize public key
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Write keys to files
with open('private_key.pem', 'wb') as f:
    f.write(private_pem)
with open('public_key.pem', 'wb') as f:
    f.write(public_pem)

print('✅ Keys generated: private_key.pem, public_key.pem')
"
```

**Key File Permissions:**

```bash
# Secure private key (read-only for owner)
chmod 600 private_key.pem

# Public key can be world-readable
chmod 644 public_key.pem

# Verify permissions
ls -l *.pem
```

**Expected output:**
```
-rw------- 1 user user  119 Jan 15 10:30 private_key.pem
-rw-r--r-- 1 user user   88 Jan 15 10:30 public_key.pem
```

#### Certificate Generation

For TLS/SSL and mTLS communication:

**Self-Signed Certificate:**

```bash
# Generate private key and self-signed certificate
openssl req -x509 \
  -newkey rsa:4096 \
  -keyout server_key.pem \
  -out server_cert.pem \
  -days 365 \
  -nodes \
  -subj "/CN=localhost/O=Development/C=US"

# Verify certificate
openssl x509 -in server_cert.pem -text -noout
```

**Certificate Authority (CA) Setup:**

```bash
# 1. Generate CA private key
openssl genrsa -out ca_key.pem 4096

# 2. Generate CA certificate
openssl req -new -x509 \
  -key ca_key.pem \
  -out ca_cert.pem \
  -days 3650 \
  -subj "/CN=Development CA/O=Development/C=US"

# 3. Generate server private key
openssl genrsa -out server_key.pem 4096

# 4. Create certificate signing request (CSR)
openssl req -new \
  -key server_key.pem \
  -out server_csr.pem \
  -subj "/CN=localhost/O=Development/C=US"

# 5. Sign certificate with CA
openssl x509 -req \
  -in server_csr.pem \
  -CA ca_cert.pem \
  -CAkey ca_key.pem \
  -CAcreateserial \
  -out server_cert.pem \
  -days 365

# Clean up CSR
rm server_csr.pem
```

**Mutual TLS (mTLS) Certificates:**

```bash
# Generate client certificate (after CA setup above)
openssl genrsa -out client_key.pem 4096

openssl req -new \
  -key client_key.pem \
  -out client_csr.pem \
  -subj "/CN=client/O=Development/C=US"

openssl x509 -req \
  -in client_csr.pem \
  -CA ca_cert.pem \
  -CAkey ca_key.pem \
  -CAcreateserial \
  -out client_cert.pem \
  -days 365

rm client_csr.pem
```

#### GPG/PGP Key Setup

For signing commits and releases:

**Generate GPG Key:**

```bash
# Generate key (follow prompts)
gpg --full-generate-key

# Choose:
# - Key type: (1) RSA and RSA
# - Key size: 4096
# - Expiration: 1y (or as needed)
# - Name and email

# List keys
gpg --list-secret-keys --keyid-format LONG

# Export public key
gpg --armor --export YOUR_EMAIL > gpg_public_key.asc

# Export private key (secure backup)
gpg --armor --export-secret-keys YOUR_EMAIL > gpg_private_key.asc
```

**Configure Git with GPG:**

```bash
# Get key ID
gpg --list-secret-keys --keyid-format LONG

# Configure Git
git config --global user.signingkey YOUR_KEY_ID
git config --global commit.gpgsign true

# Test signing
git commit --allow-empty -m "Test GPG signing"
git verify-commit HEAD
```

#### File Permissions and Security

**Recommended Permissions:**

| File Type | Permissions | Owner | Purpose |
|-----------|-------------|-------|---------|
| Private keys (*.pem, *.key) | 600 (`-rw-------`) | User only | Encryption, signing |
| Public keys (*.pub, *.cert) | 644 (`-rw-r--r--`) | World readable | Verification |
| CA certificates | 644 (`-rw-r--r--`) | World readable | Trust chain |
| Configuration files with secrets | 600 (`-rw-------`) | User only | API keys, tokens |
| Scripts with credentials | 700 (`-rwx------`) | User only | Automated operations |

**Setting Permissions:**

```bash
# Secure all private keys in directory
chmod 600 *.key *.pem 2>/dev/null || true

# Make public certs readable
chmod 644 *.cert *.pub 2>/dev/null || true

# Verify
find . -name "*.key" -o -name "*_key.pem" | xargs ls -l
```

#### Certificate Verification

**Verify Certificate Chain:**

```bash
# Verify server certificate against CA
openssl verify -CAfile ca_cert.pem server_cert.pem

# Should output: server_cert.pem: OK
```

**Check Certificate Expiration:**

```bash
# View certificate dates
openssl x509 -in server_cert.pem -noout -dates

# Check if certificate is valid for specific date
openssl x509 -in server_cert.pem -noout -checkend 86400
# Exit code 0 = valid for next 24 hours
# Exit code 1 = expires within 24 hours
```

**Inspect Certificate Contents:**

```bash
# Full certificate details
openssl x509 -in server_cert.pem -text -noout

# Just subject and issuer
openssl x509 -in server_cert.pem -noout -subject -issuer

# Just validity dates
openssl x509 -in server_cert.pem -noout -dates
```

#### Environment Variables for Crypto

Common environment variables for certificate paths:

```bash
# Certificate paths
export SSL_CERT_FILE=/path/to/ca_cert.pem
export SSL_CERT_DIR=/path/to/certs/

# Custom certificate authority
export REQUESTS_CA_BUNDLE=/path/to/ca_cert.pem
export CURL_CA_BUNDLE=/path/to/ca_cert.pem

# mTLS configuration
export CLIENT_CERT=/path/to/client_cert.pem
export CLIENT_KEY=/path/to/client_key.pem

# Signing keys
export SIGNING_KEY_PATH=/path/to/private_key.pem
export VERIFY_KEY_PATH=/path/to/public_key.pem
```

#### Python Usage Examples

**Using Certificates in Python:**

```python
from provide.foundation.crypto import Certificate
from pathlib import Path

# Load certificate
cert = Certificate.load_from_file(Path("server_cert.pem"))

# Verify certificate
cert.verify(ca_cert_path=Path("ca_cert.pem"))

# Get certificate info
print(f"Subject: {cert.subject}")
print(f"Issuer: {cert.issuer}")
print(f"Not before: {cert.not_valid_before}")
print(f"Not after: {cert.not_valid_after}")
```

**Signing and Verification:**

```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Load private key
with open("private_key.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(
        f.read(),
        password=None
    )

# Sign data
message = b"Important message"
signature = private_key.sign(message)

# Load public key
with open("public_key.pem", "rb") as f:
    public_key = serialization.load_pem_public_key(f.read())

# Verify signature
try:
    public_key.verify(signature, message)
    print("✅ Signature valid")
except Exception as e:
    print(f"❌ Signature invalid: {e}")
```

#### Security Best Practices

**Key Storage:**

1. **Never commit private keys to version control**
   - Add `*.key`, `*.pem` (private), `*.p12` to `.gitignore`
   - Use environment variables or secret management systems

2. **Use key rotation**
   - Regenerate keys periodically (e.g., annually)
   - Keep old public keys for verification of old signatures
   - Update systems to use new keys before expiration

3. **Backup keys securely**
   - Encrypt backups with strong passphrase
   - Store in secure location (password manager, HSM, vault)
   - Test restore procedures

**Certificate Management:**

1. **Monitor expiration**
   - Set alerts for certificates expiring soon
   - Automate renewal where possible
   - Keep certificate inventory

2. **Use proper certificate hierarchy**
   - Root CA → Intermediate CA → Leaf certificates
   - Keep root CA offline when possible
   - Use intermediate CA for day-to-day signing

3. **Validate certificate chains**
   - Always verify full chain to trusted root
   - Check for revocation (CRL, OCSP)
   - Reject self-signed certs in production

#### Troubleshooting

**Issue: Permission denied reading private key**

```bash
# Check permissions
ls -l private_key.pem

# Fix permissions
chmod 600 private_key.pem

# Verify ownership
sudo chown $USER:$USER private_key.pem
```

**Issue: Certificate verification failed**

```bash
# Check certificate chain
openssl verify -CAfile ca_cert.pem server_cert.pem

# Verify certificate hasn't expired
openssl x509 -in server_cert.pem -noout -dates

# Check certificate matches private key
diff \
  <(openssl x509 -in server_cert.pem -pubkey -noout) \
  <(openssl pkey -in server_key.pem -pubout)
```

**Issue: GPG signing fails**

```bash
# Test GPG functionality
echo "test" | gpg --clearsign

# Check key exists
gpg --list-secret-keys

# Verify Git configuration
git config --get user.signingkey

# Test with verbose output
GIT_TRACE=1 git commit --allow-empty -S -m "test"
```

#### Additional Resources

- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [Cryptography.io Documentation](https://cryptography.io/)
- [GPG Manual](https://www.gnupg.org/documentation/)
- [TLS/SSL Best Practices](https://wiki.mozilla.org/Security/Server_Side_TLS)
