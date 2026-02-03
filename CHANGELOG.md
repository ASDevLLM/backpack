# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-02-02

### Fixed
- Fixed CLI test suite to handle environment variables correctly (`AGENT_MASTER_KEY`).

## [0.1.1] - 2026-02-02

### Added
- **CLI Commands**:
  - `backpack status`: View details of the current `agent.lock` file.
  - `backpack info`: Display system and environment information.
  - `backpack doctor`: Diagnose common issues with dependencies and keychains.
  - `backpack version`: Show the installed version.
  - `backpack export`: Export agent to a zip file.
  - `backpack import`: Import agent from a zip file.
  - `backpack tutorial`: Interactive guide for new users.
- **Examples**:
  - `examples/basic_agent.py`: Simple agent using one key.
  - `examples/multi_key_agent.py`: Agent using multiple credentials.
  - `examples/stateful_agent.py`: Agent demonstrating persistent memory.
  - `examples/team_agent.py`: Role-based agent example.
  - `examples/integration_langchain.py`: Integration with LangChain.
- **Demos**:
  - `demos/demo_script.py`: Visual simulation script for demonstrations.

### Changed
- **Error Handling**: Improved CLI error messages with helpful "💡 Tips".
- **Logging**: Enhanced logging configuration with timestamps and better formatting.
- **Packaging**: Added `pyproject.toml` for modern build configuration.

### Fixed
- Replaced `os.system` with `subprocess.run` for better security and control.

## [0.1.0] - 2026-01-01

### Added
- Initial release of Backpack Agent Container System.
- Core `agent.lock` encryption (Credentials, Personality, Memory).
- JIT Variable Injection.
- OS Keychain integration.
- `backpack run`, `backpack init`, `backpack key` commands.
