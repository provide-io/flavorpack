#
# flavor/exceptions.py
#
class BuildError(Exception):
    pass


class PackagingError(BuildError):
    """Specific error during the packaging orchestration phase."""

    pass


class SigningError(BuildError):
    pass


class VerificationError(Exception):
    pass


class InvalidFooterError(VerificationError):
    pass


class SignatureVerificationError(VerificationError):
    pass


# ⚠️ 🆘 🚨


# 📦🍜⚠️🪄
