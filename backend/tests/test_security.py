import pytest
from cryptography.fernet import Fernet

from app.core.security import CredentialCipher, CredentialEncryptionError, generate_encryption_key


def test_generate_encryption_key_produces_a_valid_fernet_key():
    key = generate_encryption_key()
    Fernet(key.encode())  # raises if invalid — the assertion is that this doesn't raise


def test_encrypt_then_decrypt_round_trips():
    key = generate_encryption_key()
    cipher = CredentialCipher(key=key)
    ciphertext = cipher.encrypt("super-secret-password")
    assert ciphertext != "super-secret-password"
    assert cipher.decrypt(ciphertext) == "super-secret-password"


def test_missing_key_raises_credential_encryption_error(monkeypatch):
    from app.config import get_settings

    # get_settings() is a process-wide lru_cache singleton — use monkeypatch
    # (not a direct assignment) so the original value is restored after this
    # test, rather than leaking an empty key into every test that follows.
    monkeypatch.setattr(get_settings(), "credential_encryption_key", "")
    with pytest.raises(CredentialEncryptionError):
        CredentialCipher()


def test_malformed_key_raises_credential_encryption_error():
    with pytest.raises(CredentialEncryptionError):
        CredentialCipher(key="not-a-valid-fernet-key")


def test_decrypting_with_wrong_key_raises_credential_encryption_error():
    encrypted_with = CredentialCipher(key=generate_encryption_key())
    ciphertext = encrypted_with.encrypt("hunter2")

    decrypt_with = CredentialCipher(key=generate_encryption_key())
    with pytest.raises(CredentialEncryptionError):
        decrypt_with.decrypt(ciphertext)


def test_decrypting_corrupted_ciphertext_raises_credential_encryption_error():
    cipher = CredentialCipher(key=generate_encryption_key())
    with pytest.raises(CredentialEncryptionError):
        cipher.decrypt("this-is-not-valid-fernet-ciphertext")
