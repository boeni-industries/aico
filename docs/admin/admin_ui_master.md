# Master Admin UI: Architecture and Implementation

The AICO Master Admin UI is a single-page web application built with **React** and **React-Admin**. It serves as the unified dashboard for all backend administrative modules, following best practices for modularity, extensibility, and maintainability.

---

## 1. Technology Overview: React & React-Admin

- **React** is a component-based JavaScript framework for building interactive UIs. It enables modular code, fast rendering, and a huge ecosystem.
- **React-Admin** is a production-grade, open-source admin dashboard framework built on React. It provides:
  - Resource-based CRUD panels, forms, tables, and charts
  - Extensible plugin/component architecture
  - Built-in authentication, RBAC, and theming
  - Data Provider abstraction for REST, GraphQL, or WebSocket APIs

**Why it fits AICO:**
- Enables dynamic discovery and rendering of admin modules via manifests
- Supports generic and custom panels (plugins)
- Rapid development and strong contributor pool

---

## 2. SPA Structure & Project Layout

- **Entry Point:** `src/index.tsx` initializes the React app and renders the `<Admin />` component from React-Admin.
- **Routing:** React-Admin handles internal routing for each module/panel (e.g., `/admin/config`, `/admin/logs`).
- **Layout:** The main dashboard layout (sidebar, header, content area) is defined in a custom layout component if needed.

**Example Project Structure:**
```
admin-ui/
  src/
    api/                # Data provider, API helpers
    components/         # Shared UI components
    modules/            # Custom admin modules/plugins (optional)
    manifests/          # Type definitions, manifest helpers
    App.tsx             # Main app entry
    index.tsx           # React entry point
  public/
  package.json
  ...
```

---

## 3. Module/Panel Discovery & Registration

- On startup, the UI queries the backend (e.g., `GET /admin/modules`) to retrieve a list of available modules and their manifests.
- Each manifest describes:
  - `name`, `icon`, `route`, `type` (dashboard, form, table, etc.)
  - API endpoints for data
  - (Optionally) a reference to a custom React component bundle for advanced modules

**Manifest Example:**
```json
{
  "name": "Resource Monitor",
  "icon": "cpu",
  "route": "/admin/resource-monitor",
  "type": "dashboard",
  "endpoints": { "status": "/admin/resource-monitor/status" },
  "fields": [
    {"label": "CPU Usage", "type": "gauge", "source": "status.cpu"}
  ],
  "customComponent": null
}
```

**Dynamic Registration:**
- The React app maps each manifest to a `<Resource />` in React-Admin.
- If `customComponent` is specified, it is dynamically imported and registered as a plugin panel.

---

## 4. Implementing a New Admin Module

**Backend Steps:**
- Expose a REST/WebSocket API for your admin module (e.g., `/admin/logs`)
- Provide a manifest endpoint describing the UI (see above)
- (Optional) Bundle a custom React component for advanced UI (micro-frontend)

**Frontend Steps:**
- The UI will automatically discover and render your module as a panel based on the manifest
- For generic panels, no UI code changes are needed
- For custom panels, export a React component and reference it in the manifest

---

## 5. Data Provider & API Integration

- The Data Provider is a React-Admin abstraction that connects the UI to the backend API.
- Supports REST, GraphQL, and WebSocket; for AICO, use REST/WebSocket as needed.
- Handles authentication tokens, error handling, and data transformation.

**Example:**
```js
import { fetchUtils } from 'react-admin';
const apiUrl = '/admin';
const httpClient = (url, options = {}) => {
  // Add auth headers, handle errors, etc.
  return fetchUtils.fetchJson(url, options);
};
export const dataProvider = {
  getList: (resource, params) => httpClient(`${apiUrl}/${resource}`),
  // ... other CRUD methods
};
```

---

## 6. Authentication & RBAC

- Authentication is enforced via the API Gateway (OAuth2, JWT, or session-based)
- The UI uses React-Admin’s authProvider to check login status and permissions
- RBAC (role-based access control) determines which panels/modules are visible and what actions are allowed

**Example:**
```js
const authProvider = {
  login: ({ username, password }) => {/* ... */},
  logout: () => {/* ... */},
  checkAuth: () => {/* ... */},
  getPermissions: () => {/* ... */},
};
```

---

## 7. Extensibility Patterns

- **Generic Panels:** Most modules use manifest-driven generic panels (forms, tables, dashboards)
- **Custom Panels:** Advanced modules can provide a custom React component (micro-frontend) loaded dynamically
- **Plugin Registration:** New modules appear instantly in the UI when their manifest is available
- **Theming:** React-Admin supports custom themes for consistent branding

---

## 8. Best Practices & Gotchas

- **Keep manifests DRY:** Use shared schema/types for manifest definitions
- **Error handling:** Ensure backend APIs return clear errors; surface them in the UI
- **Security:** Never expose admin UI outside localhost without explicit configuration and HTTPS
- **Testing:** Use React-Admin’s built-in testing utilities for panels/components
- **Documentation:** Reference the Admin Module Developer Guideline (file does not exist) for hands-on steps

---

## 9. References
- [React-Admin Documentation](https://marmelab.com/react-admin/)
- [Admin UI Plugin Architecture](admin_ui.md)
- [Admin Domain & Modules](admin.md)

---

This document provides the architectural foundation for developing admin modules for AICO. For step-by-step coding instructions, see the Admin Module Developer Guideline.
- [Open edX Frontend Plugin Framework](https://github.com/openedx/frontend-plugin-framework)
- [Kubernetes Dashboard]
- [Grafana Plugin System]
