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

**TBD**
- How to install dependencies for each component
- How to generate code from Protocol Buffers
- Recommended tools and editors

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
