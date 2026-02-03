# CLI Reference

The `backpack` command-line interface provides tools for managing agents and keys.

## Commands

### `backpack quickstart`
Interactive wizard to create your first agent in under 2 minutes.
- `--non-interactive`: Skip prompts; use defaults.

### `backpack init`
Initialize a new agent.lock file.
- `--credentials`: Comma-separated list of required credentials.
- `--personality`: Agent personality prompt.

### `backpack run <script_path>`
Run an agent with JIT variable injection.

### `backpack key`
Manage keys in personal vault.
- `add <key_name>`: Add a key.
- `list`: List keys.
- `remove <key_name>`: Remove a key.

### `backpack template`
Use ready-made agent templates.
- `list`: List available templates.
- `use <name>`: Copy a template to the current directory.

### `backpack rotate`
Rotate the master encryption key for agent.lock.
- `--new-key`: New master key.
- `--key-file`: Path to agent.lock.

### `backpack demo`
Show a short before/after demo.

### `backpack export`
Export the current agent to a zip file.

### `backpack import`
Import an agent from a zip file.

### `backpack tutorial`
Interactive tutorial to learn Backpack.

### `backpack status`
Show current agent status.

### `backpack info`
Show system information.

### `backpack doctor`
Check for common issues.
