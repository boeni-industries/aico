# AICO Documentation Refactor Plan

## 1. Guiding Principles
- **Subsystem-Oriented**: Structure mirrors codebase (backend, frontend, cli, etc.)
- **Audience Segmentation**: Clear entry points for users, devs, admins, researchers
- **Progressive Disclosure**: Overviews → How-tos → References → Internals
- **Consistent Naming**: All files/folders use `kebab-case` (e.g. `admin-overview.md`, `quickstart.md`)
- **Best-in-Class UX**: Inspired by Stripe, Docker, Twilio, etc.
- **mkdocs-material**: Leverage features—tabs, navigation, search, light/dark mode, custom logo, etc.
- **Custom Assets**: Use `/docs/assets/` for logo, styles, scripts (see section 5)

---

## 2. Target Documentation Structure (Hybrid: Technical + Use-Case Driven)

```
docs/
  welcome.md                # Unified landing page: vision, subsystem map, quickstart links, status
  getting-started.md        # Install, setup, first run, quick links to subsystems
  architecture-overview.md  # Visual, interactive system map with clickable subsystem links
  guides/
    admin/
      overview.md           # Admin workflows (e.g. user management, backup)
      cli-automation.md     # CLI-driven admin tasks
      troubleshooting.md
    developer/
      overview.md           # Developer workflows (e.g. extending AICO, backend/frontend integration)
      api-usage.md
      plugin-development.md
    power-user/
      overview.md           # Power user workflows (e.g. scripting, advanced CLI)
      cli-scripting.md
      custom-integrations.md
    tasks/
      overview.md           # Common tasks, quick recipes
      ...                   # More task-focused guides
  cli-reference.md          # Always-accessible CLI reference (top-level)
  api-reference.md          # Always-accessible API reference (top-level)
  subsystems/
    backend/
      overview.md
      quickstart.md
      admin-guide.md
      scheduler.md
      howto-guides.md
      troubleshooting.md
      faq.md
      # For large/deep subsystems, use subfolders for major modules:
      conversation/
        overview.md
        thread-manager.md
        # (Add more conversation-related backend docs here)
    frontend/
      overview.md
      quickstart.md
      ui-customization.md
      theming.md
      faq.md
    cli/
      overview.md
      quickstart.md
      examples.md
      faq.md
    shared/
      overview.md
      data-models.md
      integration.md
    studio/
      overview.md
      usage.md
      customization.md
    modelservice/
      overview.md
      deployment.md
  concepts/
    index.md                # Landing page for research/concepts
    emotion/
      overview.md
      research.md
      implementation.md
    llm/
      overview.md
      research.md
      implementation.md
    personality/
      overview.md
      research.md
      implementation.md
  admin/
    admin-overview.md
    admin-ui.md
    security.md
    status.md               # Live status indicators or app status widget
  development/
    guidelines.md
    contributing.md
    code-style.md
    plugin-development.md
  community.md              # Links to forums, Discord, Stack Overflow, etc.
  changelog.md
  glossary.md
  troubleshooting.md
  faq.md
  cheat-sheets.md           # Recap/cheat sheets for power users
assets/
  images/logo.png           # Company logo for mkdocs-material
  stylesheets/extra.css     # Custom CSS (see section 5)
  javascripts/extra.js      # Custom JS (see section 5)
```

---

### Rationale for Hybrid Structure
- **Multiple Entry Points:** Users can navigate by workflow ("How do I..."), by subsystem, or by reference.
- **Guides/Workflows:** Task- and role-based docs (admin, dev, power user) are first-class, not buried in subsystem folders.
- **References Always Accessible:** CLI/API references are top-level, never hidden inside subsystems.
- **Cross-linking:** Guides reference CLI/API docs and vice versa. "See Also"/"Related Topics" on every page.
- **Improved UX:** Mirrors how real users and devs approach docs—by goal, not just by code structure.

---

## 4. mkdocs-material Navigation Plan (Updated)

### Navigation Structure (example for `mkdocs.yml`):

```yaml
nav:
  - Welcome: welcome.md
  - Getting Started: getting-started.md
  - Guides:
      - Admin Workflows: guides/admin/overview.md
      - Developer Workflows: guides/developer/overview.md
      - Power User Workflows: guides/power-user/overview.md
      - Common Tasks: guides/tasks/overview.md
  - CLI Reference: cli-reference.md
  - API Reference: api-reference.md
  - Subsystems:
      - Backend: ...
      - Frontend: ...
      - CLI: ...
      - Shared: ...
      - Studio: ...
      - Modelservice: ...
  - Concepts: ...
  - Admin: ...
  - Development: ...
  - Community: community.md
  - Changelog: changelog.md
  - Glossary: glossary.md
  - Troubleshooting: troubleshooting.md
  - FAQ: faq.md
  - Cheat Sheets: cheat-sheets.md
```

---
---

## 3. File Naming Conventions
- **kebab-case** for all files and folders (e.g., `admin-overview.md`, `quickstart.md`)
- **No spaces or underscores**
- **One topic per file** (avoid mega-files)
- **Landing pages** named `overview.md` or `index.md` as appropriate

---

## 4. mkdocs-material Navigation Plan

### Navigation Structure (example for `mkdocs.yml`):

```yaml
nav:
  - Welcome: welcome.md
  - Getting Started: getting-started.md
  - Architecture: architecture-overview.md
  - Subsystems:
      - Backend:
          - Overview: subsystems/backend/overview.md
          - Quickstart: subsystems/backend/quickstart.md
          - API Reference: subsystems/backend/api-reference.md
          - Admin Guide: subsystems/backend/admin-guide.md
          - Scheduler: subsystems/backend/scheduler.md
          - How-To Guides: subsystems/backend/howto-guides.md
          - Troubleshooting: subsystems/backend/troubleshooting.md
          - FAQ: subsystems/backend/faq.md
      - Frontend:
          - Overview: subsystems/frontend/overview.md
          - Quickstart: subsystems/frontend/quickstart.md
          - UI Customization: subsystems/frontend/ui-customization.md
          - Theming: subsystems/frontend/theming.md
          - FAQ: subsystems/frontend/faq.md
      - CLI:
          - Overview: subsystems/cli/overview.md
          - Quickstart: subsystems/cli/quickstart.md
          - CLI Reference: subsystems/cli/cli-reference.md
          - Examples: subsystems/cli/examples.md
          - FAQ: subsystems/cli/faq.md
      - Shared:
          - Overview: subsystems/shared/overview.md
          - Data Models: subsystems/shared/data-models.md
          - Integration: subsystems/shared/integration.md
      - Studio:
          - Overview: subsystems/studio/overview.md
          - Usage: subsystems/studio/usage.md
          - Customization: subsystems/studio/customization.md
      - Modelservice:
          - Overview: subsystems/modelservice/overview.md
          - API Reference: subsystems/modelservice/api-reference.md
          - Deployment: subsystems/modelservice/deployment.md
  - Concepts:
      - Overview: concepts/index.md
      - Emotion:
          - Overview: concepts/emotion/overview.md
          - Research: concepts/emotion/research.md
          - Implementation: concepts/emotion/implementation.md
      - LLM:
          - Overview: concepts/llm/overview.md
          - Research: concepts/llm/research.md
          - Implementation: concepts/llm/implementation.md
      - Personality:
          - Overview: concepts/personality/overview.md
          - Research: concepts/personality/research.md
          - Implementation: concepts/personality/implementation.md
  - Admin:
      - Overview: admin/admin-overview.md
      - Admin UI: admin/admin-ui.md
      - Security: admin/security.md
      - Status: admin/status.md
  - Development:
      - Guidelines: development/guidelines.md
      - Contributing: development/contributing.md
      - Code Style: development/code-style.md
      - Plugin Development: development/plugin-development.md
  - Community: community.md
  - Changelog: changelog.md
  - Glossary: glossary.md
  - Troubleshooting: troubleshooting.md
  - FAQ: faq.md
  - Cheat Sheets: cheat-sheets.md
```

### mkdocs-material Features to Enable
- **Logo**: Use `assets/images/logo.png` (set in `mkdocs.yml`)
- **Light/Dark Mode**: Enable theme switching
- **Tabs**: Use for major sections if sidebar gets too deep
- **Instant Search**: Ensure search is always visible
- **Custom CSS/JS**: Use `/assets/stylesheets/extra.css` and `/assets/javascripts/extra.js` for branding, layout tweaks, or interactive elements
- **Status Widget**: Consider embedding live status in `admin/status.md` and on the landing page

---

## 5. Special Assets & Scripts
- **Logo**: `/docs/assets/images/logo.png` (referenced in mkdocs config)
- **Custom CSS**: `/docs/assets/stylesheets/extra.css` (for branding, typography, etc.)
- **Custom JS**: `/docs/assets/javascripts/extra.js` (for interactivity)
- **Disable Logo CSS**: `/docs/assets/stylesheets/disable-logo.css` (if needed for certain pages)

---

## 6. Step-by-Step Refactor Process
1. **Create new folder structure** under `/docs/` as above
2. **Move/rename files** to follow naming conventions
3. **Update mkdocs.yml** to match new navigation
4. **Update logo, CSS, JS** references in mkdocs config
5. **Test locally**: Check navigation, search, theme switching, logo, custom styles/scripts
6. **Iterate**: Refine based on feedback and usability

---

## 7. References
- [mkdocs-material documentation](https://squidfunk.github.io/mkdocs-material/)
- [AICO README.md project vision]
- [Best-in-class docs: Stripe, Docker, Twilio, Canva, Dropbox]

---

> This plan is the single source of truth for the AICO documentation refactor. Update as needed during the process.
