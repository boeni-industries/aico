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
├── backend/           # Python FastAPI backend with plugin architecture
│
├── frontend/          # Flutter 3.27+ UI app with encrypted local storage
│
├── studio/            # React-based "Studio" for devs, power users, admins (early development)
│
├── cli/               # Python Typer/Rich CLI (v1.1.0, production-ready)
│
├── modelservice/      # Ollama integration service with ZeroMQ
│
├── shared/            # Shared Python libraries (aico.* namespace)
│
├── proto/             # Protocol Buffers and shared API schemas
│
├── config/            # Configuration files and Modelfiles
│
├── docs/              # Documentation (architecture, guidelines, etc.)
│
├── site/              # Built documentation/static site output (generated)
│
├── scripts/           # Development and testing scripts
│
├── .github/           # GitHub workflows, issue templates, etc.
├── LICENSE
├── README.md
├── mkdocs.yml         # MkDocs config for docs
├── pyproject.toml     # Unified Python dependencies
└── uv.lock            # UV dependency lock file
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
> AICO uses application-level encryption with SQLCipher for all databases (PostgreSQL in the backend and Drift on the frontend). Semantic memory and knowledge graph embeddings use ChromaDB, and working memory/cache uses LMDB, all with appropriate security measures. This approach provides better cross-platform compatibility and performance without requiring additional system dependencies.

### 3. UV Workspace Setup (Single Virtual Environment)
AICO uses UV workspace management with a unified `pyproject.toml` at the root and a single shared virtual environment for all Python components.

**Important (Development): Use `AICO_CONFIG_DIR` to isolate your runtime config**
 
AICO reads and edits configuration from the *runtime config directory* (platform-dependent) by default. In development, you should point `AICO_CONFIG_DIR` to a repo-local path so different checkouts/branches don't share the same config state.
 
 ```sh
 # Example (recommended): keep runtime config inside the repo
 export AICO_CONFIG_DIR="$PWD/.aico-dev/config"
 
 # Seed the runtime config directory with schemas/defaults/environments/modelfiles
 uv run aico config init
 ```

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
  uv sync --extra cli --extra backend --extra test --extra modelservice

  # Verify installation
  uv run aico --help
  uv run python -c "import fastapi; print('Backend deps ready')"
  ```

**Key Changes from Previous Setup:**
- **Single `.venv`** at project root instead of per-component environments
- **Unified `pyproject.toml`** with optional dependency groups (`cli`, `backend`, `test`)
- **UV workspace commands** replace manual venv activation
- **Shared dependencies** automatically resolved across all components
- **Dependency overrides**: UV's `override-dependencies` resolves GLiNER/Coqui-TTS conflict (transformers version)

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
> - **Cache**: LMDB for high-performance session caching
> - Simplified IDE configuration (one Python interpreter)
> - Automatic shared library integration

> **IDE Setup:** Point your IDE to the `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Unix) in the project root.

---

### 6. Setting Up the Flutter Frontend

The flutter project scaffolding is present in `/frontend`.

**Install Flutter:**

- Download and install Flutter from the [official site](https://docs.flutter.dev/get-started/install) for your platform (Windows, macOS, Linux).
- After installation, check your version (we recommend Flutter 3.27+):
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
  uv run uvicorn backend.main:app --reload --port 8771
  # Visit http://127.0.0.1:8771
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

## Development Notes

### Dependency Management
AICO uses UV workspace management with a unified `pyproject.toml` and shared virtual environment:

- Add dependencies: `uv add <package>` or `uv add --group <group> <package>`
- Python version: `>=3.13` (PyInstaller compatibility)
- Sync dependencies: `uv sync` after changes
- Optional groups: `cli`, `backend`, `test`

### Project Structure
The project follows a monorepo structure with shared libraries and unified tooling across all components.


## Database Setup

AICO uses a multi-database architecture. PostgreSQL, Loki, and InfluxDB run in **Docker containers** for consistent deployment across platforms.

> **🐳 Docker Deployment**
> 
> PostgreSQL, Loki, and InfluxDB are containerized using Docker for:
> - **Consistent environments** across development, testing, and production
> - **Easy version management** (PostgreSQL 18.1, Loki 2.9, InfluxDB 2.x)
> - **Isolated dependencies** without system-wide installation
> - **Simple cleanup** with container removal
> 
> **Future**: Additional components (ChromaDB, analytics services) will be containerized as the architecture evolves.

### Prerequisites

**Install Docker**:
- Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for your platform
- Verify installation: `docker --version`
- Ensure Docker daemon is running

### PostgreSQL Deployment

PostgreSQL stores all core application data (users, conversations, knowledge graph, agency).

**Initial Deployment**:
```bash
aico deploy pg
```

This command:
1. **Pulls PostgreSQL 18.1 Docker image** (if not present)
2. **Starts PostgreSQL container** with persistent volume
3. Connects to the containerized instance
4. Creates the `aico` database if it doesn't exist
5. Creates the `aico_core` schema
6. Applies all schema migrations
7. Sets up initial tables and indexes

**Container Details**:
- Image: `postgres:18.1`
- Port: `5432` (mapped to host)
- Volume: Persistent storage for database files
- Network: Docker bridge network for inter-container communication

**⚠️ DANGEROUS: Reset Database**:
```bash
aico deploy pg --nuke
```

**WARNING**: The `--nuke` flag will:
- **STOP and REMOVE the PostgreSQL container**
- **DELETE the persistent volume**
- **ERASE ALL DATA permanently**
- Pull fresh image and recreate container
- Apply all migrations to new database

**Use cases for --nuke**:
- ✅ Development: Starting fresh after schema changes
- ✅ Testing: Clean slate for integration tests
- ❌ **NEVER in production** - you will lose all user data

**Prerequisites**:
- Docker installed and running
- Database credentials configured in `config/defaults/postgres.yaml`
- Password stored in system keyring via `aico security setup`

### Loki Deployment

Loki stores application logs with LogQL query support.

**Initial Deployment**:
```bash
aico deploy loki
```

This command:
1. **Pulls Loki 2.9 Docker image** (if not present)
2. **Starts Loki container** with persistent volume
3. Configures log retention (default: 30 days)
4. Sets up label-based indexing
5. No authentication required for local development

**Container Details**:
- Image: `grafana/loki:2.9.0`
- Port: `3100` (mapped to host)
- Volume: Persistent storage for logs
- Network: Docker bridge network

**⚠️ DANGEROUS: Reset Logs**:
```bash
aico deploy loki --nuke
```

**WARNING**: The `--nuke` flag will:
- **STOP and REMOVE the Loki container**
- **DELETE the persistent volume**
- **ERASE ALL logs permanently**
- Pull fresh image and recreate container

**Use cases for --nuke**:
- ✅ Development: Clear old logs
- ✅ Testing: Fresh log baseline
- ❌ **Use with caution** - historical logs are lost

**Prerequisites**:
- Docker installed and running
- Loki URL configured in `config/defaults/loki.yaml` (http://localhost:3100)

### InfluxDB Deployment

InfluxDB stores time-series metrics and performance telemetry.

**Initial Deployment**:
```bash
aico deploy influx
```

This command:
1. **Pulls InfluxDB 2.x Docker image** (if not present)
2. **Starts InfluxDB container** with persistent volume
3. Connects to the containerized instance
4. Creates the `aico` organization if it doesn't exist
5. Creates the `aico_telemetry` bucket
6. Sets up retention policies (default: 30 days)
7. Configures API token for writes

**Container Details**:
- Image: `influxdb:2-alpine`
- Port: `8086` (mapped to host)
- Volume: Persistent storage for time-series data
- Network: Docker bridge network

**⚠️ DANGEROUS: Reset Metrics Database**:
```bash
aico deploy influx --nuke
```

**WARNING**: The `--nuke` flag will:
- **STOP and REMOVE the InfluxDB container**
- **DELETE the persistent volume**
- **ERASE ALL metrics permanently**
- Pull fresh image and recreate container
- Reconfigure organization and bucket

**Use cases for --nuke**:
- ✅ Development: Clear old telemetry data
- ✅ Testing: Fresh metrics baseline
- ❌ **Use with caution** - historical data is lost

**Prerequisites**:
- Docker installed and running
- InfluxDB URL configured in `config/defaults/influx.yaml` (http://localhost:8086)
- API token stored in system keyring

### Verification

**Check PostgreSQL**:
```bash
aico pg tables  # List all tables in aico_core schema
aico pg users   # List users (should be empty initially)
```

**Create Your User Account**

After deploying databases, create your user:

```bash
aico security create-user
```

This will:
1. Prompt for your full name and nickname
2. Create a secure PIN
3. Store user in PostgreSQL
4. Set up authentication credentials

**Check Loki**:
```bash
aico logs tail --lines 10  # Query recent logs from Loki
```

**Check InfluxDB**:
```bash
# InfluxDB now stores metrics only (not logs)
curl http://localhost:8086/health  # Check InfluxDB health
```

### Database Configuration

Edit `config/defaults/postgres.yaml`, `config/defaults/loki.yaml`, and `config/defaults/influx.yaml`:

```yaml
db_name: "aico"
core_schema: "aico_core"
host: "127.0.0.1"
port: 5432
user: "postgres"
# Password stored in keyring

# ---

url: "http://127.0.0.1:8086"
org: "aico"
bucket: "aico_telemetry"
# Token stored in keyring
```

### Troubleshooting

**PostgreSQL connection failed**:
```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# View PostgreSQL container logs
docker logs aico-postgres

# Connect to PostgreSQL container directly
docker exec -it aico-postgres psql -U postgres -c "SELECT version();"

# Verify password in keyring
aico security keyring list

# Re-setup credentials
aico security setup
```

**InfluxDB connection failed**:
```bash
# Check if InfluxDB container is running
docker ps | grep influx

# View InfluxDB container logs
docker logs aico-influx

# Check InfluxDB health endpoint
curl http://localhost:8086/health

# Verify token
aico security keyring list
```

**Loki connection failed**:
```bash
# Check if Loki container is running
docker ps | grep loki

# View Loki container logs
docker logs aico-loki

# Check Loki health endpoint
curl http://localhost:3100/ready

# Test log query
curl -G "http://localhost:3100/loki/api/v1/labels" | jq
```

**Docker issues**:
```bash
# Check Docker daemon status
docker info

# List all AICO containers
docker ps -a | grep aico

# Remove stopped containers
docker rm aico-postgres aico-loki aico-influx

# Remove volumes (⚠️ deletes data)
docker volume rm aico-postgres-data aico-lokidata aico-influx-data
```

## Database Setup (Legacy)

AICO uses encrypted databases for all data storage with security by design. The setup process automatically handles directory creation, security initialization, and database configuration.

### Quick Setup (Recommended)

```bash
# Optional (recommended in dev): isolate runtime config per repo/branch
export AICO_CONFIG_DIR="$PWD/.aico-dev/config"

# 1. Initialize AICO configuration directories
aico config init

# 2. Initialize encrypted database (auto-setup security if needed)
aico db init

# 3. Create AI character model (required for conversations)
aico ollama generate eve

# 4. Verify complete setup
aico config show
aico db show
ollama list  # Should show 'eve' model
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
# Create encrypted PostgreSQL database with automatic security setup
aico db init

# Test database connection and encryption
aico db test

# View database configuration and paths
aico db show
```

**Note**: The `aico db init` command automatically sets up master password security if not already configured, eliminating the need for separate `aico security setup` step.

#### 3. AI Character Model Setup

AICO uses Ollama with custom character definitions (Modelfiles) to create AI personalities. The Eve character is the default AI companion.

```bash
# Create the Eve character model from Modelfile
aico ollama generate eve

# Verify the model was created successfully
ollama list
# You should see the base model 'huihui_ai/qwen3-abliterated:8b-v2'

# Test the model (optional)
ollama run huihui_ai/qwen3-abliterated:8b-v2 "Hello, who are you?"
```

**What this does:**
- Reads the character definition from your *runtime config directory* (`$AICO_CONFIG_DIR/modelfiles/Modelfile.eve`)
- Seeds/syncs Modelfiles from the repo templates when needed (`aico config init`)
  - Ensures the base model is pulled from Ollama
  - Configures model parameters (temperature, context window, etc.)
  - Sets up the character's personality and behavior via Modelfile

**Character Details:**
- **Name**: Eve
- **Base Model**: `huihui_ai/qwen3-abliterated:8b-v2` (uncensored, thinking-capable)
- **Personality**: Warm, curious, contemplative companion with genuine thoughts and feelings
- **Features**: Natural conversation style, Ollama 0.12+ native thinking API support
- **Parameters**: num_ctx=8192, temp=0.7, top_p=0.8, top_k=20

**Updating the Character:**
If you modify `Modelfile.eve`, regenerate:
```bash
aico ollama generate eve --force
```

For more details, see the Modelfiles README in the repository at `config/modelfiles/README.md`.

### Directory Structure
After setup, you'll have cross-platform directories:
```
# Windows Example: %APPDATA%/aico/
# macOS Example: ~/Library/Application Support/aico/
# Linux Example: ~/.local/share/aico/
aico/
├── data/
│   ├── PostgreSQL database              # Main PostgreSQL database (encrypted)
│   ├── PostgreSQL database.salt         # Encryption salt
│   ├── analytics.db         # Analytics database (planned, backend TBD)
│   └── chroma/              # Vector database directory (ChromaDB)
├── config/
│   ├── schemas/             # Configuration schemas (*.schema.json)
│   ├── defaults/            # Default configuration files
│   ├── environments/        # Environment-specific overrides
│   ├── modelfiles/          # Modelfiles (e.g. Modelfile.eve)
│   └── runtime.yaml         # Persisted runtime overrides
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
aico config get postgres.host
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

For detailed architecture and configuration options, see [Data Layer Documentation](../../concepts/data/data-layer.md).

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

**Note:** All commands assume you're starting from the AICO project root directory.

For Python, you must include both the `proto` directory and your venv's `site-packages` as `-I` (include) paths, so that Google well-known types are found.

**Python (Backend & Shared):**

From the **project root**, run:

```sh
protoc -I=proto -I=.venv/Lib/site-packages --python_out=shared/aico/proto proto/aico_core_api_gateway.proto proto/aico_core_common.proto proto/aico_core_envelope.proto proto/aico_core_logging.proto proto/aico_core_plugin_system.proto proto/aico_core_update_system.proto proto/aico_emotion.proto proto/aico_integration.proto proto/aico_personality.proto proto/aico_conversation.proto proto/aico_modelservice.proto
```
- Note: UV workspace uses `.venv` at project root, not `backend/.venv`.
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
- [Architecture Overview](../../architecture/architecture-overview.md)
- Modules & Components (file does not exist)
- [Developer Guidelines & Conventions](./guidelines.md)
- [Plugin System Overview](../../subsystems/backend/plugin-system.md)
- [Data Layer & Storage](../../concepts/data/data-layer.md)
- [Protocol Buffers & API Contracts](./protobuf.md)
- [Privacy & Security](../../security/data-security.md)

---

> This document is a living guide and will be updated as the project grows. If you have suggestions, please open an issue or PR!
