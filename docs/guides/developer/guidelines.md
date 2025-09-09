# AICO Code Guidelines & Conventions

> **Purpose:** These guidelines ensure all contributions to AICO are consistent, maintainable, and developer-friendly. They reflect AICO’s unique values, architectural principles, and proven best practices from the open-source community.

## Core Principles

- **Simplicity First:** Prefer simple, clear solutions over clever or complex constructs. If in doubt, make it easy to read and understand.
- **Readability Trumps Fancy:** Write code for humans, not just machines. Prioritize clear naming, structure, and comments over brevity or advanced tricks.
- **DRY (Don’t Repeat Yourself):** Abstract repeated logic and avoid duplication. Use functions, classes, and modules to encapsulate reusable code.
- **KISS (Keep It Simple, Stupid):** Avoid overengineering. Solve the problem at hand with the simplest viable approach.
- **Explicit is Better Than Implicit:** Be clear about what your code does. Avoid hidden side effects and implicit magic.
- **Fail Loudly, Not Silently:** Raise meaningful errors and use assertions where appropriate. Don’t silently swallow exceptions.
- **Privacy & Security by Design:** Always respect user autonomy, local-first data, and zero-knowledge principles. Never expose or log sensitive data.
- **Modularity & Extensibility:** Design with clear module boundaries, favoring composition, well-defined interfaces, and message-driven communication.
- **Resource Awareness:** Be mindful of computational and memory usage, especially for local-first and embedded deployments.
- **User and Developer Experience:** Prioritize clear APIs, documentation, and transparency in both code and plugin development.

## Project-wide Conventions

- **Consistent Style:**
  - **Python:** Follow [PEP 8](https://peps.python.org/pep-0008/) and [PEP 257](https://peps.python.org/pep-0257/) for docstrings.
  - **Dart/Flutter:** Follow [Effective Dart](https://dart.dev/guides/language/effective-dart) guidelines.
  - **Protobuf:** Use clear, versioned schemas. See `/docs/development/protobuf.md`.
  - **File/Folder Naming:** Use `snake_case` for Python, `lowerCamelCase` for Dart, and consistent naming for all files and directories.

- **Documentation:**
  - Every module, class, and public function should have a clear docstring or comment.
  - Document non-obvious design decisions and architectural patterns.
  - Update documentation alongside code changes.

- **Testing:**
  - Write tests for new features and bug fixes.
  - Prefer small, focused tests over large, monolithic ones.
  - Use descriptive test names and clear assertions.

- **Security & Privacy:**
  - Never log or expose sensitive user data.
  - Follow project privacy principles: local-first, user-controlled data, zero-knowledge where possible.
  - Validate and sanitize all external inputs.
  - Respect permission-based access and explicit capability grants (especially for plugins and extensions).
  - Isolate plugins/extensions in secure sandboxes and mediate all resource access.

## Architectural Patterns & Approaches

- **Modular, Message-Driven Design:**
  - Structure code into logical modules/components. Use the message bus and standardized envelope/message patterns for inter-module communication.
  - Avoid tight coupling—modules should interact via well-defined interfaces and topics.
  - Design for extensibility: new features, plugins, or modalities should integrate without core changes.

- **Embodiment & Multi-Modal Awareness:**
  - When working on presentation or interaction code, support multi-modal presence (voice, avatar, gesture, spatial context) as described in the embodiment architecture.
  - Ensure cross-device and cross-environment compatibility where possible.

- **Data Layer Best Practices:**
  - Use the appropriate storage for each data type (libSQL for structured, DuckDB for analytics, ChromaDB for embeddings, RocksDB for cache).
  - Optimize for local-first, file-based operation. Plan for future federated sync but do not assume cloud dependencies.

- **Plugin System:**
  - Plugins must operate in secure, isolated sandboxes.
  - All access to core system resources and data must be mediated and permission-based.
  - Follow versioned APIs and maintain backward compatibility for plugin interfaces.
  - Provide clear documentation and transparent capability declarations for all plugins.

## Contribution Etiquette

- **Small, Atomic Commits:** Make each commit focused and self-contained. Write clear, descriptive commit messages.
- **Pull Requests:**
  - Reference related issues and provide context.
  - Describe what, why, and how in the PR description.
  - Be open to feedback and iterate as needed.
- **Code Reviews:**
  - Review others’ code with respect and constructiveness.
  - Ask for clarification rather than assuming intent.
  - Suggest improvements, but recognize different styles can be valid if they follow guidelines.

## When in Doubt
- Ask questions! Use GitHub Discussions, issues, or project conversation.
- If unsure about a pattern or approach, prefer what’s already established in the codebase.
- Propose improvements, but keep changes incremental and well-documented.
- When integrating with architecture, consult the appropriate documentation in `/docs/architecture/` for module-specific conventions.

---

> **Remember:** Our goal is to build a trustworthy, maintainable, and welcoming project. These guidelines are here to help us work together smoothly—please suggest improvements as the project evolves!
