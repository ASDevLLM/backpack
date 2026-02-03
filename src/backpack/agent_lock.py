"""
Agent lock file management.

This module provides the AgentLock class for creating, reading, and updating
encrypted agent.lock files that contain credentials, personality, and memory.

Logging in this module focuses on file paths and operation outcomes only.
No decrypted contents are ever logged.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

from .audit import AuditLogger
from .crypto import encrypt_data, decrypt_data, DecryptionError, EncryptionError
from .exceptions import (
    AgentLockNotFoundError,
    AgentLockReadError,
    AgentLockWriteError,
    InvalidPathError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class AgentLock:
    """
    Manages encrypted agent.lock files containing agent configuration and state.

    The agent.lock file contains three encrypted layers:
    1. Credentials: Placeholders for required API keys
    2. Personality: System prompts and agent configuration
    3. Memory: Ephemeral agent state

    All data is encrypted using a master key (from AGENT_MASTER_KEY env var).
    """

    def __init__(self, file_path: str = "agent.lock", master_key: str = None):
        """
        Initialize an AgentLock instance.

        Args:
            file_path: Path to the agent.lock file (default: "agent.lock")
            master_key: Optional master key to use (overrides env var)
        """
        self.file_path = file_path
        self.master_key = master_key or os.environ.get("AGENT_MASTER_KEY", "default-key")
        self.audit_logger = AuditLogger()

    def create(self, credentials: Dict[str, str], personality: Dict[str, str], memory: Dict[str, Any] = None) -> None:
        """
        Create a new agent.lock file with encrypted layers.

        Args:
            credentials: Dictionary mapping credential names to placeholder values
            personality: Dictionary containing system prompts and configuration
            memory: Optional dictionary for ephemeral agent state (default: empty dict)

        Raises:
            ValidationError: If input data is invalid
            EncryptionError: If encryption fails
            AgentLockWriteError: If writing the file fails
        """
        if memory is None:
            memory = {}

        # Validate inputs
        if not isinstance(credentials, dict):
            raise ValidationError("Credentials must be a dictionary", f"Got type: {type(credentials).__name__}")

        if not isinstance(personality, dict):
            raise ValidationError("Personality must be a dictionary", f"Got type: {type(personality).__name__}")

        if not isinstance(memory, dict):
            raise ValidationError("Memory must be a dictionary", f"Got type: {type(memory).__name__}")

        try:
            data = {
                "version": "1.0",
                "layers": {
                    "credentials": encrypt_data(json.dumps(credentials), self.master_key),
                    "personality": encrypt_data(json.dumps(personality), self.master_key),
                    "memory": encrypt_data(json.dumps(memory), self.master_key),
                },
            }
        except (EncryptionError, ValidationError) as e:
            raise AgentLockWriteError(self.file_path, f"Failed to encrypt data: {str(e)}") from e

        try:
            # Ensure directory exists
            directory = os.path.dirname(self.file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info("Created agent.lock file", extra={"path": self.file_path})
            self.audit_logger.log_event("lock_created", {"path": self.file_path})
        except PermissionError as e:
            raise AgentLockWriteError(self.file_path, f"Permission denied: {str(e)}") from e
        except OSError as e:
            raise AgentLockWriteError(self.file_path, f"OS error: {str(e)}") from e
        except Exception as e:
            raise AgentLockWriteError(self.file_path, f"Unexpected error: {str(e)}") from e

    def read(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Read and decrypt the agent.lock file.

        Returns:
            A dictionary with keys 'credentials', 'personality', and 'memory',
            each containing the decrypted data. Returns None if the file doesn't
            exist or decryption fails.

        Raises:
            AgentLockReadError: If reading the file fails (I/O/permissions).
            InvalidPathError: If the path exists but is not a file.
        """
        if not os.path.exists(self.file_path):
            logger.debug("agent.lock file not found", extra={"path": self.file_path})
            return None

        if not os.path.isfile(self.file_path):
            raise InvalidPathError(self.file_path, "Path exists but is not a file")

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # Corrupted file (or wrong content) -> treat as unreadable
            logger.warning("agent.lock file is not valid JSON", extra={"path": self.file_path})
            return None
        except PermissionError as e:
            raise AgentLockReadError(self.file_path, f"Permission denied: {str(e)}") from e
        except OSError as e:
            raise AgentLockReadError(self.file_path, f"OS error: {str(e)}") from e
        except Exception as e:
            raise AgentLockReadError(self.file_path, f"Unexpected error reading file: {str(e)}") from e

        # Validate file structure (treat invalid as unreadable)
        if not isinstance(data, dict):
            logger.warning("agent.lock file has invalid structure", extra={"path": self.file_path})
            return None
        if "layers" not in data or not isinstance(data["layers"], dict):
            logger.warning("agent.lock missing 'layers' section", extra={"path": self.file_path})
            return None

        required_layers = ["credentials", "personality", "memory"]
        for layer in required_layers:
            if layer not in data["layers"]:
                logger.warning(
                    "agent.lock missing required layer",
                    extra={"path": self.file_path, "layer": layer},
                )
                return None

        try:
            result = {
                "credentials": json.loads(decrypt_data(data["layers"]["credentials"], self.master_key)),
                "personality": json.loads(decrypt_data(data["layers"]["personality"], self.master_key)),
                "memory": json.loads(decrypt_data(data["layers"]["memory"], self.master_key)),
            }
            logger.debug("Successfully read agent.lock file", extra={"path": self.file_path})
            self.audit_logger.log_event("lock_read", {"path": self.file_path})
            return result
        except DecryptionError:
            logger.warning("Failed to decrypt agent.lock file", extra={"path": self.file_path})
            return None
        except json.JSONDecodeError:
            logger.warning("Decrypted agent.lock contents are not valid JSON", extra={"path": self.file_path})
            return None
        except Exception as e:
            logger.error("Unexpected error reading agent.lock file", extra={"path": self.file_path, "error": str(e)})
            return None

    def update_memory(self, memory: Dict[str, Any]) -> None:
        """
        Update the memory layer of the agent.lock file.

        This preserves existing credentials and personality while updating
        only the ephemeral memory state.

        Args:
            memory: New memory dictionary to store

        Raises:
            AgentLockNotFoundError: If agent.lock file doesn't exist
            ValidationError: If memory is not a dictionary
            AgentLockWriteError: If writing the updated file fails
        """
        if not isinstance(memory, dict):
            raise ValidationError("Memory must be a dictionary", f"Got type: {type(memory).__name__}")

        agent_data = self.read()
        if agent_data is None:
            raise AgentLockNotFoundError(self.file_path)

        try:
            agent_data["memory"] = memory
            self.create(agent_data["credentials"], agent_data["personality"], memory)
            self.audit_logger.log_event("lock_memory_updated", {"path": self.file_path})
        except (ValidationError, EncryptionError, AgentLockWriteError):
            raise
        except Exception as e:
            raise AgentLockWriteError(self.file_path, f"Failed to update memory: {str(e)}") from e

    def get_required_keys(self) -> list:
        """
        Get a list of required credential keys from the agent.lock file.

        Returns:
            A list of credential key names (e.g., ['OPENAI_API_KEY', 'TWITTER_TOKEN'])

        Raises:
            AgentLockNotFoundError: If agent.lock file doesn't exist
            AgentLockCorruptedError: If the file is corrupted
        """
        agent_data = self.read()
        if agent_data is None:
            return []

        if "credentials" in agent_data and isinstance(agent_data["credentials"], dict):
            return list(agent_data["credentials"].keys())
        return []
