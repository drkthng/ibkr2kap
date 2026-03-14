# DECISIONS.md

## Log
| Date | Title | Status |
|------|-------|--------|
| 2024-03-13 | Use `decimal.Decimal` strictly | Accepted |
| 2024-03-13 | Use SQLite + SQLAlchemy 2.0 | Accepted |

## Phase 0 Decisions

**Date:** 2024-03-14

### Scope
- Keep the initial setup strictly local. No CI/CD setup right now. The main focus is getting the local app running robustly. The repository will eventually be public and need a good README.
- We will stick to the predefined project structure (`src/ibkr_tax/`) right from the start.

### Approach
- Chose: `uv` for dependency management.
- Reason: The user had no strong preference. `uv` is significantly faster than `poetry` while remaining compatible with standard `pyproject.toml` formats, which is a big plus for local development speed.

### Constraints
- Python is assumed to be installed on the host machine.
