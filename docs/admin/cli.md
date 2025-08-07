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

> **Permanent CLI UX Policy:**
> 
> All CLI commands and command groups must provide actionable, friendly, and instructive feedback when invoked incorrectly or incompletely. The CLI must never:
> - Show only an aggressive error message
> - Require the user to consult help and then retry
> - Leave the user without a clear next step
>
> Instead, every CLI entrypoint must print helpful guidance, usage examples, and (where possible) a preview of the result. This is a strict and permanent requirement for all CLI development in AICO.

## Visual Style Guide

### Design Philosophy

The AICO CLI follows a **modern, minimal, clean** aesthetic that prioritizes:
- **Readability** over decoration
- **Consistency** across all commands
- **Professional appearance** suitable for enterprise environments
- **Accessibility** across different terminals and color schemes

### Color Palette

**Primary Colors:**
- **Cyan (`[bold cyan]`)**: Brand color for titles, headers, and AICO branding
- **Yellow (`[bold yellow]`)**: Table headers and section labels
- **Green (`[green]`, `[bold green]`)**: Success states, version numbers, positive values
- **Red (`[red]`)**: Errors, warnings, missing values
- **White (`[bold white]`)**: Primary content, subsystem names
- **Dim (`[dim]`)**: Secondary information, examples, help text

**Usage Guidelines:**
```python
# Titles and branding
console.print("✨ [bold cyan]AICO System Versions[/bold cyan]")

# Table headers
header_style="bold yellow"

# Success/positive values
v = f"[bold green]{version}[/bold green]"

# Errors
console.print(f"❌ [red]Error message[/red]")

# Secondary info
console.print("[dim]Use 'aico COMMAND --help' for more information.[/dim]")
```

### Typography & Formatting

**Text Hierarchy:**
1. **Titles**: `[bold cyan]` with optional sparkle emoji (✨)
2. **Headers**: `[bold yellow]` for section headers and table columns
3. **Content**: `[bold white]` for primary data, `[green]` for values
4. **Help Text**: `[dim]` for examples and guidance

**Spacing Rules:**
- Always add blank lines before and after tables/panels
- Use `console.rule()` for section dividers in complex output
- Consistent padding in tables: `padding=(0, 1)`

### Table Styling

**Standard Table Configuration:**
```python
table = Table(
    title="✨ [bold cyan]Title Here[/bold cyan]",
    title_style="bold cyan",
    border_style="bright_blue",
    header_style="bold yellow",
    show_lines=False,
    box=box.SIMPLE_HEAD,
    padding=(0, 1)
)
```

**Critical Rules:**
- **NO EMOJIS IN TABLE DATA**: Emojis break column alignment across terminals
- **Use `box.SIMPLE_HEAD`**: Clean, minimal borders that align properly
- **Left-align all columns**: `justify="left"` for consistency
- **Consistent column styling**: `style="bold white"` for labels, `style="green"` for values

### Icons & Symbols

**Approved Icons:**
- ✨ Sparkle: Titles and branding
- ❌ Cross: Errors and failures
- 📦 Package: Generic items (fallback only)
- ⚡ Lightning: CLI/command line tools (in panels only)
- 🤖 Robot: AI/backend services (in panels only)
- 🖥️ Monitor: UI/frontend (in panels only)
- ⚙️ Gear: Configuration/admin (in panels only)

**Icon Usage Rules:**
- **Tables**: NO icons in table data (alignment issues)
- **Panels**: Icons OK for single-item displays
- **Titles**: Sparkle (✨) only
- **Errors**: Cross (❌) with red text

### Panel Styling

**For single-item displays:**
```python
panel = Panel(
    f"{icon} [bold white]{item}[/bold white]\n[bold green]{value}[/bold green]",
    title="[bold cyan]Title[/bold cyan]",
    border_style="bright_blue",
    box=box.ROUNDED,
    padding=(1, 2)
)
```

### Layout Patterns

**Root CLI Help:**
```python
console.print("\n✨ [bold cyan]AICO CLI[/bold cyan]")
console.print("[dim]Description here[/dim]\n")
console.rule("[bold blue]Section Name", style="blue")
console.print("\n📦 [green]command[/green]   Description")
```

**Command Group Help:**
- Use Typer's built-in help system with comprehensive help strings
- Include examples and usage guidance in help text
- Show help automatically when no subcommand given (not errors)

### Implementation Guidelines for Developers

1. **Always use the approved color palette** - no custom colors
2. **Never put emojis in table data** - breaks alignment
3. **Use `box.SIMPLE_HEAD` for all tables** - consistent, clean appearance
4. **Include sparkle (✨) in main titles** - brand consistency
5. **Left-align all table columns** - professional appearance
6. **Add spacing around tables/panels** - breathing room
7. **Use `[dim]` for help text** - visual hierarchy

### Anti-Patterns (DO NOT USE)

❌ **Emojis in table rows** (breaks alignment)  
❌ **Center-aligned table columns** (inconsistent)  
❌ **Rounded table borders** (alignment issues)  
❌ **Custom colors outside palette** (inconsistent branding)  
❌ **Missing spacing around tables** (cramped appearance)  
❌ **Aggressive error messages** (violates UX policy)  
❌ **Complex box styles** (maintenance burden)  

This style guide ensures all CLI commands maintain the same professional, clean, minimal aesthetic that users expect from the AICO system.


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

---

## Security Command Group (`aico security`)

The `security` command group provides secure, unified management of cryptographic keys, master passwords, and encrypted filesystem operations for AICO. It enables administrators and power users to set up, audit, and operate all foundational security features from the CLI.

### Command Structure

```
aico security [COMMAND] [OPTIONS]

Commands:
  key         Master password and key management
  fs          Encrypted filesystem operations (securefs)
  audit       Security audit and health checks
```

### Subcommand Details

#### `aico security key`
| Command                        | Description                                             |
|------------------------------- |---------------------------------------------------------|
| `init`                         | Set up master password and initialize key storage        |
| `status`                       | Show key status and active authentication method         |
| `change-password`              | Change the master password                              |
| `clear`                        | Remove all stored keys and authentication state          |

#### `aico security fs`
| Command                        | Description                                             |
|------------------------------- |---------------------------------------------------------|
| `init`                         | Initialize a new encrypted data directory (securefs)    |
| `mount`                        | Mount an encrypted directory                            |
| `unmount`                      | Unmount an encrypted directory                          |
| `status`                       | Show status of encrypted mounts                         |

#### `aico security audit`
| Command                        | Description                                             |
|------------------------------- |---------------------------------------------------------|
| `log`                          | Show recent security events and audit log               |
| `check`                        | Run security health checks and report findings          |

### Usage Examples

- Initialize master password and keys:
  ```sh
  aico security key init
  ```
- Mount encrypted data directory:
  ```sh
  aico security fs mount --dir ~/.aico/data.enc
  ```
- Check key status:
  ```sh
  aico security key status
  ```
- Run security audit check:
  ```sh
  aico security audit check
  ```

### Design Principles
- All commands provide clear, actionable, and colorized output.
- Sensitive operations require confirmation or a `--yes` flag.
- CLI never stores credentials in plaintext; all keys are protected using platform-native secure storage.
- Filesystem encryption is implemented using SecureFS (system dependency; see requirements).
- Incomplete or ambiguous commands trigger predictive help text.

### Notes
- `SecureFS` must be installed on the system (see [installation guide](https://github.com/netheril96/securefs)).
- `SecureFS CLI` is used for encrypted filesystem operations.
- Key management is handled by the shared library (`AICOKeyManager`).
- Audit logs and health checks are extensible for future compliance needs.

---
