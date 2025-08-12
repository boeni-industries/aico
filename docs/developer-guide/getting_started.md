# Developer Onboarding: Getting Started with AICO

This guide is for developers and contributors. For general usage, installation, or user onboarding, see the User Guide (file does not exist).

Here you'll find everything you need to set up your development environment, understand the project structure, and start contributing.

---

## Project Overview

AICO is an open-source, local-first AI companion designed to be emotionally present, embodied, and proactive. The project is modular, privacy-first, and extensible, with contributions welcome from developers, designers, researchers, and more.

---

## Contributing

See [`contributing.md`](./contributing.md) for ways to get involved, contribution etiquette, and project values.

**Highlights:**
- All skillsets welcome (development, design, research, writing, testing, etc.)
- Small, atomic commits and clear PRs
- Respectful, constructive code reviews

---

## Repository Structure

The AICO repository is organized as a polyglot monorepo, with each major component in its own directory:

```
aico/
│
├── backend/           # Python FastAPI backend (TBD)
│
├── frontend/          # Flutter UI app (TBD)
│
├── studio/            # React-based "Studio" for devs, power users, admins (TBD)
│
├── cli/               # Python Typer/Rich CLI (TBD)
│
├── proto/             # Protocol Buffers and shared API schemas
│
├── docs/              # Documentation (architecture, guidelines, etc.)
│
├── site/              # Built documentation/static site output (generated)
│
├── .github/           # GitHub workflows, issue templates, etc.
├── .git/              # Git repo metadata
├── .nojekyll          # Prevents GitHub Pages processing
├── LICENSE
├── README.md
├── mkdocs.yml         # MkDocs config for docs
└── ... (future: scripts/, Makefile, etc.)
```

**Key Points:**
- Each main component (backend, frontend, studio, cli) is isolated with its own dependencies and tooling.
- `proto/` contains Protocol Buffer definitions for cross-component communication.
- `docs/` holds all documentation, including architecture and development guides.
- `site/` is generated from `docs/` for static site hosting.

---

## Development Principles

AICO follows strict guidelines for code quality, modularity, privacy, and extensibility. See [`guidelines.md`](./guidelines.md) for details.

**Highlights:**
- Simplicity and readability first
- Modular, message-driven architecture
- Privacy & security by design
- Local-first, file-based databases
- Extensible via plugins and clear interfaces

---

## Setting Up Your Environment

Follow these steps to get started with AICO development:

### 1. Clone or Fork the Repository
**Core team:**
  ```sh
  git clone git@github.com:boeni-industries/aico.git
  ```
**Contributors:**

- Fork the repository on GitHub.
- Clone your fork

```sh
git clone git@github.com:<your-username>/aico.git
```

### 2. Install Python 3.13.5
AICO requires Python 3.13.5 for all Python-based components. Download and install it from the official Python website:

- [Python 3.13.5 downloads](https://www.python.org/downloads/release/python-3135/)

After installation, verify with:
```sh
python --version
# or
py --version
```
You should see `Python 3.13.5`.

> **ℹ️ Data Encryption Approach**
> 
> AICO uses application-level encryption with database-native features (SQLCipher, DuckDB encryption, RocksDB EncryptedEnv) rather than filesystem-level encryption. This provides better cross-platform compatibility and performance without requiring additional system dependencies.

### 3. Python Dependency Management with Modern Tools
AICO uses modern Python packaging with `pyproject.toml` files for dependency management. Each component (CLI, backend, shared) uses `pyproject.toml` for clean, standardized dependency declarations.

**Install UV globally (recommended):**

  ```sh
  pip install uv
  # or follow: https://github.com/astral-sh/uv#installation
  ```

**CLI:**

  **Windows PowerShell**
  ```powershell
  cd cli
  py -3.13 -m venv .venv
  .venv\Scripts\Activate.ps1
  uv pip install -e .[dev]
  aico --help
  ```

  **Windows Cmd**
  ```cmd
  cd cli
  py -3.13 -m venv .venv
  .venv\Scripts\activate.bat
  uv pip install -e .[dev]
  aico --help
  ```

  **Git Bash/WSL/Linux/macOS:**
  ```sh
  cd cli
  python3.13 -m venv .venv
  source .venv/bin/activate
  uv pip install -e .[dev]
  aico --help
  ```

**Backend:**

  **Windows PowerShell**
  ```powershell
  cd backend
  py -3.13 -m venv .venv
  .venv\Scripts\Activate.ps1
  uv pip install -e .
  uvicorn main:app --reload --port 8700
  ```

  **Windows Cmd**
  ```cmd
  cd backend
  py -3.13 -m venv .venv
  .venv\Scripts\activate.bat
  uv pip install -e .
  uvicorn main:app --reload --port 8700
  ```

  **Git Bash/WSL/Linux/macOS:**
  ```sh
  cd backend
  python3.13 -m venv .venv
  source .venv/bin/activate
  uv pip install -e .
  uvicorn main:app --reload --port 8700
  ```

> **Tip:** Each Python component uses its own `.venv` and `pyproject.toml`. Always activate the correct environment before installing or running anything. In VS Code or Windsurf, select the correct Python interpreter from `.venv` for best experience.
> 
> **Shared Library:** The `/shared` directory contains common functionality used by both CLI and backend. It's automatically included as an editable dependency when you install with `[dev]` extras for CLI or directly for backend.
> 
> **Adding Dependencies:** Edit the respective `pyproject.toml` file and run `uv pip install -e .` to update your environment.

!!! warning
    Only one Python virtual environment can be active per terminal session. If you need to work with both the CLI and backend at the same time, open separate terminal windows and activate the appropriate environment in each. Changing directories does not automatically switch the active environment—you must activate it explicitly.

---

### 6. Setting Up the Flutter Frontend

The flutter project scaffolding is present in `/frontend`.

**Install Flutter:**

- Download and install Flutter from the [official site](https://docs.flutter.dev/get-started/install) for your platform (Windows, macOS, Linux).
- After installation, check your version (we recommend Flutter 3.19+):
```sh
flutter --version
```

**Set up platform dependencies:**

  - For Android: Install Android Studio and set up the Android SDK.
  - For iOS (macOS only): Install Xcode and set up the iOS toolchain.
  - For web/desktop: Follow [Flutter platform setup instructions](https://docs.flutter.dev/get-started/web) as needed.

**Install dependencies:**

  ```sh
  cd frontend
  flutter pub get
  ```

**Run the app:**
  ```sh
  flutter run
  ```
**.gitignore:** is already configured to exclude build artifacts.

!!! note "Tip"
    Use VS Code, Android Studio, or Windsurf with the Flutter/Dart plugins for the best development experience.

---

### 7. Setting Up the React Admin Studio

All React/React-Admin code and dependencies found in `/studio`.

**Install Node.js & npm:**

  - Download and install the latest LTS version of Node.js from [nodejs.org](https://nodejs.org/). npm is included.
  - After installation, check your versions (we recommend Node.js 22.x+ and npm 11.x+):

```sh
node --version
npm --version
```

**Install dependencies:**
  ```sh
  cd studio
  npm install
  ```

**Run the app:**
  ```sh
  npm start
  # Visit http://localhost:3000
  ```

**.gitignore:** Already configured to exclude build artifacts and `node_modules`.

> **Tip:**
> Use VS Code,  **Windows PowerShell**
  ```powershell
  cd studio
  npm install
  npm start
  # Visit http://localhost:3000
  ```

  **Windows Cmd**
  ```cmd
  cd studio
  npm install
  npm start
  REM Visit http://localhost:3000
  ```

  **macOS/Linux**
  ```sh
  cd studio
  npm install
  npm start
  # Visit http://localhost:3000
  ```

---

## Building and Running Components

Below are the build and run commands for each major part of the system. Substitute your platform (Windows, macOS, Linux) as appropriate.

### Backend (Python FastAPI)

- **Windows (PowerShell):**
  ```sh
  cd backend
  .venv\Scripts\Activate.ps1
  uv pip install -e .
  uvicorn main:app --reload --port 8700
  # Visit http://127.0.0.1:8700
  ```
- **Windows (Cmd):**
  ```sh
  cd backend
  .venv\Scripts\activate.bat
  uv pip install -e .
  uvicorn main:app --reload --port 8700
  ```
- **Git Bash/WSL/Linux/macOS:**
  ```sh
  cd backend
  source .venv/bin/activate
  uv pip install -e .
  uvicorn main:app --reload --port 8700
  ```

### CLI (Python CLI)

#### Run the CLI in development
- **All platforms:**
  ```sh
  cd cli
  # Activate venv (see above)
  uv pip install -e .[dev]
  python aico_main.py
  ```

#### Build the CLI executable (PyInstaller)
- **All platforms:**
  ```sh
  cd cli
  # Activate venv (see above)
  uv pip install -e .[dev]
  pyinstaller aico_main.py --onefile --name aico
  # Executable will be in dist/aico(.exe)
  ```

#### Run the built executable
- **Windows:**
  ```sh
  dist\aico.exe
  ```
- **Linux/macOS:**
  ```sh
  ./dist/aico
  ```

### Frontend (Flutter)

- **All platforms:**
  ```sh
  cd frontend
  flutter run
  ```
  - For desktop: `flutter run -d windows` (Windows), `-d macos` (macOS), `-d linux` (Linux)
  - For web: `flutter run -d chrome`
  - For mobile: Use `flutter devices` to list and select your target

### Studio (React Admin UI)

- **All platforms:**
  ```sh
  cd studio
  npm start
  ```
  - Open [http://localhost:3000](http://localhost:3000) in your browser if it does not open automatically.

---

## Maintainer Note: Dependency Management and Project Scaffolding

!!! warning 
    This section is for maintainers only. Regular contributors do NOT need to run these commands. The following steps were performed during initial project setup and are preserved for reference.

#### Python Dependency Management
- **Previous approach:** Each Python component (`cli/`, `backend/`) used its own `pyproject.toml` (PEP 621/Poetry) for dependencies and metadata. Poetry was used for dependency management and packaging. This was replaced due to friction, IDE integration issues, and version pinning complexity.
- **Current approach:** Each Python component (`cli/`, `backend/`, `shared/`) now uses modern `pyproject.toml` files for dependency management. [UV](https://github.com/astral-sh/uv) is used for ultra-fast dependency installs. This approach follows modern Python packaging standards and is simpler for contributors.

- Add dependencies by editing the respective `pyproject.toml` file and running `uv pip install -e .` to update your environment.
- The supported Python version is pinned to `>=3.13,<3.15` due to PyInstaller compatibility. Update this restriction only after verifying all key dependencies support newer Python versions.
- Use `uv pip install <package>` to add dependencies and `uv pip freeze > requirements.txt` to refresh lockfiles.
- PyInstaller is included as a CLI dependency for building distributable executables.
- If switching to a different dependency manager in the future, update this section and docs accordingly.

#### Flutter Frontend Project Creation
```sh
flutter create frontend --project-name aico_ui --platforms=windows,macos,linux,android,ios,web
```

#### React Admin Studio Project Creation
```sh
npx create-react-app studio --template typescript
cd studio
npm install react-admin ra-data-simple-rest @mui/material @mui/icons-material @emotion/react @emotion/styled react-router-dom
```

---

## Database Setup

AICO uses encrypted databases for all data storage with security by design. The setup process automatically handles directory creation, security initialization, and database configuration.

### Quick Setup (Recommended)

```bash
# 1. Initialize AICO configuration directories
aico config init

# 2. Initialize encrypted database (auto-setup security if needed)
aico db init

# 3. Verify complete setup
aico config show
aico db show
```

### Step-by-Step Process

#### 1. Configuration Directory Setup
```bash
# Initialize all AICO directories (data, config, cache, logs)
aico config init

# Verify directory structure
aico config show
```

#### 2. Database Initialization
```bash
# Create encrypted libSQL database with automatic security setup
aico db init

# Test database connection and encryption
aico db test

# View database configuration and paths
aico db show
```

**Note**: The `aico db init` command automatically sets up master password security if not already configured, eliminating the need for separate `aico security setup` step.

### Directory Structure
After setup, you'll have cross-platform directories:
```
# Windows Example: %APPDATA%/aico/
# macOS Example: ~/Library/Application Support/aico/
# Linux Example: ~/.local/share/aico/
aico/
├── data/
│   ├── aico.db              # Main libSQL database (encrypted)
│   ├── aico.db.salt         # Encryption salt
│   ├── analytics.duckdb     # Analytics database (encrypted)
│   └── chroma/              # Vector database directory (encrypted)
├── config/
│   ├── defaults/            # Default configuration files
│   └── environments/        # Environment-specific overrides
├── cache/                   # Application cache
└── logs/                    # Application logs
```

### Configuration Management
AICO uses a hierarchical configuration system with externalized settings:

```bash
# View all configuration paths and settings
aico config show

# View database-specific configuration
aico db show

# Get specific configuration values
aico config get database.libsql.journal_mode
aico config get system.paths.directory_mode
```

### Troubleshooting

**Setup issues:**
```bash
aico config show       # Check directory structure
aico db show          # Check database configuration
```

**Database connection fails:**
```bash
aico db status        # Check database status
aico db test          # Test database connection
```

**Security/encryption issues:**
```bash
aico security status  # Check security setup
aico security test    # Verify keyring access
```

For detailed architecture and configuration options, see [Data Layer Documentation](../architecture/data_layer.md).

---

## Further Reading

- [Contributing](./contributing.md)
- [Architecture Overview](../architecture/architecture_overview.md)
- Modules & Components (file does not exist)
- [Developer Guidelines & Conventions](./guidelines.md)
- [Plugin System Overview](../architecture/plugin_system.md)
- [Data Layer & Storage](../architecture/data_layer.md)
- [Admin UI Architecture](../admin/admin_ui_master.md)
- [Protocol Buffers & API Contracts](./protobuf.md)
- [Privacy & Security](../security/security_overview.md)

---

> This document is a living guide and will be updated as the project grows. If you have suggestions, please open an issue or PR!
