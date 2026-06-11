import base64
import hashlib

from cryptography.fernet import Fernet

from .settings import get_settings

settings = get_settings()


def _fernet_from_secret(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


_fernet = _fernet_from_secret(settings.pii_encryption_key)


def encrypt_pii(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_pii(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
