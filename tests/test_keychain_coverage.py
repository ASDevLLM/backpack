
import pytest
import json
from unittest.mock import patch, MagicMock
import keyring
import keyring.errors
from backpack.keychain import (
    store_key,
    get_key,
    list_keys,
    register_key,
    delete_key,
    _validate_key_name
)
from backpack.exceptions import (
    InvalidKeyNameError,
    ValidationError,
    KeychainStorageError,
    KeychainAccessError,
    KeychainDeletionError
)

class TestKeychainCoverage:
    
    def test_validate_key_name_empty(self):
        with pytest.raises(InvalidKeyNameError, match="Key name cannot be empty"):
            _validate_key_name("")

    def test_validate_key_name_not_string(self):
        with pytest.raises(InvalidKeyNameError, match="Key name must be a string"):
            _validate_key_name(123)

    def test_validate_key_name_reserved(self):
        with pytest.raises(InvalidKeyNameError, match="reserved for internal use"):
            _validate_key_name("_reserved")

    def test_store_key_none_value(self):
        with pytest.raises(ValidationError, match="Key value cannot be None"):
            store_key("test_key", None)

    def test_store_key_invalid_type_value(self):
        with pytest.raises(ValidationError, match="Key value must be a string"):
            store_key("test_key", 123)

    @patch('keyring.set_password')
    def test_store_key_keyring_error(self, mock_set_password):
        mock_set_password.side_effect = keyring.errors.KeyringError("Keyring failed")
        with pytest.raises(KeychainStorageError, match="Keyring error"):
            store_key("test_key", "value")

    @patch('keyring.set_password')
    def test_store_key_unexpected_error(self, mock_set_password):
        mock_set_password.side_effect = Exception("Unexpected")
        with pytest.raises(KeychainStorageError, match="Unexpected error"):
            store_key("test_key", "value")

    @patch('keyring.get_password')
    def test_get_key_keyring_error(self, mock_get_password):
        mock_get_password.side_effect = keyring.errors.KeyringError("Keyring failed")
        with pytest.raises(KeychainAccessError, match="Failed to retrieve key"):
            get_key("test_key")

    @patch('keyring.get_password')
    def test_get_key_unexpected_error(self, mock_get_password):
        mock_get_password.side_effect = Exception("Unexpected")
        with pytest.raises(KeychainAccessError, match="Unexpected error retrieving key"):
            get_key("test_key")

    @patch('backpack.keychain.get_key')
    def test_list_keys_json_decode_error(self, mock_get_key):
        mock_get_key.return_value = "not json"
        assert list_keys() == {}

    @patch('backpack.keychain.get_key')
    def test_list_keys_access_error(self, mock_get_key):
        mock_get_key.side_effect = KeychainAccessError("Access failed")
        assert list_keys() == {}

    @patch('backpack.keychain.list_keys')
    @patch('keyring.set_password')
    def test_register_key_access_error(self, mock_set_password, mock_list_keys):
        # We simulate an error during list_keys which is caught in register_key
        mock_list_keys.side_effect = KeychainAccessError("Access failed")
        # Should not raise exception
        register_key("test_key")

    @patch('backpack.keychain.list_keys')
    @patch('keyring.set_password')
    def test_register_key_storage_error_in_list(self, mock_set_password, mock_list_keys):
        # Assuming list_keys raises KeychainStorageError (unlikely but possible if mocked)
        # But wait, register_key catches KeychainStorageError too.
        # Let's mock set_password to raise KeychainStorageError (if we could make set_password raise it directly)
        # But set_password raises KeyringError usually.
        # The code catches (KeychainAccessError, KeychainStorageError)
        # So let's make list_keys raise KeychainStorageError
        mock_list_keys.side_effect = KeychainStorageError("key", "Storage failed")
        register_key("test_key")

    @patch('backpack.keychain.list_keys')
    def test_register_key_unexpected_error(self, mock_list_keys):
        mock_list_keys.side_effect = Exception("Unexpected")
        with pytest.raises(KeychainStorageError, match="Failed to update registry"):
            register_key("test_key")

    @patch('keyring.delete_password')
    def test_delete_key_password_delete_error(self, mock_delete_password):
        mock_delete_password.side_effect = keyring.errors.PasswordDeleteError("Delete failed")
        # Should pass silently
        delete_key("test_key")

    @patch('keyring.delete_password')
    def test_delete_key_keyring_error(self, mock_delete_password):
        mock_delete_password.side_effect = keyring.errors.KeyringError("Keyring failed")
        with pytest.raises(KeychainDeletionError, match="Keyring error"):
            delete_key("test_key")

    @patch('keyring.delete_password')
    def test_delete_key_unexpected_error(self, mock_delete_password):
        mock_delete_password.side_effect = Exception("Unexpected")
        with pytest.raises(KeychainDeletionError, match="Unexpected error"):
            delete_key("test_key")

    @patch('keyring.delete_password')
    @patch('backpack.keychain.list_keys')
    def test_delete_key_registry_update_error(self, mock_list_keys, mock_delete_password):
        mock_list_keys.side_effect = Exception("Registry update failed")
        # Should pass silently
        delete_key("test_key")
