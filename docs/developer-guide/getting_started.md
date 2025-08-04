# Developer Onboarding: Getting Started with AICO

This guide is for developers and contributors. For general usage, installation, or user onboarding, see the [User Guide](../user-guide/getting_started_overview.md).

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

### 3. Create Python Virtual Environments (CLI & Backend)
AICO uses isolated Python environments for each component to avoid dependency conflicts.

- **CLI:**
  ```sh
  cd cli
  py -3.13 -m venv .venv
  # Activate (Windows)
  .venv\Scripts\activate
  # Activate (macOS/Linux)
  source .venv/bin/activate
  ```
- **Backend:**
  ```sh
  cd backend
  py -3.13 -m venv .venv
  # Activate (Windows)
  .venv\Scripts\activate
  # Activate (macOS/Linux)
  source .venv/bin/activate
  ```

Each part manages its own dependencies and tooling. Always activate the relevant environment before installing requirements or running code.

!!! warning
    Only one Python virtual environment can be active per terminal session. If you need to work with both the CLI and backend at the same time, open separate terminal windows and activate the appropriate environment in each. Changing directories does not automatically switch the active environment—you must activate it explicitly.

---

### 4. Setting Up the Flutter Frontend

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

### 5. Setting Up the React Admin Studio

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
  ```

**.gitignore:** Already configured to exclude build artifacts and `node_modules`.

> **Tip:**
> Use VS Code, Windsurf, or any modern IDE with JS/TS support for development.

---

## Building and Running Components

Below are the build and run commands for each major part of the system. Substitute your platform (Windows, macOS, Linux) as appropriate.

### Backend (Python FastAPI)

!!! warning
    The backend is not yet implemented. This section will be updated as the backend is developed.

- **Windows:**
  ```sh
  cd backend
  .venv\Scripts\activate
  uvicorn main:app --reload
  ```
- **Linux/macOS:**
  ```sh
  cd backend
  source .venv/bin/activate
  uvicorn main:app --reload
  ```

### CLI (Python Typer/Rich CLI)

- **Windows:**
  ```sh
  cd cli
  .venv\Scripts\activate
  python -m aico_cli  # or your CLI entrypoint
  ```
- **Linux/macOS:**
  ```sh
  cd cli
  source .venv/bin/activate
  python -m aico_cli  # or your CLI entrypoint
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

## Maintainer Note: Initial Project Scaffolding

!!! warning 
    This section is for maintainers only. Regular contributors do NOT need to run these commands. The following steps were performed once to create the initial project structure and are preserved here for reference.

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

## Further Reading

- [Contributing](./contributing.md)
- [Architecture Overview](../architecture/architecture_overview.md)
- [Modules & Components](../architecture/modules.md)
- [Developer Guidelines & Conventions](./guidelines.md)
- [Plugin System Overview](../architecture/plugins.md)
- [Data Layer & Storage](../architecture/data_layer.md)
- [Admin UI Architecture](../admin/admin_ui_master.md)
- [Protocol Buffers & API Contracts](./protobuf.md)
- [Privacy & Security](../security/security_overview.md)

---

> This document is a living guide and will be updated as the project grows. If you have suggestions, please open an issue or PR!
