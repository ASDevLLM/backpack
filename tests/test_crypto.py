"""
Tests for crypto module - encryption and decryption functionality.
"""

import base64

import pytest

from backpack.crypto import decrypt_data, derive_key, encrypt_data
from backpack.exceptions import (
    DecryptionError,
    InvalidPasswordError,
    ValidationError,
)


class TestDeriveKey:
    """Tests for key derivation function."""
    
    def test_derive_key_with_salt(self):
        """Test key derivation with provided salt."""
        password = "test-password-123"
        salt = b"test-salt-123456"
        key, returned_salt = derive_key(password, salt)
        
        assert key is not None
        assert len(key) == 44  # Base64-encoded 32-byte key
        assert returned_salt == salt
        assert isinstance(key, bytes)
    
    def test_derive_key_without_salt(self):
        """Test key derivation with auto-generated salt."""
        password = "test-password-123"
        key, salt = derive_key(password)
        
        assert key is not None
        assert len(key) == 44  # Base64-encoded 32-byte key
        assert salt is not None
        assert len(salt) == 16
        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)
    
    def test_derive_key_deterministic_with_salt(self):
        """Test that same password and salt produce same key."""
        password = "test-password"
        salt = b"fixed-salt-1234"
        
        key1, _ = derive_key(password, salt)
        key2, _ = derive_key(password, salt)
        
        assert key1 == key2
    
    def test_derive_key_different_salts(self):
        """Test that different salts produce different keys."""
        password = "test-password"
        salt1 = b"salt-one-123456"
        salt2 = b"salt-two-123456"
        
        key1, _ = derive_key(password, salt1)
        key2, _ = derive_key(password, salt2)
        
        assert key1 != key2


class TestEncryptData:
    """Tests for data encryption."""
    
    def test_encrypt_data_basic(self):
        """Test basic encryption of data."""
        data = "test data to encrypt"
        password = "test-password"
        
        result = encrypt_data(data, password)
        
        assert "data" in result
        assert "salt" in result
        assert result["data"] != data
        assert isinstance(result["data"], str)
        assert isinstance(result["salt"], str)
    
    def test_encrypt_data_empty_string(self):
        """Test encryption of empty string."""
        data = ""
        password = "test-password"
        
        result = encrypt_data(data, password)
        
        assert "data" in result
        assert "salt" in result
        assert result["data"] != ""
    
    def test_encrypt_data_long_string(self):
        """Test encryption of long string."""
        data = "x" * 1000
        password = "test-password"
        
        result = encrypt_data(data, password)
        
        assert "data" in result
        assert len(result["data"]) > 0
    
    def test_encrypt_data_special_characters(self):
        """Test encryption with special characters."""
        data = "test!@#$%^&*()_+-=[]{}|;':\",./<>?"
        password = "test-password"
        
        result = encrypt_data(data, password)
        
        assert "data" in result
        assert result["data"] != data
    
    def test_encrypt_data_unicode(self):
        """Test encryption with unicode characters."""
        data = "测试数据 🚀 émoji"
        password = "test-password"
        
        result = encrypt_data(data, password)
        
        assert "data" in result
        assert result["data"] != data
    
    def test_encrypt_data_different_passwords(self):
        """Test that different passwords produce different encrypted data."""
        data = "same data"
        password1 = "password1"
        password2 = "password2"
        
        result1 = encrypt_data(data, password1)
        result2 = encrypt_data(data, password2)
        
        assert result1["data"] != result2["data"]


class TestDecryptData:
    """Tests for data decryption."""
    
    def test_decrypt_data_basic(self):
        """Test basic decryption of data."""
        original_data = "test data to encrypt"
        password = "test-password"
        
        encrypted = encrypt_data(original_data, password)
        decrypted = decrypt_data(encrypted, password)
        
        assert decrypted == original_data
    
    def test_decrypt_data_empty_string(self):
        """Test decryption of empty string."""
        original_data = ""
        password = "test-password"
        
        encrypted = encrypt_data(original_data, password)
        decrypted = decrypt_data(encrypted, password)
        
        assert decrypted == original_data
    
    def test_decrypt_data_long_string(self):
        """Test decryption of long string."""
        original_data = "x" * 1000
        password = "test-password"
        
        encrypted = encrypt_data(original_data, password)
        decrypted = decrypt_data(encrypted, password)
        
        assert decrypted == original_data
    
    def test_decrypt_data_special_characters(self):
        """Test decryption with special characters."""
        original_data = "test!@#$%^&*()_+-=[]{}|;':\",./<>?"
        password = "test-password"
        
        encrypted = encrypt_data(original_data, password)
        decrypted = decrypt_data(encrypted, password)
        
        assert decrypted == original_data
    
    def test_decrypt_data_unicode(self):
        """Test decryption with unicode characters."""
        original_data = "测试数据 🚀 émoji"
        password = "test-password"
        
        encrypted = encrypt_data(original_data, password)
        decrypted = decrypt_data(encrypted, password)
        
        assert decrypted == original_data
    
    def test_decrypt_data_wrong_password(self):
        """Test that wrong password fails to decrypt."""
        original_data = "test data"
        correct_password = "correct-password"
        wrong_password = "wrong-password"
        
        encrypted = encrypt_data(original_data, correct_password)
        
        with pytest.raises(DecryptionError):
            decrypt_data(encrypted, wrong_password)
    
    def test_decrypt_data_corrupted_data(self):
        """Test that corrupted encrypted data fails to decrypt."""
        password = "test-password"

        # Create corrupted encrypted data
        corrupted = {
            "data": "invalid-base64-data!!!",
            "salt": base64.b64encode(b"test-salt").decode(),
        }

        with pytest.raises(DecryptionError):
            decrypt_data(corrupted, password)
    
    def test_decrypt_data_corrupted_salt(self):
        """Test that corrupted salt fails to decrypt."""
        original_data = "test data"
        password = "test-password"
        encrypted = encrypt_data(original_data, password)
        
        # Corrupt the salt
        encrypted["salt"] = "invalid-salt!!!"
        
        with pytest.raises((DecryptionError, ValidationError)):
            decrypt_data(encrypted, password)
    
    def test_encrypt_decrypt_round_trip(self):
        """Test multiple encrypt/decrypt round trips."""
        test_cases = [
            "simple",
            "with spaces",
            "with\nnewlines",
            "with\ttabs",
            "测试",
            "🚀",
            "a" * 1000
        ]
        
        password = "test-password"
        
        for original_data in test_cases:
            encrypted = encrypt_data(original_data, password)
            decrypted = decrypt_data(encrypted, password)
            assert decrypted == original_data, f"Failed for: {original_data[:50]}"


class TestCryptoValidation:
    """Tests for input validation in crypto functions."""
    
    def test_derive_key_empty_password(self):
        """Test that empty password raises InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            derive_key("")
    
    def test_derive_key_none_password(self):
        """Test that None password raises InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            derive_key(None)
    
    def test_derive_key_invalid_type(self):
        """Test that non-string password raises ValidationError."""
        with pytest.raises(ValidationError):
            derive_key(123)  # type: ignore

    def test_encrypt_data_none(self):
        """Test that None data raises ValidationError."""
        with pytest.raises(ValidationError):
            encrypt_data(None, "password")  # type: ignore

    def test_encrypt_data_invalid_type(self):
        """Test that non-string data raises ValidationError."""
        with pytest.raises(ValidationError):
            encrypt_data(123, "password")  # type: ignore

    def test_decrypt_data_invalid_type(self):
        """Test that non-dict encrypted data raises ValidationError."""
        with pytest.raises(ValidationError):
            decrypt_data("not a dict", "password")  # type: ignore
    
    def test_decrypt_data_missing_keys(self):
        """Test that missing keys in encrypted dict raises ValidationError."""
        with pytest.raises(ValidationError):
            decrypt_data({}, "password")
        
        with pytest.raises(ValidationError):
            decrypt_data({"data": "test"}, "password")
        
        with pytest.raises(ValidationError):
            decrypt_data({"salt": "test"}, "password")
