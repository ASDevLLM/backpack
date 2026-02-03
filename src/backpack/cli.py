"""
Command-line interface for Backpack Agent Container System.

This module provides CLI commands for managing agents, keys, and running
agents with JIT variable injection.

Logging is configured here for CLI usage. By default it logs at INFO level,
and can be controlled via the BACKPACK_LOG_LEVEL environment variable.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from typing import Dict, List

import click

from . import __version__
from .agent_lock import AgentLock
from .exceptions import AgentLockNotFoundError, AgentLockReadError, BackpackError, KeyNotFoundError, ValidationError
from .keychain import (
    InvalidKeyNameError,
    KeychainDeletionError,
    KeychainStorageError,
    delete_key,
    get_key,
    list_keys,
    register_key,
    store_key,
)


def _configure_logging() -> logging.Logger:
    """
    Configure a default logger for CLI usage if none is configured.

    The log level can be overridden with BACKPACK_LOG_LEVEL (e.g. DEBUG, INFO).
    Can log to a file if BACKPACK_LOG_FILE is set.
    """
    root = logging.getLogger()
    if not root.handlers:
        level_name = os.environ.get("BACKPACK_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        
        handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]
        
        log_file = os.environ.get("BACKPACK_LOG_FILE")
        if log_file:
            handlers.append(logging.FileHandler(log_file))
            
        logging.basicConfig(
            level=level, 
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
            handlers=handlers
        )
    return logging.getLogger(__name__)


logger = _configure_logging()


def handle_error(e: Exception, exit_code: int = 1) -> None:
    """
    Handle and display errors in a user-friendly way.

    Args:
        e: The exception to handle
        exit_code: Exit code to use (default: 1)
    """
    if isinstance(e, BackpackError):
        logger.error("Backpack error", extra={"type": type(e).__name__, "error_message": e.message})
        click.echo(click.style(f"Error: {e.message}", fg="red"), err=True)
        if e.details:
            click.echo(click.style(f"  {e.details}", fg="yellow"), err=True)
            
        # Add helpful tips based on exception type
        if isinstance(e, KeyNotFoundError):
            click.echo(click.style("  💡 Tip: List available keys with 'backpack key list'", fg="cyan"), err=True)
        elif isinstance(e, AgentLockNotFoundError):
            click.echo(click.style("  💡 Tip: Initialize an agent with 'backpack init' or 'backpack quickstart'", fg="cyan"), err=True)
        elif isinstance(e, AgentLockReadError):
            click.echo(click.style("  💡 Tip: Check file permissions or if the file is corrupted.", fg="cyan"), err=True)
            
    elif isinstance(e, click.ClickException):
        raise e
    else:
        logger.error("Unexpected error in CLI", extra={"type": type(e).__name__, "error": str(e)})
        click.echo(click.style(f"Unexpected error: {str(e)}", fg="red"), err=True)
        if hasattr(e, "__cause__") and e.__cause__:
            click.echo(click.style(f"  Caused by: {str(e.__cause__)}", fg="yellow"), err=True)
        click.echo(click.style("  💡 Tip: Run with BACKPACK_LOG_LEVEL=DEBUG for more details.", fg="cyan"), err=True)

    sys.exit(exit_code)


@click.group()
def cli():
    """
    Backpack Agent Container CLI.

    A secure system for managing AI agents with encrypted state,
    credentials, and personality configurations.
    """


@cli.command()
@click.option("--non-interactive", is_flag=True, help="Skip prompts; use defaults (for scripts)")
def quickstart(non_interactive):
    """
    Interactive wizard to create your first agent in under 2 minutes.

    Guides you through creating an agent.lock and a starter agent script.
    Use --non-interactive for CI/scripts (uses sensible defaults).
    """
    try:
        click.echo(click.style("\n>> Backpack Quick Start\n", fg="cyan", bold=True))
        click.echo("Create a working agent in under 2 minutes.\n")

        agent_lock = AgentLock()
        if os.path.exists(agent_lock.file_path) and not non_interactive:
            if not click.confirm("agent.lock already exists here. Overwrite and continue?"):
                click.echo("Cancelled.")
                return

        # Agent name / description
        if non_interactive:
            agent_name = "My Agent"
            creds_input = "OPENAI_API_KEY"
            personality_text = "You are a helpful AI assistant. Use a professional tone."
        else:
            agent_name = click.prompt("What's your agent's name?", default="My Agent", show_default=True)
            click.echo("\nCommon credentials (comma-separated): OPENAI_API_KEY, ANTHROPIC_API_KEY, TWITTER_TOKEN")
            creds_input = click.prompt("Required credentials", default="OPENAI_API_KEY", show_default=True)
            personality_text = click.prompt(
                "Personality / system prompt",
                default="You are a helpful AI assistant. Use a professional tone.",
                show_default=True,
            )

        creds: Dict[str, str] = {}
        for cred in creds_input.replace(",", " ").split():
            c = cred.strip()
            if not c:
                continue
            if not c.replace("_", "").isalnum():
                continue
            creds[c] = f"placeholder_{c.lower()}"

        if not creds:
            creds = {"OPENAI_API_KEY": "placeholder_openai_api_key"}

        personality_data = {"system_prompt": personality_text or "You are a helpful AI assistant.", "tone": "professional"}

        agent_lock.create(creds, personality_data)
        click.echo(click.style(f"\n[OK] Created agent.lock with {len(creds)} credential(s)", fg="green"))

        # Generate starter agent.py
        agent_py = _QUICKSTART_AGENT_SCRIPT.format(agent_name=agent_name or "My Agent", creds_list=", ".join(repr(k) for k in creds))
        agent_path = "agent.py"
        if os.path.exists(agent_path) and not non_interactive:
            if not click.confirm(f"{agent_path} already exists. Overwrite?"):
                agent_path = "agent_quickstart.py"
                click.echo(f"Writing starter script to {agent_path} instead.")

        with open(agent_path, "w") as f:
            f.write(agent_py)
        click.echo(click.style(f"[OK] Created {agent_path}", fg="green"))

        click.echo(click.style("\nNext steps:", fg="cyan", bold=True))
        click.echo("  1. Add your keys:  backpack key add OPENAI_API_KEY  (and any others)")
        click.echo(f"  2. Run your agent: backpack run {agent_path}")
        click.echo("")
    except BackpackError as e:
        handle_error(e)
    except Exception as e:
        handle_error(e)


_QUICKSTART_AGENT_SCRIPT = '''"""
{agent_name} - Generated by Backpack quickstart.
Uses credentials and personality from agent.lock (injected by Backpack).
"""

import os

def main():
    # Credentials are injected by Backpack when you run: backpack run agent.py
    keys = [{creds_list}]
    for key_name in keys:
        value = os.environ.get(key_name)
        print(f"{{key_name}} available: {{'Yes' if value else 'No'}}")
    system_prompt = os.environ.get("AGENT_SYSTEM_PROMPT", "")
    print(f"Personality: {{system_prompt[:60]}}...")
    print("Agent is ready. Replace this with your real logic.")

if __name__ == "__main__":
    main()
'''


@cli.command()
@click.option("--credentials", help="Comma-separated list of required credentials (e.g., OPENAI_API_KEY,TWITTER_TOKEN)")
@click.option("--personality", help="Agent personality prompt")
def init(credentials, personality):
    """
    Initialize a new agent.lock file.
    """
    try:
        creds: Dict[str, str] = {}
        if credentials:
            for cred in credentials.split(","):
                cred_name = cred.strip()
                if not cred_name:
                    continue
                if not cred_name.replace("_", "").isalnum():
                    raise ValidationError(
                        f"Invalid credential name: {cred_name}",
                        "Credential names must contain only alphanumeric characters and underscores",
                    )
                creds[cred_name] = f"placeholder_{cred_name.lower()}"

        personality_data = {"system_prompt": personality or "You are a helpful AI assistant.", "tone": "professional"}

        agent_lock = AgentLock()
        if os.path.exists(agent_lock.file_path):
            if not click.confirm("agent.lock already exists. Overwrite it?"):
                click.echo("Cancelled.")
                return

        agent_lock.create(creds, personality_data)
        click.echo(click.style(f"[OK] Created agent.lock with {len(creds)} credential placeholders", fg="green"))
    except BackpackError as e:
        handle_error(e)
    except Exception as e:
        handle_error(e)


@cli.command()
@click.option("--new-key", help="New master key (prompted if not provided)")
@click.option("--key-file", default="agent.lock", help="Path to agent.lock file")
def rotate(new_key, key_file):
    """
    Rotate the master encryption key for agent.lock.
    
    Decrypts the current agent.lock with the current key (AGENT_MASTER_KEY),
    and re-encrypts it with the new key.
    """
    if not os.path.exists(key_file):
        click.echo(click.style(f"File {key_file} not found.", fg="red"))
        sys.exit(1)
        
    # 1. Read with current key
    current_lock = AgentLock(key_file)
    data = current_lock.read()
    
    if data is None:
        click.echo(click.style("Failed to decrypt agent.lock with current key.", fg="red"))
        click.echo("Check if AGENT_MASTER_KEY is set correctly.")
        sys.exit(1)
        
    click.echo(click.style(f"Successfully decrypted {key_file}", fg="green"))
    
    # 2. Get new key
    if not new_key:
        click.echo("\nYou are about to rotate the master key.")
        click.echo("Please provide a new secure master key.")
        new_key = click.prompt("New Master Key", hide_input=True, confirmation_prompt=True)
        
    if not new_key:
        click.echo("Key cannot be empty.")
        sys.exit(1)
        
    # 3. Write with new key
    try:
        # Create a new lock instance with the NEW key
        new_lock = AgentLock(key_file, master_key=new_key)
        new_lock.create(data["credentials"], data["personality"], data["memory"])
        
        click.echo(click.style(f"\n[OK] Re-encrypted {key_file} with new key.", fg="green"))
        click.echo(click.style("\nIMPORTANT:", fg="yellow", bold=True))
        click.echo("You MUST update your AGENT_MASTER_KEY environment variable to the new key.")
        click.echo("If you lose this key, you cannot access the agent.lock file again.")
        
    except Exception as e:
        click.echo(click.style(f"Failed to rotate key: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.argument("script_path")
@click.option("--non-interactive", is_flag=True, help="Skip prompts (auto-approve keys) - enabled automatically if AGENT_MASTER_KEY is set")
def run(script_path, non_interactive):
    """
    Run an agent with JIT variable injection.
    """
    agent_lock = AgentLock()
    agent_data = agent_lock.read()

    if not agent_data:
        raise click.ClickException("No agent.lock found. Run 'backpack init' first.")

    # Detect Cloud/Non-interactive mode
    # We assume non-interactive if the flag is passed OR if AGENT_MASTER_KEY is explicitly set
    # (implying a managed environment like Vercel/Railway)
    is_cloud_mode = non_interactive or (os.environ.get("AGENT_MASTER_KEY") is not None)

    env_vars: Dict[str, str] = {}
    
    # Get required keys directly from the loaded data
    creds_layer = agent_data.get("credentials", {})
    required_keys = list(creds_layer.keys())

    for key_name in required_keys:
        value_to_inject = None
        source = None

        # 1. Check Environment (already set?)
        if key_name in os.environ:
            source = "environment"
        
        # 2. Check Lock File (Encrypted Portability)
        # If the value in agent.lock is NOT a placeholder, it's a real encrypted key
        elif key_name in creds_layer:
             val = creds_layer[key_name]
             if val and not val.startswith("placeholder_"):
                 value_to_inject = val
                 source = "agent.lock"

        # 3. Check Local Vault (Keychain)
        if not source and not value_to_inject:
             stored_key = get_key(key_name)
             if stored_key:
                 value_to_inject = stored_key
                 source = "vault"
        
        # Decision Logic
        if source == "environment":
             # Already satisfied.
             if not is_cloud_mode:
                 click.echo(f"Key {key_name} found in environment.")
             continue
        
        if value_to_inject:
            if is_cloud_mode:
                # Cloud/Non-interactive: Auto-approve
                env_vars[key_name] = value_to_inject
            else:
                # Local/Interactive: Prompt user
                msg = f"This agent requires access to {key_name}"
                if source == "agent.lock":
                    msg += " (found in agent.lock)"
                elif source == "vault":
                    msg += " (found in vault)"
                
                if click.confirm(f"{msg}. Allow access?"):
                    env_vars[key_name] = value_to_inject
                else:
                    click.echo(f"Access denied for {key_name}. Agent may not function properly.")
        else:
            # Key not found anywhere
            click.echo(f"Key {key_name} not found in environment, agent.lock, or vault.")
            click.echo(f"  Add it with 'backpack key add {key_name}' or set it as an environment variable.")

    env_vars["AGENT_SYSTEM_PROMPT"] = agent_data["personality"]["system_prompt"]
    env_vars["AGENT_TONE"] = agent_data["personality"]["tone"]

    # Merge injected env vars with current environment
    env = os.environ.copy()
    env.update(env_vars)

    click.echo(f"Running {script_path} with {len(env_vars)} injected variables...")
    
    # Use subprocess.run() instead of os.system() for better control and security
    # sys.executable ensures we use the same Python interpreter
    result = subprocess.run([sys.executable, script_path], env=env)
    
    # Exit with the script's return code
    sys.exit(result.returncode)


@cli.group()
def key():
    """Manage keys in personal vault"""


@key.command("add")
@click.argument("key_name")
@click.option("--value", prompt=True, hide_input=True, help="Key value")
def add_key(key_name, value):
    """
    Add a key to personal vault.
    """
    try:
        if not value or not value.strip():
            raise ValidationError("Key value cannot be empty", "Please provide a non-empty value")

        existing_key = get_key(key_name)
        if existing_key:
            if not click.confirm(f"Key '{key_name}' already exists. Overwrite it?"):
                click.echo("Cancelled.")
                return

        store_key(key_name, value)
        register_key(key_name)
        click.echo(click.style(f"[OK] Added {key_name} to vault", fg="green"))
    except (InvalidKeyNameError, KeychainStorageError, ValidationError) as e:
        handle_error(e)
    except Exception as e:
        handle_error(e)


@key.command("list")
def list_keys_cmd():
    """List keys in personal vault."""
    keys = list_keys()
    if keys:
        click.echo("Keys in vault:")
        for key_name in keys:
            click.echo(f"  - {key_name}")
    else:
        click.echo("No keys in vault")


@key.command("remove")
@click.argument("key_name")
def remove_key(key_name):
    """Remove a key from personal vault."""
    try:
        delete_key(key_name)
        click.echo(click.style(f"[OK] Removed {key_name} from vault", fg="green"))
    except (KeychainDeletionError, InvalidKeyNameError) as e:
        handle_error(e)
    except Exception as e:
        handle_error(e)


def _get_templates_dir() -> str:
    """Return path to backpack/templates (works when installed or run from source)."""
    try:
        # Prefer stdlib resource APIs when available.
        try:
            from importlib import resources as importlib_resources  # py3.7+

            # `files()` is py3.9+, so guard it.
            files = getattr(importlib_resources, "files", None)
            if files is not None:
                return str(files("backpack").joinpath("templates"))
        except Exception:
            pass

        # Fallback for older environments / packaging edge-cases.
        import pkg_resources  # type: ignore

        return pkg_resources.resource_filename("backpack", "templates")
    except Exception:
        pass
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def _list_template_names() -> List[str]:
    """Return list of template directory names."""
    root = _get_templates_dir()
    if not os.path.isdir(root):
        return []
    return [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)) and not d.startswith(".")]


@cli.group()
def template():
    """Use ready-made agent templates."""


@template.command("list")
def template_list():
    """List available agent templates."""
    names = _list_template_names()
    if not names:
        click.echo("No templates found.")
        return
    click.echo(click.style("Available templates:\n", fg="cyan", bold=True))
    root = _get_templates_dir()
    for name in sorted(names):
        manifest_path = os.path.join(root, name, "manifest.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path) as f:
                    m = json.load(f)
                desc = m.get("description", "")
                click.echo(f"  {name}")
                if desc:
                    click.echo(click.style(f"    {desc}", fg="white"))
            except (json.JSONDecodeError, OSError):
                click.echo(f"  {name}")
        else:
            click.echo(f"  {name}")


@template.command("use")
@click.argument("name")
@click.option("--dir", "target_dir", type=click.Path(), default=".", help="Directory to copy template into (default: current)")
def template_use(name, target_dir):
    """Copy a template into the current (or given) directory and create agent.lock."""
    root = _get_templates_dir()
    template_path = os.path.join(root, name)
    if not os.path.isdir(template_path):
        click.echo(click.style(f"Template '{name}' not found.", fg="red"))
        click.echo("Run 'backpack template list' to see available templates.")
        sys.exit(1)
    manifest_path = os.path.join(template_path, "manifest.json")
    if not os.path.isfile(manifest_path):
        click.echo(click.style(f"Template '{name}' has no manifest.json.", fg="red"))
        sys.exit(1)
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        click.echo(click.style(f"Invalid manifest: {e}", fg="red"))
        sys.exit(1)

    creds_list = manifest.get("credentials", [])
    personality = manifest.get("personality", {})
    creds = {c: f"placeholder_{c.lower()}" for c in creds_list}
    personality_data = {
        "system_prompt": personality.get("system_prompt", "You are a helpful AI assistant."),
        "tone": personality.get("tone", "professional"),
    }

    os.makedirs(target_dir, exist_ok=True)
    agent_lock = AgentLock(file_path=os.path.join(target_dir, "agent.lock"))
    if os.path.exists(agent_lock.file_path) and not click.confirm(f"{agent_lock.file_path} exists. Overwrite?"):
        click.echo("Skipped agent.lock.")
    else:
        agent_lock.create(creds, personality_data)
        click.echo(click.style(f"[OK] Created {agent_lock.file_path}", fg="green"))

    agent_src = os.path.join(template_path, "agent.py")
    agent_dst = os.path.join(target_dir, "agent.py")
    if os.path.isfile(agent_src):
        if os.path.exists(agent_dst) and not click.confirm("agent.py exists. Overwrite?"):
            click.echo("Skipped agent.py.")
        else:
            shutil.copy2(agent_src, agent_dst)
            click.echo(click.style(f"[OK] Created {agent_dst}", fg="green"))

    click.echo(click.style("\nNext steps:", fg="cyan", bold=True))
    for c in creds_list:
        click.echo(f"  backpack key add {c}")
    click.echo("  backpack run agent.py")
    click.echo("")


@cli.command()
@click.option("--fast", is_flag=True, help="Skip pauses (for scripting)")
def demo(fast):
    """Show a short before/after demo of Backpack's value."""
    click.echo(click.style("\n  +============================================================+", fg="cyan"))
    click.echo(click.style("  |  BACKPACK DEMO: Before vs After                            |", fg="cyan"))
    click.echo(click.style("  +============================================================+\n", fg="cyan"))
    click.echo(click.style("  BEFORE (Naked Agent):", fg="red", bold=True))
    click.echo("    - Agent code + scattered .env / dashboard secrets")
    click.echo("    - 'TWITTER_API_KEY not set' -> crash -> find key -> paste -> restart")
    click.echo("    - Personality in code or random config files")
    click.echo("")
    click.echo(click.style("  AFTER (Backpack):", fg="green", bold=True))
    click.echo("    - agent.lock travels with code (encrypted credentials + personality)")
    click.echo("    - Run: backpack run agent.py")
    click.echo("    - Prompt: 'This agent needs TWITTER_API_KEY. You have it. Allow? (Y/n)' -> Y")
    click.echo("    - Key injected into process only; never plain text on disk")
    click.echo("    - Personality versioned in Git with the agent")
    click.echo("")
    click.echo(click.style("  JIT INJECTION:", fg="cyan", bold=True))
    click.echo("    1. Backpack reads agent.lock -> sees required keys")
    click.echo("    2. Checks your OS keychain (vault)")
    click.echo("    3. Asks once per key -> injects into env for this run only")
    click.echo("    4. Agent runs with credentials + AGENT_SYSTEM_PROMPT, AGENT_TONE")
    click.echo("")
    click.echo(click.style("  Try it:", fg="yellow", bold=True))
    click.echo("    backpack quickstart    # 2-minute setup")
    click.echo("    backpack template list # ready-made agents")
    click.echo("    backpack run agent.py  # run with JIT injection")
    click.echo("")


@cli.command()
@click.argument("output_file", required=False)
def export(output_file):
    """Export the current agent to a zip file."""
    if not output_file:
        output_file = "backpack_agent.zip"
    
    if not output_file.endswith(".zip"):
        output_file += ".zip"

    files_to_export = ["agent.lock", "agent.py", "requirements.txt", "README.md"]
    found_files = []
    
    try:
        with zipfile.ZipFile(output_file, "w") as zf:
            for f in files_to_export:
                if os.path.exists(f):
                    zf.write(f)
                    found_files.append(f)
        
        if found_files:
            click.echo(click.style(f"[OK] Exported {len(found_files)} files to {output_file}", fg="green"))
            for f in found_files:
                click.echo(f"  - {f}")
        else:
            click.echo(click.style("No agent files found to export.", fg="yellow"))
            # Clean up empty zip
            if os.path.exists(output_file):
                os.remove(output_file)
    except Exception as e:
        click.echo(click.style(f"Export failed: {e}", fg="red"))
        sys.exit(1)


@cli.command("import")
@click.argument("input_file")
@click.option("--dir", "target_dir", default=".", help="Target directory")
def import_agent(input_file, target_dir):
    """Import an agent from a zip file."""
    if not os.path.exists(input_file):
        click.echo(click.style(f"File {input_file} not found.", fg="red"))
        sys.exit(1)
        
    try:
        os.makedirs(target_dir, exist_ok=True)
        with zipfile.ZipFile(input_file, "r") as zf:
            zf.extractall(target_dir)
            click.echo(click.style(f"[OK] Imported agent to {target_dir}", fg="green"))
            click.echo("Files:")
            for name in zf.namelist():
                click.echo(f"  - {name}")
    except zipfile.BadZipFile:
        click.echo(click.style("Invalid zip file.", fg="red"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Import failed: {e}", fg="red"))
        sys.exit(1)


@cli.command()
def tutorial():
    """Interactive tutorial to learn Backpack."""
    click.echo(click.style("\n🎓 Backpack Interactive Tutorial", fg="cyan", bold=True))
    click.echo("Welcome! This tutorial will guide you through the core concepts.\n")
    
    if not click.confirm("Ready to start?", default=True):
        click.echo("Maybe later! 👋")
        return

    # Step 1: Concepts
    click.echo(click.style("\n1. The Problem: The Naked Agent 😱", fg="yellow", bold=True))
    click.echo("Agents usually have their keys scattered in .env files and config hardcoded.")
    click.echo("This makes them hard to share and insecure.")
    click.pause(info="Press any key to continue...")

    # Step 2: Agent Lock
    click.echo(click.style("\n2. The Solution: agent.lock 🔒", fg="yellow", bold=True))
    click.echo("Backpack creates an encrypted file that travels with your code.")
    click.echo("It contains: Credentials (placeholders), Personality, and Memory.")
    click.pause(info="Press any key to continue...")

    # Step 3: JIT Injection
    click.echo(click.style("\n3. JIT Variable Injection 💉", fg="yellow", bold=True))
    click.echo("When you run an agent, Backpack:")
    click.echo("  a. Reads agent.lock")
    click.echo("  b. Asks for permission to use keys from your secure vault")
    click.echo("  c. Injects them directly into the process memory")
    click.echo("  d. NEVER writes them to disk in plain text")
    click.pause(info="Press any key to continue...")

    # Step 4: Hands on
    click.echo(click.style("\n4. Let's try it! 🚀", fg="yellow", bold=True))
    click.echo("We'll create a dummy agent now.")
    
    if click.confirm("Create 'tutorial_agent' directory?"):
        target_dir = "tutorial_agent"
        try:
            os.makedirs(target_dir, exist_ok=True)
            
            # Simulate init
            click.echo(f"\nRunning: backpack init (in {target_dir})")
            agent_lock = AgentLock(os.path.join(target_dir, "agent.lock"))
            if not os.path.exists(agent_lock.file_path):
                 agent_lock.create({"OPENAI_API_KEY": "placeholder"}, {"system_prompt": "You are a student."})
            click.echo(click.style("[OK] Created agent.lock", fg="green"))
            
            click.echo("\nNow you would run: backpack run agent.py")
            click.echo("And Backpack would ask to inject OPENAI_API_KEY.")
        except Exception as e:
             click.echo(click.style(f"Failed to create tutorial agent: {e}", fg="red"))
        
    click.echo(click.style("\n🎉 Tutorial Complete!", fg="green", bold=True))
    click.echo("You are ready to use Backpack.")
    click.echo("Run 'backpack quickstart' to build your real agent.")


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def status(json_output):
    """Show current agent status."""
    agent_lock = AgentLock()
    if not os.path.exists(agent_lock.file_path):
        if json_output:
            click.echo(json.dumps({"error": "No agent.lock found"}))
        else:
            click.echo(click.style("No agent.lock found in current directory.", fg="yellow"))
        return

    try:
        data = agent_lock.read()
        if not data:
            if json_output:
                click.echo(json.dumps({"error": "agent.lock is corrupted or unreadable"}))
            else:
                click.echo(click.style("agent.lock is corrupted or unreadable.", fg="red"))
            return

        if json_output:
            # Return pure data for machine consumption
            output = {
                "file_path": agent_lock.file_path,
                "size": os.stat(agent_lock.file_path).st_size,
                "layers": {
                    "credentials": list(data.get("credentials", {}).keys()),
                    "personality": data.get("personality", {}),
                    "memory": data.get("memory", {})
                }
            }
            click.echo(json.dumps(output, indent=2))
            return

        click.echo(click.style(f"Agent Status ({agent_lock.file_path})", fg="cyan", bold=True))
        
        # File info
        stat = os.stat(agent_lock.file_path)
        click.echo(f"  Size: {stat.st_size} bytes")
        
        # Layers
        click.echo("\n  Layers:")
        creds = data.get("credentials", {})
        click.echo(f"    - Credentials: {len(creds)} keys defined")
        for k in creds:
            click.echo(f"      - {k}")
            
        personality = data.get("personality", {})
        click.echo(f"    - Personality: {len(personality)} items")
        
        memory = data.get("memory", {})
        click.echo(f"    - Memory: {len(memory)} items")
        
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": str(e)}))
        else:
            click.echo(click.style(f"Error reading status: {e}", fg="red"))


@cli.command()
def info():
    """Show system information."""
    click.echo(click.style("Backpack Information", fg="cyan", bold=True))
    click.echo(f"  Version: {__version__}")
    click.echo(f"  Python: {platform.python_version()} ({sys.executable})")
    click.echo(f"  Platform: {platform.platform()}")
    click.echo(f"  CWD: {os.getcwd()}")


@cli.command()
def version():
    """Show version information."""
    click.echo(f"backpack version {__version__}")


@cli.command()
def doctor():
    """Check for common issues."""
    click.echo(click.style("Running Backpack Doctor...", fg="cyan", bold=True))
    issues = []
    
    # Check Python version
    py_ver = sys.version_info
    if py_ver < (3, 7):
        issues.append("Python version is too old. Backpack requires 3.7+")
    else:
        click.echo("  [OK] Python version")
        
    # Check keyring
    try:
        import keyring
        try:
            keyring.get_keyring()
            click.echo("  [OK] Keyring backend found")
        except Exception as e:
            issues.append(f"Keyring error: {e}")
    except ImportError:
        issues.append("keyring library not installed")
        
    # Check cryptography
    try:
        import cryptography
        click.echo(f"  [OK] Cryptography library ({cryptography.__version__})")
    except ImportError:
        issues.append("cryptography library not installed")
        
    if issues:
        click.echo(click.style("\nIssues found:", fg="red", bold=True))
        for issue in issues:
            click.echo(f"  - {issue}")
        sys.exit(1)
    else:
        click.echo(click.style("\nEverything looks good! 🎒", fg="green", bold=True))


if __name__ == "__main__":
    cli()

