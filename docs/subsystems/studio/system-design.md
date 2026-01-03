# System – Layout & Content Design

## 1. Information Design Concept

The System section gives a **structural view of AICO as a product**:

- Versions and compatibility.
- Database schema and migrations.
- Plugins and extensions.
- Developer tooling.

The design principle is **"product cockpit"**:

- Quickly answer: "What exact system do I have right now?" and "Is it in a good state?".
- Present upgrade and configuration information in a non-threatening, human way.

## 2. Page Layout

### 2.1 Main Layout

- **Top row – Version overview**
  - Cards for Backend, Modelservice, Shared Library, Frontend, Studio.
  - Each card: version, build date, status vs latest recommended.

- **Middle – Schema & Migrations / Plugins**
  - Left: Database schema panel.
  - Right: Plugins & Extensions panel.

- **Bottom – Developer tools**
  - Links to CLI commands, schema generation, test suites.

## 3. Content Design

### 3.1 Version Overview

- **Visuals**
  - Card grid with each subsystem.
  - Icons subtly indicate whether version is up-to-date.

- **Functions**
  - Click card → drawer with changelog link, upgrade guides, and related docs.

### 3.2 Schema & Migrations Panel

- **Metrics**
  - Current schema version.
  - Number of migrations applied.

- **Visuals**
  - Timeline or stepper of major schema milestones.

- **Functions**
  - Link to docs for each major schema phase (e.g., memory, agency additions).

### 3.3 Plugins & Extensions Panel

- **Visuals**
  - Table or card list of installed plugins with status and origin.

- **Functions**
  - Enable/disable toggle per plugin.
  - Link to plugin docs or configuration.

### 3.4 Developer Tools Panel

- **Content**
  - High-level description of available dev tooling.
  - Shortcuts to run or inspect key tools (via CLI or docs).

## 4. Navigation & Traceability

- From System you can:
  - Jump to specific docs for subsystems.
  - Cross-link to Operations (for migrations and upgrades).
  - Cross-link to Security (for changes affecting keys and encryption).

## 5. UX Notes

- Avoid overwhelming non-developers with raw technical detail; show only what is necessary for informed decisions.
- Keep the tone invitational and informative rather than purely diagnostic.
