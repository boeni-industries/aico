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
- **PyPI Distribution** (primary):
    - Professional Python package distribution via `pip`, `pipx`, or `uv tool install`.
    - Fast startup (~0.2s vs 7.3s PyInstaller overhead).
    - Requires Python 3.9+ on target system.
    - Cross-platform: identical installation and usage on Windows, macOS, Linux.
- **PyInstaller** (legacy):
    - Single-file executable approach (deprecated due to slow startup).
    - Kept for reference but no longer recommended.

## Integration Approach

- **Backend Integration:**
    - CLI imports and reuses backend Python modules for admin logic where possible (e.g., user management, diagnostics, data migration).
    - For remote administration, CLI communicates with backend via REST API or ZeroMQ, using shared schemas and models.
    - All business logic is implemented in backend modules, not duplicated in CLI code.
- **Frontend/UI Integration:**
    - CLI may offer commands to launch or interact with the admin UI (e.g., `aico admin open`), but does not duplicate UI logic.
    - Main CLI use cases are backend/admin-focused.

## Command Structure

```
aico [command] [options]
```

Each command is implemented as a Typer sub-app with Rich output formatting.

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
    title_justify="left",
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

### Architecture

- **Modular Design**: Each command group is a separate Typer sub-app
- **Shared Infrastructure**: Common utilities for authentication, configuration, and output
- **Extensible**: New command groups can be easily added as the system grows

---

## UX & Output Standards

- **Instant startup** (<100ms typical)
- **Colorful, readable output** with Unicode, emoji, and clear formatting
- **Progress bars** for long-running tasks
- **Context-aware help** and autocompletion
- **Graceful error handling** and actionable messages
- **Consistent cross-platform behavior**

## Distribution

**Primary**: PyPI package via `uv tool install aico-cli` or `pipx install aico-cli`
**Legacy**: PyInstaller executable (deprecated due to slow startup)

## Security Considerations

- CLI commands requiring elevated privileges (e.g., user management) prompt for authentication as needed
- All remote operations are encrypted (HTTPS, ZeroMQ with CURVE, etc.)
- CLI never stores credentials in plaintext

## Future-Proofing & Extensibility

- Modular command loading for plugin/extension support
- Easy to add new commands as backend expands
- Consistent with AICO's local-first, privacy-preserving philosophy

## Performance Optimization

- **Lazy imports**: Heavy libraries loaded only when needed
- **Minimal startup**: Lightweight entrypoint with deferred initialization
- **Session caching**: Reduces authentication overhead
- **Cross-platform testing**: Consistent performance across all platforms


- [Typer documentation](https://typer.tiangolo.com/)
- [Rich documentation](https://rich.readthedocs.io/)
- [PyInstaller documentation](https://pyinstaller.org/)

---

AICO's CLI combines the power of Python's ecosystem with best-in-class UX, delivering a tool worthy of modern, privacy-first, AI-powered systems.

---

## Available Commands

The AICO CLI provides the following command groups:

### Core System Commands
- **`aico version`** - Version management and synchronization
- **`aico security`** - Master password and security operations
- **`aico db`** - Database management and operations
- **`aico config`** - Configuration management
- **`aico logs`** - Log management and analysis

### Service Management Commands
- **`aico gateway`** - API Gateway management
- **`aico scheduler`** - Task scheduler management
- **`aico modelservice`** - Model service management
- **`aico ollama`** - Ollama model management
- **`aico bus`** - Message bus testing and monitoring

### Development Commands
- **`aico dev`** - Development utilities and cleanup tools

### Command Architecture

**Security Model**: Commands use decorator-based security classification:
- `@sensitive` - Requires fresh authentication (password changes, data export)
- `@destructive` - Requires fresh authentication (database operations with data loss risk)
- Regular commands use session-based authentication with 30-minute timeout

**Integration**: All commands share common infrastructure:
- `AICOKeyManager` for unified security and encryption
- `ConfigurationManager` for cross-platform configuration
- Rich console output with consistent styling
- Session-based authentication with secure keyring storage

**For detailed usage examples and workflows, see the CLI Reference documentation (file does not exist).**

## Performance Characteristics

The AICO CLI is optimized for fast startup and responsive operation:

- **Startup time**: ~0.2s (compared to 7.3s with legacy PyInstaller)
- **Cross-platform consistency**: Identical performance on Windows, macOS, and Linux
- **Memory footprint**: Minimal - only loads required dependencies per command
- **Development workflow**: Instant code changes with editable installation

---
