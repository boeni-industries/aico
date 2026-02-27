# UV Commands Cheat Sheet for AICO (Per-Component Projects)

AICO uses UV, but **not** as a single root workspace. Each Python component is its own UV project with its own `pyproject.toml` and `uv.lock`:

- `shared/`
- `cli/`
- `backend/`
- `modelservice/`

This is required because some components intentionally depend on conflicting versions.

## Setup & Sync

CLI setup (host machine; the CLI runs locally):

```bash
cd cli
uv sync --frozen
```

Backend/modelservice run in Docker for local development:

```bash
docker compose -f docker/docker-compose.local.yml up --build
```

## Dependency Management

Add a dependency (run inside the component directory you want to change):
```bash
uv add <package>
uv lock
uv sync --frozen
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
uv lock --upgrade
uv sync --frozen
```

## Running Code with UV

CLI Commands:
```bash
cd cli
uv run aico --help                    # Show CLI help
uv run aico gateway status            # Check gateway status
uv run aico gateway start --no-detach # Start gateway in foreground
uv run aico db init                   # Initialize database
uv run aico security setup            # Setup security
```

Backend + Core + Modelservice:

```bash
docker compose -f docker/docker-compose.local.yml up --build
```

Testing:
```bash
cd cli
uv run pytest
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
uv lock                              # Generate/update the component uv.lock
uv lock --upgrade                    # Upgrade packages in the component lock
```

## Resetting a component environment

If you need a clean reinstall for a component:

```bash
rm -rf .venv
uv sync --frozen
```

## Best Practices

Always use 'uv run' instead of direct python execution:
```bash
uv run python script.py              # ✅ Good - finds all dependencies
python script.py                     # ❌ Bad - may miss packages
```

Always sync after changes:
```bash
uv lock
uv sync --frozen
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
# CLI setup
cd cli
uv sync --frozen

# Run services
docker compose -f docker/docker-compose.local.yml up --build
```

### Troubleshooting
```bash
# Check for conflicts
uv pip check

# Nuclear reset (Windows)
rmdir /s .venv
uv sync --frozen

# Nuclear reset (Unix)
rm -rf .venv
uv sync --frozen
```
