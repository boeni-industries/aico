---
title: Command-Line Interface (CLI) Architecture
---

# AICO Command-Line Interface (CLI) Architecture

## Overview

The `aico` CLI provides a professional, cross-platform, and high-performance command-line tool for administering, automating, and interacting with the AICO system. It is designed for power users, system administrators, and developers who require advanced control, scripting, and diagnostic capabilities beyond the graphical admin UI.

## Goals & Principles

- **Universal Accessibility:** The CLI is callable from anywhere on the system after installation, with no dependency on virtual environments or fragile path setup.
- **Top-Tier UX:** Fast startup, instant command responses, user-friendly and visually appealing output, modern Unicode/emoji support, and rich progress indicators.
- **Cross-Platform:** Runs natively and identically on Windows, macOS, and Linux.
- **DRY & KISS:** Shares business logic and data models with backend services, avoiding code duplication and maximizing maintainability.
- **Extensible:** Modular command structure for future expansion.

## Technology Choices

### Implementation Language
- **Python**
  - Rationale: Shares language and libraries with backend, enables DRY integration, mature ecosystem for CLI development and packaging, cross-platform by default.

### Core Libraries
- **Typer**: Modern CLI framework (built on Click) for intuitive, maintainable, and autocompleting command trees.
- **Rich**: Advanced text formatting, tables, syntax highlighting, progress bars, and beautiful output. All advanced UX is implemented directly using Rich in our own code.
- **PyInstaller**: For building a single-file, dependency-free, universal executable for all platforms. (Briefcase is not used.)
- **httpx**: Modern, async-capable HTTP client for API communication with backend services.
- **ZeroMQ** (via `pyzmq`): For direct message bus integration when required.
- **Platformdirs**: For managing config/cache paths in a cross-platform manner.

### Packaging & Distribution
- **PyInstaller** (primary):
    - Produces a single-file executable (`aico`) for each OS.
    - No .venv or Python installation required on target system.
    - Handles all dependencies, including native libraries, in the bundle.
- **Briefcase** (alternative):
    - For more native-feeling installers or app bundles if desired.

## Integration Approach

- **Backend Integration:**
    - CLI imports and reuses backend Python modules for admin logic where possible (e.g., user management, diagnostics, data migration).
    - For remote administration, CLI communicates with backend via REST API or ZeroMQ, using shared schemas and models.
    - All business logic is implemented in backend modules, not duplicated in CLI code.
- **Frontend/UI Integration:**
    - CLI may offer commands to launch or interact with the admin UI (e.g., `aico admin open`), but does not duplicate UI logic.
    - Main CLI use cases are backend/admin-focused.

## Command Structure (Example)

```
aico [command] [options]

Commands:
  status         Show system and service status
  user           Manage users (add, remove, list, roles)
  db             Database operations (backup, migrate, inspect)
  plugin         Manage plugins (list, install, enable, disable)
  logs           Tail or query logs
  config         View or edit configuration
  admin          Open admin UI
  ...            (future: agent, emotion, vector, etc.)
```

- Each command is implemented as a Typer sub-app, allowing modular growth.
- All output uses Rich for tables, markdown, progress bars, and error highlighting.

## CLI Architecture

### Core Principles
- **Modular & Extensible**: Each command is a self-contained module/sub-app, enabling massive future growth.
- **DRY & Maintainable**: Shares logic with backend modules; CLI is a thin, UX-focused layer.
- **Fast & User-Friendly**: Instant startup, rich output, robust error handling, and autocompletion.
- **Self-Documenting**: Any incomplete or ambiguous command invocation yields a helpful, predictive help text to guide the user to the next step.

### CLI Directory Structure (Suggested)

```text
/cli  
    /commands  
        status.py  
        user.py  
        db.py  
        plugin.py  
        logs.py  
        config.py  
        admin.py  
        version.py   # (First: versioning automation)  
    main.py  
    utils.py  
    ...
```
- Each command is implemented as a sub-app (using Typer) and registered in `main.py`.
- Shared utilities, config, and backend integration in `utils.py` or `/lib`.

### Command Registration Pattern

```python
# main.py
import typer
from commands import status, user, db, plugin, logs, config, admin, version

app = typer.Typer()
app.add_typer(version.app, name="version")
# ...add other sub-apps

if __name__ == "__main__":
    app()
```

### Growth & Extensibility
- Each new domain (e.g., plugin, agent, emotion, vector) gets its own command module.
- The sub-app pattern keeps the CLI scalable and organized as it grows.
- Future plugin discovery (dynamic loading) can be added as CLI matures.

---

## UX & Output Standards

- **Instant startup** (<100ms typical)
- **Colorful, readable output** with Unicode, emoji, and clear formatting
- **Progress bars** for long-running tasks
- **Context-aware help** and autocompletion
- **Graceful error handling** and actionable messages
- **Consistent cross-platform behavior**

## Building the Universal Executable

1. **Install dependencies:**
    - All CLI dependencies are specified in `requirements-cli.txt`.
2. **Build with PyInstaller:**
    - Example: `pyinstaller --onefile aico_cli/main.py --name aico`
    - Produces `aico.exe` (Windows), `aico` (Linux/macOS)
    - Test on all platforms for startup speed and compatibility
3. **Distribution:**
    - Distribute the single executable via release, package manager, or installer
    - No Python or .venv required on user system

## Security Considerations

- CLI commands requiring elevated privileges (e.g., user management) prompt for authentication as needed
- All remote operations are encrypted (HTTPS, ZeroMQ with CURVE, etc.)
- CLI never stores credentials in plaintext

## Future-Proofing & Extensibility

- Modular command loading for plugin/extension support
- Easy to add new commands as backend expands
- Consistent with AICO's local-first, privacy-preserving philosophy

## Best Practices for CLI Speed & Responsiveness

- **Minimize startup imports:** Import heavy libraries only inside functions/commands, not at the top-level.
- **Lazy-load features:** Only load modules and data when a command is actually invoked.
- **Avoid unnecessary I/O:** Defer config, network, or database access until needed.
- **Keep main() lightweight:** The entrypoint should do as little as possible before dispatching to commands.
- **Profile regularly:** Use timing tools to identify and fix slow paths.
- **Batch backend/API calls:** Where possible, reduce round-trips and use bulk operations.
- **Cache where safe:** Cache static or infrequently changing data in memory for the session.
- **Test on all platforms:** Verify speed and behavior on Windows, macOS, and Linux.


- [Typer documentation](https://typer.tiangolo.com/)
- [Rich documentation](https://rich.readthedocs.io/)
- [PyInstaller documentation](https://pyinstaller.org/)

---

AICO's CLI combines the power of Python's ecosystem with best-in-class UX, delivering a tool worthy of modern, privacy-first, AI-powered systems.
