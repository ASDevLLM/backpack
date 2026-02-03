"""
Tests for CLI module - command-line interface functionality.
"""

import os

from click.testing import CliRunner

from backpack.agent_lock import AgentLock
from backpack.cli import cli
from backpack.keychain import register_key, store_key


class TestCLIInit:
    """Tests for init command."""
    
    def test_init_basic(self, mock_keyring, temp_dir, clean_env):
        """Test basic agent initialization."""
        runner = CliRunner()
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            result = runner.invoke(cli, [
                'init',
                '--credentials', 'OPENAI_API_KEY,TWITTER_TOKEN',
                '--personality', 'Test agent personality'
            ])
            
            assert result.exit_code == 0
            assert os.path.exists('agent.lock')
            
            # Verify agent.lock contents
            agent_lock = AgentLock()
            agent_lock.master_key = "default-key"
            data = agent_lock.read()

            assert data is not None
            assert "OPENAI_API_KEY" in data["credentials"]
            assert "TWITTER_TOKEN" in data["credentials"]
            assert data["personality"]["system_prompt"] == "Test agent personality"
        finally:
            os.chdir(original_dir)
    
    def test_init_no_credentials(self, mock_keyring, temp_dir, clean_env):
        """Test initialization with only personality."""
        runner = CliRunner()
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            result = runner.invoke(cli, [
                'init',
                '--personality', 'Personality only'
            ])
            
            assert result.exit_code == 0
            assert os.path.exists('agent.lock')
            
            agent_lock = AgentLock()
            agent_lock.master_key = "default-key"
            data = agent_lock.read()
            
            assert data["credentials"] == {}
            assert data["personality"]["system_prompt"] == "Personality only"
        finally:
            os.chdir(original_dir)
    
    def test_init_no_personality(self, mock_keyring, temp_dir, clean_env):
        """Test initialization with only credentials."""
        runner = CliRunner()
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            result = runner.invoke(cli, [
                'init',
                '--credentials', 'OPENAI_API_KEY'
            ])
            
            assert result.exit_code == 0
            
            agent_lock = AgentLock()
            agent_lock.master_key = "default-key"
            data = agent_lock.read()
            
            assert "OPENAI_API_KEY" in data["credentials"]
            assert data["personality"]["system_prompt"] == "You are a helpful AI assistant."
        finally:
            os.chdir(original_dir)


class TestCLIRun:
    """Tests for run command."""
    
    def test_run_no_agent_lock(self, temp_dir):
        """Test running agent without agent.lock file."""
        runner = CliRunner()
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            result = runner.invoke(cli, ['run', 'example_agent.py'])
            
            assert result.exit_code != 0
            assert "No agent.lock found" in result.output
        finally:
            os.chdir(original_dir)
    
    def test_run_with_missing_keys(self, mock_keyring, temp_dir):
        """Test running agent with missing keys in keychain."""
        runner = CliRunner()
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            # Create agent.lock
            runner.invoke(cli, [
                'init',
                '--credentials', 'MISSING_KEY',
                '--personality', 'Test'
            ])
            
            # Try to run (should prompt for missing key)
            result = runner.invoke(cli, ['run', 'example_agent.py'], input='n\n')
            
            # Should indicate key not found
            assert "not found in vault" in result.output or "Access denied" in result.output
        finally:
            os.chdir(original_dir)
    
    def test_run_with_existing_keys(self, mock_keyring, temp_dir):
        """Test running agent with keys in keychain."""
        runner = CliRunner()
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            # Store key
            store_key("TEST_KEY", "test-value")
            register_key("TEST_KEY")
            
            # Create agent.lock
            runner.invoke(cli, [
                'init',
                '--credentials', 'TEST_KEY',
                '--personality', 'Test agent'
            ])
            
            # Create a simple test agent script
            test_script = os.path.join(temp_dir, "test_agent.py")
            with open(test_script, 'w') as f:
                f.write("""
import os
import sys
sys.exit(0 if os.environ.get('TEST_KEY') == 'test-value' else 1)
""")
            
            # Run agent (approve access)
            result = runner.invoke(cli, ['run', 'test_agent.py'], input='y\n')
            
            # Should succeed (exit code 0 from script)
            assert result.exit_code == 0 or "Running" in result.output
        finally:
            os.chdir(original_dir)


class TestCLIKey:
    """Tests for key management commands."""
    
    def test_key_add(self, mock_keyring):
        """Test adding a key to vault."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['key', 'add', 'TEST_KEY'], input='test-value\n')
        
        assert result.exit_code == 0
        assert "Added TEST_KEY to vault" in result.output
    
    def test_key_list_empty(self, mock_keyring):
        """Test listing keys when vault is empty."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['key', 'list'])
        
        assert result.exit_code == 0
        assert "No keys in vault" in result.output
    
    def test_key_list_with_keys(self, mock_keyring):
        """Test listing keys when vault has keys."""
        runner = CliRunner()
        
        # Add some keys
        store_key("KEY1", "value1")
        register_key("KEY1")
        store_key("KEY2", "value2")
        register_key("KEY2")
        
        result = runner.invoke(cli, ['key', 'list'])
        
        assert result.exit_code == 0
        assert "KEY1" in result.output
        assert "KEY2" in result.output
    
    def test_key_remove_existing(self, mock_keyring):
        """Test removing an existing key."""
        runner = CliRunner()
        
        # Add key first
        store_key("TO_REMOVE", "value")
        register_key("TO_REMOVE")
        
        result = runner.invoke(cli, ['key', 'remove', 'TO_REMOVE'])
        
        assert result.exit_code == 0
        assert "Removed TO_REMOVE" in result.output
    
    def test_key_remove_nonexistent(self, mock_keyring):
        """Test removing a non-existent key."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['key', 'remove', 'NONEXISTENT'])
        
        # Should not error, just report removal
        assert result.exit_code == 0


class TestCLIHelp:
    """Tests for CLI help and general functionality."""
    
    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Backpack Agent Container CLI" in result.output
    
    def test_init_help(self):
        """Test init command help."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['init', '--help'])
        
        assert result.exit_code == 0
        assert "Initialize a new agent.lock file" in result.output
    
    def test_run_help(self):
        """Test run command help."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['run', '--help'])
        
        assert result.exit_code == 0
        assert "Run an agent with JIT variable injection" in result.output
    
    def test_key_help(self):
        """Test key command help."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['key', '--help'])
        
        assert result.exit_code == 0
        assert "Manage keys in personal vault" in result.output

    def test_quickstart_help(self):
        """Test quickstart command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['quickstart', '--help'])
        assert result.exit_code == 0
        assert "quickstart" in result.output and "Interactive" in result.output

    def test_template_help(self):
        """Test template command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['template', '--help'])
        assert result.exit_code == 0
        assert "template" in result.output

    def test_demo_help(self):
        """Test demo command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['demo', '--help'])
        assert result.exit_code == 0
        assert "demo" in result.output


class TestCLIQuickstart:
    """Tests for quickstart command."""

    def test_quickstart_non_interactive(self, mock_keyring, temp_dir, clean_env):
        """Test quickstart with --non-interactive creates agent.lock and agent.py."""
        runner = CliRunner()
        original_dir = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(cli, ['quickstart', '--non-interactive'])
            assert result.exit_code == 0
            assert os.path.exists('agent.lock')
            assert os.path.exists('agent.py')
            assert "Next steps" in result.output
            agent_lock = AgentLock()
            agent_lock.master_key = "default-key"
            data = agent_lock.read()
            assert data is not None
            assert "OPENAI_API_KEY" in data["credentials"]
        finally:
            os.chdir(original_dir)


class TestCLITemplate:
    """Tests for template list and use."""

    def test_template_list(self):
        """Test template list shows available templates."""
        runner = CliRunner()
        result = runner.invoke(cli, ['template', 'list'])
        assert result.exit_code == 0
        assert (
            "financial_analyst" in result.output
            or "code_reviewer" in result.output
            or "twitter_bot" in result.output
        )

    def test_template_use(self, mock_keyring, temp_dir, clean_env):
        """Test template use creates agent.lock and agent.py from template."""
        runner = CliRunner()
        original_dir = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(cli, ['template', 'use', 'financial_analyst'])
            assert result.exit_code == 0
            assert os.path.exists('agent.lock')
            assert os.path.exists('agent.py')
            assert "OPENAI_API_KEY" in result.output
            agent_lock = AgentLock()
            agent_lock.master_key = "default-key"
            data = agent_lock.read()
            assert data is not None
            assert "OPENAI_API_KEY" in data["credentials"]
        finally:
            os.chdir(original_dir)

    def test_template_use_invalid(self):
        """Test template use with invalid name exits with error."""
        runner = CliRunner()
        result = runner.invoke(cli, ['template', 'use', 'nonexistent_template_xyz'])
        assert result.exit_code == 1
        assert "not found" in result.output or "Template" in result.output


class TestCLIDemo:
    """Tests for demo command."""

    def test_demo_runs(self):
        """Test demo command runs and shows before/after content."""
        runner = CliRunner()
        result = runner.invoke(cli, ['demo', '--fast'])
        assert result.exit_code == 0
        assert "BEFORE" in result.output and "AFTER" in result.output
        assert "JIT" in result.output or "injection" in result.output.lower()


class TestCLIIntegration:
    """Integration tests for CLI workflow."""
    
    def test_full_workflow(self, mock_keyring, temp_dir):
        """Test complete CLI workflow: add key, init, run."""
        runner = CliRunner()
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            
            # Add key
            runner.invoke(cli, ['key', 'add', 'WORKFLOW_KEY'], input='workflow-value\n')
            
            # Initialize agent
            runner.invoke(cli, [
                'init',
                '--credentials', 'WORKFLOW_KEY',
                '--personality', 'Workflow test agent'
            ])
            
            # Create test script
            test_script = os.path.join(temp_dir, "workflow_agent.py")
            with open(test_script, 'w') as f:
                f.write("""
import os
key = os.environ.get('WORKFLOW_KEY')
prompt = os.environ.get('AGENT_SYSTEM_PROMPT')
if key == 'workflow-value' and prompt == 'Workflow test agent':
    print("SUCCESS")
    exit(0)
else:
    print("FAILED")
    exit(1)
""")
            
            # Run agent
            result = runner.invoke(cli, ['run', 'workflow_agent.py'], input='y\n')
            
            # Should contain success indicators
            assert "SUCCESS" in result.output or result.exit_code == 0
        finally:
            os.chdir(original_dir)
