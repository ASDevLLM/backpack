# Backpack: Encrypted Agent Container System

[![PyPI version](https://badge.fury.io/py/backpack-agent.svg)](https://badge.fury.io/py/backpack-agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

**Backpack** is a secure, portable system for managing AI agents with encrypted state, credentials, and personality configurations. It solves the "Naked Agent" problem by providing a unified container format that travels with your agent code in version control.

## Why Backpack?

| Pain point | Without Backpack | With Backpack |
|------------|------------------|---------------|
| **Credentials** | Scattered in `.env`, dashboards, or copy-paste | One vault; JIT injection with one prompt per key |
| **Sharing agents** | "Clone repo, then manually add keys and config" | Clone → `backpack run agent.py` → allow keys when prompted |
| **Personality/config** | Hardcoded or random config files | Version-controlled in `agent.lock` with the code |
| **Secrets on disk** | `.env` or config in plain text | Keys only in OS keychain; never plain text in repo |
| **Time to first run** | Find keys, create `.env`, restart | `backpack quickstart` → add keys → run in minutes |

## Quick Start (3 steps)

```bash
pip install backpack-agent
backpack quickstart          # Interactive wizard: name, credentials, personality
backpack key add OPENAI_API_KEY   # Add your keys when prompted
backpack run agent.py        # Run with JIT injection
```

Or use a ready-made template:

```bash
backpack template list
backpack template use financial_analyst
backpack key add OPENAI_API_KEY
backpack run agent.py
```

See [Quick Start](#quick-start) below for more options.

## Table of Contents

- [Why Backpack?](#why-backpack)
- [Quick Start (3 steps)](#quick-start-3-steps)
- [The Problem](#the-problem-the-naked-agent)
- [The Solution](#the-solution-encrypted-agent-containers)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Templates & Examples](#templates--examples)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Security](#security)
- [Contributing](#contributing)

## The Problem: "The Naked Agent"

Right now, an agent is just code. It has no state and no keys until a developer manually injects them.

- **Code**: Public (GitHub)
- **Secrets**: Private (Scattered in `.env` or cloud dashboards)
- **Memory**: Private (Stuck in a specific vector database)

This creates friction when sharing agents, managing credentials, and maintaining state across environments.

## The Solution: Encrypted Agent Containers

Backpack creates an `agent.lock` file that travels with the agent's code in the git repo. This file contains three distinct encrypted "variable" layers:

### Layer 1: Credentials (The Keys)

**Content**: Placeholders for `OPENAI_API_KEY`, `TWITTER_TOKEN`, etc.

**Innovation**: When a user clones the agent, the system sees the `agent.lock`. It checks the user's personal local keychain. If the user has a "Global OpenAI Key" saved, it automatically injects it into the agent's encrypted runtime. No manual `.env` setup required.

### Layer 2: Personality & System Prompts (The Brain)

**Content**: "You are a senior financial analyst. Use a formal tone."

**Innovation**: These are variables that can be tweaked and version-controlled. A team can update the "Personality Variable" in Git, and everyone's local agent updates instantly upon `git pull`.

### Layer 3: Ephemeral Memory (The Context)

**Content**: User ID, Session History, last tool output.

**Innovation**: Local-first memory. The agent writes its "short-term memory" to an encrypted local file. This means you can stop an agent on your laptop, commit the encrypted state, push it to a server, and the agent resumes exactly where it left off.

## Features

- 🔐 **Encrypted State Management**: All agent data is encrypted using PBKDF2 and Fernet
- 🔑 **OS Keychain Integration**: Secure credential storage using platform-native keyrings
- 🚀 **JIT Variable Injection**: Just-in-time credential injection with user consent
- 📦 **Portable Containers**: `agent.lock` files travel with your code in version control
- 🧠 **Version-Controlled Personality**: System prompts and configuration in Git
- 💾 **Ephemeral Memory**: Encrypted state that can be committed and shared
- 🛡️ **No Plain Text Secrets**: Keys never written to disk in plain text

## Installation

### Prerequisites

- Python 3.7+
- pip

### Install from PyPI (recommended)

```bash
pip install backpack-agent
```

### Install from Source

```bash
git clone <repository-url>
cd backpack
pip install -e .
```

### Verify Installation

```bash
backpack --help
```

## Quick Start

**Option A – Interactive wizard (fastest):**

```bash
backpack quickstart
# Answer: agent name, credentials (e.g. OPENAI_API_KEY), personality
backpack key add OPENAI_API_KEY   # and any other keys
backpack run agent.py
```

**Option B – Manual init:**

```bash
backpack key add OPENAI_API_KEY
backpack key add TWITTER_TOKEN
backpack init --credentials "OPENAI_API_KEY,TWITTER_TOKEN" --personality "You are a senior financial analyst. Use a formal tone."
backpack run example_agent.py
```

**Option C – Use a template:**

```bash
backpack template list
backpack template use financial_analyst   # or twitter_bot, code_reviewer
backpack key add OPENAI_API_KEY
backpack run agent.py
```

**See the value in 30 seconds:**

```bash
backpack demo
```

For detailed usage, see [USAGE.md](USAGE.md).

## Templates & Examples

Ready-made agents you can run immediately:

| Template | Description |
|----------|-------------|
| `financial_analyst` | Formal, data-driven analyst persona; uses `OPENAI_API_KEY` |
| `twitter_bot` | Friendly Twitter bot; uses `OPENAI_API_KEY`, `TWITTER_BEARER_TOKEN` |
| `code_reviewer` | Constructive code review; uses `OPENAI_API_KEY` |

```bash
backpack template list
backpack template use <name>
```

Each template includes a README and a runnable `agent.py` you can customize.

## Testing

Backpack includes a comprehensive test suite using pytest.

### Running Tests

Tests can run **without installing** the package (conftest.py adds `src` to `PYTHONPATH`):

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests (no pip install -e . required)
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_crypto.py

# Run with verbose output
pytest -v
```

Alternatively, install in editable mode first: `pip install -e .`

### Logging

Backpack uses Python's standard `logging` module:

- Library modules (`crypto`, `keychain`, `agent_lock`) log at module level
- The CLI configures a default logger when invoked
- Control verbosity with the `BACKPACK_LOG_LEVEL` environment variable
  (e.g. `DEBUG`, `INFO`, `WARNING`):

```bash
BACKPACK_LOG_LEVEL=DEBUG backpack run agent.py
```

No secret values (keys, ciphertext, plaintext) are ever written to logs.

### Test Coverage

The test suite covers:
- ✅ Encryption/decryption operations
- ✅ Keychain storage and retrieval
- ✅ Agent lock file management
- ✅ CLI command execution
- ✅ Error handling and edge cases

See `htmlcov/index.html` after running with coverage for detailed coverage reports.

## Project Structure

```
backpack/
├── example_agent.py      # Example agent implementation
├── requirements.txt      # Python dependencies
├── pytest.ini           # Pytest configuration
├── README.md            # This file
├── USAGE.md             # Usage guide
├── ARCHITECTURE.md      # Architecture documentation
├── SECURITY.md          # Security considerations
├── CONTRIBUTING.md      # Contributing guidelines
├── LICENSE              # MIT License
├── .gitignore          # Git ignore rules
├── src/
│   └── backpack/
│       ├── __init__.py
│       ├── agent_lock.py
│       ├── cli.py
│       ├── crypto.py
│       ├── exceptions.py
│       ├── keychain.py
│       └── templates/
└── tests/
    ├── __init__.py      # Test package initialization
    ├── conftest.py      # Pytest fixtures and configuration
    ├── test_crypto.py   # Encryption/decryption tests
    ├── test_keychain.py # Keychain operation tests
    ├── test_agent_lock.py # Agent lock file tests
    └── test_cli.py      # CLI command tests
```

## Architecture

Backpack implements a three-layer encryption system:

1. **Credentials Layer**: Stores placeholders for required API keys
2. **Personality Layer**: Stores system prompts and agent configuration
3. **Memory Layer**: Stores ephemeral agent state

All layers are encrypted using PBKDF2 key derivation and Fernet symmetric encryption. The master key can be set via the `AGENT_MASTER_KEY` environment variable.

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Documentation

- **[USAGE.md](USAGE.md)**: Detailed usage guide with examples
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System architecture and design decisions
- **[SECURITY.md](SECURITY.md)**: Security considerations and best practices
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Guidelines for contributing to the project
- **[PROJECT_ASSESSMENT.md](PROJECT_ASSESSMENT.md)**: Comprehensive project assessment
- **[OPTIONAL_IMPROVEMENTS.md](OPTIONAL_IMPROVEMENTS.md)**: List of optional future enhancements

## Security

Backpack prioritizes security through:

- Encrypted storage of all agent data
- OS-native keychain integration
- No plain text secrets on disk
- User consent prompts for credential access

For detailed security information, see [SECURITY.md](SECURITY.md).

## The "JIT" Variable Injection Workflow

This is where the "GitHub of Secret Management" thinking revolutionizes agents.

### Current Workflow (Bad):

1. Agent tries to run
2. Agent crashes because `TWITTER_API_KEY` is missing
3. User goes to Twitter Developer Portal, generates key, pastes into `.env`
4. Restart

### Backpack "Agent Passport" Workflow:

1. Agent initializes
2. It reads `agent.lock` and sees it needs `TWITTER_API_KEY`
3. **Intervention**: Instead of crashing, the CLI pauses execution and prompts:
   ```
   This agent requires access to Twitter. You have a Twitter key in your personal vault. Allow access? (Y/n)
   ```
4. **Grant**: User hits 'Y'. The CLI decrypts the key only into the agent's process memory
5. The agent runs. The key is never written to disk in plain text

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Code style and standards
- Testing requirements
- Pull request process
- Development setup

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Project Assessment

For a detailed assessment of the project's current state, strengths, gaps, and recommendations, see [PROJECT_ASSESSMENT.md](PROJECT_ASSESSMENT.md).

## Support

For issues, questions, or contributions, please open an issue on the repository.
