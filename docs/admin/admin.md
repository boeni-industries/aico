# Administration Domain

AICO's **Administration** domain encompasses all backend-only, developer and operator-facing systems required for secure, reliable, and maintainable operation of the platform. These modules are distinct from user-facing settings in the frontend: they focus on system configuration, health, diagnostics, policy enforcement, and privileged operations.

---

## Web-Based Admin Interface

All administrative functions are exposed via a single, unified, secure **admin web interface** (the "master admin UI") served locally by the backend. This interface provides a central access point for all admin modules, accessible only on the local machine (e.g., `http://localhost:PORT/admin`).

- **Single UI, Many Modules:** Each admin module exposes its APIs (and optionally UI manifests) to the master admin UI, which is implemented using **React** and **React-Admin**. The UI dynamically discovers and renders module panels/plugins in a consistent dashboard, leveraging React-Admin's extensibility and industry-standard patterns.
- **No Separate UIs:** Individual modules do not provide their own standalone UIs; all UI is integrated into the master admin dashboard for consistency, security, and maintainability.
- **Extensible and DRY:** Adding a new admin module only requires exposing its API/manifest—no UI wiring or duplication needed.
- **Best Practice:** This approach is modular, extensible, DRY, and KISS, following industry standards for scalable admin systems.
- **See [admin_ui.md] for details on UI plugin/manifest architecture.**

---

### Relationship to API Gateway

The Admin Web Interface and all admin API endpoints are securely served through the **API Gateway**:
- **Single Entry Point:** The API Gateway is the only access point for admin endpoints (UI and API), ensuring consistent security and routing.
- **Authentication & Authorization:** The gateway enforces strong authentication and role-based access control for all admin functions.
- **Local-Only by Default:** The gateway restricts admin endpoints to local access unless explicitly configured otherwise.
- **Routing:** Admin API requests from the web UI are routed by the gateway to the appropriate backend admin modules (via message bus or internal API).
- **Separation from User-Facing APIs:** Admin endpoints are strictly separated from user-facing APIs and are never exposed to regular users.

This design ensures that all administrative actions are secure, auditable, and properly isolated from user-facing functionality.

**Key Characteristics:**
- **Unified Dashboard:** All admin modules (configuration, logs, plugins, updates, etc.) are accessible from a single web UI.
- **Local-Only Access:** By default, the admin web interface is only accessible from the machine running the backend, ensuring privacy and security.
- **Strong Authentication:** All admin actions require authentication; role-based access control is enforced.
- **Modular & Extensible:** New admin modules automatically appear in the web UI as they are added to the backend.
- **Real-Time & Secure:** The interface communicates with backend modules via secure internal APIs and/or the message bus.
- **No User-Facing Exposure:** The admin web interface is strictly for developers/operators, never exposed to regular users.

**Example Features:**
- System configuration editor
- Log viewing and search
- Resource and health dashboards
- Plugin management (install, disable, update)
- Update controls
- Audit/compliance log access
- Backup/restore controls
- Developer/debug tools
- Policy and permission management
- Notification and alert center

---

## Purpose
- Provide robust operational control and insight for developers, operators, and advanced maintainers
- Ensure system reliability, security, and compliance
- Enable safe extensibility and controlled evolution of the platform
- Support privacy and local-first principles by keeping all admin operations local and auditable

## Scope and Principles
- **Backend-only:** No direct user-facing UI; all admin functions are exposed via secure admin interfaces, CLI, or internal dashboards
- **Separation of Concerns:** User settings are handled in the frontend; admin/dev functions reside in backend modules
- **Security:** Strict access control, audit logging, and privilege separation for all admin actions
- **Message-Driven:** Admin modules communicate via the same ZeroMQ message bus as other backend modules, with dedicated admin topics
- **Extensible:** New admin modules can be added as the system evolves

## Administrative Modules

### 1. System Config Manager
- Loads and validates system-wide configuration (paths, ports, feature flags, etc.)
- Enforces schema and policy compliance

### 2. Instrumentation & Logging
- Aggregates logs from all backend modules
- Supports log rotation, export, and diagnostics
- Central point for system health events

### 3. Resource Monitor (Admin)
- Provides health/status dashboard for CPU, memory, disk, battery, and system load
- Issues alerts for resource exhaustion or anomalies
- Exposes health check endpoints for orchestration

### 4. Plugin Admin
- Enables privileged management of plugins: install, disable, update
- Controls sandbox and permission policies for plugins

### 5. Update Admin
- Manages backend and module updates (manual/automatic)
- Coordinates with frontend for seamless upgrades

### 6. Audit & Compliance (Admin)
- Provides privileged access to system and compliance logs
- Maintains compliance dashboard for data access and policy adherence

### 7. Backup & Restore
- Manages system/data snapshots and restores
- Enables disaster recovery and migration

### 8. Developer Tools
- Hot-reload, debug, and profiling support for backend modules
- Safe developer mode toggling

### 9. Admin Access Control
- Handles authentication and privilege management for all admin actions
- Supports role-based access and secure credential storage

### 10. Notification Center
- Centralized alerting for critical system events, errors, and updates
- Admin messaging and escalation

### 11. Policy Manager
- Enforces resource limits, plugin permissions, and operational policies
- Configurable for different deployment scenarios

## Integration Points
- All modules communicate via the message bus (ZeroMQ), using dedicated admin topics (e.g., `admin.status.*`, `admin.config.*`, `admin.audit.*`)
- Admin actions are auditable and subject to privilege checks
- Admin modules can be extended or replaced independently

## Security & Privacy Considerations
- All admin interfaces require strong authentication
- All actions are logged for audit and compliance
- No admin data or operations are exposed to the user-facing frontend
- Local-first: No admin data leaves the device unless explicitly exported by a privileged operator

---

This domain ensures that AICO remains secure, maintainable, and extensible as it evolves, while protecting user privacy and upholding system integrity.
