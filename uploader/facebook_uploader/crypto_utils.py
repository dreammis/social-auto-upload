"""
AES-256-GCM encryption/decryption — compatible with NestJS CryptoService.

NestJS wire format (base64-encoded):
    IV (16 bytes) + AuthTag (16 bytes) + Ciphertext (variable)

Requires ENCRYPTION_KEY env var — 64 hex chars (32 bytes).
"""

import os
import hashlib
import logging
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

IV_LENGTH = 16       # 128-bit IV (GCM recommended)
AUTH_TAG_LENGTH = 16  # 128-bit tag
KEY_LENGTH = 32       # 256-bit key


def _get_encryption_key() -> bytes:
    """Resolve the 32-byte AES key from the environment.

    Mirrors NestJS CryptoService logic:
      - If ENCRYPTION_KEY >= 64 hex chars → take first 64 hex chars → decode.
      - Otherwise SHA-256 hash the raw string to derive 32 bytes.
    """
    env_key = os.getenv("ENCRYPTION_KEY", "")
    if not env_key:
        raise RuntimeError("ENCRYPTION_KEY is not set in environment variables")

    if len(env_key) >= KEY_LENGTH * 2:
        return bytes.fromhex(env_key[: KEY_LENGTH * 2])
    else:
        return hashlib.sha256(env_key.encode()).digest()


def decrypt_session_data(payload: str) -> str:
    """Decrypt a base64 blob produced by NestJS CryptoService.encrypt().

    Args:
        payload: Base64-encoded string containing IV + AuthTag + Ciphertext.

    Returns:
        The original plaintext (UTF-8 string, typically JSON cookies).

    Raises:
        RuntimeError: If ENCRYPTION_KEY is missing.
        Exception: On decryption failure (bad key, tampered data, etc.).
    """
    key = _get_encryption_key()
    raw = b64decode(payload)

    iv = raw[:IV_LENGTH]
    auth_tag = raw[IV_LENGTH : IV_LENGTH + AUTH_TAG_LENGTH]
    ciphertext = raw[IV_LENGTH + AUTH_TAG_LENGTH :]

    # cryptography's AESGCM expects ciphertext || tag concatenated
    aesgcm = AESGCM(key)
    plaintext_bytes = aesgcm.decrypt(iv, ciphertext + auth_tag, None)

    return plaintext_bytes.decode("utf-8")


def encrypt_session_data(plaintext: str) -> str:
    """Encrypt plaintext to the same format NestJS CryptoService.decrypt() expects.

    Provided for round-trip testing — production encryption is done by NestJS.

    Args:
        plaintext: UTF-8 string to encrypt.

    Returns:
        Base64-encoded blob: IV(16) + AuthTag(16) + Ciphertext.
    """
    key = _get_encryption_key()
    iv = os.urandom(IV_LENGTH)

    aesgcm = AESGCM(key)
    # AESGCM.encrypt returns ciphertext || tag
    ct_with_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)

    # Split: ciphertext is everything except last 16 bytes, tag is last 16
    ciphertext = ct_with_tag[:-AUTH_TAG_LENGTH]
    auth_tag = ct_with_tag[-AUTH_TAG_LENGTH:]

    # Pack in NestJS order: IV + AuthTag + Ciphertext
    packed = iv + auth_tag + ciphertext
    return b64encode(packed).decode("ascii")
