# System – Layout & Content Design

## 1. Information Design Concept

The System section gives a **structural view of AICO as a product**:

- Configuration management and validation.
- Plugins and extensions.
- Versions and compatibility.
- Database schema and migrations.
- Developer tooling.

The design principle is **"product cockpit"**:

- Quickly answer: "What exact system do I have right now?" and "Is it in a good state?".
- Present upgrade and configuration information in a non-threatening, human way.

## 2. Page Layout

The System page uses a **tab-based layout** with the following tabs:

### 2.1 Configuration Tab (Default)

**Purpose:** Unified configuration management and validation.

**Layout:**
- **Top row – Configuration domains**
  - Cards for each domain (Core, Database, Security, Service Auth).
  - Each card: validation status, source hierarchy, last modified.

- **Middle – Configuration editor**
  - Left: Domain selector and key browser.
  - Right: Live YAML/JSON editor with schema validation.

- **Bottom – Actions**
  - Export/Import buttons, Reload configuration, Validate all domains.

### 2.2 Plugins & Extensions Tab

**Purpose:** Plugin registry and lifecycle management.

**Layout:**
- **Top row – Plugin statistics**
  - Active plugins count, disabled count, health status.

- **Middle – Plugin list**
  - Table/cards showing all registered plugins.
  - Columns: Name, Version, Status, Priority, Dependencies, Health.
  - Enable/disable toggles, reload buttons.

- **Bottom – Plugin execution order**
  - Visual dependency graph showing startup sequence.

### 2.3 Versions Tab

**Purpose:** Component versions and compatibility.

**Layout:**
- **Top row – Version overview**
  - Cards for Backend, Modelservice, Shared Library, Frontend, Studio.
  - Each card: version, build date, status vs latest recommended.

- **Middle – Compatibility matrix**
  - Shows version dependencies and compatibility warnings.

### 2.4 Schema & Migrations Tab

**Purpose:** Database schema version and migration history.

**Layout:**
- **Top – Current schema version**
  - Schema version, migrations applied, pending migrations.

- **Middle – Migration timeline**
  - Timeline or stepper of major schema milestones.

- **Bottom – Migration actions**
  - Run pending migrations, rollback options (with warnings).

### 2.5 Developer Tools Tab

**Purpose:** Developer utilities and shortcuts.

**Layout:**
- **CLI shortcuts** – Quick access to common CLI commands.
- **Test suites** – Links to run test suites.
- **Schema generation** – Tools for schema validation and generation.
- **Documentation links** – Quick access to subsystem docs.

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
