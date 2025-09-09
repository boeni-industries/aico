# AICO Changelog Automation Concept

## Overview

Simple, cross-platform changelog automation for AICO's multi-subsystem architecture using Conventional Commits and git-cliff. Zero maintenance, maximum automation, perfect CLI integration.

## Design Principles

- **KISS**: Configuration-driven, no custom scripts
- **Cross-platform**: Works on macOS, Windows, Linux
- **CLI Integration**: Extends existing `aico version` commands
- **Zero Maintenance**: Automated generation with manual curation option
- **Publication Ready**: Multiple output formats for different audiences

## Architecture

### Tool Stack

**Primary Tool**: `git-cliff` (Rust-based)
- Cross-platform binary (Windows, macOS, Linux)
- Configuration-driven (no scripting)
- High performance for large repositories
- Built-in subsystem support via scopes

**Commit Standard**: Conventional Commits
- Industry standard (used by Angular, Vue, React)
- Machine parseable
- Human readable
- Supports scoping for subsystems

**Validation**: `commitlint` with pre-commit hooks
- Enforces commit format consistency
- Cross-platform Node.js tool
- Integrates with existing git workflows

### File Structure

```
/
├── CHANGELOG.md                    # Unified project changelog
├── changelogs/
│   ├── shared/CHANGELOG.md        # Shared library changes
│   ├── cli/CHANGELOG.md           # CLI changes
│   ├── backend/CHANGELOG.md       # Backend changes
│   ├── frontend/CHANGELOG.md      # Frontend changes
│   ├── studio/CHANGELOG.md        # Studio changes
│   ├── modelservice/CHANGELOG.md  # Model service changes
│   └── templates/
│       ├── user.md               # User-facing template
│       └── technical.md          # Developer template
├── .cliff.toml                   # git-cliff configuration
├── .commitlintrc.json            # Commit validation rules
└── .gitmessage                   # Commit template
```

## Conventional Commits for AICO

### Commit Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Subsystem Scopes

All AICO subsystems:
- `shared` - Shared libraries and core functionality
- `cli` - Command-line interface
- `backend` - Backend services and APIs
- `frontend` - Flutter frontend application
- `studio` - Studio development environment
- `modelservice` - AI model service

### Examples

```bash
feat(backend): add conversation export API
fix(frontend): resolve avatar animation glitch
docs(shared): update encryption documentation
perf(cli): optimize version sync performance
feat(modelservice): add Claude 3.5 support
chore(ci): update deployment pipeline

# Cross-subsystem changes
feat(backend,frontend): implement real-time typing indicators
fix(cli,backend): resolve authentication token sync issue

# Breaking changes
feat(backend)!: redesign message bus API
feat!: migrate to new configuration format
```

### Type Mapping

| Commit Type | Changelog Section | Description |
|-------------|------------------|-------------|
| `feat` | 🚀 Added | New features |
| `fix` | 🐛 Fixed | Bug fixes |
| `perf` | ⚡ Changed | Performance improvements |
| `refactor` | 🔨 Changed | Code refactoring |
| `docs` | 📚 Documentation | Documentation changes |
| `style` | (excluded) | Code style changes |
| `test` | (excluded) | Test additions/changes |
| `chore` | (excluded) | Maintenance tasks |
| `BREAKING CHANGE` | ⚠️ Breaking Changes | Breaking changes |
| `security` | 🛡️ Security | Security fixes |

## CLI Integration

Extend existing `aico version` command group:

```bash
# Generate changelogs
aico version changelog generate [subsystem]     # Generate for subsystem or all
aico version changelog preview [subsystem]      # Preview without writing
aico version changelog edit [subsystem]         # Open in editor for curation

# Enhanced bump with changelog
aico version bump backend patch --changelog     # Auto-generate changelog entry
aico version bump --all minor --changelog       # Bump all with unified changelog

# Validation
aico version changelog validate                 # Check commit format compliance
aico version changelog setup                    # Install commit hooks and templates
```

### Implementation in version.py

Add new command group:

```python
@app.group(help="Manage changelogs for AICO subsystems")
def changelog():
    """Changelog management commands."""
    pass

@changelog.command()
def generate(
    subsystem: str = typer.Argument(None, help="Subsystem (shared/cli/backend/frontend/studio/modelservice/all)"),
    output: str = typer.Option("changelogs", "--output", help="Output directory"),
    format: str = typer.Option("technical", "--format", help="Format: user, technical"),
    unreleased: bool = typer.Option(False, "--unreleased", help="Include unreleased changes")
):
    """Generate changelog using git-cliff."""
    # Call git-cliff with appropriate config
    pass

@changelog.command()
def setup():
    """Install commit message templates and validation hooks."""
    # Install commitlint, git hooks, and templates
    pass
```

## Configuration

### .cliff.toml (git-cliff configuration)

```toml
[changelog]
header = """
# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""

body = """
{% if version %}\
## [{{ version | trim_start_matches(pat="v") }}] - {{ timestamp | date(format="%Y-%m-%d") }}
{% else %}\
## [Unreleased]
{% endif %}\
{% for group, commits in commits | group_by(attribute="group") %}
### {{ group | striptags | trim | upper_first }}
{% for commit in commits %}
- {% if commit.scope %}**{{ commit.scope }}**: {% endif %}\
{{ commit.message | upper_first }}\
{% if commit.links %} ([{{ commit.id | truncate(length=7, end="") }}]({{ commit.links[0] }})){% endif %}
{% endfor %}
{% endfor %}\n
"""

[git]
conventional_commits = true
filter_unconventional = true
commit_parsers = [
    { message = "^feat", group = "🚀 Added"},
    { message = "^fix", group = "🐛 Fixed"},
    { message = "^perf", group = "⚡ Changed"},
    { message = "^refactor", group = "🔨 Changed"},
    { message = "^docs", group = "📚 Documentation"},
    { message = "^style", skip = true},
    { message = "^test", skip = true},
    { message = "^chore", skip = true},
    { body = ".*security", group = "🛡️ Security"},
    { message = ".*breaking.*", group = "⚠️ Breaking Changes"},
]

# AICO version tags pattern
tag_pattern = "aico-.*-v[0-9]*"
```

### .commitlintrc.json (commit validation)

```json
{
  "extends": ["@commitlint/config-conventional"],
  "rules": {
    "scope-enum": [2, "always", [
      "shared", "cli", "backend", "frontend", "studio", "modelservice",
      "ci", "deps", "release"
    ]],
    "scope-case": [2, "always", "lower-case"],
    "subject-case": [2, "always", "lower-case"],
    "subject-max-length": [2, "always", 72]
  }
}
```

### .gitmessage (commit template)

```
# <type>(<scope>): <subject>
#
# <body>
#
# <footer>

# Types: feat, fix, docs, style, refactor, perf, test, chore
# Scopes: shared, cli, backend, frontend, studio, modelservice
# 
# Examples:
# feat(backend): add conversation export API
# fix(frontend): resolve avatar animation glitch
# docs(shared): update encryption documentation
# feat(backend,frontend): implement real-time typing
# feat(backend)!: redesign message bus API
```

## Workflow

### Development

1. **Commit with conventional format**:
   ```bash
   git commit -m "feat(backend): add biometric authentication"
   ```

2. **Pre-commit hook validates format** automatically

3. **Changes accumulate** in git history with proper categorization

### Release

1. **Generate changelog**:
   ```bash
   aico version changelog generate backend
   ```

2. **Review and edit** if needed:
   ```bash
   aico version changelog edit backend
   ```

3. **Bump version with changelog**:
   ```bash
   aico version bump backend minor --changelog
   ```

4. **Changelog automatically included** in:
   - Git tag annotation
   - GitHub release notes
   - Documentation site updates

## Cross-Platform Considerations

### Tool Installation

**git-cliff**: Single binary download for each platform
- macOS: `brew install git-cliff` or direct download
- Windows: `winget install git-cliff` or direct download  
- Linux: Package managers or direct download

**commitlint**: Node.js based (cross-platform)
- `npm install -g @commitlint/cli @commitlint/config-conventional`

**Integration**: CLI automatically detects and uses available tools

### File Paths

- Use `pathlib.Path` for cross-platform path handling
- Git hooks work identically across platforms
- Configuration files use forward slashes (Git standard)

## Implementation Plan

### Phase 1: Core Setup (Week 1)
- [ ] Install git-cliff and commitlint
- [ ] Create .cliff.toml configuration
- [ ] Set up commit message validation
- [ ] Create commit message templates

### Phase 2: CLI Integration (Week 1)
- [ ] Extend `aico version` with changelog commands
- [ ] Implement `generate`, `preview`, `edit` commands
- [ ] Add `--changelog` flag to bump command
- [ ] Test cross-platform functionality

### Phase 3: Automation (Week 1)
- [ ] Set up pre-commit hooks
- [ ] Configure GitHub Actions integration
- [ ] Test with sample releases
- [ ] Document workflow for team

### Phase 4: Migration (Week 1)
- [ ] Generate initial changelogs from git history
- [ ] Migrate existing CHANGELOG.md format
- [ ] Train team on conventional commits
- [ ] Establish publication workflow

## Benefits

✅ **Simple**: Configuration-driven, no custom scripts
✅ **Cross-platform**: Works on all development environments  
✅ **Automated**: Generates changelogs from commit history
✅ **Integrated**: Extends existing CLI naturally
✅ **Publication-ready**: Multiple formats for different audiences
✅ **Zero maintenance**: Tools handle complexity automatically
✅ **Industry standard**: Uses widely adopted conventions
✅ **All subsystems**: Covers shared, cli, backend, frontend, studio, modelservice

## Success Metrics

- **Zero manual changelog maintenance** for routine changes
- **100% automation** for version bump + changelog generation
- **Cross-platform compatibility** verified on macOS, Windows, Linux
- **Team adoption** of conventional commits within 2 weeks
- **Publication ready** changelogs for GitHub releases and docs
