# Exceptions

The `backpack.exceptions` module defines custom exception classes for the Backpack system.

## Base Class

- `BackpackError`: Base exception class for all Backpack-related errors.

## Crypto Exceptions

- `CryptoError`: Base for cryptographic errors.
- `DecryptionError`: Raised when decryption fails.
- `EncryptionError`: Raised when encryption fails.
- `KeyDerivationError`: Raised when key derivation fails.

## Keychain Exceptions

- `KeychainError`: Base for keychain errors.
- `KeyNotFoundError`: Raised when a key is not found.
- `KeychainAccessError`: Raised when keychain access fails.
- `KeychainStorageError`: Raised when storing a key fails.
- `KeychainDeletionError`: Raised when deleting a key fails.

## Agent Lock Exceptions

- `AgentLockError`: Base for agent lock errors.
- `AgentLockNotFoundError`: Raised when agent.lock is missing.
- `AgentLockCorruptedError`: Raised when agent.lock is invalid.
- `AgentLockReadError`: Raised when reading agent.lock fails.
- `AgentLockWriteError`: Raised when writing agent.lock fails.

## Validation Exceptions

- `ValidationError`: Base for input validation errors.
- `InvalidPathError`: Raised when a path is invalid.
- `InvalidKeyNameError`: Raised when a key name is invalid.
- `InvalidPasswordError`: Raised when a password is invalid.

## Other Exceptions

- `ScriptExecutionError`: Raised when agent script execution fails.
