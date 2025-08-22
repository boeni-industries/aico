# Developer Onboarding: Getting Started with AICO

This guide is for developers and contributors. For general usage, installation, or user onboarding, see the User Guide (file does not exist).

Here you'll find everything you need to set up your development environment, understand the project structure, and start contributing.

---

## Project Overview

AICO is an open-source, local-first AI companion designed to be emotionally present, embodied, and proactive. The project is modular, privacy-first, and extensible, with contributions welcome from developers, designers, researchers, and more.

### Quick Install (End Users)

For end users who just want to use the CLI:

```bash
pip install aico[cli]
aico --help
```

This installs the AICO CLI with all necessary dependencies. For development setup, continue reading below.

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

### 3. UV Workspace Setup (Single Virtual Environment)
AICO uses UV workspace management with a unified `pyproject.toml` at the root and a single shared virtual environment for all Python components.

**Install UV globally (required):**

  ```sh
  pip install uv
  # or follow: https://github.com/astral-sh/uv#installation
  ```

**Initial Setup:**

  ```sh
  # Clone and navigate to project root
  cd aico

  # Initialize UV workspace with all optional dependencies
  uv sync --extra cli --extra backend --extra test

  # Verify installation
  uv run aico --help
  uv run python -c "import fastapi; print('Backend deps ready')"
  ```

**Key Changes from Previous Setup:**
- **Single `.venv`** at project root instead of per-component environments
- **Unified `pyproject.toml`** with optional dependency groups (`cli`, `backend`, `test`)
- **UV workspace commands** replace manual venv activation
- **Shared dependencies** automatically resolved across all components

**Working with the Workspace:**

  ```sh
  # Run CLI commands
  uv run aico gateway status
  uv run aico db init

  # Run backend server
  uv run python backend/main.py
  # or with uvicorn
  uv run uvicorn backend.main:app --reload --port 8700

  # Install additional dependencies
  uv add requests  # adds to core dependencies
  uv add --group cli typer-cli  # adds to CLI group
  uv add --group backend fastapi-users  # adds to backend group

  # Sync after pyproject.toml changes
  uv sync
  ```

> **Benefits of UV Workspace:**
> - Single environment eliminates activation/deactivation complexity
> - Consistent dependency resolution across all components
> - Faster installs and better caching
> - Simplified IDE configuration (one Python interpreter)
> - Automatic shared library integration

> **IDE Setup:** Point your IDE to the `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Unix) in the project root.

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

**Install Coverage Tools:**

For generating HTML coverage reports across all subsystems:
```sh
npm install -g @lcov-viewer/cli
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
> Use VS Code with React/TypeScript extensions for the best development experience.

---

## Building and Running Components

Below are the build and run commands for each major part of the system. Substitute your platform (Windows, macOS, Linux) as appropriate.

### Backend (Python FastAPI)

- **All platforms (UV workspace):**
  ```sh
  # From project root
  uv run python backend/main.py
  # or with uvicorn
  uv run uvicorn backend.main:app --reload --port 8700
  # Visit http://127.0.0.1:8700
  ```

### CLI (Python CLI)

#### Run the CLI in development
- **All platforms:**
  ```sh
  # From project root
  uv run aico --help
  uv run aico gateway status
  uv run aico db init
  ```

#### Build the CLI executable (PyInstaller)
- **All platforms:**
  ```sh
  # From project root
  cd cli
  uv run pyinstaller aico_main.py --onefile --name aico
  # Executable will be in cli/dist/aico(.exe)
  ```

#### Run the built executable
- **Windows:**
  ```sh
  cli\dist\aico.exe
  ```
- **Linux/macOS:**
  ```sh
  ./cli/dist/aico
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
- **Previous approach:** Each Python component (`cli/`, `backend/`) used separate `pyproject.toml` files and virtual environments. This created complexity with environment activation and dependency conflicts.
- **Current approach:** Unified UV workspace with single `pyproject.toml` at project root and shared `.venv`. [UV](https://github.com/astral-sh/uv) provides workspace management with optional dependency groups.

- Add dependencies using `uv add <package>` or `uv add --group <group> <package>` for group-specific deps.
- The supported Python version is pinned to `>=3.13` due to PyInstaller compatibility.
- Use `uv sync` to install/update all dependencies after `pyproject.toml` changes.
- Optional dependency groups: `cli`, `backend`, `test` for component-specific requirements.
- PyInstaller is included in the CLI group for building distributable executables.

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

## Protocol Buffer Compilation

AICO uses Protocol Buffers for cross-component communication. After making changes to `.proto` files, you need to regenerate the language-specific code.

### Prerequisites

Install the Protocol Buffers compiler:
```bash
# macOS
brew install protobuf

# Ubuntu/Debian  
sudo apt-get install protobuf-compiler

# Windows (via chocolatey)
choco install protoc
```

Install language-specific plugins:
```bash
# Python
pip install protobuf mypy-protobuf

# Dart (for Flutter frontend)
dart pub global activate protoc_plugin

# JavaScript/TypeScript (for Studio admin interface)
npm install -g protoc-gen-js protoc-gen-grpc-web
```

### Generating Code

**Note:** All commands assume you're starting from the AICO project root directory (`d:/dev/aico`).

For Python, you must include both the `proto` directory and your venv's `site-packages` as `-I` (include) paths, so that Google well-known types are found.

**Python (Backend & Shared):**

From the **project root** (`d:/dev/aico`), run:

```sh
protoc -I=proto -I=backend/.venv/Lib/site-packages --python_out=shared/aico/proto proto/aico_core_api_gateway.proto proto/aico_core_common.proto proto/aico_core_envelope.proto proto/aico_core_logging.proto proto/aico_core_plugin_system.proto proto/aico_core_update_system.proto proto/aico_emotion.proto proto/aico_integration.proto proto/aico_personality.proto proto/aico_conversation.proto
```
- If your venv is in a different location, adjust the `-I` path accordingly.
- If you get errors about missing `google/protobuf/*.proto` files, make sure your venv's `site-packages/google/protobuf/` directory contains the `.proto` files. If not, download them from the [official repo](https://github.com/protocolbuffers/protobuf/tree/main/src/google/protobuf) and copy them in.

**Dart (Flutter Frontend):**
```bash
cd proto
protoc -I=. --dart_out=../frontend/lib/generated ./core/*.proto ./emotion/*.proto ./conversation/*.proto ./personality/*.proto ./integration/*.proto
```

**JavaScript/TypeScript (Studio Admin Interface):**
```bash
cd proto
protoc -I=. --js_out=import_style=commonjs,binary:../studio/src/generated --grpc-web_out=import_style=commonjs,mode=grpcwebtext:../studio/src/generated ./core/*.proto ./emotion/*.proto ./conversation/*.proto ./personality/*.proto ./integration/*.proto
```

For detailed protobuf development guidelines, see [Protocol Buffers & API Contracts](./protobuf.md).

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
