"""
PSPF 2025 Cryptography Implementation
"""

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from pyvider.telemetry import logger


def generate_key_pair() -> tuple[bytes, bytes]:
    """Generate Ed25519 key pair for package signing (in-memory).

    This function is used for internal package building where keys are
    generated, used immediately for signing, and then discarded (ephemeral keys).
    For CLI operations where keys need to be saved to files, use
    flavor.packaging.keys.generate_key_pair() which handles file persistence.

    Returns:
        tuple: (private_key_bytes, public_key_bytes)
            - private_key_bytes: 32-byte Ed25519 private key seed
            - public_key_bytes: 32-byte Ed25519 public key
            
    See Also:
        flavor.packaging.keys.generate_key_pair: For file-based key generation
    """
    logger.debug("🔐 Generating Ed25519 key pair")

    # Generate a new Ed25519 private key
    private_key = ed25519.Ed25519PrivateKey.generate()

    # Get the raw bytes for compatibility with Go/Rust implementations
    # NOTE: private_bytes_raw() returns the 32-byte seed, not the full 64-byte key
    private_key_bytes = private_key.private_bytes_raw()
    public_key_bytes = private_key.public_key().public_bytes_raw()

    logger.debug(f"✅ Generated key pair (public key: {len(public_key_bytes)} bytes)")
    return private_key_bytes, public_key_bytes


def sign_data(data: bytes, private_key_bytes: bytes) -> bytes:
    """Sign data with Ed25519 private key.

    Args:
        data: The data to sign
        private_key_bytes: 32-byte Ed25519 private key seed

    Returns:
        bytes: 64-byte Ed25519 signature
    """
    logger.debug(f"🔏 Signing {len(data)} bytes of data")

    # Reconstruct the private key from the seed bytes
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)

    # Sign the data
    signature = private_key.sign(data)

    logger.debug(f"✅ Created signature ({len(signature)} bytes)")
    return signature


def verify_signature(data: bytes, signature: bytes, public_key_bytes: bytes) -> bool:
    """Verify Ed25519 signature.

    Args:
        data: The data that was signed
        signature: 64-byte Ed25519 signature
        public_key_bytes: 32-byte Ed25519 public key

    Returns:
        bool: True if signature is valid, False otherwise
    """
    logger.debug(f"🔍 Verifying signature for {len(data)} bytes of data")

    try:
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature, data)
        logger.debug("✅ Signature verification successful")
        return True
    except InvalidSignature:
        logger.warning("❌ Invalid signature")
        return False
    except Exception as e:
        logger.error(f"❌ Signature verification error: {e}")
        return False
