# UV Commands Cheat Sheet for AICO Workspace

## UV Workspace Setup & Sync

Initial setup - install all dependencies for full development:
```bash
uv sync --extra cli --extra backend --extra test
```

Sync only core dependencies (shared by all components) - ⚠️ DANGEROUS: Will remove CLI/backend deps:
```bash
# uv sync  # DON'T USE - removes optional dependencies
```

Sync specific groups only:
```bash
uv sync --extra cli                    # CLI development only
uv sync --extra backend               # Backend development only
uv sync --extra cli --extra backend   # CLI + Backend development
```

Force reinstall everything (nuclear option) - ⚠️ DANGEROUS without extras:
```bash
uv sync --reinstall --extra cli --extra backend --extra test
```

Sync after pulling git changes or editing pyproject.toml:
```bash
uv sync --extra cli --extra backend --extra test  # ⚠️ IMPORTANT: Always specify extras to avoid removing dependencies
```

## Dependency Management

Add to core dependencies (shared by CLI, backend, shared):
```bash
uv add requests                       # Single package
uv add "pydantic>=2.0.0"             # With version constraint
uv add cryptography keyring psutil   # Multiple packages at once
```

Add to specific optional dependency groups:
```bash
uv add --group cli typer-cli          # CLI-specific dependency
uv add --group backend "fastapi[all]" # Backend-specific with extras
uv add --group test pytest-mock       # Test-specific dependency
```

Add development dependencies (Note: --dev flag may not work as expected):
```bash
uv add --group test black mypy ruff  # Remove --dev flag
```

Remove dependencies:
```bash
uv remove requests                    # Remove from core
uv remove --group cli typer-cli       # Remove from CLI group
uv remove --group backend sqlalchemy  # Remove from backend group
uv remove requests httpx aiofiles     # Remove multiple packages
```

Upgrade dependencies:
```bash
uv add "fastapi>=0.117.0" --upgrade   # Upgrade specific package
uv sync --upgrade --extra cli --extra backend --extra test  # Upgrade everything safely
```

## Running Code with UV

CLI Commands (always use 'uv run' - never direct python):
```bash
uv run aico --help                    # Show CLI help
uv run aico gateway status            # Check gateway status
uv run aico gateway start --no-detach # Start gateway in foreground
uv run aico db init                   # Initialize database
uv run aico security setup            # Setup security
```

Backend Server:
```bash
uv run python backend/main.py         # Direct Python execution
uv run uvicorn backend.main:app --reload --port 8700  # Development server
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8771  # Custom host/port
```

Testing:
```bash
uv run pytest                         # Run all tests
uv run pytest --cov=shared --cov=backend --cov=cli  # With coverage
uv run pytest backend/tests/test_api.py  # Specific test file
uv run pytest -v -s                   # Verbose output
```

## Inspection & Debugging

List installed packages:
```bash
uv pip list                           # All packages
uv pip list --outdated               # Show outdated packages
# uv pip list | grep fastapi           # May not work on Windows CMD
```

Show package details:
```bash
uv pip show fastapi                   # Basic package info
uv pip show --verbose requests        # Detailed info including dependencies
```

Dependency tree and conflicts:
```bash
uv tree                              # Show dependency tree
uv pip check                         # Check for dependency conflicts
```

Lock file management:
```bash
uv lock                              # Generate/update uv.lock
uv lock --upgrade                    # Upgrade all packages in lock
```

## AICO-Specific Workflows

Full development setup (recommended):
```bash
uv sync --extra cli --extra backend --extra test
```

CLI-only development:
```bash
uv sync --extra cli
uv run aico gateway start
```

Backend-only development:
```bash
uv sync --extra backend
uv run uvicorn backend.main:app --reload
```

Add new CLI feature dependency:
```bash
uv add --group cli rich-click
uv sync --extra cli --extra backend --extra test  # Always sync all groups
uv run aico --help  # Test CLI works
```

Add new backend feature dependency:
```bash
uv add --group backend redis
uv sync --extra cli --extra backend --extra test  # Always sync all groups
uv run python backend/main.py
```

Reset everything (troubleshooting):
```bash
# Windows: rmdir /s .venv
# Unix: rm -rf .venv
uv sync --extra cli --extra backend --extra test  # Reinstall everything
```

## AICO Dependency Groups

- **Core (shared)**: cryptography, keyring, libsql-client, pyyaml, jsonschema, watchdog, pyzmq, protobuf, platformdirs, psutil, passlib, bcrypt
- **CLI group**: typer, rich, requests
- **Backend group**: fastapi, httpx, pydantic, pyjwt, uvicorn (chromadb, duckdb planned)
- **Test group**: pytest

## Best Practices

Always use 'uv run' instead of direct python execution:
```bash
uv run python script.py              # ✅ Good - finds all dependencies
python script.py                     # ❌ Bad - may miss packages
```

Always sync after changes:
```bash
uv sync --extra cli --extra backend --extra test  # After editing pyproject.toml
uv sync --extra cli --extra backend --extra test  # After git pull
```

Use version constraints for stability:
```bash
uv add "typer>=0.12.0,<1.0.0"       # ✅ Good - constrained
uv add typer                         # ❌ Risky - unconstrained
```

Commit lock file to git:
```bash
git add uv.lock                      # Lock file ensures reproducible builds
```

Group dependencies logically:
- **Core**: shared by all components
- **CLI**: CLI-specific tools  
- **Backend**: web server dependencies
- **Test**: testing framework and tools

## Quick Reference

### Most Common Commands
```bash
# Setup
uv sync --extra cli --extra backend --extra test

# Daily usage
uv run aico gateway status
uv run uvicorn backend.main:app --reload
uv run pytest

# Adding dependencies (always sync all groups after)
uv add --group cli new-package
uv sync --extra cli --extra backend --extra test
```

### Troubleshooting
```bash
# Check for conflicts
uv pip check

# Nuclear reset (Windows)
rmdir /s .venv
uv sync --extra cli --extra backend --extra test

# Nuclear reset (Unix)
rm -rf .venv
uv sync --extra cli --extra backend --extra test
```
