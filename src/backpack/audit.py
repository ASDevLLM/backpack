"""
Encrypted audit logging for agent activity.

This module provides the AuditLogger class for creating an encrypted, tamper-evident
log of sensitive operations like key injection and lock file access.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional

from .crypto import encrypt_data, decrypt_data, EncryptionError, DecryptionError

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Manages an encrypted append-only audit log.
    
    Each log entry is individually encrypted and signed (via authenticated encryption in crypto.py)
    to ensure integrity and confidentiality.
    """

    def __init__(self, file_path: str = "agent_audit.log"):
        """
        Initialize an AuditLogger instance.

        Args:
            file_path: Path to the audit log file (default: "agent_audit.log")
        """
        self.file_path = file_path
        self.master_key = os.environ.get("AGENT_MASTER_KEY", "default-key")

    def log_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """
        Log an event to the encrypted audit log.

        Args:
            event_type: Identifier for the type of event (e.g., "key_access", "lock_created")
            details: Optional dictionary containing non-sensitive event details
        """
        if details is None:
            details = {}

        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "details": details,
        }

        try:
            # Serialize and encrypt the entry
            json_str = json.dumps(entry)
            encrypted_data = encrypt_data(json_str, self.master_key)
            
            # We store the encrypted dict as a single line JSON
            # encrypt_data returns {'data': '...', 'salt': '...'}
            log_line = json.dumps(encrypted_data)
            
            with open(self.file_path, "a") as f:
                f.write(log_line + "\n")
                
        except Exception as e:
            # We explicitly catch errors here to prevent audit logging failures 
            # from crashing the main application, but we log the error to system logs.
            logger.error(f"Failed to write to audit log: {e}")

    def read_logs(self) -> List[Dict[str, Any]]:
        """
        Read and decrypt all entries from the audit log.

        Returns:
            List of decrypted log entries sorted by timestamp.
        """
        if not os.path.exists(self.file_path):
            return []

        entries = []
        try:
            with open(self.file_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        encrypted_dict = json.loads(line)
                        decrypted_json = decrypt_data(encrypted_dict, self.master_key)
                        entry = json.loads(decrypted_json)
                        entries.append(entry)
                    except (json.JSONDecodeError, DecryptionError) as e:
                        logger.warning(f"Failed to decrypt audit log line {line_num}: {e}")
                        # We continue reading other lines
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading audit log: {e}")
            return []

        return entries

    def clear(self) -> None:
        """Clear the audit log file."""
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
