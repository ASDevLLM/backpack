import os
import json
import zipfile
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from backpack.cli import cli
from backpack.agent_lock import AgentLock

class TestCLINewCommands:
    
    def test_status_no_file(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["status"])
            assert "No agent.lock found" in result.output

    def test_status_corrupted_file(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("agent.lock", "w") as f:
                f.write("invalid json")
            result = runner.invoke(cli, ["status"])
            # AgentLock.read() catches JSONDecodeError and returns None
            assert "agent.lock is corrupted or unreadable" in result.output

    def test_status_valid_file(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create a mock agent.lock
            lock = AgentLock()
            lock.create(
                {"OPENAI_API_KEY": "placeholder"}, 
                {"system_prompt": "You are a bot", "tone": "friendly"},
                {"run_count": 1}
            )
            
            result = runner.invoke(cli, ["status"])
            assert "Agent Status" in result.output
            assert "Credentials: 1 keys defined" in result.output
            assert "Personality: 2 items" in result.output 
            assert "Memory: 1 items" in result.output

    def test_info(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["info"])
        assert "Backpack Information" in result.output
        assert "Version:" in result.output
        assert "Python:" in result.output
        assert "Platform:" in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])
        assert "backpack-agent version" in result.output

    def test_doctor_all_ok(self):
        runner = CliRunner()
        # Mock sys.version_info and imports
        with patch("sys.version_info", (3, 9, 0)):
             result = runner.invoke(cli, ["doctor"])
             assert "Everything looks good!" in result.output

    def test_doctor_issues(self):
        runner = CliRunner()
        # Mock sys.version_info to be old
        with patch("sys.version_info", (3, 6, 0)):
             result = runner.invoke(cli, ["doctor"])
             assert result.exit_code == 1
             assert "Python version is too old" in result.output

    def test_export_default_name(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create dummy files
            with open("agent.py", "w") as f: f.write("code")
            with open("agent.lock", "w") as f: f.write("lock")
            
            result = runner.invoke(cli, ["export"])
            assert "Exported 2 files to backpack_agent.zip" in result.output
            assert os.path.exists("backpack_agent.zip")
            
            # Verify zip content
            with zipfile.ZipFile("backpack_agent.zip", "r") as zf:
                names = zf.namelist()
                assert "agent.py" in names
                assert "agent.lock" in names

    def test_export_custom_name(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("agent.py", "w") as f: f.write("code")
            
            result = runner.invoke(cli, ["export", "my_agent"])
            assert "Exported 1 files to my_agent.zip" in result.output
            assert os.path.exists("my_agent.zip")

    def test_export_no_files(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["export"])
            assert "No agent files found to export" in result.output
            assert not os.path.exists("backpack_agent.zip")

    def test_import_basic(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create a zip file
            with zipfile.ZipFile("test.zip", "w") as zf:
                zf.writestr("agent.py", "print('hello')")
            
            result = runner.invoke(cli, ["import", "test.zip"])
            assert "Imported agent to ." in result.output
            assert os.path.exists("agent.py")

    def test_import_missing_file(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["import", "missing.zip"])
            assert "File missing.zip not found" in result.output

    def test_import_bad_zip(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("bad.zip", "w") as f:
                f.write("not a zip")
            
            result = runner.invoke(cli, ["import", "bad.zip"])
            assert "Invalid zip file" in result.output

    def test_tutorial_cancel(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["tutorial"], input="n\n")
        assert "Maybe later!" in result.output

    def test_tutorial_complete(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Mock click.pause to avoid needing input for it
            with patch("click.pause"):
                # Inputs: Ready? Y, Create dir? Y
                # Only 2 inputs needed now if pause is mocked
                inputs = "y\ny\n"
                result = runner.invoke(cli, ["tutorial"], input=inputs)
                assert "Tutorial Complete!" in result.output
                assert os.path.exists("tutorial_agent/agent.lock")
