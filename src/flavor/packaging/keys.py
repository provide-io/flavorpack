#
# flavor/packaging/keys.py
#
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate_key_pair(keys_dir: Path) -> tuple[Path, Path]:
    """Generates a new ECDSA key pair and saves them to the specified directory."""
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_key_path = keys_dir / "flavor-private.key"
    public_key_path = keys_dir / "flavor-public.key"

    keys_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_key_path.write_bytes(private_pem)
    private_key_path.chmod(0o600)
    public_key_path.write_bytes(public_pem)
    public_key_path.chmod(0o600)

    return private_key_path, public_key_path


# 🎮 🔧 ⚖️


# 📦🍜📄🪄
