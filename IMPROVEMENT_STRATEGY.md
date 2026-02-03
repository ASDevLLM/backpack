# Improvement Strategy & Implementation Plan

This document outlines the assessment of optional improvements and the detailed plan for implementing the highest priority items.

## Assessment of Optional Improvements

| ID | Improvement | Priority | Status | Gap Analysis |
|----|-------------|----------|--------|--------------|
| 1 | **CI/CD Pipeline** | High | Partial | Exists but lacks cross-platform testing (Windows/Mac), linting, and type checking. |
| 2 | **Logging Infrastructure** | High | Partial | Console logging exists. File logging and structured config are missing. |
| 3 | **Key Rotation Utility** | Medium | Missing | No automated way to rotate the master key and re-encrypt data. |
| 4 | **Per-Layer Key Derivation** | Low | Missing | Single master key currently used for all layers. |
| 5 | **Enhanced CLI UX** | Medium | Partial | Basic colors used. Missing progress bars, aliases, and consistent formatting. |
| 6 | **Configuration File Support** | Medium | Missing | No support for `backpack.toml` or `backpack.yaml`. |
| 7 | **Better Error Recovery** | Medium | Partial | Basic error messages. Missing interactive recovery or "did you mean" suggestions. |
| 8 | **Agent Lock Validation** | Medium | Partial | Basic JSON check. Missing schema validation (JSON Schema). |
| 14 | **API Reference Docs** | Medium | Missing | No Sphinx/MkDocs setup. |
| 17 | **Cross-Platform Tests** | Medium | Missing | CI only runs on Ubuntu. |

## Implementation Plans

### 1. CI/CD Pipeline Enhancement (High Priority)

**Scope**: 
- Update GitHub Actions to run on Ubuntu, Windows, and macOS.
- Add `ruff` for linting and formatting checks.
- Add `mypy` for static type checking.
- Ensure coverage reporting is active.

**Technical Specifications**:
- **File**: `.github/workflows/ci.yml`
- **Matrix**: `os: [ubuntu-latest, windows-latest, macos-latest]`
- **Tools**: `ruff`, `mypy` (add to `pyproject.toml`)
- **Commands**: 
    - `ruff check .`
    - `mypy src/`
    - `pytest --cov=src`

**Resource Allocation**: 1 Backend Developer (Current Agent).
**Timeline**: Immediate.
**Testing Strategy**: Verify workflow syntax and run tools locally.
**Rollback Plan**: Revert changes to `ci.yml` and `pyproject.toml`.

### 2. Logging Infrastructure (High Priority)

**Scope**: 
- Enable logging to a file (`backpack.log` or user-defined).
- Allow configuration via `BACKPACK_LOG_FILE`.
- Ensure structured logging (JSON format option) or clear text format for files.

**Technical Specifications**:
- **File**: `src/backpack/cli.py`
- **Change**: Update `_configure_logging` to check for `BACKPACK_LOG_FILE` env var and add a `FileHandler`.
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**Resource Allocation**: 1 Backend Developer.
**Timeline**: Immediate.
**Testing Strategy**: Run CLI commands and verify log file creation and content.
**Rollback Plan**: Revert changes to `cli.py`.

### 3. Key Rotation Utility (Medium Priority)

**Scope**: 
- Add `backpack key rotate` command.
- Functionality: Decrypt `agent.lock` with old key, re-encrypt with new key.
- Prompt user for new key or generate one.

**Technical Specifications**:
- **File**: `src/backpack/cli.py`
- **Command**: `@cli.command() def key_rotate(...)`
- **Logic**:
    1. Load current lock.
    2. Prompt for new master key (confirm).
    3. Re-encrypt all layers.
    4. Save `agent.lock`.
    5. Instruct user to update `AGENT_MASTER_KEY`.

**Resource Allocation**: 1 Backend Developer.
**Timeline**: Follows CI/CD and Logging.
**Testing Strategy**: Unit test creating a lock, rotating key, and verifying read with new key fails with old key.
**Rollback Plan**: Revert `cli.py` changes.

---
**Next Steps**: Proceed with implementation of Items 1, 2, and 3.
