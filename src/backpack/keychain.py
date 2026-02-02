"""
OS keychain integration for secure credential storage.

This module provides functions for storing, retrieving, and managing
API keys and other credentials using the platform's native keyring service.

Logging in this module NEVER records secret key values. Only key names and
high-level operation results are logged.
"""

import json
import logging
from typing import Dict, Optional

import keyring
import keyring.errors

from .audit import AuditLogger
from .exceptions import (
    KeychainAccessError,
    KeychainStorageError,
    KeychainDeletionError,
    InvalidKeyNameError,
    ValidationError,
)

SERVICE_NAME = "backpack-agent"
logger = logging.getLogger(__name__)
audit_logger = AuditLogger()


def _validate_key_name(key_name: str) -> None:
    """
    Validate a key name.

    Args:
        key_name: The key name to validate

    Raises:
        InvalidKeyNameError: If the key name is invalid
    """
    if not key_name:
        raise InvalidKeyNameError("", "Key name cannot be empty")

    if not isinstance(key_name, str):
        raise InvalidKeyNameError(str(key_name), f"Key name must be a string, got {type(key_name).__name__}")

    # Key names should not start with underscore (reserved for internal use)
    # except for the registry key
    if key_name.startswith("_") and key_name != "_registry":
        raise InvalidKeyNameError(key_name, "Key names starting with '_' are reserved for internal use")


def store_key(key_name: str, key_value: str) -> None:
    """
    Store a key-value pair in the OS keychain.

    Args:
        key_name: The name/identifier of the key
        key_value: The secret value to store

    Raises:
        InvalidKeyNameError: If key_name is invalid
        KeychainStorageError: If storing the key fails
    """
    _validate_key_name(key_name)

    if key_value is None:
        raise ValidationError("Key value cannot be None", "Provide a valid string value to store")

    if not isinstance(key_value, str):
        raise ValidationError("Key value must be a string", f"Got type: {type(key_value).__name__}")

    try:
        keyring.set_password(SERVICE_NAME, key_name, key_value)
        logger.info("Stored key in keychain", extra={"service": SERVICE_NAME, "key_name": key_name})
    except keyring.errors.KeyringError as e:
        raise KeychainStorageError(key_name, f"Keyring error: {str(e)}") from e
    except Exception as e:
        raise KeychainStorageError(key_name, f"Unexpected error: {str(e)}") from e


def get_key(key_name: str) -> Optional[str]:
    """
    Retrieve a key value from the OS keychain.

    Args:
        key_name: The name/identifier of the key to retrieve

    Returns:
        The stored key value, or None if not found

    Raises:
        InvalidKeyNameError: If key_name is invalid
        KeychainAccessError: If accessing the keychain fails
    """
    _validate_key_name(key_name)

    try:
        value = keyring.get_password(SERVICE_NAME, key_name)
        logger.debug(
            "Retrieved key from keychain",
            extra={"service": SERVICE_NAME, "key_name": key_name, "found": bool(value)},
        )
        return value
    except keyring.errors.KeyringError as e:
        raise KeychainAccessError(f"Failed to retrieve key '{key_name}' from keychain", str(e)) from e
    except Exception as e:
        raise KeychainAccessError(f"Unexpected error retrieving key '{key_name}'", str(e)) from e


def list_keys() -> Dict[str, bool]:
    """
    List all keys registered in the keychain.

    Note: The OS keyring doesn't provide native list functionality,
    so we maintain a registry of keys.

    Returns:
        A dictionary mapping key names to True (indicating they exist)

    Raises:
        KeychainAccessError: If accessing the keychain fails
    """
    try:
        registry = get_key("_registry")
        if registry:
            try:
                return json.loads(registry)
            except json.JSONDecodeError:
                return {}
        return {}
    except KeychainAccessError:
        return {}


def register_key(key_name: str) -> None:
    """
    Register a key name in the keychain registry.

    This is used to track which keys exist, since the OS keyring
    doesn't provide native list functionality.

    Args:
        key_name: The name of the key to register

    Raises:
        InvalidKeyNameError: If key_name is invalid
        KeychainStorageError: If storing the registry fails
    """
    _validate_key_name(key_name)

    try:
        registry = list_keys()
        registry[key_name] = True
        keyring.set_password(SERVICE_NAME, "_registry", json.dumps(registry))
    except (KeychainAccessError, KeychainStorageError):
        # Registry failures are non-critical (key itself is already stored)
        pass
    except Exception as e:
        raise KeychainStorageError("_registry", f"Failed to update registry: {str(e)}") from e


def delete_key(key_name: str) -> None:
    """
    Delete a key from the keychain and registry.

    Args:
        key_name: The name of the key to delete

    Raises:
        InvalidKeyNameError: If key_name is invalid
        KeychainDeletionError: If deletion fails
    """
    _validate_key_name(key_name)

    # Deletion is intentionally idempotent:
    # - If the secret doesn't exist in the keychain, we still remove it from the registry.
    # - Tests expect delete_key() to not raise for missing keys.
    try:
        keyring.delete_password(SERVICE_NAME, key_name)
        audit_logger.log_event("delete_key", {"service": SERVICE_NAME, "key_name": key_name})
    except keyring.errors.PasswordDeleteError:
        pass
    except keyring.errors.KeyringError as e:
        raise KeychainDeletionError(key_name, f"Keyring error: {str(e)}") from e
    except Exception as e:
        raise KeychainDeletionError(key_name, f"Unexpected error: {str(e)}") from e

    # Update registry
    try:
        registry = list_keys()
        registry.pop(key_name, None)
        keyring.set_password(SERVICE_NAME, "_registry", json.dumps(registry))
    except Exception:
        pass

