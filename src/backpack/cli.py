"""
Command-line interface for Backpack Agent Container System.

This module provides CLI commands for managing agents, keys, and running
agents with JIT variable injection.

Logging is configured here for CLI usage. By default it logs at INFO level,
and can be controlled via the BACKPACK_LOG_LEVEL environment variable.
"""

import click
import json
import logging
import os
import shutil
import subprocess
import sys
from typing import Dict, List

from .agent_lock import AgentLock
from .keychain import (
    store_key,
    get_key,
    list_keys,
    register_key,
    delete_key,
    KeychainStorageError,
    KeychainDeletionError,
    InvalidKeyNameError,
)
from .exceptions import BackpackError, ValidationError


def _configure_logging() -> logging.Logger:
    """
    Configure a default logger for CLI usage if none is configured.

    The log level can be overridden with BACKPACK_LOG_LEVEL (e.g. DEBUG, INFO).
    """
    root = logging.getLogger()
    if not root.handlers:
        level_name = os.environ.get("BACKPACK_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
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
    elif isinstance(e, click.ClickException):
        raise e
    else:
        logger.error("Unexpected error in CLI", extra={"type": type(e).__name__, "error": str(e)})
        click.echo(click.style(f"Unexpected error: {str(e)}", fg="red"), err=True)
        if hasattr(e, "__cause__") and e.__cause__:
            click.echo(click.style(f"  Caused by: {str(e.__cause__)}", fg="yellow"), err=True)

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
@click.argument("script_path")
def run(script_path):
    """
    Run an agent with JIT variable injection.
    """
    agent_lock = AgentLock()
    agent_data = agent_lock.read()

    if not agent_data:
        raise click.ClickException("No agent.lock found. Run 'backpack init' first.")

    env_vars: Dict[str, str] = {}
    required_keys = agent_lock.get_required_keys()

    for key_name in required_keys:
        stored_key = get_key(key_name)
        if stored_key:
            if click.confirm(f"This agent requires access to {key_name}. Allow access?"):
                env_vars[key_name] = stored_key
            else:
                click.echo(f"Access denied for {key_name}. Agent may not function properly.")
        else:
            click.echo(f"Key {key_name} not found in vault. Add it with 'backpack key add {key_name}'")

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


if __name__ == "__main__":
    cli()

