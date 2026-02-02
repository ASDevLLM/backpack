# Backpack Agent Container Usage Guide

## Quick Start

### Option A: Interactive wizard (recommended)

```bash
pip install backpack-agent
backpack quickstart
backpack key add OPENAI_API_KEY
backpack run agent.py
```

### Option B: Use a ready-made template

```bash
backpack template list
backpack template use financial_analyst
backpack key add OPENAI_API_KEY
backpack run agent.py
```

### Option C: Manual init

```bash
backpack key add OPENAI_API_KEY
backpack init --credentials "OPENAI_API_KEY" --personality "Helpful assistant"
backpack run agent.py
```

### See the value in 30 seconds

```bash
backpack demo
```

## Commands Reference

### `quickstart` - Interactive Wizard

Creates an `agent.lock` and a starter `agent.py` in the current directory.

**Syntax:**

```bash
backpack quickstart [--non-interactive]
```

### `init` - Create New Agent Lock

Creates a new `agent.lock` file with encrypted credentials, personality, and memory layers.

**Syntax:**
```bash
backpack init [OPTIONS]
```

**Options:**
- `--credentials TEXT`: Comma-separated list of required credentials (e.g., `OPENAI_API_KEY,TWITTER_TOKEN`)
- `--personality TEXT`: Agent personality prompt/description

**Examples:**
```bash
# Basic initialization
backpack init --credentials "OPENAI_API_KEY" --personality "Helpful assistant"

# Multiple credentials
backpack init --credentials "OPENAI_API_KEY,ANTHROPIC_API_KEY,GOOGLE_API_KEY" --personality "Multi-model AI agent"

# Personality only (no credentials)
backpack init --personality "You are a creative writing assistant"
```

### `run` - Run Agent with JIT Injection

Runs an agent script with just-in-time variable injection from the keychain.

**Syntax:**
```bash
backpack run <script_path>
```

**Examples:**
```bash
# Run example agent
backpack run example_agent.py

# Run custom agent
backpack run my_agent.py

# Run agent in subdirectory
backpack run agents/financial_analyst.py
```

**What happens:**
1. Reads `agent.lock` from current directory
2. Decrypts credential requirements
3. Checks keychain for each required key
4. Prompts for user consent: `This agent requires access to OPENAI_API_KEY. Allow access? (Y/n)`
5. Injects approved keys into environment
6. Injects personality variables (e.g., `AGENT_SYSTEM_PROMPT`, `AGENT_TONE`)
7. Executes the agent script

#### Logging for `run`

The CLI and core modules use Python's `logging`:

- By default, logs at `INFO` level to stderr when using the CLI.
- Change verbosity with `BACKPACK_LOG_LEVEL`:

```bash
BACKPACK_LOG_LEVEL=DEBUG backpack run agent.py
```

Only high-level events (file paths, key names, statuses) are logged;
**secret values are never logged**.

### `key` - Keychain Management

Manage credentials in your personal OS keychain.

#### `key add` - Add Key to Vault

**Syntax:**
```bash
backpack key add <key_name> [--value TEXT]
```

**Examples:**
```bash
# Interactive prompt (recommended)
backpack key add OPENAI_API_KEY
# Enter value: [hidden input]

# Non-interactive (for scripts)
backpack key add OPENAI_API_KEY --value "sk-..."
```

#### `key list` - List Keys in Vault

**Syntax:**
```bash
backpack key list
```

**Output:**
```
Keys in vault:
  - OPENAI_API_KEY
  - TWITTER_TOKEN
  - ANTHROPIC_API_KEY
```

#### `key remove` - Remove Key from Vault

**Syntax:**
```bash
backpack key remove <key_name>
```

**Examples:**
```bash
backpack key remove OPENAI_API_KEY
```

### `template` - Agent Template Library

Use ready-made agent templates.

```bash
backpack template list
backpack template use <name> [--dir PATH]
```

### `demo` - Visual Demo

Prints a short before/after walkthrough explaining Backpack’s value.

```bash
backpack demo [--fast]
```

## Use Cases

### Use Case 1: Sharing Agents with Team

**Scenario**: You've created a financial analysis agent and want to share it with your team.

**Steps:**

1. **Create the agent:**
   ```bash
   backpack init --credentials "OPENAI_API_KEY,ALPHA_VANTAGE_API_KEY" --personality "You are a senior financial analyst specializing in market trends."
   ```

2. **Commit to Git:**
   ```bash
   git add agent.lock example_agent.py
   git commit -m "Add financial analysis agent"
   git push
   ```

3. **Team member clones:**
   ```bash
   git clone <repo>
   cd <repo>
   ```

4. **Team member adds their keys:**
   ```bash
   backpack key add OPENAI_API_KEY
   backpack key add ALPHA_VANTAGE_API_KEY
   ```

5. **Team member runs agent:**
   ```bash
   backpack run example_agent.py
   # Prompts for consent, then runs with their keys
   ```

**Benefits:**
- No `.env` files to manage
- No manual key sharing
- Personality updates propagate via Git
- Each team member uses their own keys

### Use Case 2: Multi-Environment Deployment

**Scenario**: Deploy the same agent to development, staging, and production.

**Steps:**

1. **Development:**
   ```bash
   export AGENT_MASTER_KEY="dev-master-key-123"
   backpack init --credentials "OPENAI_API_KEY" --personality "Dev agent"
   backpack key add OPENAI_API_KEY  # Dev key
   ```

2. **Staging:**
   ```bash
   export AGENT_MASTER_KEY="staging-master-key-456"
   backpack init --credentials "OPENAI_API_KEY" --personality "Staging agent"
   backpack key add OPENAI_API_KEY  # Staging key
   ```

3. **Production:**
   ```bash
   export AGENT_MASTER_KEY="prod-master-key-789"
   backpack init --credentials "OPENAI_API_KEY" --personality "Production agent"
   backpack key add OPENAI_API_KEY  # Prod key
   ```

**Benefits:**
- Same code, different keys per environment
- Isolated keychains per environment
- Environment-specific personalities

### Use Case 3: Stateful Agent with Memory

**Scenario**: Create an agent that remembers context across sessions.

**Example Agent (`stateful_agent.py`):**
```python
import os
import json
from backpack.agent_lock import AgentLock

def main():
    agent_lock = AgentLock()
    agent_data = agent_lock.read()
    
    # Load memory
    memory = agent_data.get('memory', {})
    session_count = memory.get('session_count', 0) + 1
    
    print(f"Session #{session_count}")
    print(f"Last run: {memory.get('last_run', 'Never')}")
    
    # Update memory
    memory['session_count'] = session_count
    memory['last_run'] = "2024-01-15 10:30:00"
    agent_lock.update_memory(memory)
    
    # Use injected credentials
    api_key = os.environ.get('OPENAI_API_KEY')
    system_prompt = os.environ.get('AGENT_SYSTEM_PROMPT')
    
    print(f"System prompt: {system_prompt}")
    print("Agent running...")

if __name__ == '__main__':
    main()
```

**Usage:**
```bash
backpack run stateful_agent.py
# First run: Session #1, Last run: Never
# Second run: Session #2, Last run: 2024-01-15 10:30:00
```

**Benefits:**
- Agent state persists across runs
- Memory can be committed to Git (encrypted)
- Resume from checkpoints

### Use Case 4: Agent Personality Versioning

**Scenario**: Update agent personality and have it propagate to all users.

**Steps:**

1. **Update personality:**
   ```python
   from backpack.agent_lock import AgentLock
   
   agent_lock = AgentLock()
   agent_data = agent_lock.read()
   
   # Update personality
   agent_data['personality']['system_prompt'] = "You are an expert Python developer."
   agent_data['personality']['tone'] = "technical"
   
   agent_lock.create(
       agent_data['credentials'],
       agent_data['personality'],
       agent_data['memory']
   )
   ```

2. **Commit and push:**
   ```bash
   git add agent.lock
   git commit -m "Update agent personality to Python expert"
   git push
   ```

3. **Team members pull:**
   ```bash
   git pull
   # Next run automatically uses new personality
   ```

**Benefits:**
- Personality changes tracked in Git
- Automatic updates on pull
- Credentials remain unchanged

## Advanced Usage

### Custom Master Key

Set a custom master key for encryption:

```bash
export AGENT_MASTER_KEY="my-strong-master-key-12345"
backpack init --credentials "KEY1" --personality "Agent"
```

**Security Note**: Use a strong, unique master key in production. Never commit master keys to Git.

### Programmatic Access

Use Backpack programmatically in your Python code:

```python
from backpack.agent_lock import AgentLock
from backpack.keychain import get_key, store_key

# Create agent lock
agent_lock = AgentLock()
agent_lock.create(
    credentials={"OPENAI_API_KEY": "placeholder"},
    personality={"system_prompt": "Helpful assistant", "tone": "friendly"},
    memory={}
)

# Store key
store_key("OPENAI_API_KEY", "sk-...")

# Read agent lock
agent_data = agent_lock.read()
print(agent_data['personality']['system_prompt'])

# Get key from keychain
api_key = get_key("OPENAI_API_KEY")
```

### Environment Variables

Backpack injects the following environment variables:

- **Credentials**: As specified in `agent.lock` (e.g., `OPENAI_API_KEY`)
- **Personality**: 
  - `AGENT_SYSTEM_PROMPT`: System prompt from personality layer
  - `AGENT_TONE`: Tone setting from personality layer

Access in your agent:
```python
import os

api_key = os.environ.get('OPENAI_API_KEY')
system_prompt = os.environ.get('AGENT_SYSTEM_PROMPT')
tone = os.environ.get('AGENT_TONE')
```

## Troubleshooting

### "No agent.lock found"

**Problem**: Running `backpack run` without an `agent.lock` file.

**Solution**: Initialize first:
```bash
backpack init --credentials "KEY1" --personality "Agent"
```

### "Key not found in vault"

**Problem**: Agent requires a key that's not in your keychain.

**Solution**: Add the key:
```bash
backpack key add KEY_NAME
```

### "Decryption failed"

**Problem**: Wrong master key or corrupted `agent.lock` file.

**Solution**: 
1. Check `AGENT_MASTER_KEY` environment variable
2. Verify `agent.lock` file integrity
3. Re-initialize if necessary (you'll lose existing state)

### Keychain Access Denied

**Problem**: OS keychain access denied.

**Solution**:
- **macOS**: Check Keychain Access permissions
- **Linux**: Ensure keyring service is running (`gnome-keyring-daemon` or `kwalletd`)
- **Windows**: Check Windows Credential Manager permissions

## Best Practices

1. **Use strong master keys**: Never use the default `"default-key"` in production
2. **Commit agent.lock**: Safe to commit encrypted `agent.lock` files
3. **Never commit master keys**: Keep `AGENT_MASTER_KEY` in environment or secrets manager
4. **Review consent prompts**: Always review before approving key access
5. **Separate environments**: Use different master keys for dev/staging/prod
6. **Regular key rotation**: Rotate keys periodically for security
7. **Backup keychain**: Backup your OS keychain (platform-specific)

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- Read [SECURITY.md](SECURITY.md) for security best practices
- Read [CONTRIBUTING.md](CONTRIBUTING.md) to contribute to the project
