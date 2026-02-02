"""
Pytest configuration and shared fixtures for Backpack tests.
"""

import os
import sys
import tempfile
import shutil
import pytest

# Add src directory to Python path so tests can import backpack without
# installation. This allows tests to run without needing: pip install -e .
src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_agent_lock_path(temp_dir):
    """Return a path to a test agent.lock file in a temp directory."""
    return os.path.join(temp_dir, "agent.lock")


@pytest.fixture
def test_master_key():
    """Return a test master key for encryption."""
    return "test-master-key-12345"


@pytest.fixture
def sample_credentials():
    """Return sample credentials dictionary."""
    return {
        "OPENAI_API_KEY": "placeholder_openai_api_key",
        "TWITTER_TOKEN": "placeholder_twitter_token"
    }


@pytest.fixture
def sample_personality():
    """Return sample personality dictionary."""
    return {
        "system_prompt": "You are a helpful AI assistant.",
        "tone": "professional"
    }


@pytest.fixture
def sample_memory():
    """Return sample memory dictionary."""
    return {
        "user_id": "test_user_123",
        "session_count": 1,
        "last_run": "2024-01-15 10:30:00"
    }


@pytest.fixture
def mock_keyring(monkeypatch):
    """Mock keyring for testing without OS keychain."""
    storage = {}
    
    def mock_set_password(service, username, password):
        storage[(service, username)] = password
    
    def mock_get_password(service, username):
        return storage.get((service, username))
    
    def mock_delete_password(service, username):
        if (service, username) in storage:
            del storage[(service, username)]
    
    monkeypatch.setattr("keyring.set_password", mock_set_password)
    monkeypatch.setattr("keyring.get_password", mock_get_password)
    monkeypatch.setattr("keyring.delete_password", mock_delete_password)
    
    return storage


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing."""
    # Save original
    original_master_key = os.environ.get("AGENT_MASTER_KEY")
    
    # Clean up
    if "AGENT_MASTER_KEY" in os.environ:
        monkeypatch.delenv("AGENT_MASTER_KEY")
    
    yield
    
    # Restore original
    if original_master_key:
        monkeypatch.setenv("AGENT_MASTER_KEY", original_master_key)
