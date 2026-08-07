"""
Credential encryption at rest.

Broker passwords and other secrets that need to be *stored* (as opposed to
read once from `.env`) are encrypted with Fernet (AES-128-CBC + HMAC) before
they touch the database, and decrypted only in-memory when a service needs
to use them.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.core.exceptions import FathirError


class CredentialEncryptionError(FathirError):
    status_code = 500
    default_message = "Failed to encrypt/decrypt stored credentials."


class CredentialCipher:
    """Thin wrapper around Fernet, keyed from `CREDENTIAL_ENCRYPTION_KEY`."""

    def __init__(self, key: str | None = None):
        resolved_key = key or get_settings().credential_encryption_key
        if not resolved_key:
            raise CredentialEncryptionError(
                "CREDENTIAL_ENCRYPTION_KEY is not set. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        try:
            self._fernet = Fernet(resolved_key.encode())
        except (ValueError, TypeError) as exc:
            raise CredentialEncryptionError(
                "CREDENTIAL_ENCRYPTION_KEY is not a valid Fernet key."
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise CredentialEncryptionError(
                "Stored credential could not be decrypted (wrong key or corrupted data)."
            ) from exc


def generate_encryption_key() -> str:
    """Generate a new Fernet key (used by scripts / first-run setup)."""
    return Fernet.generate_key().decode()
