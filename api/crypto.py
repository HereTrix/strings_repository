# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from cryptography.fernet import Fernet
import base64
import hashlib

from django.conf import settings

# Supported hash algorithms for field-encryption key derivation.
# Operators can switch via FIELD_ENCRYPTION_KEY_HASH; re-encrypting all
# stored fields is required after changing this value.
_SUPPORTED_KEY_HASH_ALGORITHMS = {
    'sha256': hashlib.sha256,
    'sha384': hashlib.sha384,
    'sha512': hashlib.sha512,
}


def _fernet():
    algorithm = getattr(settings, 'FIELD_ENCRYPTION_KEY_HASH', 'sha256')
    hash_fn = _SUPPORTED_KEY_HASH_ALGORITHMS.get(algorithm)
    if hash_fn is None:
        raise ValueError(
            f"Unsupported FIELD_ENCRYPTION_KEY_HASH '{algorithm}'. "
            f"Choose from: {list(_SUPPORTED_KEY_HASH_ALGORITHMS)}"
        )
    # Fernet requires a 32-byte key; take the first 32 bytes of the digest.
    key = hash_fn(settings.SECRET_KEY.encode()).digest()[:32]
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value: str) -> bytes:
    return _fernet().encrypt(value.encode())


def decrypt(value: bytes) -> str:
    return _fernet().decrypt(bytes(value)).decode()
