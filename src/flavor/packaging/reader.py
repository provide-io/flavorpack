#
# flavor/packaging/reader.py
#
from pathlib import Path

from ..exceptions import InvalidFooterError, VerificationError
from ..models import FLAVOR_EOF_MAGIC_STRING, FOOTER_SIZE, PSPFV1Footer


class FlavorReader:
    """Reads and verifies a Pyvider Secure Package Format (Flavor) file."""

    def __init__(self, package_path: Path) -> None:
        self.package_path = package_path

    def verify(self) -> PSPFV1Footer:
        """
        Verifies the package's structure and integrity.

        Raises:
            VerificationError: If the package is invalid.

        Returns:
            The parsed FlavorFooter if verification is successful.
        """
        try:
            with self.package_path.open("rb") as f:
                # THE FIX: Check file size before attempting to seek.
                f.seek(0, 2)  # os.SEEK_END
                file_size = f.tell()
                min_size = FOOTER_SIZE + len(FLAVOR_EOF_MAGIC_STRING)
                if file_size < min_size:
                    raise VerificationError(
                        f"File is too small. Minimum size is {min_size}, but file is {file_size} bytes."
                    )

                # Verify EOF magic
                f.seek(-len(FLAVOR_EOF_MAGIC_STRING), 2)
                eof_magic = f.read()
                if eof_magic != FLAVOR_EOF_MAGIC_STRING:
                    raise InvalidFooterError(
                        f"Invalid Flavor EOF Magic. Found {eof_magic!r}."
                    )

                # Read and unpack footer
                f.seek(-len(FLAVOR_EOF_MAGIC_STRING) - FOOTER_SIZE, 2)
                footer_bytes = f.read(FOOTER_SIZE)
                footer = PSPFV1Footer.unpack(footer_bytes)
                return footer
        except (OSError, ValueError) as e:
            raise VerificationError(f"Failed to read or unpack footer: {e}") from e

    def get_info(self) -> str:
        """
        Returns a human-readable string with package information.

        Returns:
            Formatted string with package details.
        """
        try:
            footer = self.verify()
            file_size = self.package_path.stat().st_size

            info = "📦 Flavor Package Information\n"
            info += f"File: {self.package_path.name}\n"
            info += f"Size: {file_size:,} bytes\n"
            info += f"Version: {footer.flavor_version}\n"
            info += f"Flags: 0x{footer.flags:04x}\n"

            if footer.is_uv_binary_compressed:
                info += "UV Binary: Compressed\n"
            else:
                info += "UV Binary: Uncompressed\n"

            info += f"UV Binary: {footer.uv_binary_size:,} bytes at offset {footer.uv_binary_offset}\n"
            info += f"Python Install: {footer.python_install_tgz_size:,} bytes at offset {footer.python_install_tgz_size}\n"
            info += f"Metadata: {footer.metadata_tgz_size:,} bytes at offset {footer.metadata_tgz_offset}\n"
            info += f"Payload: {footer.payload_tgz_size:,} bytes at offset {footer.payload_tgz_offset}\n"
            info += f"Signature: {footer.package_signature_size:,} bytes at offset {footer.package_signature_offset}\n"
            info += f"Public Key: {footer.public_key_pem_size:,} bytes at offset {footer.public_key_pem_offset}\n"
            info += f"Footer Checksum: 0x{footer.footer_struct_checksum:08x}\n"
            info += f"Language Emoji: {footer.language_emoji.decode('utf-8')}\n"
            info += f"Type Emoji 1: {footer.type_emoji_1.decode('utf-8')}\n"
            info += f"Type Emoji 2: {footer.type_emoji_2.decode('utf-8')}\n"

            return info
        except Exception as e:
            return f"❌ Failed to read package info: {e}"


# 🕹️ ⚙️ 🏗️


# 📦🍜📄🪄
