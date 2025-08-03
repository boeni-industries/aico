# Admin UI Architecture

AICO's admin UI is implemented as a **single, unified dashboard** ("master admin UI") built with **React** and the open-source **React-Admin** framework. This approach integrates all backend administrative modules into a consistent, extensible web interface, leveraging React-Admin's mature plugin architecture, rapid development capabilities, and strong open-source community support.

## Principles
- **DRY & KISS:** No duplicated UI logic, minimal boilerplate, and simple extension pattern
- **Single Entry Point:** All admin functions are accessed through one secure dashboard (e.g., `/admin`)
- **Modular & Extensible:** New admin modules appear as panels/plugins automatically
- **Consistent UX:** Navigation, authentication, and layout are unified across all modules
- **Backend-driven:** Each admin module exposes its API and (optionally) a UI manifest/descriptor for dynamic discovery

## How It Works
1. **Module API/Manifest:** Each backend admin module exposes:
   - A REST/WebSocket API for its admin functions
   - An optional UI manifest (JSON) describing its panel(s): name, icon, routes, fields, etc.
2. **Discovery:** The master admin UI queries a central endpoint (e.g., `/admin/modules`) to discover all available modules and their manifests.
3. **Rendering:**
   - For simple modules, the UI renders generic resource panels (forms, tables, dashboards) based on the manifest and API schema
   - For advanced modules, a module may provide a micro-frontend/component bundle, loaded dynamically by the master UI
4. **Navigation:** The dashboard automatically creates navigation tabs/cards for each module
5. **Security:** All access is authenticated and authorized via the API Gateway; admin UI is local-only by default
6. **Extensibility:** Adding a new module is as simple as exposing its API and manifest; no UI code changes required in the master UI

## Example Manifest (Simplified)
```json
{
  "name": "Resource Monitor",
  "icon": "cpu",
  "route": "/admin/resource-monitor",
  "type": "dashboard",
  "endpoints": {
    "status": "/admin/resource-monitor/status"
  },
  "fields": [
    {"label": "CPU Usage", "type": "gauge", "source": "status.cpu"},
    {"label": "Memory Usage", "type": "gauge", "source": "status.memory"}
  ]
}
```

## Benefits
- **DRY:** No duplicated UI logic; modules describe their UI once
- **KISS:** Minimal configuration; the UI adapts automatically
- **Extensible:** New modules appear instantly
- **Consistent:** Users get a unified, predictable experience
- **Secure:** All access via API Gateway, RBAC, and local-only by default

## References
- Kubernetes Dashboard
- Grafana Plugin System
- Home Assistant Supervisor
- VS Code Extension Host
