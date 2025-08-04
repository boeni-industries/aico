# Developer Onboarding: Getting Started with AICO

This guide is for developers and contributors. For general usage, installation, or user onboarding, see the [User Guide](../user-guide/getting_started_overview.md).

Here you'll find everything you need to set up your development environment, understand the project structure, and start contributing.

---

## Project Overview

AICO is an open-source, local-first AI companion designed to be emotionally present, embodied, and proactive. The project is modular, privacy-first, and extensible, with contributions welcome from developers, designers, researchers, and more.

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

> ⚠️ **Warning**
> Only one Python virtual environment can be active per terminal session. If you need to work with both the CLI and backend at the same time, open separate terminal windows and activate the appropriate environment in each. Changing directories does not automatically switch the active environment—you must activate it explicitly.

---

### 4. Create the Flutter Frontend Project

The Flutter app lives in its own directory to keep dependencies and tooling isolated from other parts of the monorepo.

- **Directory:** All Flutter code and dependencies go in `/frontend`.
- **Project Name:** Use a lowercase, underscore-separated name (e.g., `aico_frontend`).
- **Platform Support:** Enable all major platforms at creation (web, desktop, mobile). You can add/remove platforms later.
- **.gitignore:** Ensure `/frontend` has a `.gitignore` that excludes Dart/Flutter build artifacts (e.g., `/build`, `.dart_tool`, etc.).

**To create the project:**

```sh
flutter create frontend --project-name aico_ui --platforms=windows,macos,linux,android,ios,web
```

This will scaffold the Flutter app in `/frontend` with all major platforms enabled.

> **Tip:**
> Use VS Code or Android Studio or Windsurf with the Flutter/Dart plugins for the best development experience.

---

### 5. Create the React Admin Studio

The admin dashboard ("studio") is a modular, manifest-driven web app built with React and React-Admin. All code and dependencies live in `/studio`.

- **Node.js & npm:** Install the latest LTS version of Node.js from [nodejs.org](https://nodejs.org/). npm (the Node package manager) is included with Node.js.
- **Version check:** After installation, verify your versions (we recommend Node.js 18.x+ and npm 9.x+):
  ```sh
  node --version
  npm --version
  ```
- **Scaffold the project:**
  ```sh
  npx create-react-app studio --template typescript
  ```
- **Install required dependencies:**
  ```sh
  cd studio
  npm install react-admin ra-data-simple-rest @mui/material @mui/icons-material @emotion/react @emotion/styled react-router-dom
  ```
- **.gitignore:** The `/studio` directory will have its own `.gitignore` (auto-generated) to exclude build artifacts and `node_modules`.

> **Tip:**
> Use VS Code, Windsurf, or any modern IDE with JS/TS support for development.

---

## Building and Running Components

**TBD**
- How to build and run the backend
- How to build and run the frontend (Flutter)
- How to launch the studio (React)
- How to use the CLI

---

## Contributing

See [`contributing.md`](./contributing.md) for ways to get involved, contribution etiquette, and project values.

**Highlights:**
- All skillsets welcome (development, design, research, writing, testing, etc.)
- Small, atomic commits and clear PRs
- Respectful, constructive code reviews

---

## Protocol Buffers & API Contracts

See [`protobuf.md`](./protobuf.md) for details on message formats, code generation, and best practices for evolving schemas.

---

## Further Reading

- [Code Guidelines & Conventions](./guidelines.md)
- [Architecture Overview](../architecture/architecture_overview.md)
- [Data Layer](../architecture/data_layer.md)
- [Data Federation](../architecture/data_federation.md)

---

## FAQ

**TBD**
- Common questions about setup, architecture, and contribution

---

## Contact & Community

**TBD**
- How to join discussions, chat, or community calls

---

> This document is a living guide and will be updated as the project grows. If you have suggestions, please open an issue or PR!
