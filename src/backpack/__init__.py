"""
Backpack Agent Container System.

This package provides the CLI and primitives for managing encrypted agent
containers (`agent.lock`), secure key storage, and just-in-time injection.
"""

__version__ = "0.1.2"

# Export exceptions for easy importing
from .exceptions import (  # noqa: F401
    BackpackError,
    CryptoError,
    DecryptionError,
    EncryptionError,
    KeyDerivationError,
    KeychainError,
    KeyNotFoundError,
    KeychainAccessError,
    KeychainStorageError,
    KeychainDeletionError,
    AgentLockError,
    AgentLockNotFoundError,
    AgentLockCorruptedError,
    AgentLockReadError,
    AgentLockWriteError,
    ValidationError,
    InvalidPathError,
    InvalidKeyNameError,
    InvalidPasswordError,
    ScriptExecutionError,
)

__all__ = [
    "BackpackError",
    "CryptoError",
    "DecryptionError",
    "EncryptionError",
    "KeyDerivationError",
    "KeychainError",
    "KeyNotFoundError",
    "KeychainAccessError",
    "KeychainStorageError",
    "KeychainDeletionError",
    "AgentLockError",
    "AgentLockNotFoundError",
    "AgentLockCorruptedError",
    "AgentLockReadError",
    "AgentLockWriteError",
    "ValidationError",
    "InvalidPathError",
    "InvalidKeyNameError",
    "InvalidPasswordError",
    "ScriptExecutionError",
]

