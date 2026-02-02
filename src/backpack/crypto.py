"""
Cryptographic utilities for encrypting and decrypting agent data.

This module provides functions for deriving encryption keys from passwords
using PBKDF2 and encrypting/decrypting data using Fernet symmetric encryption.

Logging in this module is intentionally minimal and NEVER includes any
secret material such as passwords, salts, or ciphertext. Only operation
types and high-level status are logged.
"""

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging
import os

from .exceptions import (
    DecryptionError,
    EncryptionError,
    KeyDerivationError,
    InvalidPasswordError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def derive_key(password: str, salt: bytes = None) -> bytes:
    """
    Derive an encryption key from a password using PBKDF2.

    Args:
        password: The password to derive the key from
        salt: Optional salt bytes. If None, a random salt is generated.

    Returns:
        A tuple of (key, salt) where key is a base64-encoded Fernet key
        and salt is the salt bytes used (or generated).

    Raises:
        InvalidPasswordError: If password is empty or None
        KeyDerivationError: If key derivation fails
    """
    if not password:
        raise InvalidPasswordError("Password cannot be empty or None")

    if not isinstance(password, str):
        raise ValidationError(
            "Password must be a string",
            f"Got type: {type(password).__name__}",
        )

    try:
        if salt is None:
            salt = os.urandom(16)

        if not isinstance(salt, bytes) or len(salt) < 8:
            raise ValidationError(
                "Invalid salt",
                "Salt must be at least 8 bytes",
            )

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        logger.debug("Derived encryption key using PBKDF2", extra={"salt_len": len(salt)})
        return key, salt
    except Exception as e:
        if isinstance(e, (InvalidPasswordError, ValidationError)):
            raise
        raise KeyDerivationError("Failed to derive encryption key", str(e)) from e


def encrypt_data(data: str, password: str) -> dict:
    """
    Encrypt a string using PBKDF2 key derivation and Fernet encryption.

    Args:
        data: The plaintext string to encrypt
        password: The password to use for key derivation

    Returns:
        A dictionary containing:
        - 'data': Base64-encoded encrypted data
        - 'salt': Base64-encoded salt used for key derivation

    Raises:
        ValidationError: If data is not a string or is None
        EncryptionError: If encryption fails
    """
    if data is None:
        raise ValidationError("Data cannot be None", "Provide a valid string to encrypt")

    if not isinstance(data, str):
        raise ValidationError("Data must be a string", f"Got type: {type(data).__name__}")

    try:
        key, salt = derive_key(password)
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        logger.debug("Encrypted data string", extra={"cipher_len": len(encrypted)})
        return {
            "data": base64.b64encode(encrypted).decode(),
            "salt": base64.b64encode(salt).decode(),
        }
    except (InvalidPasswordError, KeyDerivationError, ValidationError):
        raise
    except Exception as e:
        raise EncryptionError("Failed to encrypt data", str(e)) from e


def decrypt_data(encrypted_dict: dict, password: str) -> str:
    """
    Decrypt data that was encrypted with encrypt_data().

    Args:
        encrypted_dict: A dictionary containing:
            - 'data': Base64-encoded encrypted data
            - 'salt': Base64-encoded salt used for key derivation
        password: The password used for encryption

    Returns:
        The decrypted plaintext string

    Raises:
        ValidationError: If encrypted_dict is invalid or missing required keys
        DecryptionError: If decryption fails (wrong password, corrupted data, etc.)
    """
    if not isinstance(encrypted_dict, dict):
        raise ValidationError(
            "Encrypted data must be a dictionary",
            f"Got type: {type(encrypted_dict).__name__}",
        )

    if "data" not in encrypted_dict or "salt" not in encrypted_dict:
        raise ValidationError(
            "Encrypted dictionary missing required keys",
            "Expected keys: 'data' and 'salt'",
        )

    try:
        salt = base64.b64decode(encrypted_dict["salt"])
        key, _ = derive_key(password, salt)
        f = Fernet(key)
        encrypted_data = base64.b64decode(encrypted_dict["data"])
        decrypted = f.decrypt(encrypted_data)
        return decrypted.decode("utf-8")
    except InvalidToken:
        raise DecryptionError(
            "Decryption failed - invalid token",
            "The password may be incorrect or the data may be corrupted",
        )
    except (UnicodeDecodeError, ValueError) as e:
        raise DecryptionError("Decryption failed - invalid data format", str(e))
    except (InvalidPasswordError, KeyDerivationError, ValidationError):
        raise
    except Exception as e:
        raise DecryptionError("Decryption failed", str(e)) from e

